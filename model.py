import glob
import json
import copy
import importlib
import threading
import logging
import pytz

#for tables
import numpy
import numpy as np
import datetime
import dateutil.parser
import sys
import os
import time
import uuid
import hashlib
import random
import traceback

# type hints
from typing import List

import modeltemplates

# for Observer
from queue import Queue
from queue import Empty
import utils

from timeseries import TimeSeriesTable


"""
next Todo
-  
- execute: problem im thread mit der Ausführung
- code documentation
- google document
- 
"""

sys.path.append("./plugins") #for the importlib loader, doesn't understand relative paths
#sys.path.append("./private") #for the importlib loader, doesn't understand relative paths

myGlobalDir = os.path.dirname(os.path.realpath(__file__)) # holds the directory of this script



def date2secs(value):
    """ converts a date with timezone into float seconds since epoch
    Args:
        value: the date given as either a string or a datetime object
    Returns:
        the seconds since epoch or the original value of not convertibel
    """
    if type(value) == type(datetime.datetime(1970, 1, 1, 0, 0)):
        timeDelta = value - datetime.datetime(1970, 1, 1, 0, 0,tzinfo=pytz.UTC)
        return timeDelta.total_seconds()
    elif type(value) is str:
        #try a string parser
        try:
            date = dateutil.parser.parse(value)
            timeDelta = date - datetime.datetime(1970, 1, 1, 0, 0,tzinfo=pytz.UTC)
            return timeDelta.total_seconds()
        except:
            return value
    else:
        return value


def date2msecs(value):
    """
        converst a timestamp in to ms since epoch
    """
    return date2secs(value)*1000

def secs2date(epoch):
    """ converts float seconds since epoch into datetime object with UTC timezone """
    return datetime.datetime(1970, 1, 1, 0, 0,tzinfo=pytz.UTC) + datetime.timedelta(seconds=epoch)

def secs2dateString(epoch,tz="+00:00"):
    """ converts seconds since epoch into a datetime iso string format 2009-06-30T18:30:00.123456+02:00 """
    try:
        stri = secs2date(epoch).isoformat()
        return stri
    except:
        return None

def epochToIsoString(epoch,zone=pytz.UTC):
    dat = datetime.datetime(1970, 1, 1, 0, 0,tzinfo=pytz.utc) + datetime.timedelta(seconds=epoch)
    dat=dat.astimezone(zone) # we must do this later conversion due to a bug in tz lib
    return dat.isoformat()


#used as an OOP wrapper for the flat and procedural style of the model class
class Node():
    """ used as an OOP wrapper for the flat and procedural style of the model class
    it is a convenient way to access nodes and their hierarchy and internals
    """
    def __init__(self,myModel,myId):
        """  a node can be created by calling the
        mynode = model.get_node("root.mynode") or
        mynode = Node(mymodel,"123")
        Returns:
            a node object for further access to values, hierarchy etc.
        """
        self.model = myModel # this is not a copy!!
        self.id = myId

    def __repr__(self):
        return 'Node(id={:}, value={:})'.format(self.id, self.get_value())

    def get_value(self):
        """ Returns:
                the "value" property of the node
                None if node has no "value"
        """
        return self.model.get_value(self.id)

    def get_time_series(self, start=None,
                              end=None,
                              noBins=None,
                              includeIntervalLimits=False,
                              resampleTimes=None,
                              format="default",
                              toList = False,
                              resampleMethod = None):

        browsePath = self.model.get_browse_path(self.id)

        return self.model.time_series_get_table(variables = [browsePath],
                                                tableDescriptor=None,
                                                start=start,
                                                end=end,
                                                noBins=noBins,
                                                includeIntervalLimits=includeIntervalLimits,
                                                resampleTimes=resampleTimes,
                                                format=format,
                                                toList=toList,
                                                resampleMethod=resampleMethod)[browsePath]

    def add_references(self,targetNodes,deleteAll=False):
        """
            add references from the node to the targets
            Args:
                targetNodes: node or list of nodes to reference to
                deleteAll: if set true, we delete all existing references before creating the new
            Returns
                True/False for success/error
        """
        if deleteAll:
            self.model.remove_forward_refs(self.id)#this deletes all existing
        if type(targetNodes) is not list:
            targetNodes = [targetNodes]
        targetIds = [node.get_id() for node in targetNodes]
        return self.model.add_forward_refs(self.id,targetIds)

    def set_value(self,value):
        """
            special support for "column" types: if a scalar is given, we make a "full" array
        """
        if self.get_properties()["type"] == "column":
            if type(value) != numpy.ndarray and type(value) != list:
                #we have a scalar, so we set it
                #get the len of the table
                timeNode = self.get_table_time_node()
                length = len(timeNode.get_value())
                value = numpy.full(length,value,dtype=numpy.float64)

        return self.model.set_value(self.id,value)

    def set_time_series(self,values=None,times=None):
        return self.model.time_series_set(self.id,values=values,times=times)



    def get_parent(self):
        """ Returns:
                a Node()-instance of the parent of the current node,
                None if no parent available
        """
        nodeInfo = self.model.get_node_info(self.id)
        if nodeInfo:
            return self.model.get_node(nodeInfo["parent"])
        else:
            return None

    def get_child(self,childName):
        """
            Args:
                childName(nodedescription):
            Returns:
                a Node() instance of the child holding the childName
                None if the current node does not have a child with the name childName
        """
        nodeInfo = self.model.get_node_info(self.id)
        if nodeInfo:
            for childId in nodeInfo['children']:
                childInfo = self.model.get_node_info(childId)
                if childInfo["name"] == childName:
                    return self.model.get_node(childId)
        return None


    def delete(self):
        """
            delete this node from the model, note that the object itself it not destroyed, but it is disconnected from the model
            so should not be used anymore afterwards
        :return:
        """
        return self.model.delete_node(self.id)

    def create_child(self,name=None,type="folder",value=None,properties={}):
        """
            create a node under the current node, if the node exists already, we get the node
                Args:
                    name [string] the child name
                    type [string] the type of the node
                    value [any] direct assignment of values
                    properies [dict] a dict with further settings of properies like value, type etc
            Returns:
                the node objects or none if not available
        """

        if name == None:
            name = '%08x' % random.randrange(16 ** 8)
        id = self.model.create_node(parent=self.id,name=name,type=type,value=value,properties=properties)
        if id:
            return self.model.get_node(id)
        else:
            #we try to get it anyways
            return self.get_child(name)


    def get_children(self, deepLevel=1):
        """  Returns:
            a list of Node()-objects which are the children of the current node
            args:
                deepLevel: set >1 to get children and childrens' children
        """
        nodeInfo = self.model.get_node_info(self.id)
        children = []
        if nodeInfo["children"]:
            children=[self.model.get_node(id) for id in nodeInfo['children'] ]

            while deepLevel>1:
                deepLevel -=1
                childrenOld = children.copy()
                for child in childrenOld:
                    children.extend(child.get_children())
                #remove dublicates via id:
                childDict = {child.get_id():child for child in children} # same keys(id) will only be there once
                children = list(childDict.values())
        return children


    def get_properties(self):
        """  Returns:
            a dictionary holding the properties of the node like {"value":123,"name":"myVariable","children":...}
        """
        nodeInfo = self.model.get_node_info(self.id)
        return copy.deepcopy(nodeInfo)

    def get_type(self):
        """
            Retuns:
                the type of the node
        """
        return self.get_property("type")

    def get_property(self,property):
        """
        Args:
            property: the property name asked for
        Returns:
            the value of the property behind the property given
            None if the property does not exist
        """
        nodeDict =self.get_properties()
        if property in nodeDict:
            return self.get_properties()[property]
        else:
            return None

    def set_properties(self,properties):
        """
            add or modify properties of a node
            Args:
                properties [dict] holding key,value for the properties
            Returns
                True for ok, False for not done
        """
        return self.model.set_properties(properties,nodeDesc=self.id)


    def get_model(self):
        """ this function should only be used for testing, we should never be in the need to access the model inside
        Returns:
            the underlying model of type Model() class
        """
        return self.model

    def get_target_ids(self):
        """ this function returns the target ids of a referencer as a list, not resolving the leaves"""

        if self.get_properties()["type"] != "referencer":
            return None
        return self.get_properties()["forwardRefs"]

    def get_target(self):
        """ this function returns the first direct taret node of a referencer not resolving the leaves"""
        if self.get_properties()["type"] == "referencer":
            targets = self.get_properties()["forwardRefs"]
            if targets:
                return Node(self.model,targets[0])
        return None

    def get_targets(self):
        """ this function returns the target Nodes of a referencer as a list, not resolving the leaves"""
        if self.get_properties()["type"] != "referencer":
            return None
        targets = []
        for nodeid in self.get_properties()["forwardRefs"]:
            targets.append(Node(self.model,nodeid))
        return targets

    def get_leaves(self):
        """ this function returns a list of Nodes containing the leaves where this referencer points to
        this functions works only for nodes of type "referencer", as we are following the forward references
        leaves are defined as following:
            1) all nodes that are listed under the forward references and which are not of type referencer or folder
            2) if nodes pointed to are referencer, the targets are again analyzed
            3) if a node pointed to is a folder, all children of the folder are taken which are not referencer or folder themselves
               folders and referencers inside the folder are not taken into account
        doing so, hierarchies of referencers are unlimited, hierarchies of folders are only of depth 1
        Returns:
            all nodes which are considered leaves as a list of Node() objects
        """
        leaves = self.model.get_leaves(self.id) # a list of node dicts
        leaveNodes = []
        for leave in leaves:
            leaveNodes.append(Node(self.model,leave["id"]))
        return leaveNodes

    def get_leaves_ids(self):
        """
            get the list of ids of the leaves, see get_leaves()
            Returns:
                a list of ids of the leaves
        """
        return self.model.get_leaves_ids(self.id)



    def get_id(self):
        """ Returns: the nodeid (which is generated by the system) """
        return self.id

    def get_browse_path(self):
        """ Returns: the browsepath along the style "root.myfolder.myvariable..." """
        return self.model.get_browse_path(self.id)

    def get_name(self):
        """ Returns: the name of the node without the path """
        return self.model.get_node_info(self.id)["name"]

    def get_node(self,desc):
        return self.model.get_node(desc)

    def get_table_time_node(self):
        """ if the current node belongs to a table, then we can get the time node
        a node 
        Returns:
            (obj Node()) the node of type
        """
        timeNode = self.model.find_table_time_node(self.id)
        if timeNode:
            return Node(self.model,timeNode)
        else:
            return None

    def get_table_len(self):
        """
            if the current node is a type "table", we get the current len
            Return:
                 the len of the columns of the table
        """
        return self.model.get_table_len(self.id)

    def get_table_node(self):
        """
            if the current node is a column of a time series table, we get the according table node of type "table"
            Return:
                a Node() of type "table" which is the table of the current node
        """
        tableId = self.model.find_table_node(self.id)
        if tableId:
            return self.model.get_node(tableId)
        else:
            return None



    def get_time_indices(self,startTime,endTime):
        """ works only for the time node, it looks to find the timeField node of the table to which the node belongs
            then tries to find start and end time inside the timeField column and returns the index (rownumber) which are
            INSIDE the given startTime, endTime
            Args:
                startTime: the startTime to look up ,supported formats: epoch seconds, datetime object, iso string
                endTime: the startTime to look up ,supported formats: epoch seconds, datetime object, iso string
            Returns:
                (numpy array) indexnumbers containing the rows of the table that fall inside the given [startTime, endTime] intervall
                None for not finding table, timeField, start-endTimes whatsoever

        """
        try:
            startTime = date2secs(startTime)
            endTime = date2secs(endTime)
            times = numpy.asarray(self.get_value())
            indices = numpy.where((times >= startTime) & (times <= endTime))[0]
            return indices
        except:
            return None

    def execute(self):
        return self.model.execute_function(self.id)


    def get_logger(self):
        return self.model.logger

    def connect_to_table(self,tableNode):
        """
            connect a node to a table, it must be a column type
            the node itself will be reset and filled with numpy.inf and prepared to work with the table:
            an array will be created with np.inf of the current table size
            and the column will be hooked to the table referencer

            Returns:
                True on success
        """
        if self.get_property("type") != "column":
            return False

        #now make an array of np.inf of the current table size and apply the value
        timeNode = tableNode.get_table_time_node()
        if not timeNode:
            return False
        tableLen = len(timeNode.get_value())
        self.set_value(numpy.full(tableLen,numpy.inf,dtype=numpy.float64))

        #now hook it as column to the table
        #check if we are part of it already
        for column in tableNode.get_child("columns").get_leaves():
            if column.get_id() == self.get_id():
                return True
        #now connect it to the table
        return self.model.add_forward_refs(tableNode.get_child("columns").get_id(), [self.id],allowDuplicates=False)

    def get_columns(self):
        """
            get the columns nodes of a table without the time node
            can be executed on the table node

            Returns:
                list of node objects which are the columns of the table without the time node
        """
        if self.get_properties()["type"] != "table":
            return None
        nodes = self.get_child("columns").get_leaves()
        timeNode = self.get_table_time_node()
        return [node for node in self.get_child("columns").get_leaves() if node.get_id() != timeNode.get_id()]

class Observer:
    # The observer needs a reference to the model, because the rest service is not able to detect
    # when the client connection is closed, but the observer message handling loop can detect it
    # this way the observer can detach itself from the model, when the client is disconnected
    # there are two queues involved: the updateQueue holding events pushed by the observers from the model
    # and the eventQueues which is the filtered updateQueue (filtering avoids sending multiple identical events in short time
    def __init__(self, model):
        self.model = model

        # Message queues to store the new events and last time stamps
        self.updateQueue = Queue()
        self.eventQueues = {} # k,v = event:{"lasttimestamp":datetime,"queue":Queue()
        self.minWaitTime = 0.500 #in seconds float

        # use the logger of th model
        self.logger = self.model.logger
        self.lock = threading.RLock()


        #preload queue: this is a workaround as the browser does not get the first 2 events immideately
        # it actually doesn't help ..?
        for i in range(2):
            self.updateQueue.put({"event":"_preload","id":"","data":{"xy":str(i)}})

    def update(self, event):
        """
            inform about the occurrence of an event,
            Args:
                event "string": the
        :param event:
        :return:
        """

        defaultEvent = {"data":"","id":"","event":""}
        defaultEvent.update(event)
        self.updateQueue.put(defaultEvent)
        #self.logger.debug(f"Qup {id(self)} {defaultEvent['event']}, {defaultEvent['id']}")



    def get_event(self):
        """
            get the next event from the observerclass, this is used a generator for the webserver
            we also filter out events to avoid a train of identical events
            the filtering uses the self.minWaitTime, within that period we don't sent identical event;
            events are "identical", if they have the same "event" and "data"
        """

        self.logger.debug(f"Observer {id(self)} get_event()")
        stop_event_processing = False # This flag shows when to stop the event processing

        while not stop_event_processing:
            try:
                # Try to retrieve an item from the update queue
                event = self.updateQueue.get(block=True,timeout=self.minWaitTime)
                if "nodeId" in event["data"]:
                    eventIdentification = event["event"]+event["data"]["nodeId"]
                else:
                    eventIdentification = event["event"]#+str(event["data"])
                #now sort this event into the queues of eventids
                if eventIdentification not in self.eventQueues:
                    # this is a new type/identificatin of event, create an entry in the event  queue
                    # put the event in the queue and make the last timestamp so that we send it out now
                    self.eventQueues[eventIdentification]={"lastTimeStamp":0,"queue":Queue()}
                self.eventQueues[eventIdentification]["queue"].put(event)

            except Exception as ex:
                # this happens if we time out the queue get, no problem, just continue
                #self.logger.error(f"Exception observer {id(self)} thread self.updateQueue.get: {ex},{str(sys.exc_info()[0])}")
                pass

            #now go over all the sorted event queues and check what to send out:
            if 0:
                #show the queues
                for k,v in self.eventQueues.items():
                    q = v["queue"]
                    qLen = q.qsize()
                    self.logger.debug(f"Queue {k}: len {qLen} {[q.queue[id] for id in range(qLen)]}")
            try:
                now = time.time()
                for eventIdentification,entry in self.eventQueues.items(): # entry is {"lasttimestampe": "queue":
                    #self.logger.debug(f"observer {id(self)} check queue of {eventIdentification} size: {entry['queue'].qsize()},last:{entry['lastTimeStamp']}, now:{now}, ready: {now > (entry['lastTimeStamp']+self.minWaitTime)}")
                    if (not entry["queue"].empty()) and (now > (entry["lastTimeStamp"]+self.minWaitTime)):
                        #send this event, the timeout was met, we pull the first event from the queue, trash the remaining ones
                        """
                        old code
                        
                        self.eventQueues[eventIdentification]["lastTimeStamp"]=now
                        #send out this event
                        myEvent = self.eventQueues[eventIdentification]["queue"].get()
                        event_string = f'id:{myEvent["id"]}\nevent: {myEvent["event"]}\ndata: {myEvent["data"]}\n\n'
                        self.logger.debug(f'Observer {id(self)} sending event: {event_string}')

                        #pull empty the queue
                        if self.eventQueues[eventIdentification]['queue'].qsize():
                            self.logger.debug(f"Qtrash observerinstance{id(self)} eventident {eventIdentification} size {self.eventQueues[eventIdentification]['queue'].qsize()}")
                            while not self.eventQueues[eventIdentification]["queue"].empty():
                               self.eventQueues[eventIdentification]["queue"].get(False)
                        self.logger.debug(f"Qyield {id(self)} : {myEvent}")
                        yield event_string
                        """
                        self.eventQueues[eventIdentification]["lastTimeStamp"]=now
                        #send out this event

                        #pull empty the queue
                        if self.eventQueues[eventIdentification]['queue'].qsize():
                            #self.logger.debug(f"Qtrash observerinstance{id(self)} eventident {eventIdentification} size {self.eventQueues[eventIdentification]['queue'].qsize()}")
                            while not self.eventQueues[eventIdentification]["queue"].empty():
                                myEvent = self.eventQueues[eventIdentification]["queue"].get(False)

                        event_string = f'id:{myEvent["id"]}\nevent: {myEvent["event"]}\ndata: {json.dumps(myEvent["data"])}\n\n'
                        #self.logger.debug(f"Qyield {id(self)} : {myEvent}")
                        yield event_string


            # This exception is raised when the generator function is exited, which means that the
            # client side connection to the SSE stream was close, thus the observer could be removed
            except GeneratorExit:
                self.logger.warning(f"Observer {id(self)} connection closed.")
                stop_event_processing = True

        self.logger.warning(f"Observer {id(self)} exiting event processing.")

        # Detach this observer from the model
        self.model.detach_observer(self)


