#21datalabplugin

from system import __functioncontrolfolder
import streaming
import numpy
from utils import Profiling
import streaming
import json
import dates




ThresholdScorer={
    "name":"ThresholdScorer",
    "type":"object",
    "class":"streamthreshold.StreamThresholdScorerClass",
    "children": [
        __functioncontrolfolder,
        {"name":"output","type":"folder","children":[{"name":"scores","type":"folder"}]},
        {"name":"thresholds","type":"referencer"},
        {"name":"variables","type":"referencer"},
        {"name":"scoreAll","type":"function","children":[__functioncontrolfolder]}
    ]
}

ThresholdPipeline={
    "name":"ThresholdPipeline",
    "type":"object",
    "class": "streamthreshold.ThresholdPipelineClass",
    "children":[
        {"name": "processors","type":"referencer"},
        {"name":"variables","type":"referencer"},       #ref to the variables and eventseries (only one) for the renaming of incoming descriptors
        __functioncontrolfolder
    ]
}

Writer = {
    "name": "writer",
    "type": "object",
    "class": "streamthreshold.StreamWriterClass",
    "children": [
        {"name":"enabled","type":"const","value":True},
        __functioncontrolfolder
    ]
}

StreamLogger = {
    "name":"Logger",
    "type":"object",
    "class": "streamthreshold.StreamLoggerClass",
    "children": [
        __functioncontrolfolder
    ]
}


def write_series(node,data,appendOnly=True):
    if node.get_type()=="eventseries":
        #write events to an eventseries
        pass
    if node.get_type()=="timeseries":
        """
            #write timeseries values to the time series table, format must be
            {
                "23455234": [1.5,1.6,1.7]m
                "2q354342345": [2,3,4]
                "__time" :[100001,100002,100003]
        }
        """
        #so this has to be id:values


class ThresholdPipelineClass():

    def __init__(self,functionNode):
        self.logger = functionNode.get_logger()
        self.logger.debug("init ThresholdScorer()")
        self.functionNode = functionNode
        self.model = functionNode.get_model()
        #self.reset() #this is executed at startup


    def feed(self,data):
        """
            this is the interface function to the REST call to insert into the stream, so we convert the data as needed
            and send it on

        """
        p=Profiling("feed")
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
        self.pipeline = streaming.Pipeline(self.functionNode.get_child("processors").get_targets())
        self.pipeline.reset() # reset all processors


        return True



class StreamThresholdScorerClass(streaming.Interface):
    def __init__(self,objectNode):
        self.objectNode = objectNode
        self.model = objectNode.get_model()
        self.logger = objectNode.get_logger()
        self.scoreNodesFolder = objectNode.get_child("output").get_child("scores")
        #self.reset()

    def out_of_limits(self,values, mini, maxi):
        """
            returns a true/fals for out of limits, able to handle nans/infs
        """

        work = numpy.copy(values)
        workNan = ~numpy.isfinite(work)
        work[workNan] = -numpy.inf  # so we don't get a toosmall at nans
        tooSmall = work < mini
        work[workNan] = +numpy.inf
        tooBig = work > maxi
        return tooSmall | tooBig  # numpy.logical_or( values < entry['min'], values > entry['max'] )

    def feed(self,blob):
        """
            incoming data format
            "type":"timeseries",
            "data":{
                "__time":[120,130,140,150,160,170,....]

                "var1":[20,30,40,50,60,70,......]       //for the naming we allow path, id and find_node style
                "var2":[2,3,4,5,6,....]
                },
                "__states":{                                    /wird nicht von aussen gesendet
                    "euv":[True,False,True,.....]
                    "evacuating":[False,False,False,....]
                }

            }
        :param data:
        :return:
        """
        if blob["type"]=="timeseries":
            times = blob["data"]["__time"]
            length = len(times)
            if "__states" in blob["data"]:
                states = blob["data"]["__states"]
            else:
                states = {}

            #calculate the global area: the global area is the area where there is no special state
            globalState = numpy.full(len(times),True)
            for state,mask in states.items():
                globalState[mask]=False # delete the globalState where there are local states
            states["__global"] = globalState

            scoresBlob={}  #the entries to be added in the blob
            for id,values in blob["data"].items():
                if id[0:2] == "__":
                    continue
                #now check if there are thresholds entries for this var
                if id in self.thresholds:
                    scoreMask = numpy.full(length,False)
                    for tag,limits in self.thresholds[id].items():
                        if tag in states:
                            outOfLimit = self.out_of_limits(values,limits["min"],limits["max"])
                            scoreMask = scoreMask | (outOfLimit & states[tag]) # it must be out of limit and inside the state, then it's an out of limit for the score
                    #now we have the score for the variable, put it in the blob
                    score = numpy.full(length,numpy.nan)
                    score[scoreMask]=values[scoreMask]

                    scoreNodeId = self.scoreNodes[id] #lookup the score node
                    #self.model.time_series_insert(id, values=score, times=times, allowDuplicates=True)
                    scoresBlob[scoreNodeId] = score
                    #print(f"SCORE {id}: {list(scoreMask)}")
            blob["data"].update(scoresBlob)

        return blob

    def flush(self,data=None):
        return data

    def reset(self,data=None):
        # create lookup for the thresholds
        # we convert all thresholds into a list of dicts for faster access
        thresholds = {}  # a dict holding the nodeid and the threshold thereof (min and max)
        for anno in self.objectNode.get_child("thresholds").get_leaves():
            if anno.get_child("type").get_value() != "threshold":
                continue  # only thresholds
            id = anno.get_child("variable").get_leaves()[0].get_id()  # the first id of the targets of the annotation target pointer, this is the node that the threshold is referencing to

            thisMin = anno.get_child("min").get_value()
            if type(thisMin) is type(None):
                thisMin = -numpy.inf
            thisMax = anno.get_child("max").get_value()
            if type(thisMax) is type(None):
                thisMax = numpy.inf
            tags = anno.get_child("tags").get_value()
            if "threshold" in tags:
                tags.remove("threshold")
            #entry = {"min": thisMin, "max": thisMax, "tags": tags}
            if id not in thresholds:
                thresholds[id] = {}
            if not tags:
                tags = ["__global"]
            for tag in tags:
                thresholds[id][tag]={"min": thisMin, "max": thisMax}
        self.thresholds = thresholds

        #now check if we have to create the outputnodes
        self.scoreNodes = {} #dict with {id:scoreid} // id is the id of the variable, node is the node of the according score
        for id in thresholds:
            scoreNodeName = self.model.get_node_info(id)["name"]+"_score"
            scoreNode = self.scoreNodesFolder.get_child(scoreNodeName)
            if not scoreNode:
                scoreNode = self.scoreNodesFolder.create_child(scoreNodeName,properties={"type": "timeseries", "subType": "score", "creator": self.objectNode.get_id()})
            self.scoreNodes[id]=scoreNode.get_id()

        totalOutputNode = self.objectNode.get_child("output").get_child("_total_score")
        if not totalOutputNode:
            totalOutputNode = self.objectNode.get_child("output").create_child("_total_score",
                                                                            properties={"type": "timeseries",
                                                                                        "creator": self.objectNode.get_id(),
                                                                                        "subType": "score"})
        self.totalScoreNode = totalOutputNode

        return data


