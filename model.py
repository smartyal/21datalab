import json
import copy
import importlib
import threading
import time
import logging
import pytz

#for tables
import numpy
import numpy as np
import datetime
import dateutil.parser
import sys
import os
import uuid

import modeltemplates



"""
next Todo
-  
- execute: problem im thread mit der Ausführung
- code documentation
- google document
- 
"""

sys.path.append("./plugins") #for the importlib loader, doesn't understand relative paths




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

def secs2dateString(epoch):
    """ converts seconds since epoch into a datetime iso string format 2009-06-30T18:30:00.123456+02:00 """
    try:
        stri = secs2date(epoch).isoformat()
        return stri
    except:
        return None



class Table():

   #accept columnNames as list of strings for the names of the columns
    def __init__(self,columnNames=[]):
        self.__init_logger(logging.DEBUG)
        if type(columnNames)==type(dict()):
            columnNames = list(columnNames.keys())
        #self.columnNames = columnNames
        self.data = None #  data is a list (each element is a row of the data)
        self.meta ={} # to store some meta information
        self.meta["columnNames"] = columnNames

        pass

    def __init_logger(self,level):
        self.logger = logging.getLogger("Table()")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(level)

    def get_meta_information(self):
        return self.meta

    def get_column_names_dict(self):
        namesDict = {}
        for name in self.meta["columnNames"]:
            namesDict[name]=""
        return namesDict

    def get_number_of_rows(self):
        return len(self.data)

    def update_meta(self,updateDict={}):
        return copy.deepcopy(self.meta.update(updateDict))

    # exist already, replace, else enlarge table
    def write_column(self,columnName,values):
       pass

    def __get_current_rows(self):
        pass

    #accept dict or list in right order
    def add_row(self,row):
        vector = []
        if type(row)==type(dict()):
            #make correct order first
            for name in self.meta["columnNames"]:
                vector.append(row[name])
        elif type(row) == list (list()):
            pass # this is what we expect
        else:
            print("wrong input type to table")
            return False

        entry = numpy.asarray(vector, dtype="float64")
        if self.data == None:
            self.data = [entry] # first entry
        else:
            self.data.append(entry)

        return True


    #returns a value table, including postprocessing
    def get_value_table(self,variables,startTime=None,endTime=None,noBins=None,agg="sample",includeTimeStamps=None):
        if 0:#startTime==None and endTime==None and noBins==None:
            try:
                table = numpy.stack(self.data,axis=0)
                return table.T
            except:
                return None
        else:
            self.logger.info("query with processing")
            #check the start and end times

            timeIndex = self.__get_column_index(self.get_meta_information()["timeId"])
            startTimeOfTable = self.data[0][timeIndex]
            endTimeOfTable = self.data[-1][timeIndex]
            if startTime == None:
                queryStart = startTimeOfTable
            else:
                queryStart = date2secs(startTime)
            if endTime == None:
                queryEnd = endTimeOfTable
            else:
                queryEnd = date2secs(endTime)
            #check sanity of interval
            if queryStart < startTimeOfTable :
                self.logger.warn("start time query before table start")
                return None
            if queryEnd > endTimeOfTable:
                self.logger.warn("end time of query after table end")
                return None
            print("hier2")
            #now iterate over the variables and aggregate them
            if agg == "sample":
                #here, we pick some data out
                startRow = self.__get_row_index_from_time(queryStart)
                endRow = self.__get_row_index_from_time(queryEnd)
                totalRows = endRow-startRow+1
                if noBins == None:
                    rowStep = 1
                    noBins = totalRows
                else:
                    rowStep = float(totalRows) / float(noBins)
                currentRow = startRow
                result = []
                variablesIndices = [] # holding the list of variables as indices in our table
                for var in variables:
                    variablesIndices.append(self.__get_column_index(var))
                if includeTimeStamps:
                    variablesIndices.append(self.__get_column_index(self.get_meta_information()["timeId"]))
                for i in range(noBins):
                    currentRowIndex = int(startRow + float(i)*rowStep)
                    pickRow = self.data[currentRowIndex]
                    #now select only the wanted indices
                    reducedRow = [pickRow[i] for i in variablesIndices]
                    #now select only the wanted variables
                    result.append(reducedRow)

                table = numpy.stack(result,axis=0)
                return table.T
            else:
                #other aggrataion not supported
                return None



    #return the column index of a given nodeId
    def __get_column_index(self,nodeId):
        if nodeId not in self.meta["columnNames"]:
            return None
        return self.meta["columnNames"].index(nodeId)



    def __get_row_index_from_time(self,searchTime):
        timeIndex = self.__get_time_index()
        index = 0
        for row in self.data:
            if row[timeIndex]>searchTime:
                if index>0:
                    index -= 1
                return index
            if row[timeIndex]==searchTime:
                return index
            index += 1
        return None





    def __get_time_index(self):
       return self.__get_column_index(self.get_meta_information()["timeId"])



    def save(self,fileName):
        numpytable = self.get_value_table()
        numpy.save(fileName, numpytable)
        keyfile = open(fileName+ ".meta.json", "w")
        keyfile.write(json.dumps(self.get_meta_information(), indent=4))
        keyfile.close()

    def load(self,fileName):
        try:
            f = open(fileName+ ".meta.json", "r")
            self.meta = json.loads(f.read())
            f.close()
            self.data = numpy.load(fileName + ".npy")
            return True
        except:
            print("table: problem loading",fileName,sys.exc_info()[1])
            return False



