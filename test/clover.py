import zmq
import random
import sys
import time

class Clover:
    def __init__(self,kind="pub",isServer=True,port=5555,isSource=True):
        self.running = True

        self.port = port
        self.context = zmq.Context()
        if kind == "pub":
            self.socket = self.context.socket(zmq.PUB)
        elif kind == "sub":
            self.socket = self.context.socket(zmq.SUB)
        else:
            print("don't know the type")
            return
        if isServer:
            self.socket.bind("tcp://*:%s" % self.port)
        else:
            self.socket.connect("tcp://localhost:%s" % self.port)

        if isSource:
            self.send()
        else:
            self.receive()

    def send(self):
        counter = 1
        while True:
            counter +=1
            msg = "hallo"+str(counter)
            print("sending " +msg)
            msg = msg.encode("utf-8")
            self.socket.send(msg)
            time.sleep(0.1)

    def receive(self):
        self.socket.setsockopt(zmq.SUBSCRIBE, "h".encode("utf-8"))

        # Process 5 updates
        while self.running:
            string = self.socket.recv()
            print ("got "+str(string))



#call like "pub" true 5555 true
if len(sys.argv) > 1:
    kind = "pub"
    isServer = True
    port =5555
    isSource = True
    for elem in sys.argv[1:]:
        print(elem)
        if elem=="sub":
            kind = "sub"
        if elem =="client":
            isServer = False
        if elem == "sink":
            isSource = False
        if type(elem) is int:
            port = elem

    c=Clover(kind,isServer,port,isSource)
    typ = sys.argv[1]
    isServer = sys.argv[2]
    port = sys.argv[3]
    isSource = sys.argv[4]

print(type,isServer,port,isSource)

