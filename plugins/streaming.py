#21datalabplugin


from abc import ABC, abstractmethod
import utils
from utils import Profiling
from system import __functioncontrolfolder
import dates
import numpy
import numpy as np
import copy

class Interface(ABC):

    @abstractmethod
    def flush(self,data = None):
        pass

    @abstractmethod
    def feed(self, data=None):
        pass

    @abstractmethod
    def reset(self, data=None):
        pass


PipeLineHead={
    "name":"PipelineHead",
    "type":"object",
    "class": "streaming.PipelineHead",
    "children":[
        {"name": "enabled", "type":"const","value":True},
        {"name": "processors","type":"referencer"},
        {"name": "variables","type":"referencer"},       #ref to the variables and eventseries (only one) for the renaming of incoming descriptors
        __functioncontrolfolder
    ]
}

Splitter={
    "name":"Splitter",
    "type":"object",
    "class": "streaming.SplitterClass",
    "children":[
        {"name": "enabled", "type":"const","value":True},
        {"name": "threaded", "type":"const","value":True},      #set this true to execute the pipes in the threading pipeline, false to execute them sync from here
        {"name": "pipelines","type":"referencer"},
        __functioncontrolfolder
    ]
}


class PipelineHead():

    def __init__(self,functionNode):
        self.logger = functionNode.get_logger()
        self.logger.debug("init ThresholdScorer()")
        self.functionNode = functionNode
        self.model = functionNode.get_model()
        self.enabledNode = functionNode.get_child("enabled")
        #self.reset() #this is executed at startup


    def feed(self,data):
        """
            this is the interface function to the REST call to insert into the stream, so we convert the data as needed
            and send it on

        """
        p=Profiling("feed")

        if not self.enabledNode.get_value():
            return True

        for blob in data:
            #first, we convert all names to ids
            if blob["type"] in ["timeseries","eventseries"]:
                if blob["type"] == "eventseries":
                    #print(f"eventseries coming {blob}")
                    pass
                blob["data"] = self.__convert_to_ids__(blob["data"])
            p.lap("#")
            blob = self.pipeline.feed(blob)
        #print(p)
        return True



    def __convert_to_ids__(self,blob):
        """
            convert incoming descriptors to ids
            convert times to epoch
            support the __events name for a default eventnode
        """
        newBlob = {}
        for k, v in blob.items():
            if k == "__time":
                if type(v) is not list:
                    v = [v]
                if type(v[0]) is str:
                    v = [dates.date2secs(t) for t in v] # convert to epoch
                newBlob[k] = numpy.asarray(v)
            else:
                # try to convert
                if k in self.varNameLookup:
                    id = self.varNameLookup[k].get_id()
                    if type(v) is not list:
                        v=[v]
                    newBlob[id]=numpy.asarray(v)
                else:
                    self.logger.error(f"__convert_to_ids__: cant find {k}")
        return newBlob

    def reset(self,data=None):
        #create look up table for variables
        leaves = self.functionNode.get_child("variables").get_leaves()
        self.varNameLookup = {}
        for node in leaves:
            typ = node.get_type()
            if typ == "timeseries":
                self.varNameLookup[node.get_name()] = node
            elif typ == "eventseries":
                self.varNameLookup[node.get_name()] = node
                self.varNameLookup["__events"] = node # this is the default entry for incoming events
        varBrowsePathLookup = {node.get_browse_path():node for node in leaves if node.get_type() in ["timeseries","eventseries"]}
        self.varNameLookup.update(varBrowsePathLookup)

        varIdLookup = {node.get_id():node for node in leaves if node.get_type() in ["timeseries","eventseries"]}
        self.varNameLookup.update(varIdLookup)


        #build the pipeline
        self.pipeline = Pipeline(self.functionNode.get_child("processors").get_targets())
        self.pipeline.reset() # reset all processors


        return True


class SplitterClass():
    def __init__(self, functionNode):
        self.logger = functionNode.get_logger()
        self.logger.debug("init Splitter")
        self.functionNode = functionNode
        self.model = functionNode.get_model()
        self.enabledNode = functionNode.get_child("enabled")


    def reset(self,data=None):
        #build the pipeline
        self.threaded = self.functionNode.get_child("threaded").get_value()
        self.pipelineNodes = self.functionNode.get_child("pipelines").get_targets()
        for pipeline in self.pipelineNodes:
            pipeline.get_object().reset()

    def feed(self,data=None):
        if not self.enabledNode.get_value():
            return None

        for pipeline in self.pipelineNodes:
            if self.threaded:
                self.model.execute_object_function(pipeline.get_id(),"feed",copy.deepcopy(data))
            else:
                pipeline.get_object().feed(data)


