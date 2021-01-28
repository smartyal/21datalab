

import sys
import os
import time
import random
import numpy
import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import requests
import json
import logging
from logging.handlers import RotatingFileHandler
import copy
import random
import time
import threading
import sse
import pytz
import traceback



from bokeh.models import DatetimeTickFormatter, ColumnDataSource, BoxSelectTool, BoxAnnotation, Label, LegendItem, Legend, HoverTool, BoxEditTool, TapTool, Circle
from bokeh.models import Range1d,DataRange1d, Span,LinearAxis, Band
from bokeh import events
from bokeh.models.widgets import RadioButtonGroup, Paragraph, Toggle, MultiSelect, Button, Select, CheckboxButtonGroup,Dropdown
from bokeh.plotting import figure, curdoc
from bokeh.layouts import layout,widgetbox, column, row, Spacer
from bokeh.models import Range1d, PanTool, WheelZoomTool, ResetTool, ToolbarBox, Toolbar, Selection, BoxZoomTool
from bokeh.models import FuncTickFormatter, CustomJSHover, SingleIntervalTicker, DatetimeTicker, CustomJS
from bokeh.themes import Theme
from pytz import timezone
from bokeh.models.glyphs import Rect
from bokeh.models.glyphs import Quad
from bokeh.models.glyphs import VArea,VBar

from bokeh.models.renderers import GlyphRenderer



#RenderLevel = Enumeration(image, underlay, glyph, guide, annotation, overlay)

haveLogger = False
globalAlpha = 1.0#0.3

globalAnnotationLevel  = "image"
globalBackgroundsLevel = "underlay"
globalThresholdsLevel = "underlay"
globalBandsLevel = "overlay"
globalAnnotationsAlpha = 0.90
globalThresholdsAlpha = 0.5
globalBackgroundsAlpha = 0.2
globalBackgroundsHighlightAlpha = 0.6

globalRESTTimeout = 90



def setup_logging(loglevel=logging.DEBUG,tag = ""):
    global haveLogger
    print("setup_logging",haveLogger)
    if not haveLogger:
        # fileName = 'C:/Users/al/devel/ARBEIT/testmyapp.log'
        #logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', level=loglevel)

        #remove all initial handlers, e.g. console
        allHandlers = logging.getLogger('').handlers
        for h in allHandlers:
            logging.getLogger('').removeHandler(h)


        formatter = logging.Formatter('%(asctime)s %(name)-12s thid%(thread)d %(levelname)-8s %(message)s')
        console = logging.StreamHandler()
        console.setLevel(loglevel)
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)

        #logfile = logging.FileHandler('./log/widget_'+'%08x' % random.randrange(16 ** 8)+".log")
        #logfile = logging.FileHandler('./widget_' + '%08x' % random.randrange(16 ** 8) + ".log")
        if tag == "":
            tag = '%08x' % random.randrange(16 ** 8)
        logfile = RotatingFileHandler('./log/widget_' + tag+ ".log", maxBytes=1000 * 1000 * 100, backupCount=10)  # 10x100MB = 1GB max
        logfile.setLevel(loglevel)
        logfile.setFormatter(formatter)
        logging.getLogger('').addHandler(logfile)
        haveLogger = True




#import model
from dates import date2secs,secs2date, secs2dateString
from dates import epochToIsoString
import themes #for nice colorsing



#give a part tree of nodes, return a dict with const=value
def get_const_nodes_as_dict(tree):
    consts ={}
    for node in tree:
        if node["type"] in ["const","variable"]:
            consts[node["name"]]=node["value"]
        if node["type"] == "referencer":
            if "forwardPaths" in node:
                consts[node["name"]] = node["forwardPaths"]

    return consts




class TimeSeriesWidgetDataServer():
    """
        a helper class for the time series widget dealing with the connection to the backend rest model server
        it also caches settings which don't change over time
    """
    def __init__(self,modelUrl,avatarPath):
        self.url = modelUrl # get the data from here
        self.path = avatarPath # here is the struct for the timeserieswidget
        #self.timeOffset = 0 # the timeoffset of display in seconds (from ".displayTimeZone)
        self.annotations = {}
        self.pendingScoreVariablesUpdate = False# is set to true if there has been a silent update of the score variables list without telling the ts widget
        self.scoreVariables = []
        self.events = None
        self.sseCb = None # the callbackfunction on event
        self.objectsInfo = {} # a dict holding node ids and more info of the current objects in the display


        self.__init_logger(logging.DEBUG)
        self.__init_proxy()
        self.__get_settings()
        self.__init_sse()

    def __del__(self):
        print("del times series widget ") #try to understand what bokeh is doing :)

    def __init_sse(self):
        self.sse = sse.SSEReceiver(f'{self.url}event/stream',self.sse_cb)
        self.sse.start()

    def sse_cb(self,data):
        #self.logger.debug(f'sse {data}, {self.settings["observerIds"]}, my id {id(self)}')
        #now we filter out the events which are for me
        if data["data"]!="":
            try:
                dataString = data["data"]
                dataString = dataString.replace("'",'"') # json needs double quote for key/values entries
                parseData = json.loads(dataString)
                #self.logger.debug(f"parsed event {parseData}")
                if data["event"].startswith("global") or ("nodeId" in parseData and parseData["nodeId"] in self.settings["observerIds"]): #only my own observers are currently taken
                        #self.logger.info("sse match")
                        data["data"]=parseData # replace the string with the parsed info
                        if self.sseCb:
                            self.sseCb(data)
            except Exception as ex:
                self.logger.error(f"sse_Cb error {ex}, {sys.exc_info()[0]} {str(traceback.format_exc())}")

    def sse_stop(self):
        self.sse.stop()
    def sse_register_cb(self,cb):
        self.sseCb = cb

    def __init_proxy(self):
        """
            try to open the proxies file, set the local proxy if possible
        """
        self.proxySetting = {}
        try:
            with open('proxies.json','r') as f:
                self.proxySetting = json.loads(f.read())
                self.logger.info("using a proxy!")
        except:
            self.logger.info("no proxy used")
            pass

    def __init_logger(self, level=logging.DEBUG):
        setup_logging(loglevel = level, tag=self.path)
        self.logger = logging.getLogger("TSServer")
        self.logger.setLevel(level)
        #handler = logging.StreamHandler()
        #formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        #handler.setFormatter(formatter)
        #self.logger.addHandler(handler)
        #self.logger.setLevel(level)



    def __web_call(self,method,path,reqData):
        """
            this functions makes a call to the backend model serer to get data
            Args:
                method(string) one of ["GET","POST"]
                path: the nodepath to the time series widtet
                reqData: a dictionary with request data for te query like the list of variables, time limits etc.
            Returns (dict):
                the data from the backend as dict
        """
        self.logger.info("__web_call %s @%s data:%s",method,path,str(reqData))

        response = None
        now = datetime.datetime.now()
        if method.upper() == "GET":
            try:
                response = requests.get(self.url + path, timeout=globalRESTTimeout,proxies=self.proxySetting)
            except Exception as ex:
                self.logger.error("requests.get msg:"+str(ex))

        elif method.upper() == "POST":
            now = datetime.datetime.now()
            try:
                response = requests.post(self.url + path, data=json.dumps(reqData), timeout=globalRESTTimeout,
                                         proxies=self.proxySetting)
            except Exception as ex:
                self.logger.error("requets.post " + str(ex))

        after = datetime.datetime.now()
        diff = (after-now).total_seconds()
        self.logger.info("response "+str(response)+" took "+ str(diff))
        if not response:
            self.logger.error("Error calling web " + path )
            return None
        else:
            rData = json.loads(response.content.decode("utf-8"))
            return rData

    def get_selected_variables_sync(self):
        request = self.path + ".selectedVariables"
        selectedVars = []

        nodes = self.__web_call("post", "_getleaves", request)
        selectedVars=[node["browsePath"] for node in nodes]
        #build the info as id:info plus browsepath:info, so we have a faster lookup; both browsepath and id are unique
        self.objectsInfo = {}
        for node in nodes:
            info = copy.deepcopy(node)
            self.objectsInfo[node["id"]]=info
            self.objectsInfo[node["browsePath"]]=info

        self.selectedVariables=copy.deepcopy(selectedVars)
        self.logger.debug(f"get_selected_variables_sync => {self.selectedVariables}")
        return selectedVars

    def get_path(self):
        return self.path

    def load_annotations(self):
        self.logger.debug("load_annotations")
        if (self.settings["hasAnnotation"] == True) or (self.settings["hasThreshold"] == True):
            response = self.__web_call("post","_get",[self.path+"."+"hasAnnotation"])
            annotationsInfo = get_const_nodes_as_dict(response[0]["children"])
            self.settings.update(annotationsInfo)
            #now get all annotations
            nodes = self.__web_call("post","_getleaves",self.path+".hasAnnotation.annotations")
            self.logger.debug("ANNOTATIONS"+json.dumps(nodes,indent=4))
            #now parse the stuff and build up our information
            self.annotations={}
            for node in nodes:
                if node["type"]=="annotation":
                    self.annotations[node["browsePath"]]=get_const_nodes_as_dict(node["children"])

                    if "startTime" in self.annotations[node["browsePath"]]:
                        self.annotations[node["browsePath"]]["startTime"] = date2secs(self.annotations[node["browsePath"]]["startTime"])*1000
                    if "endTime" in self.annotations[node["browsePath"]]:
                        self.annotations[node["browsePath"]]["endTime"] = date2secs(self.annotations[node["browsePath"]]["endTime"]) * 1000
                    if self.annotations[node["browsePath"]]["type"] in ["threshold","motif"]:
                        #we also pick the target, only the first!
                        self.annotations[node["browsePath"]]["variable"]=self.annotations[node["browsePath"]]["variable"][0]
            self.logger.debug("server annotations" + json.dumps(self.annotations, indent=4))





    def __get_settings(self):
        """
            get all the settings of the widget and store them also in the self.settings cache
            Returns: none

        """

        self.fetch_mirror()



        request = [self.path]
        info = self.__web_call("post","_get",request)
        self.logger.debug("initial settings %s",json.dumps(info,indent=4))
        #self.originalInfo=copy.deepcopy(info)
        #grab some settings
        self.settings = get_const_nodes_as_dict(info[0]["children"])


        #also grab the selected
        self.get_selected_variables_sync()
        #request = self.path+".selectedVariables"
        #self.selectedVariables=[]
        #nodes = self.__web_call("post","_getleaves",request)
        #for node in nodes:
        #    self.selectedVariables.append(node["browsePath"])
        #get the selectable
        nodes = self.__web_call('POST',"_getleaves",self.path+'.selectableVariables')
        self.selectableVariables = []
        for node in nodes:
            self.selectableVariables.append(node["browsePath"])
        #also remeber the timefield as path
        request = self.path+".table"
        nodes = self.__web_call("post","_getleaves",request)
        #this should return only one node
        #timerefpath = nodes[0]["browsePath"]+".timeField"
        #another call to get it right
        #nodes = self.__web_call("post", "_getleaves", timerefpath)
        #self.timeNode = nodes[0]["browsePath"]
  

        #now for the annotations
        if (self.settings["hasAnnotation"] == True) or (self.settings["hasThreshold"] == True):
            response = self.__web_call("post","_get",[self.path+"."+"hasAnnotation"])
            annotationsInfo = get_const_nodes_as_dict(response[0]["children"])
            self.settings.update(annotationsInfo)
        self.annotations=self.fetch_annotations() # get all the annotations

        #for the events
        if "hasEvents" in self.settings and self.settings["hasEvents"] == True:
            self.events = self.fetch_events()

        #grab the info for the buttons
        myButtons=[]
        for node in info[0]["children"]:
            if node["name"]=="buttons":
                myButtons = node["children"]

        #now get more info on the buttons
        if myButtons != []:
            buttonInfo = self.__web_call("post","_get",myButtons)
            self.settings["buttons"]=[]
            for button in buttonInfo:
                #find the caption and target
                caption = ""
                target = ""
                for child in button["children"]:
                    if child["name"] == "caption":
                        caption=child["value"]
                    if child["name"] == "onClick":
                        targets = child["forwardRefs"]
                if targets != "":
                    #create that button
                    self.settings["buttons"].append({"name":caption,"targets":targets.copy()})


        # now compile info for the observer #new observers
        # we remeber all ids of observers in our widget
        self.settings["observerIds"]=[]
        for node in info[0]["children"]:
            if node["type"]=="observer":
                self.settings["observerIds"].append(node["id"])

        # now grab the info for the backgrounds
        try:
            background={}
            for node in info[0]["children"]:
                if node["name"] == "hasBackground":
                    background["hasBackground"] = node["value"]
                if node["name"] == "background" and background["hasBackground"]==True:
                    # we take only the first entry (there should be only one) of the referencer:
                    # this is the nodeId of the background values
                    background["background"]=node["forwardRefs"][0]
                if node["name"] == "backgroundMap":
                    background["backgroundMap"] = copy.deepcopy(node["value"])      #the json map for background values and color mapping
            if all(key in background for key in ["hasBackground","background","backgroundMap"]):
                self.settings["background"]=copy.deepcopy(background)
            else:
                self.settings["background"]={"hasBackground":False}
                    #we dont have a valid background definition
        except Exception as ex:
            self.logger.error(f"problem loading background {ex}, {str(sys.exc_info()[1])}, disabling background")
            self.settings["background"] = {"hasBackground": False}


        self.logger.debug("SERVER.SETTINGS-------------------------")
        self.logger.debug("%s",json.dumps(self.settings,indent=4))


    def fetch_events(self):
        # return a dict with {id:eventdict}
        nodes = self.__web_call("post", "_getleaves", self.path + ".hasEvents.events")
        self.logger.debug(f"fetch_events: {len(nodes)} events")
        query = {"nodes":[node["id"] for node in nodes if node["type"]=="eventseries"]}
        events = self.__web_call("post","_getEvents",query)
        self.logger.debug(f"events result {len(events)}")
        self.events = events
        return events   # dict "nodeid":{"events":{"one":....,"two":... }"eventMap"....},"id2":{}

    def get_events(self):
        return copy.deepcopy(self.events)


    def fetch_annotations(self):
        # return a dict with {id:annotationdict}
        #get a fresh copy of the annotations
        nodes = self.__web_call("post", "_getleaves", self.path + ".hasAnnotation.annotations")
        self.logger.debug(f"_fetch_annotations(): {len(nodes)} annotations")
        # now parse the stuff and build up our information
        annotations = {}
        for node in nodes:
            if node["type"] == "annotation":
                try:
                    annotation = get_const_nodes_as_dict(node["children"])
                    annotation["browsePath"]=node["browsePath"]
                    annotation["id"]=node["id"]
                    annotation["name"] = node["name"]
                    #convert some stuff
                    if "startTime" in annotation:
                        annotation["startTime"] = date2secs(
                            annotation["startTime"]) * 1000
                    if "endTime" in annotation:
                        annotation["endTime"] = date2secs(
                            annotation["endTime"]) * 1000
                    if annotation["type"] in ["threshold","motif"]:
                        # we also pick the target, only the first
                        annotation["variable"] =  annotation["variable"][0]
                    annotations[node["id"]]=annotation
                except Exception as ex:
                    self.logger.error(f"problem loading annotations {ex}, {str(sys.exc_info()[1])}")
                    continue
        #self.logger.debug("server annotations" + json.dumps(self.annotations, indent=4))
        self.annotations = copy.deepcopy(annotations)
        return annotations

    def fetch_annotations_differential(self,info):
        #args is a dict :{"new":[id1,id2], "delete":[id3,id4] "modify":[id5...] lists that contain ids where there have been changes

        #the deletes
        for id in info["delete"]:
            if id in self.annotations:
                del self.annotations[id]


        #merge the new and modify and put them in our local info
        nodes = info["new"]
        nodes.update(info["modify"])

        for id,annotation in nodes.items():
            try:
                # convert some stuff
                if "startTime" in annotation:
                    annotation["startTime"] = date2secs(
                        annotation["startTime"]) * 1000
                if "endTime" in annotation:
                    annotation["endTime"] = date2secs(
                        annotation["endTime"]) * 1000
                if annotation["type"] in ["threshold", "motif"]:
                    # we also pick the target, only the first
                    annotation["variable"] = annotation["variable"][0]
                self.annotations[id] = annotation #update or new entry
            except Exception as ex:
                self.logger.error(f"problem loading annotations {ex}, {str(sys.exc_info()[1])}")
                continue
        return self.annotations






    ##############################
    ## INTERFACE FOR THE WIDGET
    ##############################

    def execute_function(self,descriptor):
        """ trigger the execution of a registered function in the backend """
        return self.__web_call("POST","_execute",descriptor)


    def get_values(self,varList):
        """  get a list of values of variables this is for type varialb, const """
        return self.__web_call("POST","_getvalue",varList)


    def get_data(self,variables,start=None,end=None,bins=300):

        """
            retrieve a data table from the backend
            Args:
                variables(list): the nodes from which the data is retrieved
                start (float): the startime in epoch ms
                end (float): the endtime in epoch ms
                bins (int): the number of samples to be retrieved between the start and end time
            Returns (dict):
                the body of the response of the data request of the backend
        """
        self.logger.debug("server.get_data()")

        varList = self.selectedVariables.copy()
        #include background values if it has background enabled
        if self.settings["background"]["hasBackground"]==True:
            varList.append(self.settings["background"]["background"]) # include the node it holding the backgrounds
        # now get data from server
        if start:
            start=start/1000
        if end:
            end=end/1000
        body = {
            "nodes": varList,
             "startTime" : start,
             "endTime" :   end,
            "bins":bins,
            "includeTimeStamps": "02:00",
            "includeIntervalLimits" : True
        }
        r=self.__web_call("POST","_getdata",body)
        if not r:
            return None
        #convert the time to ms since epoch
        for entry in r:
            if entry.endswith("__time"):
                times = numpy.asarray(r[entry])
                debug = copy.deepcopy(times.tolist())
                r[entry]=(times*1000).tolist()
                #print(f"times {debug}")
                #print(f"times {entry} {[epochToIsoString(t) for t in debug]}")
        #make them all lists and make all inf/nan etc to nan
        for k,v in r.items():
            r[k]=[value if numpy.isfinite(value) else numpy.nan for value in v]

        #self.logger.debug(str(r))
        return r


    def get_time_node(self):
        return self.timeNode

    def get_mirror(self):
        return self.mirror

    def fetch_mirror(self,small = False):
        if small:
            query = {"node":self.path,"depth":1,"ignore":["observer"]}
        else:
            query = {"node":self.path,"depth":100,"ignore":["observer","hasAnnotation.anno","hasAnnotation.new"]}
        self.mirror = self.__web_call("post", "_getbranchpretty", query)
        self.update_score_variables_from_mirror()
        return self.mirror

    def fetch_score_variables(self):

        old = copy.deepcopy(self.scoreVariables)

        nodes = self.__web_call("post", "_getleaves", self.path + ".scoreVariables")
        scoreVariables = [node["browsePath"] for node in nodes]
        self.scoreVariables = copy.deepcopy(scoreVariables)
        #self.logger.debug(f"fetch_score_variables : old {old}, new:{self.scoreVariables}")

        if old != self.scoreVariables or self.pendingScoreVariablesUpdate:
            self.pendingScoreVariablesUpdate = False
            return True # have something new
        else:
            return False

    def update_score_variables_from_mirror(self):
        scoreVars = []
        for id,node in self.mirror["scoreVariables"][".properties"]["leavesProperties"].items():
            scoreVars.append(node["browsePath"])
        self.pendingScoreVariablesUpdate = True # if the TSwidget asks later if there was a diff in the meantime, we better say yes to not skip updates
        self.scoreVariables = scoreVars



    def get_current_colors(self):
        return self.mirror["currentColors"][".properties"]["value"]

    def update_current_colors(self,currentColors):
        if currentColors == self.mirror["currentColors"][".properties"]["value"]:
            return # nothing to do
        nodesToModify = [{"browsePath": self.path + ".currentColors", "value": currentColors}]
        self.mirror["currentColors"][".properties"]["value"] = currentColors
        self.__web_call('POST', 'setProperties', nodesToModify)

    def get_variables_selectable(self):
        """ returns the selectable variables from the cache"""
        return copy.deepcopy(self.selectableVariables)

    def get_variables_selected(self):
        """ return list of selected variables from the cache"""
        return copy.deepcopy(self.selectedVariables)

    def get_annotations(self):
        return copy.deepcopy(self.annotations)
        #return copy.deepcopy(self.annotations)

    def bokeh_time_to_string(self,epoch):
        localtz =  timezone(self.settings["timeZone"])
        dt = datetime.datetime.fromtimestamp(epoch/1000, localtz)
        return dt.isoformat()

    def get_score_variables(self):
        return copy.deepcopy(self.scoreVariables)

    def is_score_variable(self,variableBrowsePath):
        return (variableBrowsePath in self.scoreVariables)

    def get_score_marker(self,variableBrowsePath):
        #look for the uiInfo in the mirror
        #find this variable and potential info about the display
        for id,info in self.mirror["scoreVariables"][".properties"]["leavesProperties"].items():
            if info["browsePath"] == variableBrowsePath:
                if "uiInfo" in info:
                    return info["uiInfo"]["marker"]
        return "cross"


    #start and end are ms(!) sice epoch, tag is a string
    def add_annotation(self,start=0,end=0,tag="unknown",type="time",min=0,max=0, var = None):
        """
            add a new user annotation to the model and also add it to the local cache
            Args:
                start(float): the start time in epcoh ms
                end(float): the end time in epoch ms
                tag (string) the tag to be set for this annotation
            Returns:
                the node browsePath of this new annotation
        """

        #place a new annotation into path
        nodeName = '%08x' % random.randrange(16 ** 8)
        annoPath = self.path + "." + "hasAnnotation.newAnnotations."+nodeName
        if type == "time":
            nodesToCreate = [
                {"browsePath": annoPath,"type":"annotation"},
                {"browsePath": annoPath + '.type',"type":"const","value":"time"},
                {"browsePath": annoPath + '.startTime',"type":"const","value":self.bokeh_time_to_string(start)},
                {"browsePath": annoPath + '.endTime', "type": "const", "value":self.bokeh_time_to_string(end)},
                {"browsePath": annoPath + '.tags', "type": "const", "value": [tag]}
                ]
        elif type =="threshold":
            nodesToCreate = [
                {"browsePath": annoPath, "type": "annotation"},
                {"browsePath": annoPath + '.type', "type": "const", "value": "threshold"},
                {"browsePath": annoPath + '.min', "type": "const", "value": min},
                {"browsePath": annoPath + '.max', "type": "const", "value": max},
                {"browsePath": annoPath + '.tags', "type": "const", "value": [tag]},
                {"browsePath": annoPath + '.variable', "type": "referencer", "targets": [var]}

            ]
        elif type == "motif":
            nodesToCreate = [
                {"browsePath": annoPath, "type": "annotation"},
                {"browsePath": annoPath + '.type', "type": "const", "value": "motif"},
                {"browsePath": annoPath + '.startTime', "type": "const", "value": self.bokeh_time_to_string(start)},
                {"browsePath": annoPath + '.endTime', "type": "const", "value": self.bokeh_time_to_string(end)},
                {"browsePath": annoPath + '.tags', "type": "const", "value": [tag]},
                {"browsePath": annoPath + '.variable', "type": "referencer", "targets": [var]}

            ]
        else:
            self.logger.error(f"can't create anno type {type}")
            return None

        self.logger.debug("creating anno %s",str(nodesToCreate))
        res = self.__web_call('POST','_create',nodesToCreate)

        if res:
            #the first is our node id
            #now also update our internal list
            anno  = {"startTime":start,"endTime":end,"tags":[tag],"min":min,"max":max,"type":type,"variable":var,"id":res[0],"name":nodeName}
            self.annotations[anno["id"]] = copy.deepcopy(anno)
            return anno
        else:
            return None


    def adjust_annotation(self,anno):
        """
            change an exising annotation and write it back to the model via REST
            Args:
                anno [dict]: contains entries to be overwritten in the original annotation dict
        """
        if anno["id"] not in self.annotations:
            return False
        self.logger.debug(f"ser .adjust_annotation {anno}")
        self.annotations[anno["id"]].update(anno)
        path = anno["id"]# we build a "fancy" browsepath as nodeid.name.name
        if anno['type'] in ["time","motif"]:
            #for time annotation we write the startTime and endTime
            nodesToModify =[
                {"browsePath": path + ".startTime", "value":self.bokeh_time_to_string(anno["startTime"])},
                {"browsePath": path + ".endTime", "value": self.bokeh_time_to_string(anno["endTime"])}
            ]
        elif anno['type'] == "threshold":
            nodesToModify = [
                {"browsePath": path + ".min", "value": anno["min"]},
                {"browsePath": path + ".max", "value": anno["max"]}

            ]
        else:
            self.logger.error("adjust_annotations : unsopported type")
            return

        res = self.__web_call('POST', 'setProperties', nodesToModify)





    def delete_annotations(self,deleteList):
        """ delete existing annotation per browsePath from model and cache"""
        for nodePath in deleteList:
            del self.annotations[nodePath]
        self.__web_call("POST","_delete",deleteList)
        pass

    def set_variables_selected(self, varList, updateLocalNow=True):
        """ update the currently selected variables to cache and backend
            if we set updateLocalNow to False, we do not update the local list, that means we will
            only detect the changes in the next sse event
        """
        query={"deleteExisting":True,"parent":self.path+".selectedVariables","add":varList}
        self.__web_call("POST","_references",query)
        if updateLocalNow:
            self.selectedVariables=varList.copy()
        return

    def add_variables_selected(self,addList,updateLocalNow=True):

        selectedList = copy.deepcopy(self.get_variables_selected())
        selectedList.extend(addList)
        query={"deleteExisting":True,"parent":self.path+".selectedVariables","add":selectedList}
        self.__web_call("POST","_references",query)
        if updateLocalNow:
            self.selectedVariables=selectedList
        return


    def get_settings(self):
        return copy.deepcopy(self.settings)

    def refresh_settings(self):
        self.__get_settings()

    def set_background_highlight(self,x,y,backStart,backEnd,remove=False):
        if remove:
            query = {"browsePath":self.path+".backgroundHighlight","type":"variable","value":{}}
        else:
            query = {"browsePath":self.path+".backgroundHighlight","type":"variable","value":{
                "x":x/1000,
                "y":y,
                "left":backStart/1000,
                "right":backEnd/1000,
                "start":self.bokeh_time_to_string(backStart),
                "end":self.bokeh_time_to_string(backEnd)
            }}
        self.__web_call("POST","_create",[query])


    def select_annotation(self,annoList):
        #anno list is a list of browsepaths
        query = {"deleteExisting": True, "parent": self.path + ".hasAnnotation.selectedAnnotations", "add": annoList}
        self.__web_call("POST", "_references", query)
        return

    def set_x_range(self,start,end):
        startTimeString = self.bokeh_time_to_string(start)
        endTimeString = self.bokeh_time_to_string(end)

        self.mirror["startTime"][".properties"]["value"]=startTimeString
        self.mirror["endTime"][".properties"]["value"] = endTimeString

        query= [
            {"browsePath": self.path+".startTime","value":startTimeString},
            {"browsePath": self.path + ".endTime", "value": endTimeString}]
        self.__web_call("POST","setProperties",query)
        return