class Model:
    nodeTemplate = {"id": None, "name": None, "type": "folder", "parent": None, "children": [], "backRefs": [],"forwardRefs":[],"value":None}


    def __init__(self):
        """
            initialize an empty Model object, it will contain the root Node as folder with Id "0"
            during the initialization, also the plug-ins (all files in the ./plugin) are loaded:
            all templates and functions are imported
            a model holds all modelling information and data to work on
        """
        self.version = 0.1
        self.model = {"1":{
            "name":"root",
            "type":"folder",
            "children":[],
            "parent":"0",
            "id":"1",
            "backRefs":[],
            "forwardRefs":[],
            "version":self.version
           }}
        self.disableObserverCounter = 0 # a counting sema (under manual lock) for the disabling: if zero the notify_observers is active otherwise not
        self.__init_logger(logging.DEBUG)
        self.globalIdCounter=1 # increased on every creation of a node, it holds the last inserted node id
        self.idCreationHash = True # if this is true, we create the id per hash, not per counter
        self.ts = TimeSeriesTable()
        self.functions={} # a dictionary holding all functions from ./plugins
        self.templates={} # holding all templates from ./plugins
        self.lock = threading.RLock()
        self.executeFunctionRunning = False # set to true, makes sure only one functions runs at a time
        self.import_default_plugins()
        self.differentialHandles ={} # containing model_copy entries to support differential queries
        self.diffHandleCounter = 0  # used only for debugging
        self.differentialHandlesMaxPerUser = 10
        self.currentModelName = "emptyModel" # the current name of the model
        self.modelUpdateCounter = 0 #this is for the tree observer, on any change, we update the counter
        self.observerStatus = {} # a dict holding the key = observerid and value : the needed status of an observer processing
        self.executionQueue = Queue()

        self.observers = []
        self.sse_event_id = 1

        self.start_function_execution_thread()


    def __del__(self):
        self.functionExecutionRunning = False # stop the execution thread of functions

    def __init_logger(self, level):
        """setup the logger object"""
        self.logger = logging.getLogger("Model-"+'%08x' % random.randrange(16 ** 8))
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        logfile = logging.FileHandler("./log/model.log")
        logfile.setFormatter(formatter)
        self.logger.addHandler(logfile)


        self.logger.setLevel(level)

    def __get_id(self, id):
        """
            Args:
                id (string): give a browsepath ("root.myfolder.myvariable") or a nodeId ("10")
                or a "fancy" path mixed like "1000.min" where 1000 is a node id, only the first is allowed as Nodeid, the followings are names
            Returns:
                (string): the node id as string
                None if not found
        """
        if id in self.model:
            return id
        #maybe a browsepath?
        try:
            names = id.split('.')
            if names[0]=="root":
                names = names[1:]
                actualSearchId = "1"

            elif names[0] in self.model:
                #self.logger.debug(f"fancy browsepath {names}")
                actualSearchId = names[0]
                names = names[1:]
            else:
                return None
        except:
            return None

        #now we start at root
        for name in names:
            nextSearchId = None
            for childId in self.model[actualSearchId]["children"]:
                if self.model[childId]["name"] == name:
                    #this is a match
                    nextSearchId = childId
                    break
            if not nextSearchId:
                return None
            #we found it, go deeper now
            actualSearchId = nextSearchId
        return actualSearchId

    def get_node(self,desc):
        """ instantiate a Node() object on the node given as desc
            Args:
                desc (string): give a browsepath ("root.myfolder.myvariable") or a nodeId ("10")
            Returns:
                (Node()): a node object of the given node
                None if not found
        """
        with self.lock:
            id  = self.__get_id(desc)
            if id:
                return Node(self,id)

    def get_node_info(self,desc,includeLongValues=True):
        """
            Args:
                desc (string): give a browsepath ("root.myfolder.myvariable") or a nodeId ("10")
                includeLongValue if true, we include values for columns and files
            Returns:
                (dict): a dictionary holding all properties of the node includin references and children
        """
        with self.lock:
            id = self.__get_id(desc)
            if not id: return None
            if includeLongValues:
                return copy.deepcopy(self.model[id])
            else:
                #we do not include values of columns and files
                if self.model[id]["type"] in ["column","file","timeseries"]:
                    return  {k:v for k,v in self.model[id].items() if k!="value"}
                else:
                    #take all
                    return copy.deepcopy(self.model[id])




    def __get_node_with_children(self,id,nodes,includeForwardRefs=True):
        """
            recursive helper for get_branch

        """
        if self.model[id]["type"] in ["file","column","timeseries"]:
            #we do not take these values
            nodes[id]={k:v for k,v in self.model[id].items() if k!="value"} # copy the whole but leave out the value
        elif self.model[id]["type"] == "referencer":
            nodes[id] = self.model[id]
            if includeForwardRefs:
                #for referencers, we take the direct targets
                for targetId in self.model[id]["forwardRefs"]:
                    if self.model[targetId]["type"] in ["file", "column","timeseries"]:
                        # we do not take these values
                        target = {k: v for k, v in self.model[id].items() if k != "value"}  # copy the whole but leave out the value
                    else:
                        target = copy.deepcopy(self.model[targetId])
                    #xxx todo, we might take the wrong backrefs with us, also these target nodes might not have their parent here
                    nodes[targetId]=target
        else:
            nodes[id]=self.model[id]

        for child in self.model[id]["children"]:
            nodes.update(self.__get_node_with_children(child,nodes,includeForwardRefs))


        return nodes


    def get_branch(self,desc,includeRoot=True,includeForwardRefs=True):
        """
            get a branch of the model starting from desc including all children excluding:
                columns
                files
            for referencers, we do not follow deep search for leaves, we just include the first level referenced nodes
            referencers poiting to nodes that are not part of the branch will also be included


            Returns:
                a list of nodedicts that can be used as a full valid model again

        """
        with self.lock:
            id = self.__get_id(desc)
            if not id: return None
            nodes = {}
            nodes.update(self.__get_node_with_children(id,nodes,includeForwardRefs))
        #now we also need all nodes to the desc
        if includeRoot:
            while self.model[id]["parent"]!="0":
                #the parent is not invalid so take the parent, we don't make further check for files and otheres
                parentId =  self.model[id]["parent"]
                parentNode = copy.deepcopy(self.model[parentId])
                parentNode["children"]=[id] # the other side-children are not of interest
                nodes.update({parentId:parentNode})
                id = self.model[id]["parent"]

        return copy.deepcopy(nodes)

    def __get_node_with_children_pretty(self,id,depth = None,ignore = []):
        """
            recursive helper for get_branch_pretty
            args:
                nodes: the nodes so far

        """

        #t=utils.Profiling(f"id {self.get_browse_path(id)}, ignore = {ignore}")

        result = {}

        node = self.model[id]
        #create my properties
        props = {k: copy.deepcopy(v) for k, v in node.items() if k not in ["value", "backRefs", "children"]}
        if node["type"] not in ["file", "column","timeseries"]:
            # we also take the value then
            props["value"] = copy.deepcopy(node["value"])
        if node["type"] == "referencer" and (depth is None or depth>0):
            #tt = utils.Profiling("get leaves")
            leaves = self.get_leaves_ids(id)
            #print(tt)
            #tt.start("get leaves data")
            forwards = [self.get_browse_path(leaf) for leaf in leaves]
            props["leaves"]=forwards
            #tt.lap("1")
            props["targets"] = [self.get_browse_path(id) for id in self.model[id]["forwardRefs"]]
            props["leavesIds"]=leaves
            props["leavesValues"] = [self.get_value(id) if self.model[id]["type"] not in ["file","column","timeseries"] else None for id in leaves]
            #tt.lap("2")
            validation = []
            props["leavesProperties"]={}
            for id in leaves:
                prop = self.get_node_info(id,includeLongValues=False)
                if "validation" in prop:
                    validation.append(prop["validation"])
                else:
                    validation.append(None)
                props["leavesProperties"][id]=prop
                props["leavesProperties"][id]["browsePath"]=self.get_browse_path(id)
            #tt.lap("3")
            props["leavesValidation"] = validation
            #print(tt)
        #make sure we have the browsepath on board
        if "browsePath" not in props:
            props["browsePath"]=self.get_browse_path(id)
        result[".properties"]=props

        if depth is None or depth>0:
            #now the children
            nextDepth = None
            if depth is not None:
                nextDepth = depth -1
            for childId in node["children"]:
                childPath = self.get_browse_path(childId)
                if any([ignoreName in childPath for ignoreName in ignore]):
                    #self.logger.debug(f"ignore {childPath}")
                    pass
                else:
                    result[self.model[childId]["name"]]=self.__get_node_with_children_pretty(childId,nextDepth,ignore)
        #print(t)
        return result



    def get_branch_pretty(self,desc,depth=None,ignore = []):
        """
            get a branch in the form
            "child1":{"child3":... ".type":, ".value"
            "child2":{
            the properties occurr in ".property" style, the children are direct entries
            we only use names
            for the referencers, the ".forwardRefs" are the leaves with full path: ["root.folder1.tzarget2","root.varibale.bare"..]
            Args:
                desc [string] the root node to start from
                depth [int] the depth to look into
        """
        with self.lock:
            #p=utils.Profiling("get_branch_pretty")
            id = self.__get_id(desc)
            if not id: return None
            res = self.__get_node_with_children_pretty(id,depth,ignore)
            #self.logger.debug(p)
            return res









    def get_node_with_children(self,desc):
        """ retrieve node information including children of the first level
            Args:
                desc (string): give a browsepath ("root.myfolder.myvariable") or a nodeId ("10")
            Returns:
                (Node()): a node object of the given node
                None if not found
        """
        with self.lock:
            id = self.__get_id(desc)
            if not id: return None

            response = copy.deepcopy(self.model[id])
            if response["children"]!=[]:
                children =[]
                for childId in response["children"]:
                    children.append(copy.deepcopy(self.model[childId]))
            response["children"]=children
            return response


    def get_models(self):
        """
            get the available model files from the disk under /models
        :   Returns: a list of strings
        """
        try:
            mydir = myGlobalDir
            os.chdir(mydir)  # to enable import easily
            files = os.listdir(mydir + '/models')
            # take only the ones with '.json, but cut the '.model.json' extension
            models = [f.split('.model')[0] for f in files if f.endswith(".json")]

            return models
        except Exception as ex:
            self.logger.error("Model.get_models() failed "+str(ex))
            return []

    def get_info(self):
        """
            get some information about the model
            Returns: (dict) key value pairs on information of the model,
        """
        return {"name":self.currentModelName}

    def import_plugins_from_directory(self, plugin_directory: str, check_file_marker = True):
        """ find all plugins from plugin_directory.
            take from there the templates from the files and the functions
            Args:
                check_file_marker: if set to True, we expect a "#21datalabplugin" string in the first line
        """
        if plugin_directory not in sys.path:
            sys.path.append(plugin_directory)  # for the importlib to find the stuff

        plugin_filenames = glob.glob(os.path.join(plugin_directory, '**/*.py'), recursive=True)
        for fileName in plugin_filenames:
            if fileName.startswith('__'):
                continue # avoid __pycache__ things
            #we need to check if extra plugins have the "#21datalabplugin
            if check_file_marker:
                absolutePath = os.path.join(myGlobalDir,fileName)
                f = open(absolutePath,"r")
                firstLine = f.readline()
                f.close()
                if firstLine != "#21datalabplugin\n":
                    continue

            filename_relative = os.path.relpath(fileName, plugin_directory)
            moduleName = os.path.splitext(filename_relative)[0].replace(os.path.sep, '.')
            self.logger.info(f"import plugin lib {moduleName}")
            module = importlib.import_module(moduleName)
            #now analyze all objects in the module
            for objName in dir(module):
                if objName.startswith('__'):
                    continue # these are python generated info objects, we don't want them
                element = getattr(module,objName)
                if type(element) is dict:
                    #this is a template information
                    self.templates[moduleName+"."+objName]=copy.deepcopy(element)
                elif callable(element):
                    #this is a function, get more info
                    newFunction = {"module":module, "function":element}
                    self.functions[moduleName+"."+objName]=newFunction
    def import_default_plugins(self):
        """ find all plugins (= all .py files in the ./plugin folder
            take from there the templates from the files and the functions
            don't check them for #21datalabplugin marker

            this function is execution on startup of the model

        """
        self.import_plugins_from_directory(os.path.join(myGlobalDir, 'plugins'),check_file_marker=False)

    def get_id(self,ids):
        """ convert a descriptor or a list into only ids (which can be used as entry to the model dictionary
            Args:
                ids (string, list(string)): a single or list of strings containing either and id ("101") or browsepath ("root.myfolder.myvar")
            Returns:
                a list(id) or id as string
        """
        with self.lock:
            if type(ids) == type(list()):
                newList = []
                for id in ids:
                    newList.append(self.__get_id(id))
                return newList
            elif type(ids) == type(dict()):
                newDict = {}
                for oldId in ids:
                    id = self.__get_id(oldId)
                    newDict[id]=ids[oldId] #also copy the value
                return newDict
            else:
                #assume its scalar
                return self.__get_id(ids)

    def get_browse_path(self,desc):
        """
            Args:
                desc(string): a node id or browsepatch
            Returns:
                (string) a browsepath
        """
        with self.lock:
            id = self.get_id(desc)
            if not id in self.model:
                return None
            path = self.model[id]["name"]
            while 1:
                id = self.model[id]["parent"]
                if id =="0":
                    break
                else:
                    path = self.model[id]["name"]+"."+path
            return path


    def push_nodes(self,nodeDicts):
        """
            push a ready nodedict into the mode
            this is a dangerous function as it does not adjust references, parent/child relations whatsoever
            you must take care of that yourself
        """
        for nodeDict in nodeDicts:
            self.logger.warning(f"pushing node {nodeDict['id'], nodeDict['name']}")
            self.model[nodeDict["id"]]=copy.deepcopy(nodeDict)
        self.__notify_observers([],None) # just trigger the treeupdate for now
        #xxx todo notify!



    def create_node(self,parent="root",type="folder",value=None,name="newNode",properties={}):
        """
            create a node inside the model by giving several infos
            Args:
                parent: a descriptor (browsepath or id) of the parent
                type: the type of the node
                value: (optional) give a value for the node
                name(string): a name of the node, must be unique under the parent
                properties (dict): a dictionary containing further key-values to be placed into the node as properties
            Returns:
                (string) nodeid,
                 None for problem durinf creation
        """
        #check if parent exists
        with self.lock:
            parentId = self.get_id(parent)
            if not parentId:
                return None
            #check if same name existst already
            newpath = self.get_browse_path(parent)+"."+name
            if self.get_id(newpath):
                #we found it, it exists alreay, so we can't create it
                return None
            # we can create this node
            if self.idCreationHash == True:
                newId = str((random.randrange(2**64))) # a 64 bit random value
            else:
                self.globalIdCounter += 1
                newId = str(self.globalIdCounter)
            newNode = copy.deepcopy(self.nodeTemplate)
            newNode.update({"id":newId,"name":name,"type":type,"parent":parentId})
            if properties !={}:
                newNode.update(properties)
            if value != None:
                newNode["value"]=value
            self.model[parentId]["children"].append(newId)
            self.model[newId] = newNode
            if newNode["type"] == "timeseries":
                self.time_series_create(newId)
            self.__notify_observers(parentId,"children")
            return newNode["id"]

    def create_node_from_path(self,path,properties={"type":"variable"}):
        """
            create a node from a path given, all intermediate nodes of th path given that do not yet exist are also created as folder type
            Args:
                path(string): the path to the node to be creates
                properties(dict): the properties of the node
            example:
                create_node_from_path("root.myfolder.something.thisvar")
                  this will create myfolder as folder, something as folder, thisvar as variable and will also
                  set all hierarchies correctly
            Returns:
                (string) the nodeid created or
                None if problem during creation
        """
        currentNode = "root" #root
        with self.lock:
            for node in path.split('.')[1:-1]:
                if not self.__get_id(currentNode+'.'+node):
                    #this one does not exist, so make it
                    self.create_node(currentNode,name=node)
                currentNode += '.'+node

            return self.create_node(parent=currentNode,name=path.split('.')[-1],properties=properties)

    def create_nodes_from_template(self,parent="root",template=[]):
        """
            deprecated!! this is the old style of templates as lists, now it's a dict
            Create a node from a template; a template is a list of node-dicts,
            Args:
                parent(string): descriptor of the parent node under which the nodes of the template should be created
                template: a list of node dicts of the nodes to be creates, children are allowed as dict
            Returns:
                (boolenan) True for created, False for error
            Example:
                 create_nodes_from_template(parent="root.myfolder",[{"name":"myvariable1","type":"variable"},
                                                                    {"name":"myfolder","type":"folder","children":[
                                                                        {"name":"mysubvar","type":"variable"}]])
        """

        with self.lock:
            parentId = self.get_id(parent)
            if not parentId:
                return False

            newNodeIds = [] #these must be corrected later
            for node in template:
                #we take all info from the nodes and insert it into the tree
                nodeName = node["name"]
                newNodeId = self.create_node(parentId,name=nodeName,properties=node)
                newNodeIds.append(newNodeId)
                #do we have "children per template syntax"?, then remove that property from the nodes and make more nodes
                if "children" in self.model[newNodeId]:
                    savedChildren = copy.deepcopy(self.model[newNodeId]["children"])
                    self.model[newNodeId]["children"]=[] # empty out
                    for child in savedChildren:
                        newChildId = self.create_node(newNodeId,name=child["name"],properties=child)
                        newNodeIds.append(newChildId)

            #now correct missing stuff
            for nodeId in newNodeIds:
                if self.model[nodeId]["type"]== "referencer":
                    # convert the path of references into an id: get the parent path, add the tail, convert to id
                    forwardReferences =self.model[nodeId]["forwardRefs"] #make a copy, we'll delete this
                    self.model[nodeId]["forwardRefs"]=[]
                    parentPath = self.get_browse_path(self.model[nodeId]["parent"])
                    for forwardRef in forwardReferences:
                        forwardPath = parentPath+forwardRef
                        self.add_forward_refs(nodeId,[forwardPath])
            return True


    def __create_nodes_from_path_with_children(self,parentPath,nodes):
        """
            recursive helper function for create_template_from_path
            e build all nodes under the parentPath on this level and then the children
            we return a list of all created node ids
        """
        createdNodes = []

        for node in nodes:
            newModelNode = {}
            for k, v in node.items():
                if k not in ["children", "parent", "id", "browsePath"]:  # avoid stupid things
                    newModelNode[k] = v
            newId = self.create_node_from_path(parentPath+'.'+newModelNode["name"],newModelNode)
            if newId:
                createdNodes.append(newId)
            if "children" in node:
                createdNodes.extend(self.__create_nodes_from_path_with_children(parentPath+'.'+newModelNode["name"],node["children"]))
        return createdNodes



    def create_template_from_path(self,path,template):
        """
            Create a template from a path given, the template contains one or more nodes
            the path must not yet exist!
            Args:
                path(string): the path under which the template will be placed. the template always contains
                  a root node, this will be renamed according to the path
            Returns:
                (boolenan) True for created, False for error
        """

        with self.lock:
            #first create the template root node
            #we rename the template according to the path requested
            template["name"]=path.split('.')[-1]
            parentPath = '.'.join(path.split('.')[:-1])
            newNodeIds = self.__create_nodes_from_path_with_children(parentPath,[template])
            self.logger.debug(f"create_template_from_path, new nodeids: {newNodeIds}")

            #now adjust the references of new nodes and of the ones that were there
            for newNodeId in newNodeIds:
                if "references" in self.model[newNodeId]:
                    #we must create forward references
                    for ref in self.model[newNodeId]["references"]:
                        # the given path is of the form templatename.levelone.leveltwo inside the template
                        # we replace the "templatename" with the path name the template was given
                        targetPath = parentPath+'.'+template['name']+'.'+'.'.join(ref.split('.')[1:])
                        self.add_forward_refs(newNodeId,[targetPath])
                    del self.model[newNodeId]["references"] # we remove the reference information from the template

    def get_templates(self):
        """
            give all templates loaded
            Returns: a dict with entries containing the full templates
        """
        with self.lock:
            return copy.deepcopy(self.templates)

    def add_forward_refs(self,referencerDesc,targets,allowDuplicates = True):
        """
            adding forward references from a referencer to other nodes, the forward references are appended at the list
            of forward references of the referencer node
            references to oneself are not allowed

            Args:
                referenderDesc (string): descriptor of the referencer node from which we want to add forward references
                targets (list(descriptors)): listof node descriptors to which we want to add forward refs
            Returns:
                True/False for success
        """
        with self.lock:
            fromId = self.get_id(referencerDesc)
            if not fromId:
                self.logger.error("can't set forward ref on "+str(referencerDesc))
                return False

            if type(targets) is not list:
                targets = [targets]

            if targets==[]:
                return True

            if not self.model[fromId]["type"]=="referencer":
                self.logger.error("can't set forward ref on "+str(referencerDesc)+ "is not type referencer, is type"+self.model[fromId]["type"])
                return False
            for target in targets:
                toId = self.get_id(target)
                if not toId:
                    continue
                if toId == fromId:
                    continue
                if not allowDuplicates:
                    if toId in self.model[fromId]["forwardRefs"]:
                        continue # ignore this forwards ref, we have it already
                self.model[toId]["backRefs"].append(fromId)
                self.model[fromId]["forwardRefs"].append(toId)
            self.__notify_observers(fromId,"forwardRefs")
            return True

    def lock_model(self):
        self.lock.acquire()

    def release_model(self):
        self.lock.release()

    def get_model(self):
        """
            Returns: the full deepcopy of the internal model object (list of dictionaries of the nodes)
        """
        with self.lock:
            #also add the browsepath to all nodes
            for nodeid in self.model:
                self.model[nodeid]["browsePath"]=self.get_browse_path(nodeid)
            return copy.deepcopy(self.model)

    def get_model_for_web(self,getHash=False):
        """
            Returns: the full deepcopy of the internal model object (list of dictionaries of the nodes)
                     but leaving out the column values (this can be a lot of data)
                     and the file values (files are binary or strings with big size, typically serialized ML-models)
                     for files and columns, we either return a string "len 12344" or a sha1 hash value 133344
        """

        model = {}
        p=utils.Profiling("get_model_for_web")
        with self.lock:
            for nodeId, nodeDict in self.model.items():
                if nodeDict["type"] in ["column","file","timeseries"]:
                    # with columns we filter out the values
                    node = {}
                    for nk, nv in nodeDict.items():
                        if nk == "value":
                            try:
                                if not getHash:
                                    node[nk] = "len " + str(len(nv))
                                else:
                                    start = datetime.datetime.now()
                                    hash = hashlib.sha1(nv.tobytes())
                                    node[nk] = hash.hexdigest()
                                    self.logger.debug(f"hashed {nodeDict['name']} in {(datetime.datetime.now()-start).total_seconds()} hash:{node[nk]}")
                            except:
                                node[nk] = "None"
                        else:
                            node[nk] = copy.deepcopy(nv)  # values can be list, dict and deeper objects
                    model[nodeId] = node
                else:
                    #this node is not a colum, can still hold huge data
                    model[nodeId] = copy.deepcopy(nodeDict)  # values can be list, dict and deeper objects nodeDict
                model[nodeId]["browsePath"] = self.get_browse_path(nodeId) #also add the browsepath
        self.logger.debug(f"{p}")
        return model


    def remove_forward_refs(self,sourceDesc,targetDescriptors = [], deleteDuplicates=False):
        """
            remove forward references from a referencer, this also removes the backreference from the target
            Args:
                sourceDesc: the descriptor of the referencer node
                targets: a list of descriptors, if missing we delete all
                deleteDuplicates: if set true, we delete all referenes to a target if we hae more than one reference

            Returns:
                True/False for success
        """
        with self.lock:
            fromId = self.get_id(sourceDesc)
            if not fromId:
                return False
            if not self.model[fromId]["type"] == "referencer":
                return False  # only for referencers
            if targetDescriptors == []:
                targets = self.model[fromId]["forwardRefs"].copy()
            else:
                targets = self.get_id(targetDescriptors)

            if targets == []:
                return True# nothing to do

            for toId in targets:
                if not toId:
                    continue # we skip Nones coming from the get_id
                if deleteDuplicates:
                    # maybe multiple entries
                    while toId in self.model[fromId]["forwardRefs"]: # maybe multiple entries
                        self.model[fromId]["forwardRefs"].remove(toId)
                        self.model[toId]["backRefs"].remove(fromId)
                else:
                    # we delete only one entry
                    self.model[fromId]["forwardRefs"].remove(toId)
                    self.model[toId]["backRefs"].remove(fromId)
            self.__notify_observers(fromId,"forwardRefs")
        return True


    def remove_forward_ref(self,sourceDesc,targetDesc):
        """
            remove a forward reference from a referencer, this also removes the backreference from the target
            Args:
                sourceDesc: the descriptor of the referencer node
            Returns:
                True/False for success
        """
        with self.lock:
            fromId = self.get_id(sourceDesc)
            toId = self.get_id(targetDesc)
            if not fromId or not toId:
                return False
            if not self.model[fromId]["type"]=="referencer":
                return False # only for referencers

            try:
                self.model[fromId]["forwardRefs"].remove(toId)
                self.model[toId]["backRefs"].remove(fromId)
                self.__notify_observers(fromId, "forwardRefs")
                return True
            except:
                return False

    def remove_back_ref(self,sourceDesc,targetDesc):
        """
            remove a backwards reference from any node to a referencer, this also removes the forwardreferece from the target
            actually, this function is just a helper. Normally, we only talk about "forward references";
            each forward reference also creates a backwards reference in the model, but this is just for internal look up speed
            the reference here is targetDesc -> (forwardRef) -> sourceDesc
            Args:
                sourceDesc: the descriptor of the node that holds a backwards reference
                targetDesc: the descriptor of the node that holds the forward reference
            Returns:
                True/False for success
        """
        with self.lock:
            return self.remove_forward_ref(targetDesc,sourceDesc)

    def add_property(self,nodeDesc,property,value):
        """
            add a random property entry for a node, a node is a key-value store, a property is a key with a value
            Args:
                nodeDesc: the descriptor of the node
                property: the key to be created on the node
                value: the value to be stored for this property
            Returns:
                True for create
                False for node not found or if the property already exists
        """
        with self.lock:
            id = self.get_id(nodeDesc)
            if not id:
                return False
            if property in self.model[id]:
                return False # have this property already
            self.model[id][property]=value
            self.__notify_observers(id, property)
            return True

    def set_properties(self,properties={},nodeDesc=None):
        """
            changes a random set of properties given by the dict or adds them if not existant, some properties are not allowed here:
            children, parent, forward and back ward refs, allowed are all others including type, name, value
            Args:
                nodeDesc: the descriptor of the node, is optional, can also be given as browsePath or id in he properties dict
                properties: the new properties or changed
            Returns:
                True for done
                False for node not found or if the property already exists
        """
        with self.lock:
            if nodeDesc:
                id = self.get_id(nodeDesc)
            elif "id" in properties:
                id = properties["id"]
            elif "browsePath" in properties:
                id = self.get_id(properties["browsePath"])
            else:
                self.logger.error("set properties is missing id ")
                return False
            if not id:
                return False

            for k,v in properties.items():
                if k in ["id","browsePath","children","parent","forwardRefs","backRefs"]:
                    continue # we ignore these entries
                self.model[id][k]=v # overwrite or set new
            self.__notify_observers(id,list(properties.keys()))
            return True


    def find_all_children_recursive(self,nodeIds):
        """ find all children recursively, give a list of  """
        with self.lock:
            children = []
            for id in nodeIds:
                if self.model[id]["children"]:
                    children.extend(self.find_all_children_recursive(self.model[id]["children"]))
                children.append(id)
            return children


    #delete node and all subnodes
    def delete_node(self,desc):
        """
            delete a node and all its recursive children;
            flow:
            1) make a list of all nodes to be deleted
            2) rip off all references to /from delete nodes
            3) delete all nodes
            4) notify observers about children change on the delete nodes

             desc(string): the descriptor of the node
            Returns:
                True for success
                False for node not found
        """
        with self.lock:
            id = self.get_id(desc)
            if not id:
                return False

            nodesToDelete = self.find_all_children_recursive([id])
            self.logger.debug(f"delete nodes {nodesToDelete}")
            childNotify = []
            #first rip off all references
            for id in nodesToDelete:
                forwards = self.model[id]["forwardRefs"].copy()
                backwards = self.model[id]["backRefs"].copy()
                for forward in forwards:
                    self.remove_forward_ref(id,forward) # this will also trigger observers
                for backward in backwards:
                    self.remove_back_ref(id,backward) # this will also trigger observers

            #now delete the acutal nodes
            for id in nodesToDelete:
                parentId = self.model[id]["parent"]
                if parentId in self.model:
                    self.model[parentId]["children"].remove(id)
                    childNotify.append(parentId)
                if self.model[id]["type"]=="timeseries":
                    self.time_series_delete(id)
                del self.model[id]

            #now notify only those who still exist
            goodNotify=[]
            for id in childNotify:
                if id in self.model:
                    goodNotify.append(id)
            if goodNotify:
                self.__notify_observers(goodNotify, "children") # make ONE call for the observers

            return True


    # if desc.type is a var, function then we just set the value
    # if it's a timeseries" then we set a column in a table, padded if needed
    def set_value(self,desc,value):
        """
            set the value property of a node, if the node does not have a value property yet, it is created here
            Args:
                desc(string): node descriptor
                value (any): any value to be stored
        """
        with self.lock:
            id = self.get_id(desc)
            if not id: return None
            #convert if table:
            if self.model[id]["type"] == "column":
                value = numpy.asarray(value,dtype=numpy.float64)

            self.model[id]["value"] = value
            self.__notify_observers(id,"value")
            return True

    def get_value(self,desc):
        """
            read out the "value" property of a node
            Args:
                desc(string): the node that holds the value
            Returns:
                the value
                None if the node has no "value" property
        """
        with self.lock:
            id = self.get_id(desc)
            if not id: return None

            if self.model[id]["type"] == "timeseries":
                return self.time_series_get_table(id)[id]["values"]

            if "value" in self.model[id]:
                return copy.deepcopy(self.model[id]["value"])
            else:
                return None



    def __copy_node(self,id,resolveChildren=False):
        """
            get a copy of a node, we don't create a node in the model here!
            copy node with all properties, if the node is a "column", we don't copy the value
            if the resolveChildren is set to true, we also copy the direct children
            the copied node can't be used to create a node, as it is the copy of an existing node!
            Args:
                id (string): the node id to be copied
                resolveChildren (bool): False to not copy the children (the new node has no children)
                                        True to copy-create also the children
            Return:
                (dict) the node
        """
        newNode = {}
        for key in self.model[id]:
            if key == "value" and self.model[id]["type"]in ["column","file","timeseries"]:
                newNode["value"]=None
            elif key == "children" and resolveChildren:
                #we also copy the children
                newNode["children"]=[]
                for childId in self.model[id]["children"]:
                    childNode = self.__copy_node(childId)
                    newNode["children"].append(childNode)
            else:
                newNode[key]=copy.deepcopy(self.model[id][key])
        return newNode



    def __get_targets(self,id):
        """
            #this is a recusive helper function for the get_leaves function
        """
        targets=[]
        if self.model[id]["type"] == "referencer":
            for targetId in self.model[id]["forwardRefs"]:
                targets.extend(self.__get_targets(targetId))
        elif self.model[id]["type"] == "folder":
            for targetId in self.model[id]["children"]:
                targets.extend(self.__get_targets(targetId))
        else:
            addNode = self.__copy_node(id,resolveChildren=True)
            addNode["browsePath"]=self.get_browse_path(id)
            targets = [addNode]
        return targets


    def get_leaves_ids(self,desc):
        """
            get the list of ids of the leaves, see get_leaves()
            Returns:
                a list of ids of the leaves
        """
        leaves = self.get_leaves(desc) # a list of node dicts
        leaveIds = []
        for leave in leaves:
            leaveIds.append(leave["id"])
        return leaveIds


    def get_leaves(self,desc):
        """
            this function returns a list of dicts containing the leaves where this referencer points to
            this functions works only for nodes of type "referencer", as we are following the forward references
            leaves are defined as following:
                1) all nodes that are listed under the forward references and which are not of type referencer or folder
                2) if nodes pointed to are referencer, the targets are again analyzed
                3) if a node pointed to is a folder, all children of the folder are taken which are not referencer or folder themselves
                   folders and referencers inside the folder are not taken into account
            doing so, hierarchies of referencers are unlimited, hierarchies of folders are only of depth 1
            Returns:
                all node dicts which are considered leaves as a list of node dicts
        """
        with self.lock:
            id = self.__get_id(desc)
            if not id:return None

            targets=self.__get_targets(id)
            if targets and targets[0]["id"] == id:
                #this can happen if the node is not a folder, ref and had no children
                targets.pop(0)
            return targets


    def __get_referencer_parents(self,ids):
        backRefs = []
        #we look back from this node

        for id in ids:
            if self.model[id]["type"] == "referencer":
                #we take this one in
                backRefs.append(id)
            #plus we look further up
            thisBackRefs = self.model[id]["backRefs"]
            if thisBackRefs:
                backRefs.extend(self.__get_referencer_parents(thisBackRefs))
        return backRefs


    def get_referencers_old(self,desc):
        """
            find the referencers pointing to a node via the "leaves algorithm"
            initially, we take the parent and the backref referencers
            Args:
                deep: we support the reverse leave-algorithms including any depth of children level after the last referencer,
                e.g. a leaves-path of referencer -> referencer -> nodes -> child ->child is a valid match
        """
        with self.lock:
            id = self.__get_id(desc)
            if not id:return None

            ids = [self.model[id]["parent"],id]

            if "0" in ids:
                ids.remove("0")

            referencers = self.__get_referencer_parents(ids)
            return referencers


    def get_referencers(self,desc,deepLevel = 1):
        """
            find the referencers pointing to a node via the "leaves algorithm"
            initially, we take the parent and the backref referencers
            Args:
                deepLevel: we support the reverse leave-algorithms including any depth of children level after the last referencer,
                e.g. a leaves-path of referencer -> referencer -> nodes -> child ->child is a valid match
                we give the number of parent levels to include in the search at the leaves
                default is 1, so the node itself and its parent

        """
        with self.lock:
            id = self.__get_id(desc)
            if not id:return None

            if not deepLevel:
                ids = [self.model[id]["parent"],id]
            else:
                ids = self._get_parents(id,deepLevel)

            if "0" in ids:
                ids.remove("0")

            referencers = self.__get_referencer_parents(ids)
            return referencers

    def _get_parents(self,id,deepLevel = -1):
        ids = []
        while id != "1" and deepLevel >= 0:
            ids.append(id)
            deepLevel -=1
            id = self.model[id]["parent"]
        return ids

    #get a table with values like in the table stored, start and end times are optional
    # if start, end not given, then we get the full table with no postprocessing at all
    def get_timeseries_table_old(self,variables,startTime=None,endTime=None,noBins=None,agg="sample",includeTimeStamps=None,includeBackGround=None):
        with self.lock:
            variables = self.get_id(variables)
            return self.timeSeriesTables.get_value_table(variables, startTime=startTime, endTime=endTime, noBins=noBins,
                                                         agg=agg,
                                                         includeTimeStamps=includeTimeStamps)  # ,startTime,endTime)
            '''
            if startTime == None and endTime ==None:
                #request the full table
                variables = self.get_id(variables) # convert all to ids
                return self.timeSeriesTables.get_value_table(variables,startTime=startTime,endTime=endTime,noBins=noBins,agg=agg,includeTimeStamps=includeTimeStamps)#,startTime,endTime)
            else:
                # this is a more details request, we will try to deliver the data in bins and with
                # aggretation postprocessing
                variables = self.get_id(variables) # convert all to ids, not browsepath
                return self.timeSeriesTables.get_value_table(variables,startTime,endTime,noBins,agg,includeTimeStamps=includeTimeStamps)
            '''

    #used in the Node class, give a column variable or the table itself, return the nodeid of the time variable of that table
    def find_table_time_node(self,desc):
        with self.lock:
            table = self.__find_table(self.get_id(desc))
            if not table:
                return None

            pathToTimeIndex = self.get_browse_path(table)+".timeField"
            timeColumnId = self.get_leaves(pathToTimeIndex)[0]['id'] # this referencer must point to only one node
            return timeColumnId

    def find_table_node(self,desc):
        """
            get the node id of a table giving a column node of the table as input
            Args
                desc[string]: a node descriptor of a column node belonging to the table
            Returns:
                the node id of the table node

        """
        with self.lock:
            return self.__find_table(desc)

    def get_child(self,desc,childName):
        """
            get a child based on the name given
            Args:
                desc: node descriptor of the node under which we look for children
                name: the child name to look for
            Returns:
                a nodeid if we find the child with "name" under the desc or none if not found
        :return:
        """
        with self.lock:
            nodeInfo = self.get_node_info(desc)
            if nodeInfo:
                for childId in nodeInfo['children']:
                    childInfo = self.get_node_info(childId)
                    if childInfo["name"] == childName:
                        return childId
        return None

    def get_children_dict(self,desc):
        """
            create a dictionary with key= childName and value = nodedict
            Args:
                desc: the nodedescriptor
            Returns:
                a dict
        """
        with self.lock:
            childrenDic={}
            id = self.get_id(desc)
            if not id:
                return None

            for childId in self.model[id]["children"]:
                child = self.get_node_info(childId)
                childrenDic[child["name"]]=child
            return childrenDic



    def get_table_len(self,desc):
        """
            get the current length of a table
            Args:
                desc: the node descriptor of type table
            Returns:
                the current length of the columns of the table, none if error
        """
        with self.lock:

            tableId = self.get_id(desc)
            if not tableId: return None
            if not self.model[tableId]["type"]=="table": return None

            try:
                columnid = self.get_child(tableId,"columns")
                if not columnid: return None
                columnIds = self.get_leaves_ids(columnid)
                if columnIds:
                    return len(self.model[columnIds[0]]["value"])
            except:
                return None




    def get_timeseries_table(self,variables,startTime=None,endTime=None,noBins=None,agg="sample",includeTimeStamps=None,format="array",includeBackGround=None):
        """
            get a time series table from variables. The table is returned as a list[list] object
            all variables requested must be of type "column" and must belong to the same table:
            all columns requested here must have a direct backreference to the same node of type "columns"
            todo: also allow "columns" to point to folders or multiple hierarchies of referencing/folders

            Args:
                variables (list(nodedescriptors)): nodes to be part the data table requested (ordered!)
                startime, endTime: the start and endtime of the table given as seconds since epoch
                                #we also allow the special case of endTime = 0 and startTime = -interval
                                # we also allow the special case of startTime given and end time= 0
                noBins(int): the number of samples to be returned inside the table between start end endtime,
                             if None is given, we return all samples (rows) we have in the table and to not aggregate
                agg(string): the aggregation function to be used when we downsample the data,
                    "sample": this means, we just pick out values (we sample) the data set, this is actually not an aggregation
                includeTimesStampe (bool): currently ignored
                includeBackGround (bool): currently ignored
            Returns(dict)
                key : value
                "__time" : list of timestamps for the returned table in epoch seconds
                "variable1": the list of float values of one of the requested variables
        """
        with self.lock:
            #first check if all requested timeseries are columns from the same table
            vars = self.get_id(variables)
            table = []
            for var in vars:
                if self.model[var]["type"] != "column":
                    self.logger.warn("requested time series but not column type")
                    return False
                table.append(self.__find_table(var))
            if len(set(table)) != 1 or  set(table)== {None}:
                self.logger.warning("not the same table")
                return False

            #get the time field, and make fancy indexing via numpy arrays
            pathToTimeIndex = self.get_browse_path(table[0])+".timeField"
            timeColumnId = self.get_leaves(pathToTimeIndex)[0]['id']
            if startTime and endTime:
                times = numpy.asarray(self.model[timeColumnId]["value"])
                indices = numpy.where((times>=startTime) & (times<=endTime))[0]
                #xxx todo find the right index
            elif startTime and not endTime:
                #special cases for [-startTime:] and [startTime:] requests
                if startTime < 0:
                    #this is the special case that we take an interval from the end
                    endTime = self.model[timeColumnId]["value"][-1]# the last
                    startTime = endTime +startTime # as startTime is negative this is actually substraction
                else:
                    #starttime is positive
                    pass
                times = numpy.asarray(self.model[timeColumnId]["value"])
                indices = numpy.where(times >= startTime)[0]
            else:
                indices = numpy.arange(0,len(self.model[timeColumnId]["value"])) ## all indices

            #now resample the indices to have the right bins number
            if noBins:
                varIndices = np.linspace(indices[0], indices[-1], noBins, endpoint=False, dtype=int)
            else:
                varIndices = indices

            if format=="array":
                result = []
                for var in variables:
                    original = np.asarray(self.model[self.get_id(var)]["value"])[varIndices] # fancy indexing
                    data=original.tolist() # apply the selection with the indices list
                    result.append(data)
            else:
                result = {}
                for var in variables:
                    original = np.asarray(self.model[self.get_id(var)]["value"])[varIndices]  # fancy indexing
                    data = original.tolist()  # apply the selection with the indices list
                    result[var]=data
                result["__time"]=np.asarray(self.model[timeColumnId]["value"])[varIndices].tolist()
            return result





    def add_timeseries(self,blob,fast=False):
        """
            add a dictionary of variables to a table, we check if the variables belong to the same table
            also, times that come in as datetime object are converted to epoch seconds
            Args:
                blob (dict): a dictionary containing keys (node descriptors) and values (scalars)
            Returns:
                True/False for success
        """
        with self.lock:
            table = []
            for key in blob:
                id = self.get_id(key)
                if not id:
                    self.logger.warn("add_timeseries count not find the variable:" + str(key))
                    return False
                if self.model[id]["type"] != "column":
                    self.logger.warn("requested time series but not column type")
                    return False
                table.append(self.__find_table(id))

            if len(set(table)) != 1 or set(table) == {None}:
                self.logger.warn("not the same table")
                return False
            #here, the request is parsed as ok, let's put the values
            for key in blob:
                id = self.get_id(key)
                value = blob[key]
                if type(self.model[id]["value"]) is not list:
                    self.model[id]["value"]=[]

                #we auto-convert time stamps
                if type(value) is datetime.datetime:
                    value = date2secs(value)
                self.model[id]["value"].append(value)#finally put the value



    #return the id of the table, give a column variable
    def __find_table(self,desc):
        """
            return the node id of the table, give a column variable
            !! this has no lock, must be called under lock
            Args:
                desc(string): node descriptor of type column or the table itself
            Returns:
                the node id of the table to which the desc node belongs
        """
        id = self.get_id(desc)
        if not id: return False

        if self.model[id]["type"] == "table":
            return id

        for ref in self.model[id]["backRefs"]:
            if self.model[ref]["name"] == "columns":
                return self.model[ref]["parent"]
        return None

    def ts_table_add_blob(self,dataBlob):
        """
            this function add a data blob to an existing table, it accepts multiple values at once to speed up internals
            Args:
                dataBlob (dict or list(dict)): containing key:value pair with key=a descriptor of a column of one table
                                                          value: a scalar or list or numpy array of values
        """

        if type(dataBlob) is list:
            self.logger.error("currently no support for list blobs")
            return None
        with self.lock:

            #first find the table and decide for the type conversion
            for key in dataBlob:
                if key != '__time':
                    tableId = self.__find_table(key)
                    break
            if not tableId:
                self.logger.error("can't find the table of "+str(dataBlob[list(dataBlob.keys())[0]]))
            tableNode =self.get_node(tableId)
            columnsType = numpy.float64 # this is the default

            # make sure the time is there and convert it: we accept datetime objects, iso strings or floats seconds
            # plus, the key will be the time node id afterwards
            timeNode = tableNode.get_child("timeField").get_leaves()[0]
            #try to find the time entry in the dataBlob, rename it to the timenode id
            timeKeyOptions = ['__time',timeNode.get_browse_path(),timeNode.get_id()]
            for timeKeyOption in timeKeyOptions:
                if timeKeyOption in dataBlob:
                    dataBlob[timeNode.get_id()] = dataBlob.pop(timeKeyOption) # from now on the time field is names as its browsepath
                    break
            if timeNode.get_id() not in dataBlob:
                self.logger.error("time field entry missing")
                return False

            #now check if all are on the same table and convert the keys to node ids
            variables = list(dataBlob.keys())
            for var in variables:
                if self.__find_table(var) != tableId:
                    self.logger.error("variables are not on the same table")
                    return False
                id = self.get_id(var)
                if id != var:
                    dataBlob[self.get_id(var)]=dataBlob.pop(var) # make new entry as nodeid



            #now check the sizes of the incoming data and convert them to the requested type
            inputSizes = set()
            for key,value in dataBlob.items():
                if key == timeNode.get_id():
                    #if we handle the time node, we might have to convert
                    if type(value) is list or type(value) is numpy.ndarray:
                        newValues = []
                        #newValues = numpy.asarray([],dtype=numpy.float64)
                        for val in value:
                            newValues.append(date2secs(val))
                        dataBlob[key] = numpy.asarray(newValues,dtype=numpy.float64) # write it back to the data
                    else:
                        #it is a scalar
                        dataBlob[key] = numpy.asarray([date2secs(value)],dtype=numpy.float64)
                else:
                    if numpy.isscalar(dataBlob[key]):
                        dataBlob[key]=numpy.asarray([dataBlob[key]],dtype=columnsType) # make a list if it is scalar
                    else:
                        dataBlob[key]=numpy.asarray(dataBlob[key],dtype=columnsType) # if it is a numpy array already, numpy makes no copy
                inputSizes.add(dataBlob[key].shape[0])
            if len(inputSizes)!=1:
                self.logger.error("incoming data has different len, can't hande as padding is unclear")

            # when we are here, we have converted all incoming data ot numpy arrays, all belong to the same table
            # and all have the same length, we are ready to put them inside
            #print("through")
            #now append them
            return self.__ts_table_add_row(dataBlob,tableNodeId=tableId)


    def __ts_table_add_row(self,dataBlob,tableNodeId=None,autoPad=True,pad=numpy.NaN):
        """
            must be called under lock !!
            this function accepts a dataBlob which is ready to be inserted, we don't make any more checks here
            it must use variables from one table, it must contain data as numpyarrays
            variables of the tables which are missing will be filled with pad if autoPad is true
        """
        if not tableNodeId:
            tableNode = self.get_node(self.__get_table(list(dataBlob.keys())[0]))
        else:
            tableNode = self.get_node(tableNodeId)

        dataLen = dataBlob[list(dataBlob)[0]].shape[0]
        columnNodes = tableNode.get_child("columns").get_leaves()
        for columnNode in columnNodes:
            id = columnNode.get_id()
            if id in dataBlob:
                #we add that one to the table
                if type(self.model[id]['value']) != numpy.ndarray:
                    self.model[id]['value'] = dataBlob[id]
                else:
                    self.model[id]['value'] = numpy.append(self.model[id]['value'],dataBlob[id])
            else:
                #we must pad
                self.loger.debug("we are padding "+id+" with % ",dataLen)
                if type(self.model[id]['value']) != numpy.ndarray:
                    self.model[id]=numpy.full(dataLen,numpy.nan)
                else:
                    self.model[id]['value'] = numpy.append(self.model[id]['value'],numpy.full(dataLen,numpy.nan))

        return True


    def append_table(self,blob,autocreate=True,autopad=True, timeSorted = False):
        """
            this function accepts a dictionary containing paths and values and adds them as a row to a table
             if autoPad is True: it is allowed to leave out columns, those will be padded with numpy.inf,
             if autocreate is True: it is allowed to add unknown colums, those will be added automatically under the given name

            Args:
                blob(dict):
                    keys: node descriptors,
                    values: value to be appended to the table (scalar or list per variable is allowed
                    the times should be given in a variable ending with ".time"
                        if the table exists already and has another node for the time-values, then we take the .time values and put them on the timenode
                autocreate(bool): if set to true and the nodes or table in the dict do not exist yet, we autocreate a table
                autopad(bool) if set to true, we automatically pad values in an existing table if variables of the table are not part of the blob
                                doing so, we keep consistent lenght for all columns of a table

        """

        #first check if we need to autocreate something, also check if we have multiple tables in play
        with self.lock:
            autocreates = []
            tableId = None
            columnsId = None
            numberOfRows = None
            for key in blob:
                id = self.__get_id(key)
                if not id:
                    if not autocreate:
                        self.logger.warn("appending table with unknown variables")
                        return None
                    else:
                        #we create this thing later
                        autocreates.append(key)
                else:
                    #the id was found, let's find the right table
                    for ref in self.model[id]["backRefs"]:
                        if self.model[ref]["name"] == "columns":
                            #this is our table
                            if not tableId:
                                tableId = self.model[ref]["parent"]
                                columnsId = ref
                                numberOfRows = len(self.model[id]["value"])
                            else:
                                if tableId != self.model[ref]["parent"]:
                                    self.logger.warn("mixed tables request")
                                    return None


            self.logger.debug("append table "+str(self.get_browse_path(tableId)))
            if autocreates and autocreate:
                #do we even have to create our table?
                if not tableId:
                    #make a table structure based on the names given
                    tableName = autocreates[1].split('.')[1]+"_autotable"
                    tableId = self.create_node(parent="root",name=tableName,properties={"type":"table"})
                    columnsId = self.create_node(parent=tableId,name="columns",properties={"type":"referencer"})
                    timeId = self.create_node(parent=tableId, name="timeField", properties={"type": "referencer"})
                    numberOfRows=0
                else:
                    #if we don't create the table, here is our timeId
                    timeReferencer = self.get_child(tableId, "timeField")
                    timeId = self.get_leaves_ids(timeReferencer)[0]
                    #we also then don't create any new time-field
                    autocreates = [path for path in autocreates if path[-5:]!=".time"]

                self.logger.debug(f"table var autocreates: {autocreates}")
                for path in autocreates:
                    id = self.create_node_from_path(path,properties={"type":"column"})
                    self.model[id]["value"]=numpy.full(numberOfRows,numpy.inf)
                    self.add_forward_refs(columnsId,[id])
                    if path.split('.')[-1]=="time":
                        #we just created the time field, we must also give the table struct the info
                        self.add_forward_refs(timeId,[id])

            tableColumnIds = self.get_leaves_ids(columnsId) # a list of the ids of the columns
            timeReferencer = self.get_child(tableId,"timeField")
            timeId = self.get_leaves_ids(timeReferencer)[0]
            timePath = None
            for path in blob:
                if path[-5:] == ".time":
                    timePath = path
            if not timePath:
                self.logger.error("no time path given")
                return False

            #now make arrays of all values
            for k,v in blob.items():
                if type(v) is list or type(v) is numpy.ndarray:
                    blob[k]=numpy.asarray(v,dtype=numpy.float64)
                else:
                    blob[k] = numpy.asarray([v], dtype=numpy.float64)


            valuesLen = len(  blob[list(blob.keys())[0]]  )
            tableLen = len ( self.get_value(timeId))
            if not timeSorted:
                #just append
                for path in blob:
                    if path.split('.')[-1]=="time":
                        id = timeId # we take the existing time Node of the table instead of just the variable named "time"
                    else:
                        id = self.get_id(path) # here
                    self.model[id]["value"] = numpy.append(self.model[id]["value"],blob[path]) #todo: this is a very inefficient copy and reallocate
                    if id in tableColumnIds:
                        tableColumnIds.remove(id)
                    #append this value
                for id in tableColumnIds:
                    self.model[id]["value"] = numpy.append(self.model[id]["value"],numpy.full(valuesLen,numpy.inf,dtype=numpy.float64)) # pad the remainings with inf

                #now trigger observser
                self.__notify_observers(self.get_leaves_ids(columnsId),"value")
            else:
                #time sorted: find a place to insert the data in the times
                currentTimes = numpy.asarray(self.get_value(timeId),dtype=numpy.float64)
                startTime = blob[timePath][0]
                endTime = blob[timePath][-1]
                firstIndexGreaterStart, = numpy.where(currentTimes>startTime) #where returns tuple
                if len(firstIndexGreaterStart) == 0:
                    firstIndexGreaterStart = tableLen
                else:
                    firstIndexGreaterStart=firstIndexGreaterStart[0]

                firstIndexGreaterEnd, = numpy.where(currentTimes > endTime)
                if len(firstIndexGreaterEnd) == 0:
                    firstIndexGreaterEnd = tableLen
                else:
                    firstIndexGreaterEnd=firstIndexGreaterEnd[0]

                if firstIndexGreaterEnd != firstIndexGreaterStart:
                    self.logger.error("we can't insert the data in a row-wise time manner, only as block")
                    return False

                startIndex = firstIndexGreaterStart # the position to insert the incoming data
                self.logger.debug(f"insert data @{startIndex} of {tableLen}")
                for path in blob:
                    if path.split('.')[-1]=="time":
                        id = timeId # we take the existing time Node of the table instead of just the variable named "time"
                    else:
                        id = self.get_id(path) # here
                    self.model[id]["value"] = numpy.insert(self.model[id]["value"],startIndex,blob[path]) #todo: this is a very inefficient copy and reallocate
                    if id in tableColumnIds:
                        tableColumnIds.remove(id)
                    #append this value
                for id in tableColumnIds:
                    self.model[id]["value"] = numpy.insert(self.model[id]["value"],startIndex,numpy.full(valuesLen,numpy.inf,dtype=numpy.float64)) # pad the remainings with inf


                #
                pass
            return True



    def __show_subtree(self,rootId):
        currentBrowsePath = self.get_browse_path(rootId)
        indentation = "|  "*(len(currentBrowsePath.split('.'))-1)
        print (indentation+"-",self.model[rootId]["name"],end="")
        noShowProperties=["name","parent","children"]
        for property in self.model[rootId]:
            try:
                if property=="value" and len(self.model[rootId]["value"])>10:
                    print(",len:"+str(len(self.model[rootId]["value"])),end="")
            except:
                pass
            if not property in noShowProperties:
                try:
                    #if this entry has a len and the len is larger then 20, show only a part of it
                    if len(self.model[rootId][property]) > 10:
                        print("," + property + "=" + str(self.model[rootId][property][0:10])+"...("+str(len(self.model[rootId][property]))+")", end="")
                    else:
                        print("," + property + "=" + str(self.model[rootId][property]), end="")
                except:
                    print("," + property + "=" + str(self.model[rootId][property]), end="")

        if self.model[rootId]["type"]=="timeseries":
            print(","+self.time_series_get_info(rootId), end="")

        print("")
        for child in self.model[rootId]["children"]:
            self.__show_subtree(child)

    def execute_function(self,desc):
        """
            create a thread to execute a function there,
            if the function has autoReload, we re-import the external
            file
            Args:
                desc: node descriptor of the node (type "function") to be executed
            Returns:
                True if the execution thread was launched
        """

        with self.lock:


            id = self.get_id(desc)
            if self.model[id]["type"]!= "function":
                return False

            functionName = self.model[id]["functionPointer"]
            if not functionName in self.functions:
                self.logger.error(f"can't find function {functionName} in global list")
                return False

            functionNode = self.get_node(id)

            executionType = functionNode.get_child("control").get_child("executionType").get_value()
            if executionType in ["async","sync"]:
                self.executionQueue.put(id)
                self.logger.info(f"function {desc} queued for execution")
                return True
            elif executionType =="threaded":
                self.logger.info(f"function {desc} started in thread")
                thread = threading.Thread(target=self.__execution_thread, args=[id])
                thread.start()
                return True
            else:
                self.logger.error(f"function {desc} cant be started, unknown execution type {executionType}")
                return False

            #check if function is interactive, then we reload it right now
            if self.model[id]["autoReload"] == True:
            #if self.functions[functionName]["isInteractive"]:
                # must reload the module
                module = importlib.reload(self.functions[functionName]["module"])
                functionPointer = getattr(module,functionName.split('.',1).pop())
                #now update our global list
                self.functions[functionName]["module"] = module
                self.functions[functionName]["function"] = functionPointer

        #here, the lock is open again!
        try:
            if executionType == "async" or executionType == "threaded":
                thread = threading.Thread(target=self.__execution_thread, args=[id])
                thread.start()
                return True
            elif executionType == "sync":
                self.__execution_thread(id) # call it sync here
                return True
            else:
                self.logger.error("unsupported execution type"+str(executionType)+" in fuction"+str(id))
                raise(Exception)
        except:
            return False

    def start_function_execution_thread(self):
        self.functionExecutionRunning = True
        self.functionExecutionThread = threading.Thread(target=self._function_execution_thread)
        self.functionExecutionThread.start()



    def _function_execution_thread(self):
        while self.functionExecutionRunning:
            try:
                nextId = self.executionQueue.get(timeout=1)
                self.logger.info(f"now executing function {nextId}")
                self.__execution_thread(nextId)
            except:
                pass

    def delete(self):
        self.functionExecutionRunning = False

    def exit(self):
        self.delete()

    def close(self):
        self.delete()


    def __execution_thread(self,id):
        """
            the thread function to execute functions
            it currently uses the global lock so it will lock out any other work on the model during execution
            all inputs and outputs are found in the model
            we also set the status and result from here, not needed to do that in the function
            Args:
                id: the node id of the function to be executed
        """
        try:

            with self.lock:

                if self.model[id]["autoReload"] == True:
                    # must reload the module
                    functionName = self.model[id]["functionPointer"]
                    module = importlib.reload(self.functions[functionName]["module"])
                    functionPointer = getattr(module, functionName.split('.', 1).pop())
                    # now update our global list
                    self.functions[functionName]["module"] = module
                    self.functions[functionName]["function"] = functionPointer


                self.logger.info(f"in execution Thread {threading.get_ident()}, executing {id}")
                #check the function
                functionName = self.model[id]["functionPointer"]
                functionPointer = self.functions[functionName]['function']

                #now set some controls
                try:
                    node = self.get_node(id)
                    controlNode = node.get_child("control")
                    controlNode.get_child("status").set_value("running")
                    controlNode.get_child("result").set_value("pending")
                    targetId = self.get_id("root.system.progress.targets")
                    if targetId:
                        self.remove_forward_refs(targetId)
                        self.add_forward_refs(targetId,[controlNode.get_child("progress").get_id()])
                    controlNode.get_child("progress").set_value(0)
                    #controlNode.get_child("signal").set_value("nosignal")
                    startTime = datetime.datetime.now()
                    controlNode.get_child("lastStartTime").set_value(startTime.isoformat())
                finally:
                    pass

            # model lock open: we execute without model lock
            result = functionPointer(node) # this is the actual execution

            #now we are back, set the status to finished
            duration = (datetime.datetime.now()-startTime).total_seconds()

            with self.lock:
                # this is a bit dangerous, maybe the node is not there anymore?, so the
                # inner functions calls of node.xx() will return nothing, so we try, catch
                try:
                    controlNode.get_child("lastExecutionDuration").set_value(duration)
                    #controlNode.get_child("signal").set_value("nosignal") #delete the signal
                    controlNode.get_child("status").set_value("finished")
                    controlNode.get_child("executionCounter").set_value(controlNode.get_child("executionCounter").get_value()+1)
                    controlNode.get_child("progress").set_value(1)
                    if result == True:
                        controlNode.get_child("result").set_value("ok")
                    else:
                        if controlNode.get_child("result").get_value() == "pending":
                            #if the functions hasn't set anything else
                            controlNode.get_child("result").set_value("error")
                except:
                    self.logger.error("problem setting results from execution of #"+str(id))
                    pass


        except Exception as ex:
            self.logger.error("error inside execution thread, id " +str(id)+" functionname"+str(functionName)+str(sys.exc_info()[1])+" "+str(ex)+" "+str(traceback.format_exc()))
            controlNode.get_child("status").set_value("interrupted")
            controlNode.get_child("result").set_value("error")
        return

    def get_error(self):
        s=f"{sys.exc_info()[1]}, {traceback.format_exc()}"
        return s

    def log_error(self):
        self.logger.error(self.get_error())

    def show(self):
        """
            show the current model as a ascii tree on he console
        """
        with self.lock:
            self.__show_subtree("1")


    # save model and data to files
    def save(self, fileName, includeData = True):
        """
            save the model to disk, save the tables separately
            the model file will be saves as ./models/fileName.model.json and the tables will be saved under
            ./models/filename.tablePath.npy

            Args:
                fileName to store it under, please don't give extensions
                includeData : if set to False, we DONT store the values of node types tables or files to disk

        """
        self.logger.debug(f"save model as {fileName} with data {includeData}")
        self.publish_event(f"saving model {fileName}...")
        with self.lock:
            try:
                m = self.get_model_for_web()  # leave out the tables

                model_directory = None
                model_filename = None
                if os.path.isabs(fileName):
                    model_directory = os.path.dirname(fileName)
                    model_filename = os.path.basename(fileName)
                else:
                    file_directory = os.path.dirname(fileName)
                    if len(file_directory) == 0:
                        # we are only given a filename, use 21datalab subfolder models as directory
                        model_directory = os.path.join(os.path.dirname(__file__), "models")
                        model_filename = fileName
                    else:
                        # we are given a relative path + filename
                        model_directory = os.path.dirname(fileName)
                        model_filename = os.path.basename(fileName)

                if includeData:
                    self.ts.save(os.path.join(model_directory, model_filename))
                f = open(os.path.join(model_directory, model_filename)+ ".model.json", "w")
                f.write(json.dumps(m, indent=4))
                f.close()
                self.currentModelName = fileName
                self.publish_event(f"model {fileName} saved.")
                return True
            except Exception as e:
                self.logger.error("problem sving "+str(e))
                self.publish_event(f"saving model {fileName} error")
                return False

    def move(self, nodeList, newParent, newIndex=None):
        """
            move a list of nodes under a new Parent on the child position new Index
            if the newParent is a referencer, we are creating references instead and keep the nodes where they are

            Args:
                nodeList [string]: a list of node descriptors of the nodes to move, scalar is also allowed
                NewParent [string] a node descriptor for the new parent under which the nodes should appear
                new Index  int : the position on the children of newParent where the new nodes should appear
            Returns:
                True
        """
        with self.lock:
            if not type(nodeList) is list:
                nodeList = [nodeList]

            nodeIds = self.get_id(nodeList)
            parentId = self.get_id(newParent)
            if not parentId: return False

            #check the special case that the parent is a referencer:
            if self.model[parentId]["type"] == "referencer":
                self.add_forward_refs(parentId,nodeIds)
                self.logger.info("moves nodes as references "+ parentId + str(nodeIds))
                return True

            #for all others, we start moving nodes
            self.logger.debug(f"model.move():{nodeIds}=>{parentId}")
            try:
                for id in nodeIds:
                    if id == parentId or id == "1":
                        self.logger.error("cant move " +id + " to " + parentId)
                        continue
                    oldParent = self.model[id]["parent"]
                    self.model[oldParent]["children"].remove(id) # remove the child from the old parent
                    self.model[id]["parent"]=parentId
                    if newIndex:
                        self.model[parentId]["children"].insert(newIndex,id) # at specific index
                    else:
                        self.model[parentId]["children"].append(id)    # at the end
                    self.__notify_observers(oldParent, "children")
                    self.__notify_observers(parentId, "children")

            except Exception as ex:
                self.logger.error(f"problem moving {nodeIds} to new parent {parentId} this is critical, the model can be messed up {ex}")
            return True


    def load(self,fileName,includeData = True):
        """
            replace the current model in memory with the model from disk
            please give only a name without extensions
            the filename must be in ./models
            Args:
                fileName(string) the name of the file without extension, we also accept a dict here: a list of nodes
                includeData bool: if set to false, the values for tables and files will NOT be loaded
        """
        result = False
        self.logger.info(f"load {fileName}, includeData {includeData}")
        with self.lock:
            self.publish_event(f"loading model {fileName}...")
            self.disable_observers()
            try:
                if type(fileName) is str:
                    model_directory = None
                    model_filename = None
                    if os.path.isabs(fileName):
                        model_directory = os.path.dirname(fileName)
                        model_filename = os.path.basename(fileName)
                    else:
                        file_directory = os.path.dirname(fileName)
                        if len(file_directory) == 0:
                            # we are only given a filename, use 21datalab subfolder models as directory
                            model_directory = os.path.join(os.path.dirname(__file__), "models")
                            model_filename = fileName
                        else:
                            # we are given a relative path + filename
                            model_directory = os.path.dirname(fileName)
                            model_filename = os.path.basename(fileName)

                    #if os.path.dirname(fileName)

                    f = open(os.path.join(model_directory, model_filename) + ".model.json","r")
                    model = json.loads(f.read())
                    self.model = model
                    f.close()
                    self.currentModelName = fileName
                elif type(fileName) is dict:
                    self.model = copy.deepcopy(fileName) # take over the nodes
                    self.currentModelName = "fromNodes"
                #now also load the tables
                self.globalIdCounter = 0    #reset the counter and recover it further down
                for nodeId in self.model:
                    if not self.idCreationHash:
                        #we only recover the counter if necessary
                        if int(nodeId)>self.globalIdCounter:
                            self.globalIdCounter = int(nodeId) # here, we recover the global id counter
                if includeData:
                    if "version" in self.model["1"] and self.model["1"]["version"]>=0.1:
                        #new loader
                        self.ts.load(os.path.join(model_directory, model_filename))
                    else:
                        self.logger.debug("time series compatibility loader")
                        #we assume data in file and use the standard inmemory table storage
                        for nodeId in self.model:
                            if self.get_node_info(nodeId)["type"] == "table":
                                table = self.get_browse_path(nodeId)
                                data = numpy.load(os.path.join(model_directory, model_filename) + "." + table + ".npy")
                                #now find the time data, apply it to all variables
                                timeId=self.find_table_time_node(table)
                                ids = self.get_leaves_ids(table+".columns")
                                for id, column in zip(ids, data):
                                    if id==timeId:
                                        times = column
                                    else:
                                        self.ts.create(id)
                                        self.set_properties({"type":"timeseries"},id)
                                        self.ts.set(id,values=column)
                                for id in ids:
                                    if id == timeId:
                                        continue
                                    self.ts.set(id,times=times)

                self.enable_observers()
                self.publish_event(f"loading model {fileName} done.")
                self.model["1"]["version"]=self.version #update the version
                result = True
            except Exception as e:
                self.logger.error("problem loading"+str(e))
                self.publish_event(f"loading model {fileName} error.")
                self.enable_observers()
                result = False

            self.update() # automatically adjust all widgets and other known templates to the latest style

        return result


    def create_differential_handle(self, user = None):
        """
            make a copy of the current model and keep it as copy, create a handle for it and return that handle
            this new handle is at the same time the id of te new "user", all the following requests for differential updata
            will be referred to this user id

            Returns:
             a hash handle for the current model
        """
        with self.lock:
            #newHandle = str(uuid.uuid4().hex) # make a new unique handle
            newHandle = str(self.diffHandleCounter)
            self.diffHandleCounter += 1
            if not user:
                #also create a new user
                user = newHandle
            self.differentialHandles[newHandle]= {
                "user":user,
                "model":self.get_model_for_web(),
                "time": int(time.time()),
                "updateCounter": self.modelUpdateCounter
            }# make an entry by copying the whole model
            return newHandle


    def get_differential_update(self,oldHandle,newHandle=None):
        """
            this function takes the copy of the model (hopefully) held under handle and compares it to the current model:
            the differences are analyzed and returned, t
            to avoid endless storage of old references, we have the deletin stategy: for every "user" we keep a max of
            self.differentialHandlesMaxPerUser, if we have more, we delete the oldest

            Args:
                oldHandle (string): the unique id of the old version of the model
                newHandle (string): the unique id of the new version to compare to, if not given, we take the current
                                    and will automatically make a new entry for the current
                delOld: if set, we remove the old entry from the memorized models with a one step delay
            Returns (dict):
                containing information about the changes between and old and new version of the model
                key values:
                "handle":(string): the handle under which we find the new version of the model
                "newNodes": (dict) nodes which are new to the tree in the form Nodeid:{properties}
                "deletedNodeIds": (list) list of node ids which have been deleted
                "modifiedNodes": (dict) nodes which have changed properties: if so, we give the full updated node back

        """
        with self.lock:
            diff={"handle":None,"newNodes":{},"deletedNodeIds":[],"modifiedNodes":{}} # the response for web

            if oldHandle not in self.differentialHandles:
                return None # the old handle does not exist, we can't handle this request

            if newHandle is None:
                # this is the standard case, we generate the new handle now
                user = self.differentialHandles[oldHandle]["user"]
                # we make a quick check if the model has changed at all, if not we simply return the old handle
                if self.differentialHandles[oldHandle]["updateCounter"] == self.modelUpdateCounter:
                    self.logger.debug("get_differential_update: shortcut for no changes")
                    diff["handle"] = oldHandle
                    return diff
                newHandle = self.create_differential_handle(user=user) # this function also makes a copy of the current tree and puts it in the self.differential handles list
                newModel = self.differentialHandles[newHandle]["model"]
            else:
                if newHandle in self.differentialHandles:
                    newModel = self.differentialHandles[newHandle]
                else:
                    return None # the newhandle did not exist
            oldModel = self.differentialHandles[oldHandle]["model"]

            # delete strategy: for every "user" we track a maximum of self.differentialHandlesMaxPerUser
            users={}
            for handle,entry in self.differentialHandles.items():
                user = entry["user"]
                if user not in users:
                    users[user]={}
                users[ user][ handle ] = entry["time"]
            for user,entries in users.items():
                if len(entries)> self.differentialHandlesMaxPerUser:
                    #must clean up history of that user, entries is a dict of handle:time
                    sortedKeys =[key for key, value in sorted(entries.items(), key=lambda item: item[1])]
                    removeKeys = sortedKeys[:-self.differentialHandlesMaxPerUser]
                    self.logger.debug("remove handle"+str(removeKeys)+" of user"+user)
                    for key in removeKeys:
                        del self.differentialHandles[key]





            #find the changes between the models
            for newNodeId in newModel:
                if newNodeId not in oldModel:
                    #this node is not found in the old model, so it is new
                    diff["newNodes"][newNodeId]=copy.deepcopy(newModel[newNodeId])
                else:
                    #this node is in both models, check if there was a change insight the nodes
                    #for a deep comparison, serialize them
                    newNodeSerialized = json.dumps(newModel[newNodeId],sort_keys=True)
                    oldNodeSerialized = json.dumps(oldModel[newNodeId],sort_keys=True)
                    if newNodeSerialized != oldNodeSerialized:
                        #something is different, so return that node
                        diff["modifiedNodes"][newNodeId]=copy.deepcopy(newModel[newNodeId])

            #now check for deleted once, these appear in the old but not in the new
            diff["deletedNodeIds"]=list(set(oldModel.keys())-set(newModel.keys()))
            diff["handle"]=newHandle

            return diff


    def publish_event(self, event):
        """
            send out an event e.g. for status information
            event to send looks like
                event = { "id": 1123,
                            "event": "system.status"
                            "data:"{"nodeId":xx, "value":..,"function":... ...}
                            }
            Args
                event [string or dict]
        """

        self.modelUpdateCounter += 1

        if type(event) is str:
            event={"event":"system.status","data":{"text":event}}
        event["id"]=self.modelUpdateCounter

        for observerObject in self.observers:
            observerObject.update(event)


    def disable_observers(self):
        with self.lock:
            self.disableObserverCounter += 1
            self.logger.debug(f"disable_observers() {self.disableObserverCounter}")
    def enable_observers(self):
        with self.lock:
            if self.disableObserverCounter >0:
                self.disableObserverCounter -=1
            else:
                self.logger.error("enable_observers without disable observers")
        self.logger.debug(f"enable_observers() {self.disableObserverCounter}")

    def notify_observers(self, nodeIds, properties):
        """
            public wrapper for __notify observser, only expert use!
        """
        self.logger.info(f"notify observser, {nodeIds}, {properties}")
        return self.__notify_observers(nodeIds,properties)

    def __notify_observers(self, nodeIds, properties ):
        """
            this function is called internally when nodes or properties have changed. Then, we look if any
            observer has to be triggered
            we also increase the counter and time on the root.observers.modelObserver
            Args:
                nodeId: the nodeId where a change occurred
                properties: the property or list of properties of the node that has changed

        """

        # for now we only do the tree update thing
        if self.disableObserverCounter>0:
            return
        #  tree update thing
        with self.lock:
            #self.logger.debug(f"__notify_observers {nodeIds}: {properties}")
            # this is for the tree updates, any change is taken
            self.modelUpdateCounter = self.modelUpdateCounter + 1 #this is used by the diff update function and model copies
            # Notify all observers about the tree update
            event = {
                "id": self.modelUpdateCounter,
                "event": "tree.update",
                "data": ""}
            for observer in self.observers:
                observer.update(event)
                pass

            if type(properties) is not list:
                properties = [properties]
            if type(nodeIds) is  not list:
                nodeIds = [nodeIds]

            names =[self.model[id]["name"] for id in nodeIds]
            self.logger.debug(f"__notify_observers {names}: {properties}")
            #if "value" in properties:
            #    print("value")

            triggeredObservers=[] # we use this to suppress multiple triggers of the same observer, the list holds the observerIds to be triggered
            for nodeId in nodeIds:
                #now check if the node is being observed, we do everything over ids to have max speed
                #for id in self.model[nodeId]["backRefs"]:
                #paths = [ self.model[id]['browsePath'] for id in self.get_referencers(nodeId)] # this one might not work because browsepath is not available always
                #self.logger.debug(f"nodeId {nodeId} {self.get_browse_path(nodeId)}:{paths}")
                #if self.model[nodeId]["browsePath"]=="root.folder.cos":
                #    print("debug cos")


                backrefs =  self.get_referencers(nodeId,deepLevel=3) # deepLevel non standard, three parents! we support ref->ref->node->child->child->child
                for id in backrefs:
                    if self.model[id]["name"] == "targets" and self.model[self.model[id]["parent"]]["type"] == "observer":
                        # this node is being observed,
                        observerId = self.model[id]["parent"]
                        observer = self.get_children_dict(observerId)
                        # check if trigger
                        if observer["enabled"]["value"] == True:
                            #self.logger.debug(f"{self.model[nodeId]['name']} is targeted by observer {self.get_browse_path(observerId)}")
                            if observerId in triggeredObservers:
                                self.logger.debug(f"we have triggered the observer {self.get_browse_path(observerId)} in this call already, pass")
                                continue
                            for property in properties:
                                if property in observer["properties"]["value"]:
                                    #self.logger.debug(f"observer trigger on {self.get_browse_path(observerId)} for change in {property}")
                                    self.model[observer["triggerCounter"]["id"]]["value"] = self.model[observer["triggerCounter"]["id"]]["value"]+1
                                    self.model[observer["lastTriggerTime"]["id"]]["value"] = datetime.datetime.now().isoformat()
                                    for funcNodeId in self.get_leaves_ids(observer["onTriggerFunction"]["id"]):
                                        self.logger.debug(f"execute ontrigger function {funcNodeId}")
                                        self.execute_function(funcNodeId)
                                    if "triggerSourceId" in observer:
                                        self.model[observer["triggerSourceId"]["id"]]["value"] = nodeId
                                    if observer["hasEvent"]["value"] == True:
                                        #self.logger.debug(f"send event {observer['eventString']['value']}")
                                        #also send the real event
                                        #self.modelUpdateCounter = self.modelUpdateCounter+1
                                        event = {
                                            "id": self.modelUpdateCounter,
                                            "event": observer["eventString"]["value"],
                                            "data": {"nodeId":observerId,"sourceId":nodeId,"sourcePath":self.get_browse_path(nodeId)}}
                                        if self.model[nodeId]["type"] not in ["column","file","timeseries"]:
                                            event["data"]["value"]=self.model[nodeId]["value"]
                                        #some special handling
                                        try:
                                            if event["event"] == "system.progress":
                                                progressNode = self.get_node(self.get_leaves_ids("root.system.progress.targets")[0])
                                                event["data"]["value"]=progressNode.get_value()
                                                event["data"]["function"]=progressNode.get_parent().get_parent().get_browse_path()
                                            else:
                                                eventNode = self.get_node(observerId)
                                                extraInfoNode = eventNode.get_child("eventData")
                                                if extraInfoNode:
                                                    extraInfo = extraInfoNode.get_value()
                                                    if type(extraInfo) is not dict:
                                                        extraInfo={"info":extraInfo}
                                                    event["data"].update(extraInfo)

                                        except Exception as ex:
                                            self.logger.error(f"error getting extra info for event {ex}, {sys.exc_info()[0]}")
                                        #for all other events, take the event data if there is one (as json)

                                        self.logger.debug(f"send event {event}")
                                        for observerObject in self.observers:
                                            observerObject.update(event)
                                    triggeredObservers.append(observerId)# next time, we don't trigger
                                    break # leave the properties, we only trigger once

    def create_observer(self):
        # Instantiate a new observer
        observer = Observer(self)
        # attach it to the model
        self.attach_observer(observer)
        # return the observer
        return observer

    def attach_observer(self, observer):
        # Add a new observer
        self.logger.debug(f"Adding new observer: {id(observer)}")
        with self.lock:
            self.observers.append(observer)

    def detach_observer(self, observer):
        with self.lock:
            try:
                self.observers.remove(observer)
                self.logger.debug(f"Removing observer: {id(observer)}")

            except ValueError:
                self.logger.exception("Trying to remove an observer which doesn't exist in the list of observers.")
  
    def set_column_len(self,nodeDescriptor,newLen):
        """
            adjust the len of a colum, extension are inf-padded,
            Args: nodeDescriptor: the node
                    newLen (int) the new lenth of the column
            Returns:
                    the new value set or none if problem
        """
        with self.lock:
            id = self.get_id(nodeDescriptor)
            if not id: return None
            if self.model[id]["type"] != "column":
                self.logger.error("set_column_len: not a column")
                return None
            #now make the adjustments
            if type(self.model[id]['value']) != numpy.ndarray:
                self.model[id]['value'] = numpy.full(newLen, numpy.nan)
            else:
                #is already an array
                if len(self.model[id]['value']) == newLen:
                    #nothing to do
                    pass
                if len(self.model[id]['value']) > newLen:
                    self.model[id]['value'] = self.model[id]['value'][0:newLen]
                elif len(self.model[id]['value']) < newLen:
                    self.model[id]['value'] = numpy.append(self.model[id]['value'], numpy.full(dataLen-len(self.model[id]['value']), numpy.nan))
                else:
                    #same len
                    pass
                return newLen

    def update(self):
        """
            update all known widgets to the latest template including complex backward compatibility changes
            :return:
        """
        self.logger.info("update() running...")
        self.disable_observers()
        try:
            # the ts widgets:
            # now go throught the widget and update all according the template
            # now find all type widget
            newNodes = {}
            helperModel = Model()
            helperModel.disable_observers()
            helperModel.create_template_from_path("root.widget", self.get_templates()['templates.timeseriesWidget'])

            widgets = []
            for id, props in self.model.items():
                if props["type"] == "widget":
                    widgetObject = self.get_node(id)
                    if widgetObject.get_child("widgetType").get_value() == "timeSeriesWidget":
                        widgets.append(id)
                        self.logger.debug(f"update():found widget {widgetObject.get_browse_path()}")

            for id in widgets:
                path = self.get_browse_path(id)
                mirrorBefore = self.get_branch_pretty(path)
                self.create_template_from_path(path,self.get_templates()['templates.timeseriesWidget']) # this will create all nodes which are not there yet

                # now make specific updates e.g. linking of referencers, update of list to dicts etc.
                # if colors is a list: make a dict out of it
                colors = self.get_value(f"{id}.hasAnnotation.colors")
                tags = self.get_value(f"{id}.hasAnnotation.tags")
                if type(colors) is list:
                    colors = {v:{"color":colors[idx],"pattern":None} for idx,v in enumerate(tags)}
                    self.logger.debug(f"update(): set value{id}.hasAnnotation.colors := {colors} ")
                    self.set_value(f"{id}.hasAnnotation.colors",colors)

                if not "visibleTags" in mirrorBefore["hasAnnotation"] or (self.get_value(f"{id}.hasAnnotation.visibleTags") != mirrorBefore["hasAnnotation"]["visibleTags"][".properties"]["value"]):
                    #it is different or new, so we created it now
                    visibleTags = {tag:True for tag in tags}
                    #make sure that from the colors, we take them as well
                    updateVisibleTags = {tag:True for tag in colors}
                    visibleTags.update(updateVisibleTags)

                    self.set_value(f"{id}.hasAnnotation.visibleTags",visibleTags)
                    self.logger.debug(f"update(): set value{id}.visibleTagss := {visibleTags} ")

                #make sure the hasAnnotation.annotations referencer points to newannotations as well
                self.add_forward_refs(f"{id}.hasAnnotation.annotations",[f"{id}.hasAnnotation.newAnnotations"],allowDuplicates=False)

                #now make sure the observers have at least the required properties enabled
                widget = self.get_node(id)
                helperRoot = helperModel.get_node("root.widget")
                template = self.get_templates()['templates.timeseriesWidget']

                children = helperRoot.get_children(3)
                print(f"2 level children {[node.get_browse_path() for node in children]}")
                for child in helperRoot.get_children():
                    if child.get_properties()["type"] == "observer":
                        widgetNode = widget.get_child(child.get_name()).get_child("properties")
                        helperNode = child.get_child("properties")

                        for prop in helperNode.get_value():
                            current = widgetNode.get_value()
                            if prop not in current:
                                current.append(prop)
                                widgetNode.set_value(current)

                for child in helperRoot.get_children(3):
                    if child.get_properties()["type"] == "referencer":
                        self.logger.debug(f"found referencer {child.get_name()}")
                        # now adjust the references of new nodes and of the ones that were there
                        targets = child.get_properties()["forwardRefs"]
                        if targets:
                            targets = [helperModel.get_browse_path(ref) for ref in targets]
                            requiredTargets = [widget.get_browse_path()+"."+".".join(ref.split(".")[2:]) for ref in targets]
                            self.logger.debug(f"required targets {requiredTargets}")
                            #now check in the model
                            widgetNodePath = widget.get_browse_path()+ child.get_browse_path()[len(helperRoot.get_browse_path()):]
                            widgetNode = self.get_node(widgetNodePath)
                            #now check if we have them
                            targetPaths = [tNode.get_browse_path() for tNode in widgetNode.get_targets()]
                            for target in requiredTargets:
                                if target not in targetPaths:
                                    self.logger.debug(f"adding ref {widgetNode.get_browse_path()} => {target}")
                                    self.add_forward_refs(widgetNode.get_id(),[target])



            #now the system progress observer
            if not self.get_node("root.system.progress"):
                self.create_template_from_path("root.system.progress",self.get_templates()['system.observer'])
                self.set_value("root.system.progress.hasEvent",True)
                self.set_value("root.system.progress.eventString","system.progress")
                self.set_value("root.system.progress.properties",["value"])
                self.set_value("root.system.progress.enabled",True)


        except Exception as ex:
            self.logger.error(f" {ex} , {sys.exc_info()[0]}")
            helperModel.delete()

        helperModel.delete()
        self.enable_observers()

    # ########################################
    # time series api

    def time_series_create(self,desc):
        id = self.get_id(desc)
        return self.ts.create(id)

    def time_series_delete(self,desc):
        id = self.get_id(desc)
        return self.ts.delete(id)

    def time_series_insert_data(self, desc, values=None, times=None):
        id = self.get_id(desc)
        if not id in self.model:
            return None
        result =  self.ts.insert(id,values, times)
        self.__notify_observers(id, "value")
        return result

    def time_series_set(self,desc,values=None,times=None):
        id = self.get_id(desc)
        if not id in self.model:
            return None
        result =  self.ts.set(id,values=values,times=times)
        self.__notify_observers(id, "value")
        return result

    def time_series_get_table(self,
                              variables,
                              tableDescriptor = None,
                              start=None,
                              end=None,
                              noBins=None,
                              includeIntervalLimits=False,
                              resampleTimes=None,
                              format="default",
                              toList = False,
                              resampleMethod = None):
        """
            get a time series table from variables (nodes of type "timeseries").


            Args:
                variables [list of ode descriptors]: nodes to be part the data table requested (ordered!)

                tableDescriptor : a desc for the table where the variables reside
                    possible addressing of te request nodes:
                    1) ids or browsepaths of nodes (no tableDescriptor needed)
                    2) names of nodes and tableDescriptor of the table (names must be unique in the columns of the table)

                startime, endTime [float]:
                                the start and endtime of the table given as seconds since epoch
                                we also allow the special case of endTime = 0 and startTime = -interval
                                we also allow the special case of startTime given and end time= 0

                noBins(int): the number of samples to be returned inside the table between start end endtime,
                             if None is given, we return all samples (rows) we have in the table and to not aggregate

                includeIntervalLimits [bool]: if set to true, we will include one more data point each left and right of the requested time

                format:  [enum] "default", "flat", see return description


                resampleMethod [enum]:
                    how to resample if we need to; options are:
                    None (if not specified): sample and hold
                    "linear": linear interpolation
                    "linearfill": linear interpolation and also interpolate "nan" or "inf" values in the original data

                toList: (bool) True: return data as python list, False: return numpy arrays

                examples:
                - get all data of the variables
                    data = m.get_time_series_table(["root.mytable.variables.a","root.mytable.variables.b"]) # get all data
                - request max 300 values of data (this is what the UI does)
                    data = m.get_time_series_table(["a","b"],"root.mytable",start=1581483065.323,end=1581483080.323,noBins=300,includeIntervalLimits=True)
                - request data and resample to equiditant 25 sec spacing, also fill possible nan values with interpolation
                    times = list(range(1581483065,1581483065+100,25))
                    data = m.get_time_series_table(["a","b"],"root.mytable",resampleTimes = times,resampleMethod = "linearfill")


            Returns(dict)
                formatting depends on the "format" option
                 "defaut": return the result as {"var_a":{"values":[],"__time":[]}, "var_b":{"values":[],"__time":[]..}
                    "flat" return the result as {"var_a":[], "var_a__time":[],"var_b":[],"var_b__time":[]....}
                the variable descriptor are the ones given in the request
                    "__time" : list of timestamps for the returned table in epoch seconds as float64
                    "values": the list of float values of one of the requested variables
        """
        if tableDescriptor:
            tableId = self.get_id(tableDescriptor)
            tableVars = self.get_leaves(tableId+".columns")
        else:
            tableId = None

        if type(start) is str:
            start = date2secs(start)
        if type(end) is str:
            end = date2secs(end)

        with self.lock:
            #first check if all requested timeseries exist and have type time series
            #vars = [] #self.get_id(variables)

            if not type(variables) is list:
                variables= [variables]

            varIds = {} # NodeId: request descriptor
            for var in variables:
                varId = self.get_id(var)
                if not varId:
                    #try to find per columns and table desc
                    found = False
                    if tableId:
                        for tableVar in tableVars:
                            if tableVar["name"] == var:
                                varId = tableVar["id"]
                                found = True
                                break

                    if not found:
                        self.logger.error(f"requested variable {var} does not exist")
                        return False
                if self.model[varId]["type"]!="timeseries":
                    self.logger.error(f"requested variable {var} not timeseries, instead {self.model[varId]['type']}")
                    return False

                varIds[varId]=var #remeber it for later

            table = self.ts.get_table(list(varIds.keys()), start=start, end=end, copy=copy, resampleTimes=resampleTimes, noBins = noBins, includeIntervalLimits=includeIntervalLimits,resampleMethod=resampleMethod)

        #now wrap back the descriptor to the query, if is was a browsepath, we return and browsepath, if is was an id, we return id
        # make some formatting
        def convert(input,toList=toList):
            if toList:
                return list(input)
            else:
                return input

        result = {}
        for k,v in table.items():
            if format=="flat":
                result[varIds[k]]=convert(v["values"])
                result[varIds[k]+"__time"]=convert(v["__time"])
            else:
                result[varIds[k]] = {"values":convert(v["values"]),"__time":convert(v["__time"])}

        #if len(variables) == 1:
        #    #we only have one variable, so we return without descriptor
        #    result = result[list(result.keys())[0]]

        return result

    def time_series_get_info(self,name=None):
        return self.ts.get_info(name)


    def time_series_insert_blobs(self, tableDesc, blobs=[]):
        """ blob is a dict or list of dicts of key and values containing one time base like
        the descriptors of teh variables can be ids, browsepaths or just names (without dots)
        if the descriptors are names, we try to find them in the model, they must exist there uniquely, otherwise
        they cant be processed
        we also autocreate the table or missing variables

        the data will be put in a table:
         - we try to find the table based on one of the variables, if not found, we create the table

        {
            "a": [1.5,1.6,1.7]m
            "b": [2,3,4]
            "__time" :[100001,100002,100003]
        }
        """
        if not type(blobs) is list:
            blobs=[blobs]

        #first, find the table
        with self.lock:
            tableId = self.get_id(tableDesc)
            if not tableId:
                #try to find the table from the first node

                #table not found, create it
                tableId = self.create_node_from_path(tableDesc,properties={"type":"table"})
                if tableId:
                    columnsId = self.create_node(parent=tableId, name="columns", properties={"type": "referencer"})
                    variablesId = self.create_node(parent=tableId, name="variables", properties={"type": "folder"})
                else:
                    self.logger.error(f"cant create table {tableDesc}")
                    return False
            else:
                columnsId = self.get_child(tableId,"columns")
                variablesId = self.get_child(tableId, "variables")

            #now we know the tableId, columnsId, variablesId

        # iterate over all blobs and find the ids of the names in the blobs, if not found, create it
        # exchange the descriptors to ids

        desc2Id = {} # key: the descriptor from the input blob v: the id in the model

        tableVars = self.get_leaves(columnsId)
        desc2Id = {dic["name"]:dic["id"] for dic in tableVars}  # key: the descriptor from the input blob v: the id in the model, preload with the names

        #convert all to ids
        newBlobs=[]
        for blob in blobs:
            newBlob={}
            for k,v in blob.items():

                if k=="__time":
                    newBlob[k]=v
                else:
                    #does this id already exist?
                    if k in desc2Id:
                        id = desc2Id[k]
                    else:
                        id = None
                        #try to find
                        for var in tableVars:
                            if var["name"] == k:
                                id = v["id"]
                                break
                        if not id:
                            #still not found, we need to create it
                            id = self.create_node(parent=variablesId,name=k,properties={"type": "timeseries"})
                        if not id:
                            self.logger.error(f"cant find  or create {name}")
                            continue
                        else:
                            self.add_forward_refs(columnsId,[id])
                            desc2Id[k]=id #remember to speed up next time

                    newBlob[id] = v
            newBlobs.append(newBlob)
        self.logger.debug(f"inserting blobs {len(newBlobs)}")
        self.__notify_observers([v for k,v in desc2Id.items()], "value")
        return self.ts.insert_blobs(newBlobs)


    def create_test(self,testNo=1):
        """
            this functions crates tests for demostrating purposes
        """
        if testNo == 1:
            self.create_node("root",name="variables",type="folder")
            for var in ["f0","f1","f2","f3","count","time","back"]:
                self.create_node("root.variables",name=var,type="column")
            self.create_node_from_path('root.folder2.myconst',{"type":"const","value":"21data"})
            self.create_node_from_path('root.folder2.myfkt', {"type": "function"})

            #for the visu
            self.create_node_from_path('root.visualization.pipelines.occupancy.url',{"type":"const","value":"http://localhost:5006/bokeh_web"})
            self.create_node_from_path('root.visualization.pipelines.demo2.url',{"type":"const","value":"http://21data.io"})


            #create an official table
            template = [
                {
                    "name": "description",
                    "type": "const",
                    "value": "this is a great table"
                },
                {
                    "name": "columns",
                    "type": "referencer",
                },
                {
                    "name": "timeField",
                    "type": "referencer",
                },
                {
                    "name": "numberOfRows",
                    "type": "variable",
                    "value": 0
                }

            ]
            self.create_node("root", name="mytable", type="table")
            self.create_nodes_from_template("root.mytable", template=template)
            for var in ["f0","f1","f2","f3","time","back"]:
                self.add_forward_refs("root.mytable.columns",["root.variables."+var])
            self.add_forward_refs("root.mytable.timeField", ["root.variables.time"])

            #add data
            startTime=datetime.datetime(2018,1,1,0,0,0,tzinfo=pytz.UTC)
            vars={"f0":0.01,"f1":0.02,"f2":0.04,"f3":0.1,"back":0.01}
            SIZE = 10*60  # in  seconds units
            STEP = 0.1
            #!!! we are producing size/step time points

            """ for i in range(SIZE):
                dataDict = {}
                for var in vars:
                    value = numpy.cos(2*numpy.pi*vars[var]*i/SIZE*3)
                    dataDict["root.variables."+var]=value
                mytime = startTime + datetime.timedelta(seconds = i)
                dataDict["root.variables.time"] = mytime
                #print(mytime)
                self.add_timeseries(dataDict)
            """

            startEpoch = date2secs(startTime)
            times = numpy.arange(startEpoch,startEpoch+SIZE,STEP,dtype=numpy.float64)
            print("we have time:",times.shape)
            for var in vars:
                values = numpy.cos(2*numpy.pi*vars[var]*times)
                id=self.get_id("root.variables."+str(var))
                if var =="back":
                    #we make -1,0,1 out of it
                    values = numpy.round(values)
                self.model[id]["value"]=values.tolist()
            id = self.get_id("root.variables.time")
            self.model[id]["value"]=(times).tolist()
            #now correct the background



            #now make some widget stuff
            self.create_node_from_path('root.visualization.widgets.timeseriesOne',{"type":"widget"})
            self.create_node_from_path('root.visualization.widgets.timeseriesOne.selectableVariables',
                                       {"type":"referencer"})
            self.create_node_from_path('root.visualization.widgets.timeseriesOne.selectedVariables',
                                       {"type": "referencer"})
            self.create_node_from_path('root.visualization.widgets.timeseriesOne.startTime',
                                       {"type": "variable","value":None})
            self.create_node_from_path('root.visualization.widgets.timeseriesOne.endTime',
                                       {"type": "variable","value":None})
            self.create_node_from_path('root.visualization.widgets.timeseriesOne.bins',
                                       {"type": "const","value":300})
            self.create_node_from_path('root.visualization.widgets.timeseriesOne.hasAnnotation',
                                       {"type": "const", "value": True})
            self.create_node_from_path('root.visualization.widgets.timeseriesOne.hasSelection',
                                       {"type": "const", "value": False})
            self.create_node_from_path('root.visualization.widgets.timeseriesOne.hasAnnotation.annotations',
                                       {"type": "referencer"})
            self.create_node_from_path('root.visualization.widgets.timeseriesOne.hasAnnotation.newAnnotations',
                                       {"type": "folder"})


            self.create_node_from_path('root.visualization.widgets.timeseriesOne.hasAnnotation.tags',
                                       {"type": "const","value":["one","two"]})
            self.create_node_from_path('root.visualization.widgets.timeseriesOne.hasAnnotation.colors',
                                       {"type": "const","value":["yellow","brown","greay","green","red"]})


            self.create_node_from_path('root.visualization.widgets.timeseriesOne.table',
                                       {"type": "referencer"})
            self.create_node_from_path('root.visualization.widgets.timeseriesOne.lineColors',
                                       {"type": "const", "value": ["blue", "yellow", "brown", "grey", "red"]})
            self.add_forward_refs('root.visualization.widgets.timeseriesOne.selectedVariables',['root.variables.f0','root.variables.f1','root.variables.f3'])
            self.add_forward_refs('root.visualization.widgets.timeseriesOne.selectableVariables',['root.variables'])
            self.add_forward_refs('root.visualization.widgets.timeseriesOne.table',['root.mytable'])

            self.create_node_from_path('root.visualization.widgets.timeseriesOne.observer',{"type":"referencer"})
            self.create_node_from_path('root.visualization.widgets.timeseriesOne.observerUpdate', {"type": "const","value":["line","background","annotations"]})



            #now the annotations
            anno = [
                {
                    "name": "tags",
                    "type": "const",
                    "value": ["one","two"]
                },
                {
                    "name": "startTime",
                    "type": "const",
                    "value": None
                },
                {
                    "name": "endTime",
                    "type": "const",
                    "value": None
                },
                {
                    "name": "text",
                    "type": "const",
                    "value": "this is a great annotation"
                }

            ]

            tags=["one","two","one","one","two","two","one","one","one","two","one","one"]
            self.create_node_from_path("root.annotations",{"type":"folder"})
            startTime = datetime.datetime(2018, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
            for i in range(10):
                newAnno = copy.deepcopy(anno)
                newAnno[1]["value"] = (startTime + datetime.timedelta(minutes=(i*10))).isoformat()
                newAnno[2]["value"] = (startTime + datetime.timedelta(minutes=(i*10+1))).isoformat()
                newAnno[0]["value"] = [tags[i],tags[i+1]]
                newAnnoPath = "root.annotations.anno"+str(i)
                self.create_node_from_path(newAnnoPath,{"type":"annotation"})
                self.create_nodes_from_template(newAnnoPath,newAnno)

            #also add the annotations to the widget
            self.add_forward_refs("root.visualization.widgets.timeseriesOne.hasAnnotation.annotations",["root.annotations","root.visualization.widgets.timeseriesOne.hasAnnotation.newAnnotations"])


            #make a real function
            self.create_node_from_path("root.functions",{"type":"folder"})
            self.create_nodes_from_template("root.functions",[self.templates["testfunction.delayFunctionTemplate"]])

            #now make cutom function to trigger something
            self.create_nodes_from_template("root.functions",[self.templates["counterfunction.counterFunctionTemplate"]])
            #now hook the function output to the observer of the plot
            self.add_forward_refs('root.visualization.widgets.timeseriesOne.observer',['root.functions.counterFunction.output'])

            #now make custom buttons
            buttons = [
                {
                    "name":"button1",
                    "type":"folder",
                    "children":[
                        {"name":"caption","type":"const","value":"start learner"},
                        {"name":"counter", "type": "variable", "value":0},
                        {"name": "onClick", "type": "referencer"}
                    ]
                }
            ]
            self.create_node_from_path("root.visualization.widgets.timeseriesOne.buttons",{"type":"folder"})
            self.create_nodes_from_template("root.visualization.widgets.timeseriesOne.buttons",buttons)
            self.add_forward_refs("root.visualization.widgets.timeseriesOne.buttons.button1.onClick",["root.functions.counterFunction"])


            #now the backgrounds
            self.create_node_from_path("root.visualization.widgets.timeseriesOne.hasBackground",{"type":"const","value":True})
            self.create_node_from_path("root.visualization.widgets.timeseriesOne.background",{"type":"referencer"})
            self.add_forward_refs("root.visualization.widgets.timeseriesOne.background",["root.variables.back"])
            self.create_node_from_path("root.visualization.widgets.timeseriesOne.backgroundMap",{"type":"const","value":{"1":"red","0":"green","-1":"blue","default":"white"}})


            self.show()

        elif testNo == 2:
            #we take the full test number 1 and rearrange some things
            self.create_test(1)
            self.currentModelName = "occupancydemo"

            import data.occupancy_data.occupancy as occ
            occData = occ.read_occupancy("./data/occupancy_data/datatest2.txt")

            #create an official table
            template = [
                {
                    "name": "description",
                    "type": "const",
                    "value": "this is the occupancy data table"
                },
                {
                    "name": "columns",
                    "type": "referencer",
                },
                {
                    "name": "timeField",
                    "type": "referencer",
                },
                {
                    "name": "variables",
                    "type": "folder",
                }

            ]
            self.create_node("root", name="occupancy", type="table")
            self.create_nodes_from_template("root.occupancy", template=template)
            for var in occData:
                path = "root.occupancy.variables."+var
                self.create_node_from_path(path,{"type":"column"})
                self.set_value(path,occData[var])
                self.add_forward_refs("root.occupancy.columns",[path])
            self.add_forward_refs("root.occupancy.timeField",["root.occupancy.variables.date"])
            #now create the classification
            self.create_node("root.occupancy", name="classification", type="column")
            self.set_value("root.occupancy.classification", [0]*len(occData[list(occData.keys())[0]]))
            self.add_forward_refs("root.occupancy.columns", ["root.occupancy.classification"])

            #create another TS-widget
            self.create_node_from_path('root.visualization.widgets.timeseriesOccupancy', {"type": "widget"})
            self.create_nodes_from_template('root.visualization.widgets.timeseriesOccupancy',modeltemplates.timeseriesWidget)
            self.create_nodes_from_template('root.visualization.widgets.timeseriesOccupancy.buttons.button1',modeltemplates.button)
            self.add_forward_refs('root.visualization.widgets.timeseriesOccupancy.selectedVariables',["root.occupancy.variables.Temperature"])
            self.add_forward_refs('root.visualization.widgets.timeseriesOccupancy.selectableVariables',["root.occupancy.variables"])
            self.add_forward_refs('root.visualization.widgets.timeseriesOccupancy.table',['root.occupancy'])
            self.add_forward_refs('root.visualization.widgets.timeseriesOccupancy.background',['root.occupancy.classification'])
            self.set_value('root.visualization.widgets.timeseriesOccupancy.backgroundMap', {"0": "brown", "1": "yellow", "-1": "blue", "default": "white"}) #match annotation colors
            #self.set_value('root.visualization.widgets.timeseriesOccupancy.backgroundMap', {"0": "blue", "1": "black", "-1": "blue", "default": "white"}) #match annotation colors
            self.set_value('root.visualization.widgets.timeseriesOccupancy.hasAnnotation.tags',["busy","free"])

            #now create the logistic regression
            self.create_nodes_from_template('root',[self.templates["logisticregression.logisticRegressionTemplate"]])
            self.add_forward_refs('root.logisticRegression.input',['root.occupancy.variables.Temperature', 'root.occupancy.variables.Light','root.occupancy.variables.CO2'])
            self.add_forward_refs('root.logisticRegression.output', ['root.occupancy.classification'])
            self.add_forward_refs('root.logisticRegression.annotations',['root.visualization.widgets.timeseriesOccupancy.hasAnnotation.newAnnotations'])
            self.set_value('root.logisticRegression.categoryMap', {"busy": 1, "free": 0})
            #also hook the button on it
            self.add_forward_refs('root.visualization.widgets.timeseriesOccupancy.buttons.button1.onClick',['root.logisticRegression'])

            self.add_forward_refs('root.visualization.widgets.timeseriesOccupancy.observer',['root.logisticRegression.executionCounter']) # observe the execution of the scorer

            self.show()

        elif testNo == 3:
            # make some nodes

            for id in range(10):
                self.create_node_from_path("root.add.var"+str(id), {"type": "variable", "value": id+100})
            for id in range(100):
                self.create_node_from_path("root.remove.var"+str(id), {"type": "variable", "value": id+100})

            self.create_node_from_path("root.change_name_one")
            self.create_node_from_path("root.change_value")

            self.create_node_from_path("root.move.first")
            self.create_node_from_path("root.move.second")

            self.create_node_from_path("root.refs",properties={"type":"referencer"})
            self.add_forward_refs("root.refs",["root.move.first","root.move.second","root.move"])


            #now start a thread that changes the tree periodically

            def __update_tree():
                while True:
                    time.sleep(3.0)
                    with self.lock:
                        self.logger.debug("__update_tree")

                        self.create_node_from_path("root.add.dyn"+str(uuid.uuid4()))
                        removeFolder = self.get_id("root.remove")
                        if self.model[removeFolder]["children"]:
                            self.delete_node(self.model[removeFolder]["children"][0])

                        id = self.get_id("root.change_name_one")
                        if id:
                            self.model[id]["name"]="change_name_two"
                        else:
                            id = self.get_id("root.change_name_two")
                            self.model[id]["name"]="change_name_one"

                        id = self.get_id("root.move")
                        self.model[id]["children"].reverse()

                        id=self.get_id("root.refs")
                        self.model[id]["forwardRefs"].reverse()

                        self.set_value("root.change_value",int(uuid.uuid4())%100)


            self.testThread = threading.Thread(target=__update_tree)
            self.testThread.start()






if __name__ == '__main__':


    def test1():
        m=Model()
        m.create_node("root",name="folder1")
        m.create_node("root.folder1",name="folder2")
        m.create_node("2",name="second")
        m.create_node("root",name="myreferencer",type="referencer")
        m.create_node("root.folder1",name="myvar",type="variable")
        m.set_value("root.folder1.myvar",44.5)
        m.add_forward_refs("root.myreferencer",["root.folder1"])
        m.add_property("root.folder1.folder2","uasource","192.168.5.6")
        m.show()
        m.get_model()
        m.delete_node("root.myreferencer")

        return m


    def test_template():
        m=Model()
        template = {
            "myfunction": {
                "type": "function",
                "value": "someValue",
                "opcua":"opc.tcp://129.160.1.1:4880::n2=2;s=mystrin"
            },
            "myreferencer": {
                "type": "referencer",
                "forwardRefs": ['.myfolder.var1', '.myfolder.var2', '.myfolder.var3']
            },
            "myfolder": {
                "type": "folder",
                "children": {
                    "var1": {"type": "const", "value": "1"},
                    "var2": {"type": "variable"},
                    "var3": {"type": "timeseries"},
                }
            },

        }
        m.create_nodes_from_template(template=template)
        m.show()

    def save_test():
        print("save and load test")
        m=Model()
        m.create_test()

        m.save("savetest")

        n=Model()
        n.load("savetest")

        if len(n.get_model())!= len(m.get_model()):
            print("unequal size")
            return False
        #now compare
        mModel = m.get_model()
        nModel = n.get_model()
        for nodeId in mModel:
            #print("check",nodeId)
            try:
                if nModel[nodeId]!=mModel[nodeId]:
                    print("unequal before after ",nodeId,m[nodeId],n[nodeId])
                    return False
            except:
                print("cant find",nodeId)
                return False

        print("savetest passed")
        return True


    def plugintest():
        m=Model()
        m.create_node("root", name="folder1")
        m.create_nodes_from_template("root.folder1",m.templates["testfunction.delayFunctionTemplate"])
        m.show()
        m.execute_function("root.folder1.delayFunction")
        statusNode = m.get_node("root.folder1.delayFunction.status")
        progressNode = m.get_node("root.folder1.delayFunction.progress")

        while(statusNode.get_value()!="finished"):
            print("progress is",progressNode.get_value())
            time.sleep(0.3)



        print("execution re===================")
        m.show()

    def getnodetest():
        m=Model()
        m.create_node("root", name="folder1")
        m.create_node("root.folder1", name="folder2")
        m.create_node("root.folder1", name="myvar", type="variable")
        myvar = m.get_node("root.folder1.myvar")
        myvar.set_value(33)
        print("value",myvar.get_value())





    def testfunctions_test():
        m = Model()
        m.create_test(1)
        m.show()

        table= m.get_timeseries_table(["root.variables.f0","root.variables.f1","root.variables.time"],noBins=25)
        print("shape",table.shape)
        for row in table.T:
            for elem in row:
                print(str("%3.7f"%elem)," ",end="")
            print("")

    def time_conver_test():
        d1=datetime.datetime(2018,1,1,0,0,0,tzinfo = pytz.UTC)
        print(d1)
        s1 = date2secs(d1)
        print(s1)
        d2 = secs2date(s1)
        print(d2)

        d3 ="2018-01-01T00:10:08.445+02:00"
        print(d3)
        d4=dateutil.parser.parse(d3)
        print(d4)
        s4=date2secs(d4)
        print(s4)
        d5=secs2date(s4)
        print(d5)

    def table_test():
        m=Model()
        print("this test creates a table and writes some data in")

        template = [
            {
                "name": "type",
                "type": "const",
                "value": "timeSeriesTable"
            },
            {
                "name":"description",
                "type": "const",
                "value": "this is a great table"
            },
            {
                "name":"data",
                "type":"folder",
                "children":[
                    {"name":"var1","type": "column","value":[]},
                    {"name":"var2","type": "column","value":[]},
                    {"name":"var3","type": "column","value":[]},
                    {"name":"time","type": "column","value":[]}
                ]
            },
            {
                "name":"columns",
                "type": "referencer",
                "forwardRefs": ['.data.var1', '.data.var2', '.data.var3',".data.time"]
            },
            {
                "name":"timeField",
                "type": "referencer",
                "forwardRefs":['.data.time']
            },
            {
                "name": "numberOfRows",
                "type": "variable",
                "value":0
            }

        ]
        m.create_node("root", name="mytable",type="table")
        m.create_nodes_from_template("root.mytable",template=template)
        m.show()

        #now write some data with autocreates
        mytime = datetime.datetime.now(pytz.timezone("CET"))
        myepoch=date2secs(mytime)
        blob = {"root.mytable.data.var1":1,"root.mytable.data.var2":2,"root.mytable.data.time":myepoch,"root.mytable.data.newvar":99}
        m.append_table(blob)
        m.show()

        #now add more data but leave out var
        blob = {"root.mytable.data.var1": 10, "root.mytable.data.var2": 20, "root.mytable.data.time": myepoch}
        m.append_table(blob)
        blob = {"root.mytable.data.var1": 10, "root.mytable.data.var2": 20, "root.mytable.data.var4": 4, "root.mytable.data.time": myepoch}
        m.append_table(blob)
        m.show()


    def test_table_autocreate():
        mytime = datetime.datetime.now(pytz.timezone("CET"))
        myepoch=date2secs(mytime)
        blob = {"root.data.var1":1,"root.data.var2":2,"root.folder.time":myepoch,"root.data.newvar":99}
        m=Model()
        m.append_table(blob)
        m.show()


    def test_create_from_path():
        m=Model()
        m.create_node_from_path("root.myfolder.myfolder2.var",{"type":"variable","value":33})
        m.show()

    def test_get_children():
        m=Model()
        m.create_test()
        nodes = m.get_node_with_children('root.folder2')
        #lastnode = '10'
        #print(m.get_path(lastnode))
        print(json.dumps(nodes,indent=4))

    def test_create():
        m=Model()
        m.create_test(1)
        m.show()
    def test_get_forwards():#
        #in this test, we check the forwards get results over folders, referencers etc.
        m=Model()
        m.create_node_from_path("root.folder.var1",{"type":"variable"})
        m.create_node_from_path("root.folder.var2", {"type": "variable"})
        m.create_node_from_path("root.folder.var3", {"type": "variable"})
        m.create_node_from_path("root.ref1", {"type": "referencer"})
        m.create_node_from_path("root.ref2", {"type": "referencer"})
        m.add_forward_refs("root.ref1",["root.folder"])
        m.add_forward_refs("root.ref2", ["root.ref1"])

        m.show()

        res=m.get_leaves("root.ref1")
        print(res)
        for k in res:
            print(k["name"])
        res = m.get_leaves("root.ref2")
        for k in res:
            print(k["name"])

    def pickle_save():
        import pickle
        m=Model()
        m.create_test(2)
        # write python dict to a file

        output = open('pickle_save.pkl', 'wb')
        pickle.dump(m.get_model(), output)
        output.close()

        n=Model()
        # read python dict back from the file
        pkl_file = open('pickle_save.pkl', 'rb')
        restore = pickle.load(pkl_file)
        pkl_file.close()

        print("compare after pickle restre",restore==m.get_model())


if __name__ == '__main__':
    #############


    #test1()
    #ts_test1()
    #test_template()
    save_test()
    pickle_save()
    #plugintest()
    #getnodetest()
    #table_query_test()
    #testfunctions_test()
    #time_conver_test()

    #test_create_from_path()
    #table_test()
    #test_table_autocreate()
    #test_get_children()
    #test_get_forwards()
    #test_create()

    #read in the commmand line options:
    # demo1: create the test for the demo1, and store it in file (option2)
    #
    if len(sys.argv) > 1:
        if sys.argv[1] == "demo1":
            fileName = sys.argv[2]
            print("creating demo and save as ",fileName)
            m = Model()
            m.create_test()
            m.show()
            fileName = sys.argv[2]
            m.save(fileName)