class Pipeline():

    def __init__(self,processors=[]):
        self.processors=processors # these are Nodes()!

    def reset(self,data=None):
        for p in self.processors:
            p.get_object().reset(data)

    def feed(self,data):
        pro = utils.Profiling("pipee")
        for p in self.processors:
            if not type(data) is list:
                data = [data]
            returnData = []
            for blob in data:
                result = p.get_object().feed(blob)
                if type(result) is list:
                    returnData.extend(result)
                else:
                    returnData.append(result)
                pro.lap(p.get_name())
            data = returnData
        print(pro)
        return data

    def flush(self,data):
        for p in self.processors:
            data = p.get_object().flush()
        return data




class Windowing:

    def __init__(self,samplePeriod,stepSize, maxHoleSize, samplePointsPerWindow, debug = False):
        """
            Args:
                windowSize  [int]        the windowLen in samples
                stepSize    [int]        advance to the next window in samples
                maxHoleSize [int]        in seconds
                samplingPerio [float]    resampling in seconds
        :param windowLen:
        """
        self.samplePeriod = samplePeriod
        self.stepSize = stepSize
        self.maxHoleSizeSeconds = maxHoleSize
        self.samplePointsPerWindow = samplePointsPerWindow
        self._update_max_hole_size()
        self.debug = debug
        self.windowTime = (samplePointsPerWindow-1)*samplePeriod

        self.times = np.asarray([],dtype=np.float64)
        self.values = np.asarray([], dtype=np.float64)
        self.currentStartTime = 0


    def _update_max_hole_size(self):
        self.maxHoleSamples = int(float(self.maxHoleSizeSeconds)/float(self.samplePeriod))
        if (self.maxHoleSamples > self.samplePointsPerWindow): self.maxHoleSamples = self.samplePointsPerWindow - 1



    def __append(self,times,values):
        if self.times.size==0:
            self.currentStartTime = times[0]
        self.times = np.append(self.times,times)
        self.values = np.append(self.values,values)

    def insert(self,times, values):
        """
            insert data in the internal cache
        """
        self.__append(times,values)

    def get_all(self,times,values):
        return list(self.iterate(times,values))

    def log(self,msg):
        if self.debug:
            print(msg)

    def __sample_times(self,start,stop,step):
        """
            creating an array of equidistant points including the stop value i
            Args:
                start: first value in the array
                stop: last value in the array (including)
                step: step size
        """
        c = np.arange(start, stop, step)
        if c.size == 0:
            c=np.asarray([start])
        if c[-1]+step<=stop:            # can including the last ?
            c=np.append(c,c[-1]+step)   # unfortunately, this requires realloc of the array memory
        return c

    def iterate(self,times=None,values=None):
        """
            we assume :
             - time-ordered incoming data, so we can simply append
        """

        # first, update the internal cache memory
        if type(times) is not type(None):
            self.__append(times,values)

        #first downsample the current data, so create the target time points
        samplingTimes = self.__sample_times(self.currentStartTime,self.times[-1],self.samplePeriod)
        samplingIndices = np.searchsorted(self.times,samplingTimes)
        #print(f"no sampingIndices {samplingIndices}, sample times {samplingTimes}")

        #now downsample
        values = self.values[samplingIndices]
        times = self.times[samplingIndices]

        start = 0 # the startindex of the window
        while True:
            if values.size-start >= self.samplePointsPerWindow:
                timesW = times[start:start+self.samplePointsPerWindow]
                if self.maxHoleSamples:
                    # find holes by subtracting times and shifted times, if the diff is zero they are the same
                    # (instead, we could have taken the samplingIndices and look into them)
                    # so the original data did not have any "new" points there, the timeseries class just filled them
                    # with the forward fill method
                    # attention: this does not easily work for UPSAMPLING, as we will have many samples in a row from the same original time
                    # as we forward fill the upsampling with the one original value
                    holes = (timesW[self.maxHoleSamples:]-timesW[0:-self.maxHoleSamples])==0
                    if np.any(holes):
                        #this window has a hole, step forward
                        #find the last index and advance
                        #print("hole")
                        lastZero = np.max(np.argwhere(holes))+self.maxHoleSamples
                        start = start+lastZero
                        continue
                yield([samplingTimes[start:start+self.samplePointsPerWindow],values[start:start+self.samplePointsPerWindow]])
                start=start+self.stepSize
            else:
                break
        # complete all yields, now shift the data
        # the current start position is the position which did not work, so we take that for the next
        if start != 0: #if start is zero we did not create any window
            originalIndex = samplingIndices[start]
            self.times = self.times[originalIndex:]
            self.values = self.values[originalIndex:]
            self.currentStartTime=samplingTimes[1]
        #print(f"now shift by {start}, the original was {originalIndex}")



