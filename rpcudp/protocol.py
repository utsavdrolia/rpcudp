import umsgpack
import random
import hashlib
from base64 import b64encode

from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet import defer
from twisted.python import log

from rpcudp.exceptions import MalformedMessage


class RPCProtocol(protocol.DatagramProtocol):
    noisy = True
    REQ = 0x00
    RESP = 0x01
    def __init__(self, waitTimeout=5):
        """
        @param waitTimeout: Consider it a connection failure if no response
        within this time window.
        """
        self._waitTimeout = waitTimeout
        self._outstanding = {}

    def datagramReceived(self, datagram, address):
        if self.noisy:
            log.msg("received datagram from %s" % repr(address))
        if len(datagram) < 22:
            log.msg("received datagram too small from %s, ignoring" % repr(address))
            return

        [mtype, msg_id, data] = umsgpack.unpackb(datagram)
        if mtype == self.REQ:
            self._acceptRequest(msg_id, data, address)
        elif mtype == self.RESP:
            self._acceptResponse(msg_id, data, address)
        else:
            # otherwise, don't know the format, don't do anything
            log.msg("Received unknown message from %s, ignoring" % repr(address))

    def _acceptResponse(self, msgID, data, address):
        msgargs = (b64encode(msgID), address)
        if msgID not in self._outstanding:
            log.err("received unknown message %s from %s; ignoring" % msgargs)
            return
        if self.noisy:
            log.msg("received response for message id %s from %s" % msgargs)
        d, timeout = self._outstanding[msgID]
        timeout.cancel()
        d.callback((True, data))
        del self._outstanding[msgID]

    def _acceptRequest(self, msgID, data, address):
        if not isinstance(data, list) or len(data) != 2:
            raise MalformedMessage("Could not read packet: %s" % data)
        funcname, args = data
        f = getattr(self, "rpc_%s" % funcname, None)
        if f is None or not callable(f):
            msgargs = (self.__class__.__name__, funcname)
            log.err("%s has no callable method rpc_%s; ignoring request" % msgargs)
            return
        d = defer.maybeDeferred(f, address, *args)
        d.addCallback(self._sendResponse, msgID, address)

    def _sendResponse(self, response, msgID, address):
        if self.noisy:
            log.msg("sending response for msg id %s to %s" % (b64encode(msgID), address))
        txdata = umsgpack.packb([self.RESP, msgID, response])
        self.transport.write(txdata, address)

    def _timeout(self, msgID):
        args = (b64encode(msgID), self._waitTimeout)
        log.err("Did not received reply for msg id %s within %i seconds" % args)
        self._outstanding[msgID][0].callback((False, None))
        del self._outstanding[msgID]

    def __getattr__(self, name):
        if name.startswith("_") or name.startswith("rpc_"):
            return object.__getattr__(self, name)

        try:
            return object.__getattr__(self, name)
        except AttributeError:
            log.msg("Attrbute Error:{}".format(name))
            pass

        def func(address, *args):
            if self.noisy:
                log.msg("Creating RPC to send:{}".format(name))
            msgID = hashlib.sha1(str(random.getrandbits(255)).encode()).digest()
            if self.noisy:
                log.msg("RPC MsgID:{}".format(msgID))
            data = umsgpack.packb([self.REQ, msgID, [name, args]])
            if self.noisy:
                log.msg("RPC Data:{}".format(data))
            if len(data) > 8192:
                msg = "Total length of function name and arguments cannot exceed 8K"
                log.err(msg)
            if self.noisy:
                log.msg("calling remote function {} on {} (msgid {})".format(name, address, b64encode(msgID)))

            self.transport.write(data, address)
            if self.noisy:
                log.msg("Sending data:{}".format(data))
            d = defer.Deferred()
            timeout = reactor.callLater(self._waitTimeout, self._timeout, msgID)
            self._outstanding[msgID] = (d, timeout)
            return d
        if self.noisy:
            log.msg("Created RPC. Sent data. Returning:{}".format(func))
        return func