class TimeSeriesTables():
    def __init__(self):
        self.tables=[]
        self.__init_logger(logging.DEBUG)
        pass


    def __init_logger(self,level):
        self.logger = logging.getLogger("TimeSeriesTables")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(level)

    # row is a dict with all variables, try to find a matching table, if not, create a new one
    def __get_table(self,row,timeId=None):
        workTable = None
        for table in self.tables:
            if table.get_column_names_dict().keys()==row.keys():
                #this is the right table
                workTable = table
                break
        if not workTable:
            #haven't found it, make new table
            workTable = Table(row)
            if timeId:
                workTable.update_meta({"timeId":timeId})
            self.tables.append(workTable)
        return workTable

    # find to which table the variable belongs
    # the desc param can be a browsepath or be a list of
    #     the table can only be found if all of the variables are in the same table
    def __find_table(self,desc):
        if type(desc)==type(str()):
            for table in self.tables:
                if desc in table.get_column_names_dict():
                    return table
            return None
        elif type(desc) == type(list()):
            lastTable = None
            for key in desc:
                if not lastTable:
                    lastTable = self.__find_table(key)
                else:
                    nowTable = self.__find_table(key)
                    if nowTable != lastTable:
                        return None
            return lastTable


    #get the number of rows of the table to which this id belongs
    def get_number_of_rows(self,desc):
        workTable = self.__find_table(desc)
        if workTable:
            return workTable.get_number_of_rows()
        else:
            return None

    #the row is dict containing "name":value and one "time":"2018-01-05T...."
    # here, we will also convert all types
    def add_row(self,row):
        #first check if the row contains the time

        timeId= None
        for key in row:
            value = row[key]
            if type(value) == type(datetime.datetime(1,1,1,1,1)):
                date2secs(value)
                #timeDelta = value-datetime.datetime (1970,1 , 1, 0, 0)
                row[key]=date2secs(value)
                timeId = key


        #now find the right table
        workTable = self.__get_table(row,timeId=timeId)
        return workTable.add_row(row)


    #params: variables is an ordered list
    def get_value_table(self,variables,startTime=None,endTime=None,noBins=100,agg="sample",includeTimeStamps = None):
        workTable = self.__find_table(variables)
        if not workTable: return None
        return workTable.get_value_table(variables, startTime=startTime, endTime=endTime, noBins=noBins, agg=agg, includeTimeStamps=includeTimeStamps)
        '''
        if not startTime and not endTime:
            #get full table
            return workTable.get_value_table(variables,startTime=startTime, endTime=endTime, noBins=noBins, agg=agg)
        else:
            return workTable.get_value_table(variables, startTime=startTime, endTime=endTime, noBins=noBins, agg=agg)
        '''

    def save(self,fileName):
        index = 0
        for table in self.tables:
            table.save(fileName+".table_"+str(index))
            index +=1

    def load(self,fileName):
        index = 0
        running = True
        #delete all existing tables
        self.tables=[]
        while running:
            #load the keys and the data
            try:
                newTable = Table()
                if not newTable.load(fileName+".table_"+str(index)):
                    break
                self.tables.append(newTable)
                index+=1
            except:
                print("not found, index",index)

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

    def get_value(self):
        """ Returns:
                the "value" property of the node
                None if node has no "value"
        """
        return self.model.get_value(self.id)

    def set_value(self,value):
        return self.model.set_value(self.id,value)

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
        """  Returns:
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

    def get_children(self):
        """  Returns:
            a list of Node()-objects which are the children of the current node
        """
        nodeInfo = self.model.get_node_info(self.id)
        children=[]
        for childId in nodeInfo['children']:
            children.append(self.model.get_node(childId))
        return children

    def get_properties(self):
        """  Returns:
            a dictionary holding the properties of the node like {"value":123,"name":"myVariable","children":...}
        """
        nodeInfo = self.model.get_node_info(self.id)
        return copy.deepcopy(nodeInfo)

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

    def get_model(self):
        """ this function should only be used for testing, we should never be in the need to access the model inside
        Returns:
            the underlying model of type Model() class
        """
        return self.model

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

    def get_id(self):
        """ Returns: the nodeid (which is generated by the system) """
        return self.id

    def get_browse_path(self):
        """ Returns: the browsepath along the style "root.myfolder.myvariable..." """
        return self.model.get_browse_path(self.id)

    def get_name(self):
        """ Returns: the name of the node without the path """
        return self.model.get_node_info(self.id)["name"]

    
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


    def get_time_indices(self,startTime,endTime):
        """ works only for "column" nodes, it looks to find the timeField node of the table to which the node belongs
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