class ThresholdsClass(streaming.Interface):

    def __init__(self,objectNode):
        self.logger=objectNode.get_logger()
        pass
    def reset(self,data=None):
        return data
    def feed(self,data):
        self.logger.debug("Thresholds.feed()")
        return data
    def flush(self,data):
        return data


class StreamWriterClass(streaming.Interface):

    def __init__(self,objectNode):
        self.objectNode = objectNode
        self.writeEnableNode = objectNode.get_child("enabled")
        self.model = objectNode.get_model()
        self.logger = objectNode.get_logger()
        pass

    def reset(self,data):

        return data

    def feed(self,blob=None):
        self.logger.debug("StreamWriterClass.feed()")
        pro=Profiling("WRITER")
        notifyIds = []
        self.model.disable_observers()
        if self.writeEnableNode.get_value()== True:
            try:
                #write the data to nodes
                if blob["type"] == "timeseries":
                    times = blob["data"]["__time"]
                    for id, values in blob["data"].items():
                        #print(f"write to {id}:{values},{times}")
                        if id[0:2] !="__": # the __ entries are others like state etc.
                            self.model.time_series_insert(id, values=values, times=times, allowDuplicates=True)
                            notifyIds.append(id)
                            pro.lap(id)
                if blob["type"] == "eventseries":
                    times = blob["data"]["__time"]
                    for id, values in blob["data"].items():
                        if id[0:2] != "__":
                            self.model.event_series_insert(id, values=values, times=times, allowEventDuplicates=True) # allow same events on the same time
                            notifyIds.append(id)
            except Exception as ex:
                self.logger.error(f"can't write data to model {ex}")

        pro.lap("XXX")
        self.model.enable_observers()
        if notifyIds:
            self.model.notify_observers(notifyIds,"value")
        pro.lap("YYY")
        #print(pro)
        return blob

    def flush(self,data):
        return data




class StreamLoggerClass(streaming.Interface):

    def __init__(self,objectNode):
        self.objectNode = objectNode
        self.logger = objectNode.get_logger()
        self.name = objectNode.get_browse_path()
        pass

    def reset(self,data=None):
        self.logger.debug(f"{self.name}.reset()")
        self.logger.debug(f"{data}")
        return data

    def feed(self,data=None):
        self.logger.debug(f"{self.name}.feed():")
        self.logger.debug(f"{data}")
        return data

    def flush(self,data=None):
        self.logger.debug(f"{self.name}.flush():")
        self.logger.debug(f"{data}")
        return data

