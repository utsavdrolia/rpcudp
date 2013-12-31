# RPCUDP
### Python lib to support [RPC](http://en.wikipedia.org/wiki/Remote_procedure_call) over [UDP](http://en.wikipedia.org/wiki/User_Datagram_Protocol).

RPC over UDP may seem like a silly idea, but things like the [DHT](http://en.wikipedia.org/wiki/Distributed_hash_table) [Kademlia](http://en.wikipedia.org/wiki/Kademlia) require it.  This project is specifically designed for asynchronous [Python Twisted](http://twistedmatrix.com) code to accept and send remote proceedure calls.

Because of the use of UDP, you will not always know whether or not a procedure call was successfully received.  This isn't considered an exception state in the library, though you will know if a response isn't received by the server in a configurable amount of time.

## Installation

```
easy_install rpcudp
```

## Usage
*This assumes you have a working familiarity with Twisted.*

First, let's make a server that accepts a remote procedure call and spin it up.

```python
from rpcudp.protocol import RPCProtocol
from twisted.internet import reactor

class RPCServer(RPCProtocol):
    def rpc_sayhi(self, name):
        # This could return a Deferred as well
        return "Hello %s" % name

# start a server on UDP port 1234
server = RPCServer(1234)
reactor.run()
```

Now, let's make a client.  Note that we do need to specify a port for the client as well, since it needs to listen for responses to RPC calls on a UDP port.

```python
from rpcudp.protocol import RPCProtocol
from twisted.internet import reactor

class RPCClient(RPCProtocol):
    def handleResult(self, result):
    	# result will be a tuple - first arg is a boolean indicating
        # whether a response was received, and the second argument is
	# the response if one was received.
        if result[0]:
            print "Success! %s" % result[1]
        else:
            print "Response not received."

client = RPCClient(5678)
client.sayhi(('127.0.0.1', 1234), "Snake Plissken").addCallback(client.handleResult)
reactor.run()
```

You can run this example in the example.py file in the root folder.