##############################################################################################################################################################################################################
# TEST AREA
##############################################################################################################################################################################################################
if __name__ == "__main__":


    def test1():
        #(self, samplePeriod, stepSize, maxHoleSize, samplePointsPerWindow, debug = False):
        p = Windowing(samplePeriod = 2, stepSize = 1,maxHoleSize=5,samplePointsPerWindow=10)
        v = np.arange(100)
        p.insert(v,v)
        for w in p.iterate():
            print(w)



    def test2():
        #a longer window with a hole
        p = Windowing(samplePeriod=0.5, stepSize=1, maxHoleSize=2, samplePointsPerWindow=5)
        v = np.append(np.arange(0,100),np.arange(130,200))
        for w in p.iterate(v,v):
            print(w)


    def test3():
        #check the precise shift
        p = Windowing(samplePeriod=2, stepSize=1, maxHoleSize=1, samplePointsPerWindow=6)
        v=np.arange(51)
        for w in p.iterate(v,v):
            print(w)

        v = np.arange(55,100)
        for w in p.iterate(v,v):
            print(w)

    def test4():
        #streaming each points
        p = Windowing(samplePeriod=2, stepSize=1, maxHoleSize=1, samplePointsPerWindow=6)
        v=np.arange(50)
        for i in v:
            print(i)
            for w in p.iterate([i],[i]):
                print(w)

    def test5():
        #test resampling alignment
        p = Windowing(samplePeriod=2, stepSize=1, maxHoleSize=1, samplePointsPerWindow=10)
        v=np.arange(10,40,1.42)
        for w in p.iterate(v,v):
            print(list(w[0]),list(w[1]))

        #same in singe
        print("same in single streaming")
        p = Windowing(samplePeriod=2, stepSize=1, maxHoleSize=1, samplePointsPerWindow=10)
        v=np.arange(10,40,1.42)
        for i in v:
            for w in p.iterate([i],[i]):
                print(list(w[0]), list(w[1]))


    def test_up1():
        #upsampling with holes
        p = Windowing(samplePeriod=0.1, stepSize=1, maxHoleSize=2, samplePointsPerWindow=10)
        v = np.append(np.arange(0,10),np.arange(13,20))
        for w in p.iterate(v,v):
            print(w)



    def resampling_test():

        t = np.arange(101)
        re1 = np.linspace(0,t[-1],11)
        re2 = np.linspace(0, t[-1], 200)
        i1 = np.searchsorted(t,re1)
        i2 = np.searchsorted(t, re2)
        print(t[i1],t[i2])


    def timing_test():
        #typical application
        # 10sek sampling over one year = 3Mio Points
        # window i 1 hour = 360
        # we step by 5 min = 300 sec = 3 step
        # downsamping faktor 10  = 100 sec
        stepSize = 5
        samplePeriod = 100
        p = Windowing(samplePeriod=samplePeriod, stepSize=stepSize, maxHoleSize=3, samplePointsPerWindow=20)

        v = np.arange(0,30000*1000,10)
        print(f"expected no window {v.size/(stepSize*samplePeriod)}")
        start = time.time()
        count = 0
        for i in p.iterate(v,v):
            count = count+1
            if count %1000 == 0:
                print("count:",count, "current window len",i[0].size,i[0][0],"...",i[1][-1])
            pass
        total = time.time()-start
        #res = list(p.iterate(v,v))
        print(f"took {total} no windows:{count}, per yield = {total/count*1000}ms")

    def check_timings():
        total = 3*1000*1000
        a=np.arange(0,total,0.98)

        start = time.time()
        diff = np.diff(a)
        where = a > 10
        locs = np.argwhere(where)

        print(f"diff and where on {a.size} = {time.time()-start}")

        times = np.linspace(0,total,int(total/13))
        times = times[:-1]
        start = time.time()
        indices = np.searchsorted(a,times)
        re = a[indices]
        print(f"timing resample {a.size} -> {re.size} = {time.time()-start}")


    #main
    #timing_test()
    #check_timings()
    #resampling_test()
    #test1()
    test2()
    #test3()
    #test4()
    #test5()
    #lin_space_test()
    #test_up1()