class Model():
    nodeTemplate = {"id": None, "name": None, "type": "folder", "parent": None, "children": [], "backRefs": [],"forwardRefs":[],"value":None}


    def __init__(self):
        """
            initialize an empty Model object, it will contain the root Node as folder with Id "0"
            during the initialization, also the plug-ins (all files in the ./plugin) are loaded:
            all templates and functions are imported
            a model holds all modelling information and data to work on
        """
        self.model = {"1":{"name":"root","type":"folder","children":[],"parent":"0","id":"1","backRefs":[],"forwardRefs":[]}}
        self.__init_logger(logging.DEBUG)
        self.globalIdCounter=1 # increased on every creation of a node, it holds the last inserted node id
        self.timeSeriesTables = TimeSeriesTables()
        self.functions={} # a dictionary holding all functions from ./plugins
        self.templates={} # holding all templates from ./plugins
        self.lock = threading.RLock()
        self.import_plugins()
        self.differentialHandles ={} # containing handle:model_copy entries to support differential queries

    def __init_logger(self, level):
        """setup the logger object"""
        self.logger = logging.getLogger("Table()")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(level)

    def __get_id(self, id):
        """
            Args:
                id (string): give a browsepath ("root.myfolder.myvariable") or a nodeId ("10")
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
        except:
            return None

        #now we start at root
        actualSearchId = "1"
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

    def get_node_info(self,desc):
        """
            Args:
                desc (string): give a browsepath ("root.myfolder.myvariable") or a nodeId ("10")
            Returns:
                (dict): a dictionary holding all properties of the node includin references and children
        """
        with self.lock:
            id = self.__get_id(desc)
            if not id: return None
            return copy.deepcopy(self.model[id])


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




    def import_plugins(self):
        """ find all plugins (= all .py files in the ./plugin folder
            take from there the templates from the files and the functions
            this function is execution on startup of the model
        """
        mydir =os.path.dirname(os.path.realpath(__file__))
        os.chdir(mydir)#to enable import easily
        sys.path.append(mydir+'/plugins') # for the importlib to find the stuff

        plugins = os.listdir(mydir+'/plugins')
        for fileName in plugins:
            if fileName.startswith('__'):
                continue # avoid __pycache__ things
            moduleName = fileName[:-3]
            module = importlib.import_module(moduleName)
            #now analyze all objects in the module
            for objName in dir(module):
                if objName.startswith('__'):
                    continue # these are python generated info objects, we don't want them
                element = getattr(module,objName)
                if type(element ) is list:
                    #this is a template information
                    self.templates[moduleName+"."+objName]=copy.deepcopy(element)
                elif callable(element):
                    #this is a function, get more info
                    newFunction = {"module":module,"function":element}
                    self.functions[moduleName+"."+objName]=newFunction

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
            #we can create this node
            self.globalIdCounter+=1
            newId = str(self.globalIdCounter)
            newNode = copy.deepcopy(self.nodeTemplate)
            newNode.update({"id":newId,"name":name,"type":type,"parent":parentId})
            if properties !={}:
                newNode.update(properties)
            if value != None:
                newNode["value"]=value
            self.model[parentId]["children"].append(newId)
            self.model[newId]=newNode
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
            Create a node from a template; a template is a list of node-dicts
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



    def add_forward_refs(self,referencerDesc,targets):
        """
            adding forward references from a referencer to other nodes, the forward references are appended at the list
            of forward references of the referencer node

            Args:
                referenderDesc (string): descriptor of the referencer node from which we want to add forward references
                targets (list(descriptors)): listof node descriptors to which we want to add forward refs
            Returns:
                True/False for success
        """
        with self.lock:
            fromId = self.get_id(referencerDesc)
            if not fromId:
                self.logger.error("can't set forward ref on ",referencerDesc)
                return False
            if not self.model[fromId]["type"]=="referencer":
                self.logger.error("can't set forward ref on ", referencerDesc, "is not type referencer, is type",self.model[fromId]["type"])
                return False
            for target in targets:
                toId = self.get_id(target)
                if not toId:
                    return None
                self.model[toId]["backRefs"].append(fromId)
                self.model[fromId]["forwardRefs"].append(toId)
            return True

    def get_model(self):
        """
            Returns: the full deepcopy of the internal model object (list of dictionaries of the nodes)
        """
        with self.lock:
            #also add the browsepath to all nodes
            for nodeid in self.model:
                self.model[nodeid]["browsePath"]=self.get_browse_path(nodeid)
            return copy.deepcopy(self.model)

    def get_model_for_web(self):
        """
            Returns: the full deepcopy of the internal model object (list of dictionaries of the nodes)
                     but leaving out the column values (this can be a lot of data)
                     and the file values (files are binary or strings with big size, typically serialized ML-models)
        """

        model = {}
        with self.lock:
            for nodeId, nodeDict in self.model.items():
                if nodeDict["type"] in ["column","file"]:
                    # with columns we filter out the values
                    node = {}
                    for nk, nv in nodeDict.items():
                        if nk == "value":
                            try:
                                node[nk] = "len " + str(len(nv))
                            except:
                                node[nk] = "None"
                        else:
                            node[nk] = copy.deepcopy(nv)  # values can be list, dict and deeper objects
                    model[nodeId] = node
                else:
                    #this node is not a colum, can still hold huge data
                    model[nodeId] = copy.deepcopy(nodeDict)  # values can be list, dict and deeper objects nodeDict
                model[nodeId]["browsePath"] = self.get_browse_path(nodeId) #also add the browsepath
        return model


    def remove_forward_refs(self,sourceDesc):
        """
            remove all forward references from a referencer, this also removes the backreference from the target
            Args:
                sourceDesc: the descriptor of the referencer node
            Returns:
                True/False for success
        """
        with self.lock:
            fromId = self.get_id(sourceDesc)
            if not fromId:
                return False
            if not self.model[fromId]["type"] == "referencer":
                return False  # only for referencers
            targets = self.model[fromId]["forwardRefs"].copy()
            for toId in targets:
                self.model[fromId]["forwardRefs"].remove(toId)
                self.model[toId]["backRefs"].remove(fromId)
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
            return True

    #delete node and all subnodes
    def delete_node(self,desc):
        """
            delete a node and all its recursive children; if we have referencer nodes on the way which have to be deleted, then
            we also remove their references in the model
            Args:
             desc(string): the descriptor of the node
            Returns:
                True for success
                False for node not found
        """
        with self.lock:
            id = self.get_id(desc)
            if not id:
                return False

            nodesToDelete = self.model[id]["children"].copy()
            print("remove",id,"and children",nodesToDelete)
            for node in nodesToDelete:
                self.delete_node(node)
            #if we are done with the inner, we can now remove all dependencies
            #for a referencer we remove forwards to others and the accoring backwards to me
            if self.model[id]["type"]=="referencer":
                forwards = self.model[id]["forwardRefs"].copy()
                for forwardRefId in forwards:
                    self.remove_forward_ref(id,forwardRefId)

            #for all type of nodes, remove potential backward refs
            backs = self.model[id]["backRefs"].copy()
            for backRefId in backs:
                self.remove_back_ref(id,backRefId)
            #now remove me from the parent
            self.model[self.model[id]["parent"]]["children"].remove(id)
            #now remove me
            del self.model[id]
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
            self.model[id]["value"] = value
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
            if "value" in self.model[id]:
                return self.model[id]["value"]
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
            if key == "value" and self.model[id]["type"]=="column":
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
                all nodes which are considered leaves as a list of node dicts
        """
        with self.lock:
            id = self.__get_id(desc)
            if not id:return None

            targets=self.__get_targets(id)
            return targets


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

    #used in the Node class, give a column variable, return the nodeid of the time variable of that table
    def find_table_time_node(self,desc):
        with self.lock:
            table = self.__find_table(self.get_id(desc))
            if not table:
                return None

            pathToTimeIndex = self.get_browse_path(table)+".timeField"
            timeColumnId = self.get_leaves(pathToTimeIndex)[0]['id'] # this referencer must point to only one node
            return timeColumnId

    def get_timeseries_table(self,variables,startTime=None,endTime=None,noBins=None,agg="sample",includeTimeStamps=None,format="array",includeBackGround=None):
        """
            get a time series table from variables. The table is returned as a list[list] object
            all variables requested must be of type "column" and must belong to the same table:
            all columns requested here must have a direct backreference to the same node of type "columns"
            todo: also allow "columns" to point to folders or multiple hierarchies of referencing/folders

            Args:
                variables (list(nodedescriptors)): nodes to be part the data table requested (ordered!)
                startime, endTime: the start and endtime of the table given as seconds since epoch
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


    def old_get_timeseries_len(self,desc): #deprecated
        with self.lock:
            id = self.get_id(desc)
            if not id: return False
            if self.model[id]["type"]!="timeseries": return False
            return self.timeSeriesTables.get_number_of_rows(desc)

    #return the id of the table, give a column variable
    def __find_table(self,desc):
        """
            return the node id of the table, give a column variable
            !! this has no lock, must be called under lock
            Args:
                desc(string): node descriptor of type column
            Returns:
                the node id of the table to which the desc node belongs
        """
        id = self.get_id(desc)
        if not id: return False
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



    def append_rows_to_table(self,dataRow):
        """
            this function takes one data row and adds it to a table
        """
        pass


    def append_table(self,blob,autocreate=True,autopad=True):
        """
            this function accepts a dictionary containing paths and values and adds them as a row to a table
             if autoPad is True: it is allowed to leave our columns, those will be padded with NaN,
             if autocreate is True: it is allowed to add unknown colums, those will be added automatically under the given name

            Args:
                blob(dict): keys: node descriptors, values: value to be appended to the table (only one scalar per variable at a time)
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


            self.logger.debug("table "+str(tableId)+" autocreates "+str(autocreates))
            if autocreates and autocreate:
                #do we even have to create our table?
                if not tableId:
                    #make a table structure based on the names given
                    tableName = autocreates[1].split('.')[1]+"_autotable"
                    tableId = self.create_node(parent="root",name=tableName,properties={"type":"table"})
                    columnsId = self.create_node(parent=tableId,name="columns",properties={"type":"referencer"})
                    timeId = self.create_node(parent=tableId, name="timeField", properties={"type": "referencer"})
                    numberOfRows=0

                for path in autocreates:
                    id = self.create_node_from_path(path,properties={"type":"column"})
                    self.model[id]["value"]=[None]*numberOfRows
                    self.add_forward_refs(columnsId,[id])
                    if path.split('.')[-1]=="time":
                        #we just created the time field, we must also give the table struct the info
                        self.add_forward_refs(timeId,[id])

            #now insert data: prepare a row that contains values for all columns in the right order
            row = []
            for id in self.model[columnsId]["forwardRefs"]:
                path = self.get_browse_path(id)
                if path in blob:
                    row.append(blob[path])
                else:
                    #table variable is missing in the incoming data
                    if autopad:
                        row.append(None)
                    else:
                        self.logger.warn("variable missing in row append"+path)
                        return False

            #here, we have all prepared, let's write the data finally
            for (id,value) in zip(self.model[columnsId]["forwardRefs"],row):
                self.model[id]["value"].append(value)
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
                #value = str(self.model[rootId][property])
                #if len(value)>40:
                #    value = value[0:37]+"..."
                #print("," + property + "=" +value, end="")
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
            if not functionName in  self.functions:
                print ("can't find function in global list")
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
            thread = threading.Thread(target=self.__execution_thread, args=[id])
            thread.start()
            return True
        except:
            return False

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
                print("in exec Thread")
                #check the function
                functionName = self.model[id]["functionPointer"]
                if not functionName in self.functions:
                    print("not found in global functions list")
                    return False
                functionPointer = self.functions[functionName]['function']
                #now execute
                node = self.get_node(id)
                statusNode = node.get_child("status")
                statusNode.set_value("running")

                resultNode = node.get_child("result")
                resultNode.set_value("pending")

                signalNode = node.get_child("signal")
                signalNode.set_value("nosignal")

            #lock open: we execute without lock
            result = functionPointer(node) # this is the actual execution
            #now we are back, set the status to finished

            with self.lock:
                #this is a bit dangerous, maybe the node is not there anymore, so the
                # inner functions calls of node.xx() will return nothing, so we try, catch
                try:
                    statusNode.set_value("finished")
                    if result == True:
                        resultNode.set_value("ok")
                    else:
                        if resultNode.get_value() == "pending":
                            #if the functions hasn't set anything else
                            resultNode.set_value("error")
                except:
                    print("problem setting results from execution of #",id)
                    pass

            return result
        except:
            print("error inside execution thread", "id",id,"functionname",functionName,sys.exc_info()[1])
            return False

    def show(self):
        """
            show the current model as a ascii tree on he console
        """
        with self.lock:
            self.__show_subtree("1")


    # save model and data to files
    def save(self, fileName):
        """
            save the model to disk, save the tables separately
            the model file will be saves as ./models/fileName.model.json and the tables will be saved under
            ./models/filename.tablePath.npy

            Args: the fileName to store it under, please don't give extensions

        """
        with self.lock:
            m = self.get_model_for_web()  # leave out the tables
            for nodeId in self.model:
                if self.get_node_info(nodeId)["type"] == "table":
                    tablePath = self.get_browse_path(nodeId)
                    self.logger.debug("found table "+tablePath)
                    columnNodes = self.get_leaves(tablePath+".columns")
                    myList = []
                    for node in columnNodes:
                        myList.append(self.get_value(node["id"]))
                    table = numpy.stack(myList,axis=0)
                    numpy.save("./models/" + fileName + "."+tablePath+".npy", table)
            f = open("./models/"+fileName + ".model.json", "w")
            f.write(json.dumps(m, indent=4))
            f.close()

    def load(self,fileName):
        """
            replace the current model in memory with the model from disk
            please give only a name without extensions
            the filename must be in ./models
            Args:
                fileName(string) the name of the file without extension
        """
        with self.lock:
            try:
                f = open("./models/"+fileName+".model.json","r")
                model = json.loads(f.read())
                self.model = model
                f.close()
                #now also load the tables
                for nodeId in self.model:
                    if self.get_node_info(nodeId)["type"] == "table":
                        table = self.get_browse_path(nodeId)
                        data = numpy.load("./models/" + fileName+'.'+table + ".npy")
                        ids = self.get_leaves_ids(table+".columns")
                        for id, column in zip(ids, data):
                            self.set_value(id,column)
            except Exception as e:
                print("problem loading"+str(e))

    def create_differential_handle(self):
        """
            make a copy of the current model and keep it as copy, create a handle for it and return that handle
            Returns:
             a hash handle for the current model
        """
        with self.lock:
            newHandle = str(uuid.uuid4().hex) # make a new unique handle
            self.differentialHandles[newHandle]= self.get_model_for_web() # make an entry by copying the whole model
            return newHandle

    def remove_differential_handle(self,handle):
        """
            removes an entry from the memorized model states of the past identified by the handle
            Arges: handle (uuid string): the id of the handle
            Returns (bool) for success
        """
        with self.lock:
            if handle in self.differentialHandles:
                del self.differentialHandles[handle]
                return True
            else:
                return False # not found

    def get_differential_update(self,oldHandle,newHandle=None,delOld=True):
        """
            this function takes the copy of the model (hopefully) held under handle and compares it to the current model:
            the differences are analyzed and returned, the old copy of the model under "handle" is replaced by
            Args:
                oldHandle (string): the unique id of the old version of the model
                newHandle (string): the unique id of the new version to compare to, if not given, we take the current
                                    and will automatically make a new entry for the current
                delOld: if set, we remove the old entry from the memorized models
            Returns (dict):
                containing information about the changes between and old and new version of the model
                key values:
                "handle":(string): the handle under which we find the new version of the model
                "newNodes": (dict) nodes which are new to the tree in the form Nodeid:{properties}
                "deletedNodeIds": (list) list of node ids which have been deleted
                "modifiedNodes": (dict) nodes which have changed properties: if so, we give the full updated node back

        """
        diff={"handle":None,"newNodes":{},"deletedNodeIds":[],"modifiedNodes":{}}
        if newHandle is None:
            newModel = self.get_model_for_web()
        else:
            if newModel in self.differentialHandles:
                newModel = self.differentialHandles[newModel]
            else:
                return None # the newhandle did not exist
        if oldHandle not in self.differentialHandles:
            return None # the old handle does not exist
        oldModel = self.differentialHandles[oldHandle]

        #now iterate over the nodes

        #find the changes
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

        if delOld:
            del self.differentialHandles[oldHandle]

        if not newHandle:
            #we auto-create a new handle and entry
            diff["handle"]=self.create_differential_handle()

        return diff





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
            self.create_nodes_from_template("root.functions",self.templates["testfunction.delayFunctionTemplate"])

            #now make cutom function to trigger something
            self.create_nodes_from_template("root.functions",self.templates["counterfunction.counterFunctionTemplate"])
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
            self.create_nodes_from_template('root',self.templates["logisticregression.logisticRegressionTemplate"])
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

    def ts_test1():
        m=Model()
        m.create_node("root", name="folder1")
        m.create_node("root.folder1", name="folder2")
        m.create_node("2", name="second")
        m.create_node("root", name="myreferencer", type="referencer")
        m.create_node("root.folder1", name="myvar", type="variable")
        m.create_node("root",name="data",type ="folder")
        for node in ["varA","varB","varC","time"]:
            m.create_node("root.data",name=node,type="timeseries")
        #m.show()
        #now write some data
        start=datetime.datetime.now()
        timeNow = datetime.datetime.now()
        for i in range(5):
            dataDict ={"root.data.varA":i,"root.data.varB":float(i)/10,"root.data.time":timeNow+datetime.timedelta(i)}
            #dataDict = {"8": i, "9": float(i) / 10,
            #            "11": timeNow + datetime.timedelta(i)}
            #dataDict=m.get_id(dataDict)
            m.add_timeseries(dataDict)
        print("done inserting",(datetime.datetime.now()-start))
        start = datetime.datetime.now()
        table = m.get_timeseries_table(dataDict)
        print("readBack",len(table))
        if len(table)<10:
            print(table)
        print("time for readback",(datetime.datetime.now()-start))

        m.show()

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


    def table_query_test():
        m = Model()
        m.create_node("root", name="a",type="timeseries")
        m.create_node("root", name="b", type="timeseries")
        m.create_node("root", name="c", type="timeseries")
        m.create_node("root", name="d", type="timeseries")
        m.create_node("root", name="e", type="timeseries")
        m.create_node("root", name="time", type="timeseries")
        m.show()
        # now write some data
        start = datetime.datetime.now()
        timeNow = datetime.datetime.now()
        for i in range(5000):
            timeNow = start+ datetime.timedelta(i)
            dataDict = {"root.a": i,
                        "root.b": 1+i/10,
                        "root.c":1+i/100,
                        "root.d":1+i/1000,
                        "root.time": timeNow
                        }
            m.add_timeseries(dataDict)
        print("done inserting", (datetime.datetime.now() - start))

        #now make a timed query
        queryStart = start +datetime.timedelta(100)
        queryEnd = start +datetime.timedelta(1100)
        vars=["root.a","root.c","root.d","root.time"]
        table = m.get_timeseries_table(vars,queryStart,queryEnd,10)
        print (table)


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


