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
                maxHoleSize [int]        in samples
                samplingPerio [float]    resampling in seconds
        :param windowLen:
        """
        self.samplePeriod = samplePeriod
        self.stepSize = stepSize
        self.maxHoleSize = maxHoleSize
        self.samplePointsPerWindow = samplePointsPerWindow
        self.debug = debug
        self.windowTime = (samplePointsPerWindow-1)*samplePeriod

        self.times = np.asarray([],dtype=np.float64)
        self.values = np.asarray([], dtype=np.float64)
        self.currentStartTime = 0





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
                if self.maxHoleSize:
                    holes = (timesW[self.maxHoleSize:]-timesW[0:-self.maxHoleSize])==0
                    if np.any(holes):
                        #this window has a hole, step forward
                        #find the last index and advance
                        #print("hole")
                        lastZero = np.max(np.argwhere(holes))+self.maxHoleSize
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