class TimeSeriesWidget():
    def __init__(self, dataserver,curdoc=None):
        self.curdoc = curdoc
        self.id = "id#"+str('%8x'%random.randrange(16**8))
        self.__init_logger()
        self.logger.debug("__init TimeSeriesWidget()")
        self.server = dataserver
        self.height = 600
        self.width = 900
        self.lines = {} #keeping the line objects
        self.legendItems ={} # keeping the legend items
        self.legend ={}
        self.hasLegend = False
        #self.data = None
        self.columnData = {}
        self.inPeriodicCb = False
        self.dispatchList = [] # a list of function to be executed in the bokeh app context
                                # this is needed e.g. to assign values to renderes etc
        self.dispatchLock = threading.Lock() # need a lock for the dispatch list
        #self.dispatcherRunning = False # set to true if a function is still running
        self.annotationTags = []
        self.hoverTool = None
        self.showThresholds = True # initial value to show or not the thresholds (if they are enabled)
        self.showMotifs = False
        self.streamingMode = False # is set to true if streaming mode is on
        self.annotations = {} #   holding the bokeh objects of the annotations
        self.userZoomRunning = False # set to true during user pan/zoom to avoid stream updates at that time
        self.inStreamUpdate = False # set true inside the execution of the stream update
        self.backgrounds = [] #list of current boxannotations dict entries: these are not the renderers
        self.threadsRunning = True # the threads are running: legend watch
        self.annotationsVisible = False # we are currently not showing annotations
        self.boxModifierVisible = False # we are currently no showing the modifiert lines
        self.backgroundHighlightVisible = False # we currently show a background hightlighted
        self.renderers = {}  # each element is ["id":["renderer":object,"info":annoDict] these are the created renderers to be later used e.g. annotations

        self.streamingUpdateData = None
        self.showBackgrounds = False
        self.showAnnotationTags = [] # a list with tags to display currently
        self.showAnnotations = False # curently displaying annotations
        self.currentAnnotationVariable = None
        self.currentAnnotationTag = None

        self.renderersLock = threading.Lock()
        self.renderersGarbage = [] # a list of renderers to be deleted when time allowes

        self.autoAdjustY = True # autoscaling of the y axis
        self.inPan = False      #we are not currently in pan mode
        self.annoHovers=[]      #holding the objects for hovering annotatios (extra glyph, eg. a circle)

        self.eventLines = {}    #holding event line renderes and the columndatasources
        self.eventsVisible = False  #set true if events are currently turned on



        self.__init_figure() #create the graphical output

        self.init_additional_elements() # we need the observer already here eg for the scores s we might modifiy the backend and rely on the callback

        self.__init_new_observer()  #

        self.debug = None
    class ButtonCb():
        """
            a wrapper class for the user button callbacks. we need this as we are keeping parameters with the callback
            and the bokehr callback system does not extend there
        """
        def __init__(self,parent,parameter):
            self.parameter = parameter
            self.parent = parent
        def cb(self):
            self.parent.logger.info("user button callback to trigger %s",str(self.parameter))
            self.parent.server.execute_function(self.parameter[0]) # we just trigger the first reference
            pass


    def __init_logger(self, level=logging.DEBUG):
        """initialize the logging object"""
        setup_logging()
        self.logger = logging.getLogger("TSWidget")
        self.logger.setLevel(logging.DEBUG)
        #handler = logging.StreamHandler()

        #formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        #handler.setFormatter(formatter)
        #self.logger.addHandler(handler)

        #self.logger.setLevel(level)


    def log_error(self):
        self.logger.error(f"{sys.exc_info()[1]}, {traceback.format_exc()}")

    def observer_cb(self,data):
        """
         called by the ts server on reception of an event from the model server
         events are
         - update for lines (selection of lines, add, remove lines)
         - update in the backgrounds
         - streaming update
           we can do calls to the restservice here but can't work with the bokeh data, therefore we
           dispatch functions to be executed in the callback from the bokeh loop

        """
        self.logger.debug(f"observer_cb {data}")
        if data["event"] == "timeSeriesWidget.variables" or data["event"] == "global.timeSeries.values":
            #refresh the lines
            if data["event"] == "timeSeriesWidget.variables":
                self.server.get_selected_variables_sync() # get the new set of lines
                self.__dispatch_function(self.update_scores)
            self.logger.debug("dispatch the refresh lines")
            self.__dispatch_function(self.refresh_plot) #this includes the backgrounds
        elif data["event"] == "timeSeriesWidget.background":
            self.logger.debug("dispatch the refresh background")
            self.__dispatch_function(self.refresh_backgrounds)

        elif data["event"] == "global.series.stream":
            #this is a stream update, we only do something if the stream update in inside the visible area
            if self.stream_update_is_relevant(data):
                self.__dispatch_function(self.stream_update_new, arg=copy.deepcopy(data))
            else:
                self.logger.debug("stream update not relevant, ignore!")

        elif data["event"] == "timeSeriesWidget.stream":
            self.logger.debug(f"self.streamingMode {self.streamingMode}")
            if self.streamingMode and not self.streamingUpdateData:
                self.logger.debug("get stream data")
                #we update the streaming every second
                #get fresh data, store it into a variable and make the update on dispatch in the context of bokeh
                variables = self.server.get_variables_selected()
                variablesRequest = variables.copy()
                #variablesRequest.append("__time")  # make sure we get the time included
                #self.logger.debug(f"request stream data{self.streamingInterval}")
                self.streamingUpdateDataInterval = self.streamingInterval #store this to check later if it has changed
                self.streamingUpdateData = self.server.get_data(variablesRequest, -self.streamingInterval, None,
                                                                self.server.get_settings()["bins"])  # for debug
                self.__dispatch_function(self.stream_update)
            elif not self.streamingMode:
                #do the same as for the "timeseriesWidget.variables" event
                # refresh the lines
                self.server.get_selected_variables_sync()  # get the new set of lines
                self.logger.debug("dispatch the refresh lines")
                self.__dispatch_function(self.update_scores)
                self.__dispatch_function(self.refresh_plot)

        elif data["event"] == "timeSeriesWidget.annotations":
            self.logger.info(f"must reload annotations")
            #self.reInitAnnotationsVisible = self.annotationsVisible #store the state
            # sync from the server
            #self.__dispatch_function(self.reinit_annotations)
            self.__dispatch_function(self.update_annotations_and_thresholds,arg=copy.deepcopy(data))

        elif data["event"] == "global.annotations":
            self.__dispatch_function(self.update_annotations_and_thresholds,arg=copy.deepcopy(data))

        elif data["event"] == "timeSeriesWidget.eventSeries":
            self.logger.debug(f"must reload events")
            self.__dispatch_function(self.update_events,data)

        elif data["event"] == "global.evenSeries.value":
            self.logger.debug(f"must reload events")
            self.__dispatch_function(self.update_events, data)

        elif data["event"] == "timeSeriesWidget.visibleElements":
            self.logger.debug("update the visible Elements")
            eventData  = data["data"]

            #check for start/EndTime
            if "sourcePath" in eventData:
                serverPath = self.server.get_path()
                for var in ["startTime","endTime"]:
                    if eventData["sourcePath"] == serverPath+"."+var:
                        if self.server.get_mirror()[var][".properties"]["value"] == eventData["value"]:
                            self.logger.info("sync x asis not needed")
                            return # ignore this event
                            #must sync the x axis




            oldMirror = copy.deepcopy(self.server.get_mirror())
            visibleElementsOld = oldMirror["visibleElements"][".properties"]["value"]
            visibleTagsOld =oldMirror["hasAnnotation"]["visibleTags"][".properties"]["value"]
            if "hasEvents" in oldMirror:
                visibleEventsOld = oldMirror["hasEvents"]["visibleEvents"][".properties"]["value"]
            else:
                visibleEventsOld = None

            newMirror = copy.deepcopy(self.server.fetch_mirror())
            visibleElementsNew = newMirror["visibleElements"][".properties"]["value"]
            visibleTagsNew = newMirror["hasAnnotation"]["visibleTags"][".properties"]["value"]
            if "hasEvents" in newMirror:
                visibleEventsNew = newMirror["hasEvents"]["visibleEvents"][".properties"]["value"]
            else:
                visibleEventsNew = None

            for entry in ["thresholds","annotations","scores","background","motifs","events"]:
                #check for turn on:
                if entry in visibleElementsNew and visibleElementsNew[entry] == True:
                    if not entry in visibleElementsOld or visibleElementsOld[entry] == False:
                        # element was turned on
                        if entry == "annotations":
                            self.__dispatch_function(self.show_annotations)
                        elif entry == "thresholds":
                            self.__dispatch_function(self.show_thresholds)
                        elif entry == "scores":
                            self.__dispatch_function(self.show_scores)
                        elif entry == "background":
                            self.__dispatch_function(self.show_backgrounds)
                        elif entry == "motifs":
                            self.__dispatch_function(self.show_motifs)
                        elif entry == "events":
                            self.__dispatch_function(self.show_all_events)

                if entry in visibleElementsOld and visibleElementsOld[entry] == True:
                    if not entry in visibleElementsNew or visibleElementsNew[entry]== False:
                        # element was turned off
                        if entry == "annotations":
                            self.__dispatch_function(self.hide_annotations)
                        elif entry == "thresholds":
                            self.__dispatch_function(self.hide_thresholds)
                        elif entry == "scores":
                            self.__dispatch_function(self.hide_scores)
                        elif entry == "background":
                            self.__dispatch_function(self.hide_backgrounds)
                        elif entry == "motifs":
                            self.__dispatch_function(self.hide_motifs)
                        elif entry == "events":
                            self.__dispatch_function(self.hide_all_events)


            #visible tag selections for annotations has changed
            if (visibleTagsOld != visibleTagsNew) and self.showAnnotations:
                self.__dispatch_function(self.show_annotations)

            if (visibleEventsOld != visibleEventsNew):
                self.__dispatch_function(self.show_all_events)
            #startime/endtime has changed

            if (oldMirror["startTime"][".properties"]["value"] !=
                newMirror["startTime"][".properties"]["value"]) or (
                 oldMirror["endTime"][".properties"]["value"] !=
                 newMirror["endTime"][".properties"]["value"]):
                start = date2secs(newMirror["startTime"][".properties"]["value"])*1000
                end = date2secs(newMirror["endTime"][".properties"]["value"])*1000
                #self.rangeStart = date2secs(newMirror["startTime"][".properties"]["value"])*1000
                #self.rangeEnd = date2secs(newMirror["endTime"][".properties"]["value"])*1000
                self.logger.debug("start/end changed")
                times = {"start":start,"end":end}
                self.__dispatch_function(self.sync_x_axis,times)

            #check if streaming mode has changed
            if oldMirror["streamingMode"][".properties"]["value"] != newMirror["streamingMode"][".properties"]["value"]:
                if newMirror["streamingMode"][".properties"]["value"]:
                    self.start_streaming()
                else:
                    self.stop_streaming()

            if oldMirror["panOnlyX"][".properties"]["value"] != newMirror["panOnlyX"][".properties"]["value"]:
                self.set_pan_tool(newMirror["panOnlyX"][".properties"]["value"])

            if "showMarker" in newMirror:
                if oldMirror["showMarker"][".properties"]["value"] != newMirror["showMarker"][".properties"]["value"]:
                    if newMirror["showMarker"][".properties"]["value"]:
                        self.__dispatch_function(self.show_marker)
                    else:
                        self.__dispatch_function(self.hide_marker)

            if "showLegend" in newMirror:
                if oldMirror["showLegend"][".properties"]["value"] != newMirror["showLegend"][".properties"]["value"]:
                    if newMirror["showLegend"][".properties"]["value"]:
                        self.__dispatch_function(self.show_legend)
                    else:
                        self.__dispatch_function(self.hide_legend)

            if "autoScaleY" in newMirror:
                self.autoAdjustY = newMirror["autoScaleY"][".properties"]["value"]

        elif data["event"] == "timeSeriesWidget.values":
            #the data has changed, typically the score values?
            pass

        elif data["event"] == "timeSeriesWidget.newAnnotation":
            #self.logger.debug(f"draw anno!")
            self.__dispatch_function(self.draw_new_annotation)

    def update_scores(self):
        if self.server.fetch_score_variables():
           if self.showScores:
                self.show_scores()

    def show_legend(self):
        self.plot.legend.visible = True

    def hide_legend(self):
        self.plot.legend.visible = False

    def hide_marker(self):
        self.remove_renderers([lin+"_marker" for lin in self.lines])
    def show_marker(self):
        self.logger.debug("show marker")

        for variableName in self.lines:

            markerName = variableName + "_marker"
            color = self.lines[variableName].glyph.line_color
            marker = self.plot.circle(x="x",y="y", line_color=color, fill_color=color,
                                      source=self.columnData[variableName], name=markerName,
                                      size=3)  # x:"time", y:variableName #the legend must havee different name than the source bug


        pass

    def update_column_datas(self,newData):

        if self.columnData =={}:
            self.logger.info("init the colum data")
            for var in self.server.get_variables_selectable():
                self.columnData[var]=ColumnDataSource({"x":[],"y":[]})

        if "__time" in newData:
            del newData["time"]


        for var in newData:
            if not var.endswith("__time"):
                if var.endswith("_limitMax"):
                    #special dictionary
                    minName = var[:-len("_limitMax")]+"_limitMin"
                    if minName in newData:
                        dic = {"x":newData[var+"__time"],
                               "upper":newData[var],
                               "lower":newData[minName],
                               "y":newData[var]} # is needed for the auto adjust y limits
                    else:
                        #min is missing, can't process
                        continue
                else:
                    dic = {"y":newData[var],
                           "x":newData[var+"__time"]}
                if var in self.columnData:
                    self.columnData[var].data = dic #update
                else:
                    self.columnData[var] = ColumnDataSource(dic)


    def sync_x_axis(self,times=None):
        self.logger.debug(f"sync_x_axis x ")

        variables = self.server.get_variables_selected()
        start = times["start"]
        end = times["end"]
        #self.set_x_axis(start,end)
        variablesRequest = variables.copy()
        variablesRequest.append("__time")  # make sure we get the time included
        newData = self.server.get_data(variablesRequest, start, end,
                                                        self.server.get_settings()["bins"])  # for debug
        self.update_column_datas(newData)

        self.set_x_axis(start, end)
        #self.plot.x_range.start = start
        #self.plot.x_range.end = end
        self.autoAdjustY = self.server.get_mirror()["autoScaleY"][".properties"]["value"]
        self.adjust_y_axis_limits()


    def draw_new_annotation(self):
        data = self.server.fetch_mirror()
        entry =  data["nextNewAnnotation"][".properties"]["value"]
        if entry["type"] == "time":
            self.boxSelectTool.dimensions = "width"
            self.set_active_drag_tool(self.boxSelectTool)
            self.currentAnnotationTag = entry["tag"]
        elif entry["type"] == "threshold":
            self.boxSelectTool.dimensions = "height"
            self.set_active_drag_tool(self.boxSelectTool)
            self.currentAnnotationTag = "threshold"
            self.currentAnnotationVariable = entry["variable"]
        elif entry["type"] == "motif":
            self.boxSelectTool.dimensions = "width"
            self.set_active_drag_tool(self.boxSelectTool)
            self.currentAnnotationTag = "motif"
            self.currentAnnotationVariable = entry["variable"]


    def _compare_anno(self,anno1,anno2):

        keysInBoth = set(anno1.keys()).intersection(set(anno2.keys()))

        for k in keysInBoth:
            if k == "browsePath":
                continue
            elif k in ["startTime", "endTime"]:
                diff = abs(anno1[k]-anno2[k])
                if diff < 0.1:
                    continue
                else:
                    self.logger.debug(f'compare failded time diff {diff}')
                    return False
            else:
                if anno1[k] != anno2[k]:
                    print(f"compare failed {k}, {anno1[k]}  {anno2[k]}")
                    return False
        return True



    def update_annotations_and_thresholds(self,arg=None):
        self.logger.debug(f"update_annotations {arg}")
        # this is called when the backend has changed annotation leaves or values, it adjusts annotations
        # and thresholds

        #avoid reload if an envelope embedded in a annotation is changed
        if "data" in arg and "sourcePath" in arg["data"]:
            splitted = arg["data"]["sourcePath"].split('.')
            if len(splitted)>2 and splitted[-2]=="envelope":
                self.logger.info("skip anno update due to envelope")
                return


        lastAnnotations = self.server.get_annotations()
        if "data" in arg and "_eventInfo" in arg["data"]:
            newAnnotations = self.server.fetch_annotations_differential(arg["data"]["_eventInfo"])
        else:
            newAnnotations = self.server.fetch_annotations()

        #check for deletes
        deleteList = [] # a list of ids
        for annoId,anno in lastAnnotations.items():
            if annoId not in newAnnotations:
                self.logger.debug(f"update_annotations() -- annotations was deleted on server: {annoId}, {lastAnnotations[annoId]['name']}")
                deleteList.append(annoId)
                if annoId in self.renderers:
                    with self.renderersLock:
                        self.renderersGarbage.append(self.renderers[annoId]["renderer"])
                    del self.renderers[annoId]
        self.logger.debug(f"update_annotations() -- must delete {deleteList}")



        if self.boxModifierVisible:
            if self.boxModifierAnnotationName in deleteList:
                self.box_modifier_hide()

        #now the new ones
        createdTimeAnnos = []

        for annoId,anno in newAnnotations.items():

            if anno["type"] == "time":
                if annoId not in self.renderers:# and self.showAnnotations:
                    self.logger.debug(f"new annotations {annoId}")
                    self.draw_annotation(anno,visible=False) #will be activated later with show_annotations
                    createdTimeAnnos.append(annoId)
                else:
                    #check if is has changed
                    #if anno != self.renderers[annoId]["info"]:
                    if not self._compare_anno(anno,self.renderers[annoId]["info"] ):
                        self.logger.debug(f"update_annotations() -- annotation has changed {annoId} {self.renderers[annoId]['info']} => {anno}")

                        isVisible = self.renderers[annoId]["renderer"] in self.plot.renderers # remember if the annotation was currently visible
                        with self.renderersLock:
                            self.renderersGarbage.append(self.renderers[annoId]["renderer"])
                        del self.renderers[annoId]# kick out the entry,
                        # if the currently selected is being changed, we hide the box modifier
                        if self.boxModifierVisible:
                            if self.boxModifierAnnotationName == annoId:
                                self.box_modifier_hide()

                        # now recreate: if the annotation was visible before (was in the plot.renderers
                        # then we show it again, if not, we decide later in the show_annotations if it will be shown or not
                        # depending on selected tags etc. this covers especially the exception case where a user
                        # draws a new annotation, which is a currently NOT activated tag, then modifies that new annotation:
                        # it should stay visible!
                        if isVisible:
                            self.draw_annotation(anno, visible=True)        #show right away because it was visible before
                        else:
                            self.draw_annotation(anno, visible=False)       # show later if allowed depending on tags etc.
                            createdTimeAnnos.append(annoId)                 #show later if allowed
            if anno["type"] in ["threshold","motif"]:
                # for thresholds/motifs we do not support delete/create per backend, only modify
                # so check for modifications here
                # it might not be part of the renderers: maybe thresholds are currently off
                if annoId in self.renderers and not self._compare_anno(anno,self.renderers[annoId]["info"]):
                    self.logger.debug(f"update_annotations() -- thresholds has changed {annoId} {self.renderers[annoId]['info']} => {anno}")
                    with self.renderersLock:
                        self.renderersGarbage.append(self.renderers[annoId]["renderer"])
                    del self.renderers[annoId]  # kick out the entry, the remaining invisible renderer will stay in bokeh as garbage
                    #if the currently selected is being changed, we hide the box modifier
                    if self.boxModifierVisible:
                        if self.boxModifierAnnotationName == annoId:
                            self.box_modifier_hide()
                    # now recreate
                    if anno["type"] =="threshold":
                        self.draw_threshold(anno)
                    else:
                        self.draw_motif(anno)

        #now execute the changes
        if 0:
            for entry in deleteList:
                # we only switch it invisible for now, we don't delete the
                # renderer, as this takes too long
                r = self.find_renderer(entry)
                if r:
                    r.visible = False

        if self.showAnnotations and createdTimeAnnos != []:
            self.show_annotations(createdTimeAnnos) # this will put them to the plot renderes

        #self.show_annotations()

        self.remove_renderers() # execute at least the deletes



    def reinit_annotations(self):
        self.hide_annotations()
        self.server.load_annotations()
        self.logger.debug("reinit_annotations=>init_annotations")
        self.init_annotations()
        if self.reInitAnnotationsVisible:
            self.logger.debug("reinit_annotations=>init_annotations")
            self.show_annotations()

    def __legend_check(self):
        try:
            # now we also check if we have a legend click which means that we must delete a variable from the selection
            # self.logger.debug("RENDERERS CHECK --------------------------")
            deleteList = []
            for r in self.plot.renderers:
                if r.name and r.name in self.server.get_variables_selected() and r.visible == False:
                    # there was a click on the legend to hide the variables
                    self.logger.debug("=>>>>>>>>>>>>>>>>>DELETE FROM plot:" + r.name)
                    self.logger.debug("=>>>>>>>>>>>>>>>>>DELETE FROM plot:" + r.name)
                    deleteList.append(r.name)


            if deleteList != []:
                # now make a second run and check the _score variables of the deletlist
                deleteScoreNames = [deletePath.split('.')[-1]+"_score" for deletePath in deleteList]
                deleteExpectedNames = [deletePath.split('.')[-1]+"_expected" for deletePath in deleteList]
                for r in self.plot.renderers:
                    if r.name and (r.name.split('.')[-1] in deleteScoreNames or r.name.split('.')[-1] in deleteExpectedNames):
                        deleteList.append(r.name) #take the according score as well


                # now prepare the new list:
                newVariablesSelected = [var for var in self.server.get_variables_selected() if var not in deleteList]
                self.logger.debug("new var list" + str(newVariablesSelected))
                self.server.set_variables_selected(newVariablesSelected)
                # self.__dispatch_function(self.refresh_plot)

                #now delete potential markers and expected
                self.remove_renderers([lin+"_marker" for lin in deleteList])

        except Exception as ex:
            self.logger.error("problem during __legend_check" + str(ex))

        return (deleteList != [])


    def __init_new_observer(self):
        self.server.sse_register_cb(self.observer_cb)


    def __init_figure(self):

        """
            initialize the time series widget, plot the lines, create controls like buttons and menues
            also hook the callbacks
        """

        self.hoverCounter = 0
        self.newHover = None
        self.hoverTool = None # forget the old hovers
        self.showBackgrounds = False
        self.showThresholds = False
        self.showMotifs = False
        self.showScores = False
        self.buttonWidth = 70

        #layoutControls = []# this will later be applied to layout() function

        settings = self.server.get_settings()
        mirror = self.server.get_mirror()

        if "width" in settings:
            self.width = settings["width"]
        if "height" in settings:
            self.height = settings["height"]

        """ 
        #set the theme
        if settings["theme"] == "dark":
            self.curdoc().theme = Theme(json=themes.darkTheme)
            self.lineColors = themes.darkLineColors
            self.plot.xaxis.major_label_text_color = themes.darkTickColor
        else:
            self.curdoc().theme = Theme(json=themes.whiteTheme)
            self.lineColors = themes.whiteLineColors
            self.plot.xaxis.major_label_text_color = themes.whiteTickColor
        """
        #self.cssClasses = {"button":"button_21","groupButton":"group_button_21","multiSelect":"multi_select_21"}
        #self.cssClasses = {"button": "button_21_sm", "groupButton": "group_button_21_sm", "multiSelect": "multi_select_21_sm"}
        #self.layoutSettings = {"controlPosition":"bottom"} #support right and bottom, the location of the buttons and tools


        #initial values
        try:
            self.rangeStart = date2secs(settings["startTime"])*1000
            self.rangeEnd = date2secs(settings["endTime"])*1000
        except:
            self.rangeStart = None
            self.rangeEnd = None
            self.logger.error("range start, end error, use default full")

        #create figure
        """
           the creation of the figure was reworked as this is a work around for a well known bug (in 1.04), see here
           https://github.com/bokeh/bokeh/issues/7497

           it's a bokeh problem with internal sync problems of frontend and backend, so what we do now is:
           1) use toolbar_location = None to avoid auto-creation of toolbar
           2) create tools by hand
           3) assign them to the figure with add_tools()
           4) create a toolbar and add it to the layout by hand
        """

        if self.server.get_mirror()["panOnlyX"][".properties"]["value"]==True:
            self.wheelZoomTool = WheelZoomTool(dimensions="width")
            self.panTool = PanTool(dimensions="width")
        else:
            self.wheelZoomTool = WheelZoomTool()#dimensions="width")
            self.panTool = PanTool()#dimensions="width")

        tools = [self.wheelZoomTool, self.panTool]
        """
        self.wheelZoomTool = WheelZoomTool()
        self.wheelZoomToolX = WheelZoomTool(dimensions = "width")
        self.panTool = PanTool()
        tools = [self.wheelZoomTool,self.wheelZoomToolX,self.panTool]
        """

        if settings["hasAnnotation"] == True:
            self.boxSelectTool = BoxSelectTool(dimensions="width")
            tools.append(self.boxSelectTool)
        elif settings["hasThreshold"] == True:
            self.boxSelectTool = BoxSelectTool(dimensions="height")
            tools.append(self.boxSelectTool)
        tools.append(ResetTool())
        self.freeZoomTool = BoxZoomTool()
        tools.append(self.freeZoomTool)










        fig = figure(toolbar_location=None, plot_height=self.height,
                     plot_width=self.width,
                     sizing_mode="scale_width",
                     x_axis_type='datetime', y_range=Range1d(),x_range=(0,1))
        self.plot = fig

        # set the theme
        if settings["theme"] == "dark":
            self.curdoc().theme = Theme(json=themes.darkTheme)
            self.lineColors = themes.darkLineColors
            self.plot.xaxis.major_label_text_color = themes.darkTickColor
            self.plot.yaxis.major_label_text_color = themes.darkTickColor
        else:
            self.curdoc().theme = Theme(json=themes.whiteTheme)
            self.lineColors = themes.whiteLineColors
            self.plot.xaxis.major_label_text_color = themes.whiteTickColor
            self.plot.yaxis.major_label_text_color = themes.whiteTickColor


        #b1 = date2secs(datetime.datetime(2015,2,13,3,tzinfo=pytz.UTC))*1000
        #b2 = date2secs(datetime.datetime(2015,2,13,4,tzinfo=pytz.UTC))*1000
        #wid = 20*60*1000 # 20 min
        #self.boxData = ColumnDataSource({'x': [b1,b2], 'y':[0,0],'width': [5, 5],'height':[300,300],"alpha":[1,1,0.2]})

        #self.boxRect = self.plot.rect(x="x", y="y", width="width", height="height",source=self.boxData)
        #self.boxRect = self.plot.rect('x', 'y', 'width', 'height', source=self.boxData,width_units="screen")#, height_units="screen")#, height_units="screen")
        self.boxModifierTool=BoxEditTool( renderers=[],num_objects=0,empty_value=0.1)#,dimensions="width")
        self.box_modifier_init()
        #self.box_modifier_show()

        # possible attribures to boxedittool:
        # custom_icon, custom_tooltip, dimensions, empty_value, js_event_callbacks, js_property_callbacks, name, num_objects, renderers, subscribed_events
        #self.plot.add_layout(self.boxRect)
        #self.boxModifierRect.data_source.on_change("selected",self.box_cb)
        #self.boxRect.data_source.on_change("active", self.box_cb_2)

        tools.append(self.boxModifierTool)





        for tool in tools:
            fig.add_tools(tool) # must assign them to the layout to have the actual use hooked
        toolBarBox = ToolbarBox()  #we need the strange creation of the tools to avoid the toolbar to disappear after
                                   # reload of widget, then drawing an annotations (bokeh bug?)
        toolBarBox.toolbar = Toolbar(tools=tools,active_inspect=None,active_scroll=self.wheelZoomTool,active_drag = None)
        #active_inspect = [crosshair],
        # active_drag =                         # here you can assign the defaults
        # active_scroll =                       # wheel_zoom sometimes is not working if it is set here
        # active_tap
        toolBarBox.toolbar_location = "right"
        toolBarBox.toolbar.logo = None # no bokeh logo

        self.tools = toolBarBox
        self.toolBarBox = toolBarBox


        self.plot.xaxis.formatter = FuncTickFormatter(code = """
            let local = moment(tick).tz('%s');
            let datestring =  local.format();
            return datestring.slice(0,-6);
            """%settings["timeZone"])

        self.plot.xaxis.ticker = DatetimeTicker(desired_num_ticks=5)# give more room for the date time string (default was 6)

        self.plot.xgrid.ticker = self.plot.xaxis.ticker

        self.build_second_y_axis()

        self.refresh_plot()

        #hook in the callback of the figure
        self.plot.x_range.on_change('start', self.range_cb)
        self.plot.x_range.on_change('end', self.range_cb)
        self.plot.on_event(events.Pan, self.event_cb)
        self.plot.on_event(events.PanStart, self.event_cb)
        self.plot.on_event(events.PanEnd, self.event_cb)
        self.plot.on_event(events.LODEnd, self.event_cb)
        self.plot.on_event(events.Reset, self.event_cb)
        self.plot.on_event(events.SelectionGeometry, self.event_cb)
        self.plot.on_event(events.Tap,self.event_cb)


        #make the controls
        layoutControls =[]

        #Annotation drop down
        if 0: #no drop down for now
            labels=[]
            if settings["hasAnnotation"] == True:
                labels = settings["tags"]
                labels.append("-erase-")
            if settings["hasThreshold"] == True:
                labels.extend(["threshold","-erase threshold-"])
            if labels:
                menu = [(label,label) for label in labels]
                self.annotationDropDown = Dropdown(label="Annotate: "+str(labels[0]), menu=menu,width=self.buttonWidth,css_classes = ['dropdown_21'])
                self.currentAnnotationTag = labels[0]
                self.annotationDropDown.on_change('value', self.annotation_drop_down_on_change_cb)
                #self.annotation_drop_down_on_change_cb() #call it to set the box select tool right and the label
                layoutControls.append(self.annotationDropDown)

        """ 
        currently disabled
        
        # show Buttons
        # initially everything is disabled
        # check background, threshold, annotation, streaming
        self.showGroupLabels = []
        self.showGroupLabelsDisplay=[]
        if self.server.get_settings()["hasAnnotation"] == True:
            self.showGroupLabels.append("Annotation")
            self.showGroupLabelsDisplay.append("Anno")
        if self.server.get_settings()["background"]["hasBackground"]:
            self.showGroupLabels.append("Background")
            self.showGroupLabelsDisplay.append("Back")
            self.showBackgrounds = False # initially off
        if self.server.get_settings()["hasThreshold"] == True:
            self.showGroupLabels.append("Threshold")
            self.showGroupLabelsDisplay.append("Thre")
            self.showThresholds = False # initially off
        if self.server.get_settings()["hasStreaming"] == True:
            self.showGroupLabels.append("Streaming")
            self.showGroupLabelsDisplay.append("Stream")
            self.streamingMode = False # initially off
        self.showGroup = CheckboxButtonGroup(labels=self.showGroupLabelsDisplay)
        self.showGroup.on_change("active",self.show_group_on_click_cb)
        layoutControls.append(row(self.showGroup))
        """

        #make the custom buttons
        buttonControls = []
        self.customButtonsInstances = []
        if "buttons" in settings:
            self.logger.debug("create user buttons")
            #create the buttons
            for entry in settings["buttons"]:
                button = Button(label=entry["name"],width=self.buttonWidth)#,css_classes=['button_21'])
                instance = self.ButtonCb(self,entry["targets"])
                button.on_click(instance.cb)
                buttonControls.append(button)
                self.customButtonsInstances.append(instance)

        #make the debug button
        if "hasReloadButton" in self.server.get_settings():
            if self.server.get_settings()["hasReloadButton"] == True:
                #we must create a reload button
                button = Button(label="reload",width=self.buttonWidth)#, css_classes=['button_21'])
                button.on_click(self.reset_all)
                buttonControls.append(button)


        if 0: # turn this helper button on to put some debug code
            self.debugButton= Button(label="debug")
            self.debugButton.on_click(self.debug_button_cb)
            self.debugButton2 = Button(label="debug2")
            self.debugButton2.on_click(self.debug_button_2_cb)
            buttonControls.append(self.debugButton)
            buttonControls.append(self.debugButton2)


        layoutControls.extend(buttonControls)

        #build the layout


        self.layout = layout([row(children=[self.plot, self.tools], sizing_mode="fixed")], row(layoutControls, width=int(self.width*0.6),sizing_mode="scale_width"))
        #self.layout = layout([row(children=[self.plot, self.tools], sizing_mode="fixed")])

        if self.server.get_settings()["hasAnnotation"] == True:
            self.init_annotations() # we create all annotations that we have into self.annotations

        if "hasEvents" in self.server.get_settings() and self.server.get_settings()["hasEvents"] == True:
            self.init_events()


    def init_additional_elements(self):
        #now also display further elements
        visibleElements = self.server.get_mirror()["visibleElements"][".properties"]["value"]
        if "annotations" in visibleElements and visibleElements["annotations"] == True:
            self.show_annotations()

        if "thresholds" in visibleElements and visibleElements["thresholds"] == True:
            self.show_thresholds()

        if "background" in visibleElements and visibleElements["background"] == True:
            #self.showBackgrounds=True
            self.show_backgrounds()

        if "scores" in visibleElements and visibleElements["scores"] == True:
            self.show_scores()

        if "motifs" in visibleElements and visibleElements["motifs"] == True:
            self.show_motifs()

        if self.server.get_mirror()["streamingMode"][".properties"]["value"] == True:
            self.start_streaming()

    def set_active_drag_tool(self,tool):
        #we need to change the default selection of active drag and then write the list of tools to the toolsbar
        # the list must be different, otherwise the write will not cause the "rebuild" of the tools
        # so we take the last from the list and hide it shortly
        self.logger.debug(f"set active drag tool, {tool}")

        if hasattr(self,"toolBarBox"): #check this: at the startup we are not yet fully supplied, so nothing to do here
            if self.toolBarBox.toolbar.active_drag == tool:
                self.logger.debug("active drag already active")
                return
            store = self.toolBarBox.toolbar.tools
            self.toolBarBox.toolbar.tools = store[:-1] # write something else so we have a change to force the rebuild
            #now set the active drag
            self.toolBarBox.toolbar.active_drag = tool
            self.toolBarBox.toolbar.tools = store

    def set_pan_tool(self,panOnlyX=True):
        self.logger.debug(f"set x only pan: {panOnlyX}")
        if hasattr(self,"toolBarBox"): #check this: at the startup we are not yet fully supplied, so nothing to do here

            store = self.toolBarBox.toolbar.tools

            if panOnlyX==True:
                self.wheelZoomTool = WheelZoomTool(dimensions="width")
                self.panTool = PanTool(dimensions="width")
            else:
                self.wheelZoomTool = WheelZoomTool()#dimensions="width")
                self.panTool = PanTool()#dimensions="width")


            store =[self.wheelZoomTool,self.panTool]+store[2:]
            self.toolBarBox.toolbar.tools = store

    def build_second_y_axis(self):
        self.plot.extra_y_ranges = {"y2": Range1d(start=0, end=1)}
        self.y2Axis = LinearAxis(y_range_name="y2")
        self.y2Axis.visible = False
        self.plot.add_layout(self.y2Axis, 'right')
        self.y2Axis.visible=False
        #self.plot.circle(list(range(len(new_df['zip']))), new_df['station count'], y_range_name='NumStations', color='blue')


    def debug_button_2_cb(self):

        if 0:
            source = copy.deepcopy(self.debugsource.data)

            infi = 1000000
            self.logger.debug("debug button cb")
            basic = date2secs("20150214T12:00:00+02:00")
            times=[]
            ys = []
            for n in range(500):
                tim = basic+n
                times.extend([tim,tim,numpy.nan])
                ys.extend([-infi,infi,numpy.nan])
            times=numpy.asarray(times)*1000
            dic = {"x":times,"y":ys}
            self.debugsource.data = dic # update


        if 1:
            self.evs.visible=False



    def debug_button_cb(self):

        if 1:
            infi = 1000000
            self.logger.debug("debug button cb")
            basic = date2secs("20150214T00:00:00+02:00")
            times=[]
            ys = []
            for n in range(10000):
                tim = basic+n
                times.extend([tim,tim,numpy.nan])
                ys.extend([-infi,infi,numpy.nan])
            times=numpy.asarray(times)*1000
            self.debugsource = ColumnDataSource({"x": times,"y":ys})
            self.logger.debug(f"epoches {times}")

            infinity = 1000000000

            self.evs = self.plot.line(x="x",y="y", source=self.debugsource,color="red") # works

        if 0:
            basic = date2secs("20150214T00:00:00+02:00")
            ss=[]
            self.logger.debug("start span createion")
            for n in range(5000):
                s= Span(location=(basic+n)*1000, dimension='height', line_color='red', line_width=3)
                ss.append(s)
            self.logger.debug("add spans")
            self.add_renderers(ss)
            self.ss = ss
            self.logger.debug("adding done")










    def setup_toolbar(self):
        self.logger.debug("set back")
        self.toolBarBox.toolbar.active_drag = self.debug["next"]
        self.toolBarBox.toolbar.tools = self.debug["value"]
        self.debug = None


    def box_cb(self,attr,old,new):
        self.debug("BOXCB")

    def box_update(self,x1,x2):
        self.boxData.data["xs"]=[x1,x2]

    def show_group_on_click_cb(self,attr,old,new):
        # in old, new we get a list of indices which are active
        self.logger.debug("show_group_on_click_cb "+str(attr)+str(old)+str(new))
        turnOn = [self.showGroupLabels[index] for index in (set(new)-set(old))]
        turnOff = [self.showGroupLabels[index] for index in (set(old)-set(new))]
        if "Background" in turnOn:
            self.showBackgrounds = True
            self.refresh_backgrounds()
        if "Background" in turnOff:
            self.showBackgrounds = False
            self.refresh_backgrounds()
        if "Annotation" in turnOn:
            self.show_annotations()
        if "Annotation" in turnOff:
            self.hide_annotations()
        if "Threshold" in turnOn:
            self.showThresholds = True
            self.show_thresholds()
        if "Threshold" in turnOff:
            self.showThresholds = False
            self.hide_thresholds()
        if "Streaming" in turnOn:
            self.start_streaming()
        if "Streaming" in turnOff:
            self.stop_streaming()

    def start_streaming(self):
        self.logger.debug(f"start_streaming {self.rangeEnd-self.rangeStart}")
        #get data every second and push it to the graph
        self.streamingInterval = self.rangeEnd-self.rangeStart # this is the currently selected "zoom"
        self.streamingUpdateData = None
        self.streamingMode = True


    def stop_streaming(self):
        self.logger.debug("stop streaming")
        self.streamingMode = False



    def annotation_drop_down_on_change_cb(self,attr,old,new):
        mytag = self.annotationDropDown.value
        self.logger.debug("annotation_drop_down_on_change_cb " + str(mytag))
        self.annotationDropDown.label = "Annotate: "+mytag
        self.currentAnnotationTag = mytag
        if "threshold" in mytag:
            #we do a a threshold annotation, adjust the tool
            self.boxSelectTool.dimensions = "height"
        else:
            self.boxSelectTool.dimensions = "width"


    """
    def annotations_radio_group_cb(self,args):
        #called when a selection is done on the radio button for the annoations
        option = self.annotationButtons.active  # gives a 0,1 list, get the label now
        # tags = self.server.get_settings()["tags"]
        mytag = self.annotationTags[option]
        self.logger.debug("annotations_radio_group_cb "+str(mytag))
        if "threshold" in mytag:
            #we do a a threshold annotation, adjust the tool
            self.boxSelectTool.dimensions = "height"
        else:
            self.boxSelectTool.dimensions = "width"
    """

    def testCb(self, attr, old, new):
        self.logger.debug("testCB "+"attr"+str(attr)+"\n old"+str(old)+"\n new"+str(new))
        self.logger.debug("ACTIVE: "+str(self.plot.toolbar.active_drag))

    def remove_hover(self):

        self.hoverTool.renderers=[]


        self.logger.debug(f"remove hover")

        #self.remove_hover_2()
        #self.__dispatch_function(self.remove_hover_2)
        #self.__dispatch_function(self.__make_tooltips)
        #self.__make_tooltips()

    def remove_hover_2(self):
        self.logger.debug(f"remove hover2")

        self.hoverTool.renderers = []
        store = self.toolBarBox.toolbar.tools
        newTools = []
        for entry in self.toolBarBox.toolbar.tools:
            if type(entry) != HoverTool:
                newTools.append(entry)
        self.toolBarBox.toolbar.tools = newTools
        self.hoverTool = None

        #self.__make_tooltips()


    def __make_tooltips(self):
        #make the hover tool
        """
            if we create a hover tool, it only appears if we plot a line, we need to hook the hover tool to the figure and the toolbar separately:
            to the figure to get the hover functionality, there we also need to add all renderers to the hover by hand if we create line plots later on
            still haven't found a way to make the hover tool itself visible when we add it to the toolbar; it does appear when we draw a new line,
            if we change edit/del and add lines, (including their renderers, we need to del/add those renderes to the hover tools as well

        """

        #check if lines have changed:
        if self.hoverTool:
            newLines = set([v for k,v in self.lines.items() if not self.server.is_score_variable(k) ]) # only the non-score lines
            newEventLines = set([ v["renderer"] for k,v in self.eventLines.items()])
            newLines.update(newEventLines)
            hoverLines = set(self.hoverTool.renderers)
            if newLines != hoverLines:

                self.logger.debug(f"reset hover tool MUSt UPDATE newLines {newLines}, hoverLines{hoverLines}")
                self.hoverTool.renderers = []
                store = self.toolBarBox.toolbar.tools
                newTools = []
                for entry in self.toolBarBox.toolbar.tools:
                    if type(entry) != HoverTool:
                        newTools.append(entry)
                self.toolBarBox.toolbar.tools = newTools
                self.hoverTool = None

        if not self.hoverTool or  newLines != hoverLines:
            renderers = []

            for k, v in self.eventLines.items():
                self.logger.debug(f"add {k} to hover")
                renderers.append(v["renderer"])

            for k, v in self.lines.items():
                if not self.server.is_score_variable(k):
                    self.logger.debug(f"add line {k} t hover")
                    renderers.append(v)

            self.logger.info(f"number of new hovers {len(renderers)}")
            #for h in self.annoHovers:
            #    #print(f"add hover {h}")
            #    renderers.append(h)






        if not self.hoverTool:
            #we do this only once

            self.logger.info("MAKE TOOLTIPS"+str(self.hoverCounter))
            hover = HoverTool(renderers=renderers) #must apply them here to be able to dynamically change them
            #hover.tooltips = [("name","$name"),("time", "@__time{%Y-%m-%d %H:%M:%S.%3N}"),("value","@$name{0.000}")] #show one digit after dot
            #hover.tooltips = [("name", "$name"), ("time", "@{__time}{%f}"),
            #                 ("value", "@$name{0.000}")]  # show one digit after dot


            hover.tooltips = [("name", "$name"), ("time", "@{x}{%f}"),
                              ("value", "@y{0.000}")]  # show one digit after dot
            if 0:
                mytooltip = """
                    <script>
                        //.bk-tooltip>div:not(:first-child) {display:none;}
                        console.log("hier hallo");
                    </script>
    
                    <b>X: </b> @x <br>
                    <b>Y: </b> @y
                """
            #hover.tooltips = mytooltip

            #hover.formatters={'__time': 'datetime'}
            #custom = """var local = moment(value).tz('%s'); return local.format();"""%self.server.get_settings()["timeZone"]
            custom = """var local = moment(value).tz('%s'); return local.format();""" % self.server.get_settings()["timeZone"]
            #custom2 = """var neu;neu = source.data['test'][0]; return String(value);"""
            #self.testSource = ColumnDataSource({"test":[67]*1000})
            #hover.formatters = {'__time': CustomJSHover(code=custom)}
            custom3 = """ console.log(cb_data);"""
            hover.formatters = {'x': CustomJSHover(code=custom)}#, 'z':CustomJSHover(args=dict(source=self.testSource),code=custom2)}
            #hover.callback=CustomJS(code=custom3)

            if self.server.get_settings()["hasHover"] in ['vline','hline','mouse']:
                hover.mode = self.server.get_settings()["hasHover"]
            hover.mode = "mouse"
            hover.line_policy = 'interp'#need this instead of nearest for the event lines: they end in +- infinity, with the "nearest", they would show their tooltip hover at the end of their line, outside the visible area
            self.plot.add_tools(hover)

            self.hoverTool = hover
            self.toolBarBox.toolbar.tools.append(hover)  # apply he hover tool to the toolbar




        # we do this every time
        # reapply the renderers to the hover tool
        if 0:
            renderers = []
            self.hoverTool.renderers = []
            renderers = []
            for k, v in self.lines.items():

                if not self.server.is_score_variable(k):
                    self.logger.debug(f"add line {k} t hover")
                    renderers.append(v)
            self.hoverTool.renderers = renderers



    def stream_update_backgrounds(self):
        """ we update the background by following this algo:
            - take the last existing entry in the backgrounds
            - do we have a new one which starts inside the last existing?
              NO: find the
        """
        #make current backgrounds from the latest data and check against the existing backgrounds, put those which we need to append
        newBackgrounds = self.make_background_entries(self.streamingUpdateData)
        addBackgrounds = [] # the backgrounds to be created new
        self.logger.debug("stream_update_backgrounds")
        if self.backgrounds == []:
            #we don't have backgrounds yet, make them
            self.hide_backgrounds()
        else:
            # we have backgrounds
            # now see if we have to adjust the last background
            for entry in newBackgrounds:
                if entry["start"] <= self.backgrounds[-1]["end"] and entry["end"] > self.backgrounds[-1]["end"]:
                    # this is the first to show, an overlapping or extending one, we cant' extend the existing easily, so
                    # we put the new just right of the old
                    addEntry = {"start": self.backgrounds[-1]["end"], "end": entry["end"], "value":entry["value"], "color": entry["color"]}
                    addBackgrounds.append(addEntry)
                if entry["start"] > self.backgrounds[-1]["end"] and entry["end"]> self.backgrounds[-1]["end"]:
                    #these are on the right side of the old ones, just add them
                    addBackgrounds.append(entry)

        boxes =[]

        for back in addBackgrounds:
            name = "__background"+str('%8x'%random.randrange(16**8))
            newBack = BoxAnnotation(left=back["start"], right=back["end"],
                                    fill_color=back["color"],
                                    fill_alpha=globalBackgroundsAlpha,
                                    level = globalBackgroundsLevel,
                                    name=name)  # +"_annotaion
            boxes.append(newBack)
            back["rendererName"]=name
            self.backgrounds.append(back) # put it in the list of backgrounds for later use

        self.plot.renderers.extend(boxes)

        #remove renderes out of sight
        deleteList = []
        for r in self.plot.renderers:
            if r.name and "__background" in r.name:
                #self.logger.debug(f"check {r.name}, is is {r.right} vs starttime {self.plot.x_range.start}")
                #this is a background, so let's see if it is out of sight
                if r.right < self.plot.x_range.start:
                    #this one can go, we can't see it anymore
                    deleteList.append(r.name)
        self.logger.debug(f"remove background renderes out of sight{deleteList}")
        if deleteList:
            self.remove_renderers(deleteList=deleteList)


        #newBackgrounds = self.make_background_entries(self.streamingUpdateData)
        #self.hide_backgrounds()
        #self.show_backgrounds()


        return

    def stream_update_new(self,data):
        """
            this is triggered from the "global.series.stream" event, we first need to check if there is any id in this
            event which we want
        :return:
        """

        #check for variable/score update
        if data["data"]["_eventInfo"]["startTime"] < self.plot.x_range.end / 1000:
            for browsePath in data["data"]["_eventInfo"]["browsePaths"]:
                if browsePath in self.lines and self.lines[browsePath].visible == True:
                    self.refresh_plot()
                    break

        allEventIds = [v["nodeId"] for k, v in self.eventLines.items()]
        for id in data["data"]["_eventInfo"]["nodeIds"]:
            if id in allEventIds:
                #must update the events
                self.update_events()
                break

    def stream_update_is_relevant(self,data):
        """
            this is triggered from the "global.series.stream" event,
            we first need to check if it is relevant for us
            event which we want
        :return:
        """
        try:
            #first check if we have an event update info, then we pick it
            allEventIds = [v["nodeId"] for k,v in self.eventLines.items()]
            for id in data["data"]["_eventInfo"]["nodeIds"]:
                if id in allEventIds:
                    return True # a currently visible event type is updated

            if data["data"]["_eventInfo"]["startTime"]>self.plot.x_range.end/1000:
                #the update is outside (to the right) of the visible area, so ignore
                return False
            # now check if any of the ids are relevant
            # they can be an line, a score, a background or an event
            for browsePath in data["data"]["_eventInfo"]["browsePaths"]:
                if browsePath in self.lines and self.lines[browsePath].visible==True:
                    return True # a variable or score is updated

        except:
            self.log_error()
        return False



    def stream_update(self):
        try:
            self.inStreamUpdate = True # to tell the range_cb that the range adjustment was not from the user
            self.logger.debug("stream update")#+str(self.streamingUpdateData))
            if self.streamingUpdateData:
                if not self.userZoomRunning:
                    if not self.streamingUpdateDataInterval == self.streamingInterval:
                        #the interval has changed in the meantime due to user pan/zoom, we skip this data, get fresh one
                        self.streamingUpdateData = None
                        self.inStreamUpdate = False
                        self.logger.warning("streaming interval has changed")
                        return

                    self.logger.debug(f"apply data {self.streamingUpdateData.keys()},")
                    self.update_column_datas(self.streamingUpdateData)
                    mini,maxi = self.get_min_max_times(self.streamingUpdateData)
                    self.logger.debug(f"streaming x_range: start {mini} end {maxi}, interv {self.streamingInterval}, {maxi-self.streamingInterval} ")
                    self.set_x_axis(maxi-self.streamingInterval,maxi)
                    self.adjust_y_axis_limits()
                    if self.showBackgrounds:
                        self.stream_update_backgrounds()

                    self.streamingUpdateData = None #the thread can get new data
                else:
                    self.logger.info("user zoom running, try later")
                    #user is panning, zooming, we should wait and try again later
                    self.__dispatch_function(self.stream_update)
        except Exception as ex:
            self.logger.error(f"stream_update error {ex}")
        self.inStreamUpdate = False
        self.streamingUpdateData = None


    def reset_all(self):
        """
            this is an experimental function that reloads the widget in the frontend
            it should be executed as dispatched
        """
        self.logger.debug("self.reset_all()")
        self.server.refresh_settings()

        #clear out the figure
        self.hasLegend = False # to make sure the __init_figure makes a new legend
        self.plot.renderers = [] # no more renderers
        #self.data = None #no more data
        self.columnData={}
        self.lines = {} #no more lines



        self.__init_figure()
        #self.__init_observer()
        self.__init_new_observer()

        self.curdoc().clear()
        self.curdoc().add_root(self.get_layout())

    def __dispatch_function(self,function,arg=None):
        """
            queue a function to be executed in the periodic callback from the bokeh app main loop
            this is needed for functions which are triggered from a separate thread but need to be
            executed in the context of the bokeh app loop

        Args:
            function: functionpointer to be executed
        """
        with self.dispatchLock:
            self.logger.debug(f"__dispatch_function {function.__name__}, arg: {arg}")
            self.dispatchList.append({"function":function,"arg":arg})


    def is_second_axis(self,name):
        return ".score" in name

    def adjust_y_axis_limits(self):
        """
            this function automatically adjusts the limts of the y-axis that the data fits perfectly in the plot window
        """
        self.logger.debug(f"adjust_y_axis_limits self.autoAdjustY:{self.autoAdjustY}")

        if not self.autoAdjustY:
            ## only rescale the box_modifier, this is needed in streaming to keep the left
            # and right limits
            self.box_modifier_rescale() # only rescale the box_modifier, this is needed in streaming to keep the left
            return

        lineData = []
        selected = self.server.get_variables_selected()
        for item in self.columnData:
            if item in selected and not self.is_second_axis(item):
                yData = self.columnData[item].data["y"]
                if len(yData) >= 2:
                    # the outer left and right are ignored in the scaling to avoid influence of
                    # points that are included in the data query and which are far away due to a missin data area
                    # if you have small variation of values and then a gap and than a totally different value
                    # and that value is part of the query but only one point, the small variations can't be seen
                    # now it's possible, this problem was introduced via the "include borders" style of the data
                    # query to get the connecting lines to the next point OUT of the visible area
                    yData=yData[1:-1]
                lineData.extend(yData)

        if len(lineData) > 0:
            all_data = numpy.asarray(lineData, dtype=numpy.float)
            dataMin = numpy.nanmin(lineData)
            dataMax = numpy.nanmax(lineData)
            if dataMin==dataMax:
                dataMin -= 1
                dataMax += 1
            # Adjust the Y min and max with 2% border
            yMin = dataMin - (dataMax - dataMin) * 0.02
            yMax = dataMax + (dataMax - dataMin) * 0.02
            self.logger.debug("current y axis limits" + str(yMin)+" "+str(yMax))

            self.plot.y_range.start = yMin
            self.plot.y_range.end = yMax
            
            self.box_modifier_rescale()

        else:
            self.logger.warning("not y axix to arrange")


    def box_modifier_init(self):
        self.logger.debug("box_modifier_init")
        self.boxModifierWidth = 8

        b1 = date2secs(datetime.datetime(2015, 2, 13, 3, tzinfo=pytz.UTC)) * 1000
        b2 = date2secs(datetime.datetime(2015, 2, 13, 4, tzinfo=pytz.UTC)) * 1000
        wid = 20 * 60 * 1000  # 20 min
        self.boxModifierData = ColumnDataSource( {'x': [b1, b2], 'y': [0, 0], 'width': [self.boxModifierWidth, self.boxModifierWidth], 'height': [300, 300] })

        self.boxModifierRectHorizontal = self.plot.rect('x', 'y', 'width', 'height', source=self.boxModifierData, width_units="screen",line_width=1,line_dash="dotted",line_color="white",fill_color="white" )  # , height_units="screen")#, height_units="screen")
        self.boxModifierRectVertical = self.plot.rect('x', 'y', 'width', 'height', source=self.boxModifierData, height_units="screen",line_width=1,line_dash="dotted",line_color="white",fill_color="white")  # , height_units="screen")#, height_units="screen")

        self.boxModifierRectHorizontal.data_source.on_change("selected", self.box_cb)
        self.boxModifierRectVertical.data_source.on_change("selected", self.box_cb)

        self.box_modifier_hide()# remove the renderers

    def box_modifier_tap(self, x=None, y=None):

        self.logger.debug(f"box_modifier_tap x:{x} y:{y}")
        candidates = []
        #check if we are inside a visible annotation
        for annoId, anno in self.server.get_annotations().items():
            #self.logger.debug("check anno "+annoName+" "+anno["type"])
            candidate = False
            if anno["type"] in ["time","motif"]:
                if anno["startTime"]<x and anno["endTime"]>x:
                    #we are inside this annotation:
                    candidate=True
            elif anno["type"] == "threshold":
                if anno["min"] < y and anno["max"] > y:
                    candidate = True
            if candidate:
                if self.find_renderer(anno["id"]):
                    #we are inside this anno and it is visible,
                    candidates.append(annoId)
                    if self.boxModifierVisible:
                        pass # we rotate activation later
                    else:
                        self.box_modifier_show(annoId, anno)
                        return

        if candidates:
            if self.boxModifierAnnotationName in candidates:

                candidates.append(candidates[0])  # if wrap around
                next = candidates.index(self.boxModifierAnnotationName)+1
                annoNext = candidates[next]
                #self.logger.debug(f"candidates, next {annoNext}")
                self.box_modifier_show(annoNext, self.server.get_annotations()[annoNext])
                return
            else:
                annoId = candidates[0]
                #self.logger.debug(f"only {annoId}")
                self.box_modifier_show(annoId,self.server.get_annotations()[annoId])
                return

        else:

            backgroundSelected = self.background_highlight_show(x,y)
            if backgroundSelected:
                return



        #we are not inside an annotation, we hide the box modifier
        self.box_modifier_hide(auto=True)

    def background_highlight_show(self,x,y):
        if self.backgroundHighlightVisible:
            #havent found one
            self.background_highlight_hide()

        for r in self.plot.renderers:
            if r.name:
                if r.name.startswith("__background"):
                    backStart = r.left
                    backEnd = r.right
                    if x >= backStart and x <= backEnd:
                        #alphaNow = r.fill_alpha
                        r.fill_alpha = globalBackgroundsHighlightAlpha#alphaNow + 0.5 * (1 - alphaNow)
                        self.logger.debug("inside Background!")
                        self.server.set_background_highlight(x,y,backStart,backEnd)
                        self.backgroundHighlightVisible = True
                        return True



        return False

    def background_highlight_hide(self):
        if self.backgroundHighlightVisible:
            self.backgroundHighlightVisible=False
            for r in self.plot.renderers:
                if r.name:
                    if r.name.startswith("__background"):
                        alphaNow = r.fill_alpha
                        if alphaNow != globalBackgroundsAlpha:
                            r.fill_alpha = globalBackgroundsAlpha
                            self.server.set_background_highlight(0,0,0,0,remove=True)
                            return


    def box_modifier_show(self,annoName,anno):
        """
            Args:
                annoName: the key in the annotationlist (=id in the model)
        """

        self.logger.debug(f"box_modifier_show {annoName}")

        if self.boxModifierVisible:
            if self.boxModifierAnnotationName == annoName:
                #this one is already visible, we are done
                return False
            else:
                # if another is already visible, we hide it first
                # but we keep the tool active, so don't call box_modifier_hide() here
                self.boxModifierRectVertical.visible = False  # hide the renderer
                self.boxModifierRectHorizontal.visible = False  # hide the renderer

        self.boxModifierAnnotationName = annoName
        #self.server.select_annotation(annoName)
        boxYCenter = float(self.plot.y_range.start + self.plot.y_range.end) / 2
        boxXCenter = float(self.plot.x_range.start + self.plot.x_range.end) / 2
        boxYHeight = (self.plot.y_range.end - self.plot.y_range.start) * 4
        boxXWidth = (self.plot.x_range.end - self.plot.x_range.start) *4

        if anno["type"] in ["time","motif"]:
            start = anno["startTime"]
            end = anno["endTime"]
            self.boxModifierData.data = {'x': [start, end], 'y': [boxYCenter, boxYCenter], 'width': [self.boxModifierWidth, self.boxModifierWidth], 'height': [boxYHeight, boxYHeight]}
            self.boxModifierRectHorizontal.visible=True
            self.boxModifierOldData = dict(copy.deepcopy(self.boxModifierData.data))
            self.boxModifierVisible = True
            #self.plot.renderers.append(self.boxModifierRectHorizontal)
            self.boxModifierTool.renderers = [self.boxModifierRectHorizontal]  # ,self.boxModifierRectVertical]

        if anno["type"] == "threshold":
            self.boxModifierData.data = {'x': [boxXCenter, boxXCenter], 'y': [anno['min'], anno['max']], 'width': [boxXWidth,boxXWidth], 'height': [self.boxModifierWidth, self.boxModifierWidth]}
            self.boxModifierRectVertical.visible=True
            self.boxModifierOldData = dict(copy.deepcopy(self.boxModifierData.data))
            self.boxModifierVisible = True
            #self.plot.renderers.append(self.boxModifierRectVertical)
            self.boxModifierTool.renderers = [self.boxModifierRectVertical]

        self.set_active_drag_tool(self.boxModifierTool)
        self.server.select_annotation(annoName)
        return True

    def box_modifier_hide(self,auto = False):
        """
            if auto is set, we check if visible before
        """
        if auto and not self.boxModifierVisible:
            self.set_active_drag_tool(self.panTool)
            return

        self.boxModifierVisible = False
        self.boxModifierRectVertical.visible = False #hide the renderer
        self.boxModifierRectHorizontal.visible = False #hide the renderer

        self.set_active_drag_tool(self.panTool) # this is actually pretty slow ~ 500ms

        self.server.select_annotation([]) # unselect all
        #also remove the renderer from the renderers
        #self.remove_renderers(renderers=[self.boxModifierRectHorizontal,self.boxModifierRectVertical])



    # this is called when we resize the plot via variable selection, mouse wheel etc
    def box_modifier_rescale(self):
        self.logger.info(f"box_modifier_rescale self.boxModifierVisible{self.boxModifierVisible}, self.inPan{self.inPan}")
        #self.logger.debug(f"box_modifier_rescale self.boxModifierVisible={self.boxModifierVisible}")
        if self.boxModifierVisible == False:
            return

        # also, if we currently move the boxmodifier around per drag and drop,
        # we don't want to touch it here until the user releases
        if self.inPan:
            self.logger.info("box_modifier_rescale skipped in pan")
            return

        anno = self.server.get_annotations()[self.boxModifierAnnotationName]
        if anno["type"] in ["time","motif"]:
            #adjust the limits to span the rectangles on full view area
            boxYCenter = float((self.plot.y_range.start + self.plot.y_range.end)/2)
            boxYHeight = (self.plot.y_range.end - self.plot.y_range.start)*4
            data = dict(copy.deepcopy(self.boxModifierData.data))
            data['y'] = [boxYCenter, boxYCenter]
            data['height'] = [boxYHeight, boxYHeight]
            self.boxModifierData.data = data
        if anno["type"] == "threshold":
            boxXCenter = float((self.plot.x_range.start + self.plot.x_range.end) / 2)
            data = dict(copy.deepcopy(self.boxModifierData.data))
            data['x'] = [boxXCenter, boxXCenter]
            self.boxModifierData.data = data

    def adjust_annotation(self,anno):
        if anno["type"]=="time":
            if self.find_renderer(anno["id"]):
                if anno["rendererType"] == "VArea":
                    source = self.renderers[anno["id"]]["source"]
                    source.patch({'x':[ (0,anno["startTime"]),(1,anno["endTime"]) ]})
                elif anno["rendererType"] == "VBar":
                    source = self.renderers[anno["id"]]["source"]
                    start = anno["startTime"]
                    end = anno["endTime"]
                    source.patch({'x':[(0,start + (end - start) / 2)],'w':[(0,end-start)]})
                else:
                    #boxannotation must be recreated
                    self.remove_renderers(anno["id"])
                    self.draw_annotation(anno,visible=True)

                #self.renderers[anno["id"]]["source"]["x"]=[anno["startTime"],anno["endTime"]]

    def box_modifier_modify(self):
        self.logger.debug(f"box_modifier_modify {self.boxModifierVisible}, now => {self.boxModifierData.data}")
        if self.boxModifierVisible == False:
            return False

        anno = self.server.get_annotations()[self.boxModifierAnnotationName]
        self.logger.debug(f" box_modifier_modify {anno}")


        if anno["type"] in ["time","motif"]:
            if self.boxModifierData.data['x'][1] <= self.boxModifierData.data['x'][0]:
                #end before start not possible
                self.logger.warning("box_modifier_modify end before start error")
                return False

            # re-center the y axis height to avoid vertical out-shifting
            boxYCenter = float(self.plot.y_range.start + self.plot.y_range.end) / 2
            boxYHeight = (self.plot.y_range.end - self.plot.y_range.start) * 4
            self.boxModifierData.data['y'] = [boxYCenter, boxYCenter]
            self.boxModifierData.data['height'] = [boxYHeight, boxYHeight]

            #now modify it:
            # adjust the local value in the timeseries server,
            # correct the visible glyph of the annotation
            # push it back to the model

            #may this is just a zoom, so check if start or endtime has changed
            if anno["startTime"] != self.boxModifierData.data['x'][0] or anno["endTime"] != self.boxModifierData.data['x'][1]:
                # sanity check: end not before start
                anno["startTime"] = self.boxModifierData.data['x'][0]
                anno["endTime"] = self.boxModifierData.data['x'][1]
                self.server.adjust_annotation(anno)#wait for observer to notify the real change


        elif anno["type"] == "threshold":
            if self.boxModifierData.data['y'][1] <= self.boxModifierData.data['y'][0]:
                #end before start not possible
                self.logger.warning("box_modifier_modify min gt max error")
                return False
                # sanity check: end not before start
            #now move the box back in
            boxXCenter = float(self.plot.x_range.start + self.plot.x_range.end) / 2
            self.boxModifierData.data['x'] = [boxXCenter, boxXCenter]

            #maybe just a zoom
            if anno["min"] != self.boxModifierData.data['y'][0] or anno["max"] != self.boxModifierData.data['y'][1]:
                anno["min"] = self.boxModifierData.data['y'][0]
                anno["max"] = self.boxModifierData.data['y'][1]
                self.server.adjust_annotation(anno)#s(self.boxModifierAnnotationName, anno)
                self.remove_renderers(deleteMatch=anno["id"],deleteFromLocal=True)
                self.draw_threshold(anno)#self.boxModifierAnnotationName,anno['variable'])



        else:
            self.logger.error(f"we don't support annos of type {anno['type']}")
            return False



        return True


    def check_boxes(self):
        if self.inPan:
            self.logger.debug("check_boxes skip in pan")
            return

        if self.boxModifierVisible:
            try:
                #self.logger.debug(self.boxData.data)
                #self.logger.debug(self.toolBarBox.toolbar.active_drag)

                if len(self.boxModifierData.data["x"]) != 2:
                    self.logger.warning("box modifier >2:  restore")
                    self.boxModifierData.data = copy.deepcopy(self.boxModifierOldData)


                new = json.dumps(self.boxModifierData.data)
                old = json.dumps(self.boxModifierOldData)
                if old!= new:
                    if not self.box_modifier_modify():
                        self.logger.warning("box modifier invalid,  restore")
                        self.boxModifierData.data = dict(copy.deepcopy(self.boxModifierOldData))


                    self.boxModifierOldData = dict(copy.deepcopy(self.boxModifierData.data))

            except Exception as ex:
                self.logger.error(f"check_boxes {ex}")


    def periodic_cb(self):
        """
            called periodiaclly by the bokeh system
            here, we execute function that modifiy bokeh variables etc via the dispatching list
            this is needed, as modifications to data or parameters in the bokeh objects
            are only possible withing the bokeh thread, not from any other.

            attention: make sure this functin does normally not last longer than the periodic call back period, otherwise
            bokeh with not do anything else than this function here

        """
        #self.logger.debug("periodic_cb")
        if self.inPeriodicCb:
            self.logger.error("in periodic cb")
            return
        self.inPeriodicCb = True

        try:
            start = time.time()
            self.check_boxes()
            legendChange =  self.__legend_check() # check if a user has deselected a variable
            #try: # we need this, otherwise the inPeriodicCb will not be reset

            #self.logger.debug("enter periodic_cb")

            executelist=[]
            with self.dispatchLock:
                if self.dispatchList:
                    executelist = self.dispatchList.copy()
                    self.dispatchList = []

            for entry in executelist: # avoid double execution
                fkt = entry["function"]
                arg = entry["arg"]
                self.logger.info(f"now executing dispatched fkt {fkt.__name__} arg {arg}")
                if arg:
                    fkt(arg) # execute the functions which wait for execution and must be executed from this context
                else:
                    fkt()

        except Exception as ex:            self.logger.error(f"Error in periodic callback {ex} , {str(traceback.format_exc())}")

        if legendChange or executelist != []:
            self.logger.debug(f"periodic_cb was {time.time()-start}")

        self.inPeriodicCb = False

    def __get_free_color(self,varName = None):
        """
            get a currently unused color from the given palette, we need to make this a function, not just a mapping list
            as lines come and go and therefore colors become free again

            Returns:
                a free color code

        """

        #try to find the color first:
        if varName:
            currentLinesColors = self.server.get_current_colors()
            if varName in currentLinesColors:
                return currentLinesColors[varName]["lineColor"]

        #not found, get a new one

        usedColors =  [self.lines[lin].glyph.line_color for lin in self.lines if hasattr(self.lines[lin],"glyph")]
        for color in self.lineColors:
            if color not in usedColors:
                return color
        return "green" # as default




    def __plot_lines(self,newVars = None):
        """ plot the currently selected variables as lines, update the legend
            if newVars are given, we only plot them and leave the old
        """
        self.logger.debug("@__plot_lines")

        if newVars == None:
            #take them all fresh
            newVars = self.server.get_variables_selected()

        #first, get fresh data
        settings= self.server.get_settings()
        variables = self.server.get_variables_selected()
        mirr = self.server.get_mirror()
        if "autoScaleY" in mirr:
            self.autoAdjustY = mirr["autoScaleY"][".properties"]["value"]

        showMarker = False
        if "showMarker" in mirr:
            showMarker = mirr["showMarker"][".properties"]["value"]
        #self.logger.debug("@__plot_lines:from server var selected %s",str(newVars))
        variablesRequest = variables.copy()
        variablesRequest.append("__time")   #make sure we get the time included
        #self.logger.debug("@__plot_lines:self.variables, bins "+str(variablesRequest)+str( settings["bins"]))
        if not self.streamingMode:
            getData = self.server.get_data(variablesRequest,self.rangeStart,self.rangeEnd,settings["bins"]) # for debug
        else:
            # avoid to send a different request between the streaming data requests, this causes "jagged" lines
            # still not the perfec solution as zooming out now causes a short empty plot
            getData = self.server.get_data(variablesRequest, -self.streamingInterval, None,
                                                            self.server.get_settings()["bins"])  # for debug
        #self.logger.debug("GETDATA:"+str(getData))
        if not getData:
            self.logger.error(f"no data received")
            return
        if self.rangeStart == None:
            mini,maxi = self.get_min_max_times(getData)
            #write it back
            self.rangeStart = mini#getData["__time"][0]
            self.rangeEnd   = maxi#getData["__time"][-1]
            self.server.set_x_range(self.rangeStart, self.rangeEnd)

        #del getData["__time"]
        #getData["__time"]=[0]*settings["bins"] # dummy for the hover


        """
        if newVars == []:
            #self.data.data = getData  # also apply the data to magically update
            for k,v in getData.items():
                if not k.endswith("__time"):
                    self.columnData[k].data ={"y":v,"x":getData[k+"__time"]}
        else:
            self.logger.debug("new column data source")
            if self.data is None:
                #first time
                self.data = ColumnDataSource(getData)  # this will magically update the plot, we replace all data
                #also new store
                self.columnData  = {}
                for k,v in getData.items():
                    if not k.endswith("__time"):
                        self.columnData[k]=ColumnDataSource({"y":v,"x":getData[k+"__time"]})

            else:
                #add more data
                for variable in getData:
                    if variable not in self.columnData:#data.data:
                        self.columnData[variable]=ColumnDataSource({"y":v,"x":getData[k+"__time"]})
                        #self.data.add(getData[variable],name=variable)
        """
        self.update_column_datas(getData)

        #self.logger.debug(f"self.columnData {self.columnData}")
        self.adjust_y_axis_limits()
        #timeNode = "__time"
        #now plot var

        if newVars != []:
            #sort the limits to the end so that the lines are created first, then the band can take the same color
            newList = []
            for elem in newVars:
                if elem.endswith("_limitMax") or elem.endswith("_limitMin"):
                    newList.append(elem)
                else:
                    newList.insert(0,elem)
            newVars = newList

        for variableName in newVars:
            if variableName.endswith('__time'):
                continue
            color = self.__get_free_color(variableName)
            self.logger.debug("new color ist"+color)

            self.logger.debug(f"plotting line {variableName}, is score: {self.server.is_score_variable(variableName)}")
            if self.server.is_score_variable(variableName):
                scoreMarker = self.server.get_score_marker(variableName)
                #this is a red circle score varialbe
                if scoreMarker == "x":
                    self.lines[variableName] = self.plot.asterisk(x="x", y="y", line_color="red", fill_color=None,
                                                            source=self.columnData[variableName], name=variableName,size=10)  # x:"time", y:variableName #the legend must havee different name than the source bug
                elif scoreMarker=="+":
                    self.lines[variableName] = self.plot.cross(x="x", y="y", line_color="red", fill_color=None,
                                                            source=self.columnData[variableName], name=variableName,size=10)
                else:
                    #default is circle
                    self.lines[variableName] = self.plot.circle(x="x", y="y", line_color="red", fill_color=None,
                                                            source=self.columnData[variableName], name=variableName,
                                                            size=7)  # x:"time", y:variableName #the legend must havee different name than the source bug


            elif variableName.endswith("_limitMax"):
                if variableName in self.columnData:# if it is in the column data we can process
                    #we found both min and max
                    thisLineColor = None
                    originalVarName = variableName.split('.')[-1][:-len("_expected")]
                    for lineName in self.lines:
                        if lineName.split('.')[-1] == originalVarName:
                            thisLineColor = self.lines[lineName].glyph.line_color
                            break
                    if not thisLineColor:
                        thisLineColor = "gray"
                    band = Band(base='x', lower='lower', upper='upper', level=globalBandsLevel,fill_color = thisLineColor,
                                fill_alpha=0.4, line_width=0,source = self.columnData[variableName])
                    self.lines[variableName] = band
                    self.plot.add_layout(band)
                continue
            elif variableName.endswith("_limitMin"):
                continue


            else:
                #these are the lines

                if ".score" in variableName:
                    # this is a score 0..1 line
                    self.lines[variableName] = self.plot.line(x="x", y="y", color="gray", line_dash="dotted",
                                                              source=self.columnData[variableName], name=variableName, line_width=2,
                                                              y_range_name="y2")  # x:

                else:

                    if variableName.endswith("_expected"):
                        # this is a special case of a line which we display dotted in the same color as the original one
                        # try to find the corresponding variable
                        thisLineColor = None
                        originalVarName = variableName.split('.')[-1][:-len("_expected")]
                        for lineName in self.lines:
                            if lineName.split('.')[-1] == originalVarName:
                                thisLineColor = self.lines[lineName].glyph.line_color
                                break
                        if not thisLineColor:
                            thisLineColor = color
                        self.lines[variableName] = self.plot.line(x="x", y="y", color=thisLineColor,
                                                                  source=self.columnData[variableName], name=variableName,
                                                                  line_width=4, line_dash="dashed")
                    else:

                        #this is a real line
                        #self.debugStore =copy.deepcopy(getData)
                        #self.lines[variableName] = self.plot.line(x=variableName+"__time", y=variableName, color=color,
                        #                              source=self.data, name=variableName,line_width=2)  # x:"time", y:variableName #the legend must havee different name than the source bug
                        self.lines[variableName] = self.plot.line(x="x", y="y", color=color,source=self.columnData[variableName], name=variableName,line_width=2)

                        if showMarker:
                            markerName = variableName+"_marker"
                            marker = self.plot.circle(x="x",y="y", line_color=color, fill_color=color,
                                                      source=self.columnData[variableName], name=markerName,size=3)  # x:"time", y:variableName #the legend must havee different name than the source bug
                #legend only for lines
                self.legendItems[variableName] = LegendItem(label='.'.join(variableName.split('.')[-2:]),
                                                            renderers=[self.lines[variableName]])

            #we set the lines and glypsh to no change their behaviour when selections are done, unfortunately, this doesn't work, instead we now explicitly unselect in the columndatasource
            self.lines[variableName].nonselection_glyph = None  # autofading of not selected lines/glyphs is suppressed
            self.lines[variableName].selection_glyph = None     # self.data.selected = Selection(indices = [])

            #self.legendItems[variableName] = LegendItem(label=variableName,renderers=[self.lines[variableName]])

            if self.showThresholds:
                self.show_thresholds_of_line(variableName)
            if self.showMotifs:
                self.show_motifs_of_line(variableName)

        #compile the new colors
        nowColors = {}
        for variableName,glyph in self.lines.items():
            if variableName.endswith("_limitMax"):
                nowColors[variableName] = {"lineColor": glyph.line_color}
            else:
                nowColors[variableName] = {"lineColor":glyph.glyph.line_color}
        self.server.update_current_colors(nowColors)




        #now make a legend
        #legendItems=[LegendItem(label=var,renderers=[self.lines[var]]) for var in self.lines]
        legendItems = [v for k,v in self.legendItems.items()]
        if not self.hasLegend:
            #at the first time, we create the "Legend" object
            self.plot.add_layout(Legend(items=legendItems))
            self.plot.legend.location = "top_left"
            self.plot.legend.click_policy = "hide"
            self.hasLegend = True
            #check if we need to hide it on start
            mirr = self.server.get_mirror()
            if "showLegend" in mirr:
                if mirr["showLegend"][".properties"]["value"] == False:
                    self.plot.legend.visible=False
        else:
            self.plot.legend.items = legendItems #replace them

        self.set_x_axis()
        #self.adjust_y_axis_limits()

        return getData # so that later executed function don't need to get the data again

    def range_cb(self, attribute,old, new):
        """
            callback by bokeh system when the scaling have changed (roll the mouse wheel), see bokeh documentation
        """
        #we only store the range, and wait for an LOD or PANEnd event to refresh
        #self.logger.debug(f"range_cb {attribute}")
        if attribute == "start":
            self.rangeStart = new
        if attribute == "end":
            self.rangeEnd = new
        if self.streamingMode == True and not self.inStreamUpdate:
            self.userZoomRunning = True
        #print("range cb"+str(attribute),self.rangeStart,self.rangeEnd)
        #self.logger.debug(f"leaving range_cb with userzoom running {self.userZoomRunning}")

    def get_min_max_times(self,newData):
        mini = 1000*1000*1000*1000*1000
        maxi = 0
        for k,v in newData.items():
            if k.endswith("__time"):
                check=[mini]
                check.extend(v[1:-1])
                mini =  min(check)
                check=[maxi]
                check.extend(v[1:-1])
                maxi=max(check)
        return mini,maxi


    def set_x_axis(self,start=None,end=None):
        if start:
            self.rangeStart = start
        if end:
            self.rangeEnd = end
        self.plot.x_range.start = self.rangeStart
        self.plot.x_range.end   = self.rangeEnd

    def refresh_plot(self):
        """
            # get data from the server and plot the lines
            # if the current zoom is out of range, we will resize it:
            # zoom back to max zoom level shift
            # or shift left /right to the max positions possible
            # if there are new variables, we will rebuild the whole plot
        """
        self.logger.debug("refresh_plot()")
        #have the variables changed?

        #make the differential analysis: what do we currently show and what are we supposed to show?
        currentLines = [lin for lin in self.lines] #these are the names of the current vars
        backendLines = self.server.get_variables_selected()
        deleteLines = list(set(currentLines)-set(backendLines))
        newLines = list(set(backendLines)-set(currentLines))
        scoreVars = self.server.get_score_variables()  # we assume ending in _score

        self.logger.debug("diffanalysis new"+str(newLines)+"  del "+str(deleteLines))


        # now delete the ones to delete

        # automatically add the score to the deletion if a variable has one

        """
        additionalDeletes = []
        for key in deleteLines:
            if not key in scoreVars:
                #this line is not a score itself
                scoreNodeName = key.split('.')[-1]+'_score' # we assume root.myvariable.var1, then we build var1_score
                #now check
                for lineName in currentLines:
                    if scoreNodeName in lineName:
                        additionalDeletes.append(lineName)
        deleteLines.extend(additionalDeletes)
        deleteLines=list(set(deleteLines)) # avoid duplicates
        """

        if deleteLines:
            removeLegendKeys = []
            removeSelfLines = []
            self.plot.legend.items=[] # avoid errors later, we might remove the glyph but the legend needs it
            for key in deleteLines:
                self.lines[key].visible = False
                removeSelfLines.append(key)
                removeLegendKeys.append(key)

            #remove the lines
            self.remove_renderers(deleteLines)
            #remove the according thresholds if any
            for lin in deleteLines:
                self.remove_renderers(self.find_thresholds_of_line(lin),deleteFromLocal=True)
                self.remove_renderers(self.find_motifs_of_line(lin),deleteFromLocal=True)
                #marker = self.find_renderer(lin+"_marker")
                #if marker:
                #    self.remove_renderers(renderers=[marker])

            extraDeleteRenderers = self.find_extra_renderers_of_lines(deleteLines)
            for r in extraDeleteRenderers:
                if r.name in self.legendItems:
                    #del self.legendItems[r.name]
                    removeLegendKeys.append(r.name)

            self.remove_renderers(renderers=extraDeleteRenderers,deleteFromLocal=True)# remove scores, expected, markers

                #del self.columnData[lin] #delete the ColumnDataSource


            #rebuild the legend is done at the end of the plot_lines
            for key in removeLegendKeys:
                if key in self.legendItems:
                    del self.legendItems[key]
            for key in removeSelfLines: # remove them after the legend remove
                if key in self.lines:
                    del self.lines[key]

            #also delete the links from the model in the backend
            #put together all deletes
            serverDeletes = deleteLines.copy()
            serverDeletes.extend([r.name for r in extraDeleteRenderers])
            newServerSelection=[lin for lin in backendLines if lin not in serverDeletes]
            #self.logger.debug(f"SET SELECTED {newServerSelection} {backendLines}")
            if set(newServerSelection) != set(backendLines):
                self.server.set_variables_selected(newServerSelection)




        #create the new ones

        #automatically add scores if needed: if the user adds a variable to the tree, we might need to add also the score
        if self.showScores:
            additionalLines=[]
            currentLineEndings = [name.split('.')[-1] for name in currentLines]
            for key in newLines:
                scoreName = key.split('.')[-1]+"_score"
                for scoreVar in scoreVars:
                    if scoreName in scoreVar:
                        #we add this one only if it is not there already
                        if scoreName not in currentLineEndings:
                            additionalLines.append(scoreVar)
            if additionalLines:
                additionalLines=list(set(additionalLines))# remove duplicates
                self.logger.debug(f"MUST add scores: {additionalLines}.. in the next event")
                self.server.add_variables_selected(additionalLines)
                #return # wait for next event


        data = self.__plot_lines(newLines) # the data contain all visible time series including the background
        #todo: make this differential as well
        if self.server.get_settings()["background"]["hasBackground"]:
            self.refresh_backgrounds(data)

        if self.server.get_settings()["hasHover"] not in [False,None]:
            self.__make_tooltips() #must be the last in the drawings

    def refresh_backgrounds_old(self):
        """ check if backgrounds must be drawn if not, we just hide them"""
        self.hide_backgrounds()
        if self.showBackgrounds:
            self.show_backgrounds()

    def refresh_backgrounds(self,data = None):
        if self.backgroundHighlightVisible:
            return #don't touch a running selection
        self.background_highlight_hide()
        # we show the new backgrounds first and then delete the old to avoid the short empty time, looks a bit better
        deleteList = []
        for r in self.plot.renderers:
            if r.name:
                if "__background" in r.name:
                    deleteList.append(r.name)
        if self.showBackgrounds:
            self.show_backgrounds(data = data)
        if deleteList:
            self.remove_renderers(deleteList=deleteList)


    def var_select_button_cb(self):
        """
            UI callback, called when the variable selection button was clicked
        """
        #apply the selected vars to the plot and the backend
        currentSelection = self.variablesMultiSelect.value
        #write the changes to the backend
        self.server.set_variables_selected(currentSelection)
        self.refresh_plot()


    def event_cb(self,event):
        """
            the event callback from the UI for any user interaction: zoom, select, annotate etc
            Args:
                event (bokeh event): the event that happened
        """

        eventType = str(event.__class__.__name__)
        msg = " "
        for k in event.__dict__:
            msg += str(k) + " " + str(event.__dict__[k]) + " "
        self.logger.debug("event " + eventType + msg)
        #print("event " + eventType + msg)

        if eventType in ["PanStart","Pan"]:
            if self.streamingMode:
                self.userZoomRunning = True # the user is starting with pannin, we old the ui updates during user pan
            self.inPan = True

        """
        if eventType == "PanEnd":
            #self.refresh_plot()
            if self.streamingMode:
                self.userZoomRunning = False # the user is finished with zooming, we can now push data to the UI again
            #self.logger.debug(f"{self.toolBarBox.toolbar.active_pan}")
            self.autoAdjustY = False
            self.refresh_plot()
        """

        #if eventType == "LODEnd":
        if eventType in ["LODEnd","PanEnd"]:
            self.inPan = False
            if self.streamingMode:
                self.userZoomRunning = False # the user is finished with zooming, we can now push data to the UI again
                # also update the zoom level during streaming
                self.streamingInterval = self.plot.x_range.end - self.plot.x_range.start #.rangeEnd - self.rangeStart
                self.logger.debug(f"new streaming interval: {self.streamingInterval}")
            #if self.server.get_settings()["autoScaleY"][".properties"]["value"] == True
            self.autoAdjustY = self.server.get_mirror()["autoScaleY"][".properties"]["value"]
            self.server.set_x_range(self.rangeStart,self.rangeEnd)
            self.refresh_plot()

        if eventType == "Reset":
            self.reset_plot_cb()

        if eventType == "SelectionGeometry":
            #option = self.annotationButtons.active # gives a 0,1 list, get the label now
            #tags = self.server.get_settings()["tags"]
            #mytag = self.annotationTags[option]
            for k,v in self.columnData.items():
                v.selected =Selection(indices=[]) #not allowed in bokeh 2.01 f
                pass

            mytag =self.currentAnnotationTag
            #self.logger.info("TAGS"+str(self.annotationTags)+"   "+str(option))

            #self.data.selected = Selection(indices=[])  # suppress real selection
            if mytag != None:
                self.edit_annotation_cb(event.__dict__["geometry"]["x0"],event.__dict__["geometry"]["x1"],mytag,event.__dict__["geometry"]["y0"],event.__dict__["geometry"]["y1"])
        if eventType == "Tap":
            #self.logger.debug(f"TAP {self.annotationsVisible}, {event.__dict__['sx']}")
            #plot all attributes
            #self.logger.debug(f"legend {self.plot.legend.width}")
            self.box_modifier_tap(event.__dict__["x"],event.__dict__["y"]  )
            self.logger.debug(f"TAP done")


        self.logger.debug(f"leave event with user zomm running{self.userZoomRunning}")
    def reset_plot_cb(self):
        self.logger.debug("reset plot")
        self.rangeStart = None
        self.rangeEnd = None
        self.box_modifier_hide() # reset the selection
        self.refresh_plot()


    def find_renderer(self,rendererName):
        for r in self.plot.renderers:
            if r.name:
                if r.name == rendererName:
                    return r
        return None

    def add_renderers(self,addList):
        self.plot.renderers.extend(addList)

    def remove_renderers(self,deleteList=[],deleteMatch="",renderers=[],deleteFromLocal = False):
        """
         this functions removes renderers (plotted elements from the widget), we find the ones to delete based on their name attribute
         Args:
            deletelist: a list or set of renderer names to be deleted
            deleteMatch(string) a part of the name to be deleted, all renderer that have this string in their names will be removed
            renderers : a list of bokeh renderers to be deleted
        """

        deletedRenderers = []
        #sanity check:
        with self.renderersLock:
            if self.renderersGarbage:
                self.logger.info(f"renderers garbage collector {self.renderersGarbage}")
                renderers.extend(self.renderersGarbage)
                self.renderersGarbage = []

        if deleteList == [] and deleteMatch == "" and renderers == []:
            return
        #self.logger.debug(f"remove_renderers(), {deleteList}, {deleteMatch}, {renderers}")

        deleteList = deleteList.copy() # we will modify it
        newRenderers = []
        for r in self.plot.renderers:
            if r in renderers:
                deletedRenderers.append(r)
                continue # we ignore this one and do NOT add it to the renderers, this will hide the object
            if r.name:
                if r.name in deleteList:
                    self.logger.debug(f"remove_renderers {r.name}")
                    deleteList.remove(r.name) # reduce the list to speed up looking later
                    deletedRenderers.append(r)
                    continue  # we ignore this one and do NOT add it to the renderers, this will hide the object
                elif deleteMatch != "" and deleteMatch in r.name:
                    deletedRenderers.append(r)
                    continue  # we ignore this one and do NOT add it to the renderers, this will hide the object
                else:
                    newRenderers.append(r)  # we keep this one, as it doesnt mathc the deletersl
            else:
                newRenderers.append(r)  # if we have no name, we can't filter, keep this

        self.plot.renderers = newRenderers

        if deleteFromLocal:
            #delete this also from the local renderers list:
            delList = []
            for k,v in self.renderers.items():
                if v["renderer"] in deletedRenderers:
                    delList.append(k)
            for k in delList:
                del self.renderers[k]


    def annotation_toggle_click_cb(self,toggleState):
        """
            callback from ui for turning on/off the annotations
            Args:
                toggleState (bool): true for set, false for unset
        """
        if toggleState:
            self.showAnnotationToggle.label = "hide Annotations"
            self.show_annotations()
        else:
            #remove all annotations from plot
            self.showAnnotationToggle.label = "show Annotations"
            self.hide_annotations()

    def threshold_toggle_click_cb(self,toggleState):
        """
            callback from ui for turning on/off the threshold annotations
            Args:
                toggleState (bool): true for set, false for unset
        """
        if toggleState:
            self.showThresholdToggle.label = "hide Thresholds"
            self.showThresholds = True
            self.show_thresholds()
        else:
            #remove all annotations from plot
            self.showThresholdToggle.label = "show Thresholds"
            self.showThresholds = False
            self.hide_thresholds()

    def show_thresholds(self):
        """
            check which lines are currently shown and show their thresholds as well
        """
        #if not self.showThresholds:
        #    return

        self.showThresholds = True

        for annoName,anno in self.server.get_annotations().items():
            #self.logger.debug("@show_thresholds "+annoName+" "+anno["type"])
            if anno["type"]=="threshold":
                # we only show the annotations where the lines are also there
                self.logger.debug("@show_thresholds "+annoName+" "+anno["type"]+"and the lines are currently"+str(list(self.lines.keys())))
                if anno["variable"] in self.lines:
                    self.draw_threshold(anno)#,anno["variable"])


    def show_motifs(self):
        self.showMotifs = True
        for annoName,anno in self.server.get_annotations().items():
            #self.logger.debug("@show_thresholds "+annoName+" "+anno["type"])
            if anno["type"]=="motif":
                # we only show the annotations where the lines are also there
                self.logger.debug("@show_motifs "+annoName+" "+anno["type"]+"and the lines are currently"+str(list(self.lines.keys())))
                if anno["variable"] in self.lines:
                    self.draw_motif(anno)#,anno["variable"])

    def hide_motifs(self):
        self.showMotifs = False
        self.box_modifier_hide()
        annotations = self.server.get_annotations()
        timeAnnos = [anno for anno in annotations.keys() if annotations[anno]["type"] == "motif"]
        self.remove_renderers(deleteList=timeAnnos, deleteFromLocal=True)


    def hide_thresholds(self):
        """ hide the current annotatios in the widget of type time"""
        self.showThresholds=False

        self.box_modifier_hide()
        annotations = self.server.get_annotations()
        timeAnnos = [anno for anno in annotations.keys() if annotations[anno]["type"]=="threshold" ]
        self.remove_renderers(deleteList=timeAnnos,deleteFromLocal=True)




    def backgroundbutton_cb(self,toggleState):
        """
            event callback function triggered by the UI
            toggleStat(bool): True/False on toggle is set or not
        """
        if toggleState:
            self.backgroundbutton.label = "hide Backgrounds"
            self.showBackgrounds = True
            self.show_backgrounds(None)
        else:
            self.backgroundbutton.label = "show Backgrounds"
            self.hide_backgrounds()
            self.showBackgrounds = False


    def init_annotations(self):
        # we assume that annotations are part of the model,
        ## get the annotations from the server and build the renderers, plot them if wanted
        ## but only the time annotations, the others are created and destroyed on demand
        #self.visibleAnnotations = set() # a set

        self.logger.debug(f"init_annotations() {len(self.server.get_annotations())} annotations..")

        #now we build all renderers for the time annos and don't show them now
        for annoname, anno in self.server.get_annotations().items():
            if anno["type"] == "time":
                self.draw_annotation(anno,False)

        self.logger.debug("init annotations done")


    def init_events(self):
        self.logger.debug(f"init_events")
        #create all renderers but don't show them
        visible = self.server.get_mirror()["visibleElements"][".properties"]["value"]
        if "events" in visible and visible["events"]==True:
            self.eventsVisible = True #currently turned on
            self.logger.debug(f"init_events visible")
            self.show_all_events()
        else:
            self.logger.debug("init events invisible")


    def show_all_events(self):
        self.logger.debug("show_all_events")
        data = self.server.get_events()
        self.eventsVisible = True
        if data:
            self.show_events(data)

    def init_annotations_old(self):
        """
            chreate the actual bokeh objects based on existing annotations, this speeds up the process a lot when show
            ing the annotations later, we will keep the created objecs in the self.annotations list and apply it to
            the renderes later, this will only be used for "time" annotations, the others are called thresholds
        """
        self.annotations={}
        self.logger.debug(f"init {len(self.server.get_annotations())} annotations..")
        for annoname, anno in self.server.get_annotations().items():
            if "type" in anno and anno["type"] != "time":
                continue # ignore any other type
            self.draw_annotation(annoname,add_layout=False)
        #now we have all bokeh objects in the self.annotations
        self.logger.debug("init_annotations.. done")

    def show_annotations(self, annoIdFilter=[]):
        """
            show annotations and hide annotations according to their tags (compare with visibleTags
        """

        self.logger.debug("show_annotations()")
        self.showAnnotations = True

        mirror = self.server.fetch_mirror()
        allowedTags = mirror["hasAnnotation"]["visibleTags"][".properties"]["value"]
        self.showAnnotationTags = [tag for tag in allowedTags if allowedTags[tag]]
        self.logger.debug(f"show annotation tags {self.showAnnotationTags}")

        addList = []
        removeList = []

        for k, v in self.renderers.items():
            if annoIdFilter:
                if k not in annoIdFilter:
                    continue
            if v["info"]["type"] != "time":
                continue # only the time annotations
            if not v["renderer"] in self.plot.renderers:
                #this renderer is not yet in the renderers, check if we are allowed to show it
                if any ([True for tag in v["info"]["tags"] if tag in self.showAnnotationTags ]):
                    addList.append(v["renderer"])
            if v["renderer"] in self.plot.renderers:
                #this renderer is already there, check if we might need to hide it
                if not any([True for tag in v["info"]["tags"] if tag in self.showAnnotationTags]):
                    removeList.append(v["renderer"])
                    # is the box modifier on this currently active?
                    # if the currently selected is being hidden, we hide the box modifier
                    if self.boxModifierVisible:
                        if self.boxModifierAnnotationName == k:
                            self.box_modifier_hide()

        self.logger.debug(f"add {len(addList)} annotations to plot remove {len(removeList)} from plot")
        self.plot.renderers.extend(addList)
        self.remove_renderers(renderers=removeList)


    def hide_annotations(self):
        self.showAnnotations = False
        """ hide the current annotatios in the widget of type time"""
        annotations = self.server.get_annotations()
        timeAnnos = [anno  for anno in annotations.keys() if annotations[anno]["type"]=="time" ]
        self.logger.debug("hide_annotations "+str(timeAnnos))
        self.remove_renderers(deleteList=timeAnnos)
        #self.annotationsVisible = False
        self.box_modifier_hide()

    def get_layout(self):
        """ return the inner layout, used by the main"""
        return self.layout
    def set_curdoc(self,curdoc):
        self.curdoc = curdoc
        #curdoc().theme = Theme(json=themes.defaultTheme) # this is to switch the theme

    def remove_annotations(self,deleteList):
        """
            remove annotation from plot, object list and from the server
            modelPath(list of string): the model path of the annotation, the modelPath-node must contain children startTime, endTime, colors, tags
        """
        self.remove_renderers(deleteList=deleteList)
        self.server.delete_annotations(deleteList)
        for anno in deleteList:
            if anno in self.annotations:
                del self.annotations[anno]


    def draw_motif(self,anno):
        """ draw the boxannotation for a motif
            Args:
                 modelPath(string): the path to the annotation, the modelPath-node must contain children startTime, endTime, colors, tags
        """
        self.logger.debug(f"draw motif {anno}")
        try:
            #if the box is there already, then we skip
            if anno["id"] in self.renderers:
                self.logger.warning(f"have this already {anno['id']}")
                return
            color = self.lines[anno["variable"]].glyph.line_color

            start = anno["startTime"]
            end = anno["endTime"]

            infinity = 1000000
            # we must use varea, as this is the only one glyph that supports hatches and does not create a blue box when zooming out
            # self.logger.debug(f"have pattern with hatch {pattern}, tag {tag}, color{color} ")

            """
            source = ColumnDataSource(dict(x=[start, end], y1=[-infinity, -infinity], y2=[infinity, infinity]))
            area = VArea(x="x", y1="y1", y2="y2",
                         fill_color="black",
                         name=anno["id"],
                         fill_alpha=0.2,
                         hatch_color=color,
                         hatch_pattern="v",
                         hatch_alpha=0.5)
            
            """
            # this overcomes the bokeh bug that on super zoom, the hatch pattern of varea disappears:
            # Vbar behaves correctly
            source = ColumnDataSource(dict(x=[start+(end-start)/2], t=[infinity], b=[-infinity],w=[end-start]))
            area = VBar(x="x", top="t", bottom="b", width="w", fill_color="black",
                         name=anno["id"],
                         fill_alpha=0.2,
                         hatch_color=color,
                         hatch_pattern="v",
                         hatch_alpha=0.5)


            #    bokeh hack to avoid adding the renderers directly: we create a renderer from the glyph and store it for later bulk assing to the plot
            # which is a lot faster than one by one
            myrenderer = GlyphRenderer(data_source=source, glyph=area, name=anno['id'])
            self.add_renderers([myrenderer])

            self.renderers[anno["id"]] = {"renderer": myrenderer, "info": copy.deepcopy(anno),
                                      "source": source}  # we keep this renderer to speed up later

        except Exception as ex:
            self.logger.error("error draw motif"+str(ex))
            return None


    def draw_annotation(self, anno, visible=False):
        """
            draw one time annotation on the plot
            Args:
             anno: the annotation
             visible: true/false
        """
        try:
            #self.logger.debug(f"draw_annotation  {anno['name']} visible {visible}")

            tag = anno["tags"][0]
            mirror = self.server.get_mirror()
            myColors = mirror["hasAnnotation"]["colors"][".properties"]["value"]
            myTags = mirror["hasAnnotation"]["tags"][".properties"]["value"]

            try: # to set color and pattern
                if type(myColors) is list:
                    tagIndex = myTags.index(tag)
                    pattern = None
                    color = myColors[tagIndex]
                elif type(myColors) is dict:
                    color = myColors[tag]["color"]
                    pattern = myColors[tag]["pattern"]
                    if not pattern is None:
                        if pattern not in [" ",".","o","-","|","+",":","@","/","\\","x",",","`","v",">","*"]:
                            pattern = 'x'
            except:
                color = None
                pattern = None
            if not color:
                self.logger.error("did not find color for boxannotation")
                color = "red"

            start = anno["startTime"]
            end = anno["endTime"]

            infinity=1000000
            # we must use varea, as this is the only one glyph that supports hatches and does not create a blue box when zooming out
            #self.logger.debug(f"have pattern with hatch {pattern}, tag {tag}, color{color} ")
            

            if not pattern is None:
                """
                source = ColumnDataSource(dict(x=[start, end], y1=[-infinity, -infinity], y2=[infinity, infinity]))
                area = VArea(x="x",y1="y1",y2="y2",
                                    fill_color=color,
                                    name=anno["id"],
                                    fill_alpha=globalAnnotationsAlpha,
                                    hatch_color="black",
                                    hatch_pattern=pattern,
                                    hatch_alpha=1.0)
                rendererType = "VArea"
                """
                source = ColumnDataSource(dict(x=[start + (end - start) / 2], t=[infinity], b=[-infinity], w=[end - start]))
                area = VBar(x="x", top="t", bottom="b", width="w",
                            fill_color=color,
                            name=anno["id"],
                            fill_alpha=globalAnnotationsAlpha,
                            hatch_color="black",
                            hatch_pattern=pattern,
                            hatch_alpha=1.0)
                
                
                myrenderer = GlyphRenderer(data_source=source, glyph=area, name=anno['id'])
                myrenderer.level = globalThresholdsLevel
                rendererType = "VBar"
            else:
                #we use a Boxannotation as this is a lot more efficient in bokeh
                """ 
                area = VArea(x="x", y1="y1", y2="y2",
                                    fill_color=color,
                                    name=anno["id"],
                                    fill_alpha=globalAlpha)
                """
                source = None

                if any([True for tag in anno["tags"] if "anomaly" in tag]):
                    #if we have an anomaly to draw, we put it on top
                    level = globalThresholdsLevel
                else:
                    level = globalAnnotationLevel
                myrenderer = BoxAnnotation(left=start,right=end,fill_color=color,fill_alpha=globalAnnotationsAlpha,name=anno['id'],level=level)
                rendererType = "BoxAnnotation"

            # bokeh hack to avoid adding the renderers directly: we create a renderer from the glyph and store it for later bulk assing to the plot
            # which is a lot faster than one by one

            if 0: #this was a trial for an extra object to hover the annotations
                dic = {"y": [0],
                       "x": [start+(end-start)/20],
                       "w":[end-start],
                       "h":[infinity],
                       "l":[start],
                       "r":[end-start],
                       "t":[infinity],
                       "b":[-infinity],
                       "f":[0.9]}
                col = ColumnDataSource(dic)
                # the only glyph that worked for hovering was the circle, rect, quad did not work
                #annoHover = self.plot.circle(x="x", y="f",size=15, fill_color="white",fill_alpha=0.5,source=col,name="annohover",y_range_name="y2",line_color="white",line_width=2) #works
                 #self.annoHovers.append(annoHover)

            if visible:
                self.add_renderers([myrenderer])

            self.renderers[anno["id"]] = {"renderer": myrenderer, "info": copy.deepcopy(anno),"source": source,"rendererType":rendererType}  # we keep this renderer to speed up later

        except Exception as ex:
            self.logger.error(f"error draw annotation {anno}"+str(ex))
            return None

    def hide_all_events(self):
        self.eventsVisible = False
        self.hide_events()

    def hide_events(self,keep=[],selectId=None):
        """
            hide all events excpect the keep list
            keep: a list of event tags
            selectId: give a nodeid, we only work on the renderes of that node
        """
        #hide the ones which are not here

        deleteList=[]
        for nodeId,entry in self.eventLines.items():
            if selectId and selectId != nodeId:
                continue# we have a id filter and it did not match
            if entry["eventString"] not in keep:
                deleteList.append(nodeId)
        for id in deleteList:
            self.remove_renderers(renderers=[self.eventLines[id]["renderer"]])
            del self.eventLines[id]

    def __make_colum_data_for_events(self,times):
        times = numpy.asarray(times)
        times = times * 1000  # in ms for bokeh
        infi = 1000 * 1000
        x = []
        y = []
        for t in times:
            x.extend([t, t, numpy.nan]) #need the nan to avoid connecting diagonals between the vertical lines
            y.extend([-infi, infi, numpy.nan])
        return {"x": x, "y": y}

    def show_events(self,eventsData,redraw=False):
        """
            show all currently visible event tags

            Args:
                nodeId: the node id
                redraw: if set to true, we delete the lines of a node and redraw them, if not, we keep them
                eventes: a dict containing  {"nodeid":{"events":{"one":[t1,t2,t3],"two":[t1,t,2,t3]...}},"nodeid2":{}
        """
        self.eventsVisible = True
        myColors = self.server.get_mirror()["hasEvents"]["colors"][".properties"]["value"]
        visibleEvents = self.server.get_mirror()["hasEvents"]["visibleEvents"][".properties"]["value"]
        visible = [k for k,v in visibleEvents.items() if v == True]

        #hide the ones which are not here
        self.hide_events(keep=visible)

        deliveredKeys = []  # build a list of all eventLines that we updated with the data
        #now show the ones to show
        for nodeId, eventInfo in eventsData.items():
            if redraw:
                #make sure we delete all lines of this node
                self.hide_events(selectId=nodeId)  # delete all lines of this node

            for eventString,times in eventInfo["events"].items():
                if eventString not in visible:
                    continue
                key = nodeId+"."+eventString
                deliveredKeys.append(key) # remember that we got this in the data
                dic = self.__make_colum_data_for_events(times)

                if key not in self.eventLines:
                    #only draw if it is not there yet
                    if eventString in myColors:
                        color = myColors[eventString]["color"]
                    else:
                        color = "yellow"
                    source = ColumnDataSource(dic)
                    li = self.plot.line(x="x",y="y", source=source,color=color,line_width=2,name=key)
                    self.eventLines[key] = {"renderer":li,"data":source,"eventString":eventString,"nodeId":nodeId}
                else:
                    #line is there already, update per bokeh data replacement
                    self.eventLines[key]['data'].data = dic

        #now check the eventLines which have not been in the data delivered, those must be deleted, as the backend has no data for them anymore
        toBeDeleted = set(self.eventLines.keys())-set(deliveredKeys)
        for id in toBeDeleted:
            self.remove_renderers(renderers=[self.eventLines[id]["renderer"]])
            del self.eventLines[id]

        #now also update the hovers
        self.__make_tooltips()


    def update_events_old(self,observerEvent):
        """
            observerEvent: the event data coming from the observer
            eventData contains ["<nodeid>":"events:[]....} for one node
        """
        self.logger.debug(f"update_evetns {observerEvent}")
        #simply kill and redraw all events
        self.hide_events()
        self.server.fetch_events()
        self.show_all_events()

    def update_events(self,observerEvent=None):
        """
            observerEvent: the event data coming from the observer
            eventData contains ["<nodeid>":"events:[]....} for one node
        """
        self.logger.debug(f"update_evetns {observerEvent}")
        eventsData = self.server.fetch_events()


        self.show_events(eventsData)
        """
        for nodeId, eventInfo in eventsData.items():
            if nodeId!=observerEvent["data"]["sourceId"]:
                continue #only the new event series are touched
            #xxx also check if this event is new or update
            for eventString, times in eventInfo["events"].items():
                self.logger.debug(f"eventlines {self.eventLines.keys()}")
                #prepare the update data
                key = nodeId + "." + eventString
                dic = self.__make_colum_data_for_events(times)
                #update the data
                self.eventLines[key]['data'].data = dic

        self.show_all_events()
        """



    def find_thresholds_of_line(self,path):
        """
            find the hreshold annotations that belong to a line given as model path
            Args:
                path: the path to the variable
            Returns:
                (list of strings of the threshold sannotations that belong to this variable
        """
        result = []
        for k,v in self.server.get_annotations().items():
            if v["type"] == "threshold":
                if v["variable"] == path:
                    result.append(k)
        self.logger.debug("@find_thresholds of line returns "+path+" => "+str(result))
        return result





    def find_motifs_of_line(self,path):
        result = []
        for k,v in self.server.get_annotations().items():
            if v["type"] == "motif":
                if v["variable"] == path:
                    result.append(k)
        self.logger.debug("@find_motifs_of_line of line returns "+path+" => "+str(result))
        return result

    def find_extra_renderers_of_lines(self,lines,markers=True,scores=True,expected=True):
        if type(lines) is not list:
            lines = [lines]

        extraRenderes = []
        deleteNames = []
        for line in lines:
            name = line.split('.')[-1]
            if scores:
                deleteNames.append(name+"_score")
            if expected:
                deleteNames.append(name+"_expected")
            if markers:
                deleteNames.append(name + "_marker")
        for r in self.plot.renderers:
            if r.name and (r.name.split('.')[-1] in deleteNames):
                extraRenderes.append(r)  # take the according score as well

        for r in extraRenderes:
            self.logger.debug(f"remove extra {r.name}")
        return extraRenderes

    def show_motifs_of_line(self,path):
        self.logger.debug("@show_motifs_of_line " + path)
        motifs = self.find_motifs_of_line(path)
        annotations = self.server.get_annotations()
        for motif in motifs:
            self.draw_motif(annotations[motif])  # ,path)

    def show_thresholds_of_line(self,path):
        self.logger.debug("@show_threasholds_of_line "+path)
        thresholds = self.find_thresholds_of_line(path)
        annotations = self.server.get_annotations()
        for threshold in thresholds:
            self.draw_threshold(annotations[threshold])#,path)

    """
        def hide_thresholds_of_line(self,path):
        thresholds = self.find_thresholds_of_line(path)
        self.remove_renderers(deleteList=thresholds,deleteFromLocal=True)
    """

    def draw_threshold(self, annoDict):#, linePath=None):
        """ draw the boxannotation for a threshold
            Args:
                 modelPath(string): the path to the annotation, the modelPath-node must contain children startTime, endTime, colors, tags
        """
        self.logger.debug(f"draw thresholds {annoDict}")
        try:
            #if the box is there already, then we skip
            if annoDict["id"] in self.renderers:
                self.logger.warning(f"have this already {annoDict['id']}")
                return
            #foundRenderer = self.find_renderer(annoDict["id"])
            #if foundRenderer:
            #    #nothing to do
            #    return



            #annotations = self.server.get_annotations()
            # now get the first tag, we only use the first
            #tag = annoDict["tags"][0]



            color = self.lines[annoDict["variable"]].glyph.line_color

            min = annoDict["min"]
            max = annoDict["max"]
            if min>max:
                max,min = min,max # swap them

            # print("draw new anno",color,start,end,modelPath)

            newAnno = BoxAnnotation(top=max, bottom=min,
                                    fill_color=color,
                                    fill_alpha=globalThresholdsAlpha,
                                    level = globalThresholdsLevel,
                                    name=annoDict["id"])  # +"_annotaion

            self.add_renderers([newAnno])

            self.renderers[annoDict["id"]] = {"renderer": newAnno, "info": copy.deepcopy(annoDict)}  # we keep this renderer to speed up later


        except Exception as ex:
            self.logger.error("error draw threshold "+str(annoDict["id"])+str(ex))


    def draw_threshold2(self, anno,visible=False):
        """ draw the boxannotation for a threshold
            Args:
                 anno
        """

        try:
            tag = anno["tags"][0]

            if linePath:
                color = self.lines[linePath].glyph.line_color
            else:
                color ="blue"

            min = annotations[modelPath]["min"]
            max = annotations[modelPath]["max"]
            if min>max:
                max,min = min,max # swap them

            # print("draw new anno",color,start,end,modelPath)

            newAnno = BoxAnnotation(top=max, bottom=min,
                                    fill_color=color,
                                    fill_alpha=globalAlpha,
                                    name=modelPath)  # +"_annotaion

            self.add_renderers([newAnno])
        except Exception as ex:
            self.logger.error("error draw threshold "+str(modelPath)+ " "+linePath+" "+str(ex))


    def make_background_entries(self, data, roundValues = True):
        """
            create background entries from background colum of a table:
            we iterate through the data and create a list of entries
            {"start":startTime,"end":time,"value":value of the data,"color":color from the colormap}
            those entries can directly be used to draw backgrounds
            Args:
                data: dict with {backgroundId: list of data , __time: list of data
                roundValue [bool] if true, we round the values to int, floats are not useful for table lookups
            Returns:
                list of dict entries derived from the data
        """
        backGroundNodeId = self.server.get_settings()["background"]["background"]
        colorMap = self.server.get_settings()["background"]["backgroundMap"]

        startTime = None
        backgrounds = []
        defaultColor = "grey"

        if roundValues:
            # round the values, it is not useful to have float values here, we use the background value
            # for lookup of coloring, so we need int
            #self.logger.debug(f"before round {data[backGroundNodeId]}")
            data[backGroundNodeId]=[ round(value) if numpy.isfinite(value) else value for value in data[backGroundNodeId] ]
            #self.logger.debug(f"after round {data[backGroundNodeId]}")


        for value, time in zip(data[backGroundNodeId], data[backGroundNodeId+"__time"]):
            # must set the startTime?
            if not startTime:
                if not numpy.isfinite(value):
                    continue  # can't use inf/nan
                else:
                    startTime = time
                    currentBackGroundValue = value
            else:
                # now we are inside a region, let's see when it ends
                if value != currentBackGroundValue:
                    # a new entry starts, finish the last and add it to the list of background
                    try:
                        color = colorMap[str(int(currentBackGroundValue))]
                    except:
                        color = defaultColor
                    entry = {"start": startTime, "end": time, "value": currentBackGroundValue, "color": color}
                    self.logger.debug("ENTRY" + json.dumps(entry))
                    backgrounds.append(entry)
                    # now check if current value is finite, then we can start
                    if numpy.isfinite(value):
                        currentBackGroundValue = value
                        startTime = time
                    else:
                        startTime = None  # look for the next start
        # now also add the last, if we have one running
        if startTime:
            try:
                color = colorMap[str(int(currentBackGroundValue))]
            except:
                color = defaultColor
            entry = {"start": startTime, "end": time, "value": currentBackGroundValue, "color": color}
            backgrounds.append(entry)

        return copy.deepcopy(backgrounds)


    def show_backgrounds(self,data=None):
        """
            show the current backgrounds
            Args:
                data(dict):  contains a dict holding the nodeid with of the background and the __time as keys and the lists of data
                    if te data is not given, we get the backgrounds fresh from the data server
        """
        self.showBackgrounds=True

        try:
            self.logger.debug("show_backgrounds()")
            backGroundNodeId = self.server.get_settings()["background"]["background"]

            if not data:
                #we have to pick up the background data first
                self.logger.debug("get fresh background data from the model server %s",backGroundNodeId)
                bins = self.server.get_settings()["bins"]
                getData = self.server.get_data([backGroundNodeId], start=self.rangeStart, end=self.rangeEnd,
                                               bins=bins)  # for debug
                data = getData

            #now make the new backgrounds
            backgrounds = self.make_background_entries(data)
            #now we have a list of backgrounds
            self.logger.info("have %i background entries",len(backgrounds))
            #now plot them

            boxes =[]

            self.backgrounds=[]

            for back in backgrounds:
                name = "__background"+str('%8x'%random.randrange(16**8))
                newBack = BoxAnnotation(left=back["start"], right=back["end"],
                                        fill_color=back["color"],
                                        fill_alpha=globalBackgroundsAlpha,
                                        level = globalBackgroundsLevel,
                                        name=name)  # +"_annotaion
                boxes.append(newBack)
                back["rendererName"] = name
                self.backgrounds.append(back)  # put it in the list of backgrounds for later look up for streaming

            self.plot.renderers.extend(boxes)
        except Exception as ex:
            self.logger.error(f"problem duringshow_backgrounds {ex} ")

    def hide_backgrounds(self):
        self.showBackgrounds = False
        """ remove all background from the plot """
        self.remove_renderers(deleteMatch="__background")


    def show_scores(self):
        self.logger.debug("show_scores()")
        #adjust the current selected variables that they also contain the scores if they have any

        self.showScores=True

        additionalScores = [] # the list of score variables that should be displayed
        currentVariables = self.server.get_variables_selected()
        #now check if we need to add some scores
        for scoreVarName in self.server.get_score_variables():
            for var in currentVariables:
                scoreNameEnding = var.split('.')[-1]+"_score"
                if scoreNameEnding in scoreVarName:
                    #this score should be displayed
                    if scoreVarName not in currentVariables:
                        additionalScores.append(scoreVarName)

        #now we have in additionalScores the missing variables to add
        #write it to the backend and wait for the event to plot them
        if additionalScores !=[]:
            currentVariables.extend(additionalScores)
            self.server.set_variables_selected(currentVariables,updateLocalNow=False)

    def hide_scores(self):
        #remove the "score vars" from the selected in the backend
        #hide the scores
        self.logger.debug("hide_scores()")
        self.showScores=False

        currentVariables = self.server.get_variables_selected()
        scoreVars = self.server.get_score_variables()  # we assume ending in _score

        newVars = [var for var in currentVariables if var not in scoreVars]
        if newVars != currentVariables:
            self.server.set_variables_selected(newVars)





    #called when the user dreates/removes annotations
    def edit_annotation_cb(self,start,end,tag,min,max):
        """
            call as a callback from the UI when a user adds or removes an annotation
            Args:
                start(float): the start time in epoch ms
                end (float): the end time in epoch ms
                tag (string): the currently selected tag by the UI, for erase there is the "-erase-" tag
        """
        self.logger.debug("edit anno %s %s %s",str(start),str(end),str(tag))
        if tag == '-erase-':
            #remove all annotations which are inside the time
            deleteList = []
            annotations=self.server.get_annotations()
            for annoPath,annotation in annotations.items():
                if annotation["type"] == "time":
                    if annotation["startTime"]>start and annotation["startTime"]<end:
                        self.logger.debug("delete "+annoPath)
                        deleteList.append(annoPath)
            #now hide the boxes
            self.remove_annotations(deleteList)
        elif tag =="-erase threshold-":
            # remove all annotations which are inside the limits are are currently visible
            deleteList = []
            annotations = self.server.get_annotations()
            currentThresholds = [] # the list of threshold annotation currently visible
            for r in self.plot.renderers:
                if r.name in annotations:
                    #this annotation is currenlty visible
                    if annotations[r.name]["type"] == "threshold":
                        #this annotation is a threshold
                        currentThresholds.append(r.name)

            #now check if we have to delete it
            deleteList =[]
            for threshold in currentThresholds:
                tMin = annotations[threshold]["min"]
                tMax = annotations[threshold]["max"]
                if tMin>tMax:
                    tMin,tMax = tMax,tMin
                if tMax<=max and tMax>=min: # we check against the top line of the annotation
                    #must delete this one
                    deleteList.append(threshold)
            # now hide the boxes
            self.logger.debug(f"deletelist {deleteList}")
            self.remove_renderers(deleteList=deleteList)
            self.server.delete_annotations(deleteList)

        elif tag =="motif":
            variable = self.currentAnnotationVariable
            newAnno = self.server.add_annotation(start,end,tag,type="motif",var=variable)
            self.draw_motif(newAnno)


        elif "threshold" not in tag:
            #create a time annotation one

            newAnno= self.server.add_annotation(start,end,tag,type="time")
            #print("\n now draw"+newAnnotationPath)
            self.draw_annotation(newAnno,visible=True)
            #print("\n draw done")
        else:
            #create a threshold annotation, but only if ONE variable is currently selected
            variable = None
            if self.currentAnnotationVariable == None: # no variable given from context menu
                variables = self.server.get_variables_selected()
                scoreVariables = self.server.get_score_variables()
                vars=list(set(variables)-set(scoreVariables))
                if len(vars) != 1:
                    self.logger.error("can't create threshold anno, len(vars"+str(len(vars)))
                    return
                variable = vars[0]
            else:
                variable = self.currentAnnotationVariable


            newAnnotation  = self.server.add_annotation(start,end,tag,type ="threshold",min=min,max=max,var = variable )
            #self.currentAnnotationVariable = None
            self.draw_threshold(newAnnotation)# ,vars[0])

    def find_score_variable(self,variablePath):
        scoreVariables = self.server.get_score_variables()



    def session_destroyed_cb(self,context):
        # this still doesn't work
        self.id=self.id+"destroyed"
        self.logger.debug(f"SEESION_DETROYED CB {self.id} id{self}")
        self.server.sse_stop()




if __name__ == '__main__':

    ts_server = TimeSeriesWidgetDataServer('http://localhost:6001/',"root.visualization.widgets.timeseriesOne")
    t=TimeSeriesWidget(ts_server)
