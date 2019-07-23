import sseclient
import threading


class SSEReceiver():
    def __init__(self,url,callback = None, logger = None):
        """
            Args:
                url [string] the full url like 'http://127.0.0.1:6001/event/stream
                callback: the function to be called on event, it should take one argument (the event
                logger: python logger object
        """
        self.url = url
        self.callback = callback
        self.logger = logger

    def thread_function(self):
        self.msgs = sseclient.SSEClient(self.url)
        while self.running:
            try:
                for nextEvent in self.msgs:
                #nextEvent = next(self.msgs)
                    if not self.running:
                        #the thread was cancelled in the meantime
                        break
                    if self.callback:
                        outEvent = {"event":nextEvent.event,"data":nextEvent.data,"id":nextEvent.id}
                        self.callback(outEvent)
            except Exception as ex:
                if self.logger:
                    self.logger.error(f"except {ex}")
                else:
                    print(f"except {ex}")
        if self.logger:
            self.logger.warning("SSE Reciever Thread finishee")
        else:
            print("SSE Receiver thread finished")

    def start(self):
        """
            call this to start the receiver thread
        """
        self.running = True
        self.thread = threading.Thread(target = self.thread_function)
        self.thread.start()





    def stop(self):
        """
            call this to stop the receiver, it is unfortunately only stopped AFTER the the next event (which will of 
            course not be executed)
        """
        self.running = False
