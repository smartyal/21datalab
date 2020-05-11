import datetime

class Timer:
    def __init__(self):
        self.start()
        pass
    def start(self,totalCount = None):
        self.startTime = datetime.datetime.now()
        self.totalCount = totalCount
    def stop(self,text=""):
        now = datetime.datetime.now()
        delta = (now-self.startTime).total_seconds()
        print(text+", elapsed time:",delta)
        self.startTime = datetime.datetime.now()
    def remaining(self, nowCount, totalCount=None):
        if totalCount:
            self.totalCount=totalCount
        if nowCount!= 0:
            now = datetime.datetime.now()
            delta = (now - self.startTime).total_seconds()
            remainingSecs = (float(self.totalCount)/float(nowCount))*delta-delta
            print(str(nowCount)+"/"+str(self.totalCount)+": remaining sec %2.2f"%remainingSecs)

class Profiling:
    def __init__(self,name):
        self.start(name)

    def start(self,rename = None):
        self.result = []
        if rename:
            self.name= rename
        now = datetime.datetime.now()
        self.initTime = now
        self.startTime =now
    def lap(self,label):
        now = datetime.datetime.now()
        delta = (now - self.startTime).total_seconds()
        total = (now-self.initTime).total_seconds()
        self.result.append({"label":label,"delta":delta,"total":total})
        self.startTime=now
    def __repr__(self):
        self.lap("end")
        s="Time Profiling -"+self.name+" :"

        for l in self.result:
            s=s+f" {l['label']}: {l['delta']}"
        s=s+f"total: {l['total']}"
        return s