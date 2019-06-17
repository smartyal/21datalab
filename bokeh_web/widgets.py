

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
import copy
import random
import time
import threading


from bokeh.models import DatetimeTickFormatter, ColumnDataSource, BoxSelectTool, BoxAnnotation, Label, LegendItem, Legend, HoverTool, BoxEditTool, TapTool
from bokeh.models import Range1d,DataRange1d
from bokeh import events
from bokeh.models.widgets import RadioButtonGroup, Paragraph, Toggle, MultiSelect, Button, Select, CheckboxButtonGroup,Dropdown
from bokeh.plotting import figure, curdoc
from bokeh.layouts import layout,widgetbox, column, row, Spacer
from bokeh.models import Range1d, PanTool, WheelZoomTool, ResetTool, ToolbarBox, Toolbar
from bokeh.models import FuncTickFormatter, CustomJSHover, SingleIntervalTicker, DatetimeTicker
from pytz import timezone


haveLogger = False



def setup_logging(loglevel=logging.DEBUG,tag = ""):
    global haveLogger
    if not haveLogger:
        # fileName = 'C:/Users/al/devel/ARBEIT/testmyapp.log'


        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        console = logging.StreamHandler()
        console.setLevel(loglevel)
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)

        #logfile = logging.FileHandler('./log/widget_'+'%08x' % random.randrange(16 ** 8)+".log")
        #logfile = logging.FileHandler('./widget_' + '%08x' % random.randrange(16 ** 8) + ".log")
        if tag == "":
            tag = '%08x' % random.randrange(16 ** 8)
        logfile = logging.FileHandler('./log/widget_' + tag+ ".log")
        logfile.setLevel(loglevel)
        logfile.setFormatter(formatter)
        logging.getLogger('').addHandler(logfile)
        haveLogger = True




#import model
from model import date2secs,secs2date, secs2dateString
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

        self.__init_logger()
        self.__init_proxy()
        self.__get_settings()


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
        self.logger = logging.getLogger("TSWidgetDataServer")
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
            for timeout in [0.001, 0.1, 1, 10]:
                try:
                    response = requests.get(self.url + path, timeout=timeout,proxies=self.proxySetting)
                    break
                except Exception as ex:
                    #self.logger.error("requests.get"+str(timeout)+" msg:"+str(ex))
                    continue
        elif method.upper() == "POST":
            now = datetime.datetime.now()
            for timeout in [0.1, 0.1, 1, 10]:
                try:
                    response = requests.post(self.url + path, data=json.dumps(reqData), timeout=timeout,
                                             proxies=self.proxySetting)
                    break
                except Exception as ex:
                    #self.logger.error("requets.post" + str(timeout) + " msg:" + str(ex))
                    continue
        after = datetime.datetime.now()
        diff = (after-now).total_seconds()
        self.logger.info("response "+str(response)+" took "+ str(diff)+"@ my timeout"+str(timeout))
        if not response:
            #print("no ressponse")
            self.logger.error("Error calling web " + path + str(timeout))
            return None
        else:
            rData = json.loads(response.content.decode("utf-8"))
            return rData

    def get_selected_variables_sync(self):
        request = self.path + ".selectedVariables"
        selectedVars = []

        nodes = self.__web_call("post", "_getleaves", request)
        selectedVars=[node["browsePath"] for node in nodes]
        self.selectedVariables=copy.deepcopy(selectedVars)
        return selectedVars


    def __get_settings(self):
        """
            get all the settings of the widget and store them also in the self.settings cache
            Returns: none

        """
        request = [self.path]
        info = self.__web_call("post","_get",request)
        self.logger.debug("initial settings %s",json.dumps(info,indent=4))
        #self.originalInfo=copy.deepcopy(info)
        #grab some settings
        self.settings = get_const_nodes_as_dict(info[0]["children"])

        #also grab the selected
        request = self.path+".selectedVariables"
        self.selectedVariables=[]
        nodes = self.__web_call("post","_getleaves",request)
        for node in nodes:
            self.selectedVariables.append(node["browsePath"])
        #get the selectable
        nodes = self.__web_call('POST',"_getleaves",self.path+'.selectableVariables')
        self.selectableVariables = []
        for node in nodes:
            self.selectableVariables.append(node["browsePath"])

        #also remeber the timefield as path
        request = self.path+".table"
        nodes = self.__web_call("post","_getleaves",request)
        #this should return only one node
        timerefpath = nodes[0]["browsePath"]+".timeField"
        #another call to get it right
        nodes = self.__web_call("post", "_getleaves", timerefpath)
        self.timeNode = nodes[0]["browsePath"]


        #now grab more infor for annotations if needed:
        if self.settings["hasAnnotation"] == True:
            response = self.__web_call("post","_get",[self.path+"."+"hasAnnotation"])
            annotationsInfo = get_const_nodes_as_dict(response[0]["children"])
            self.settings.update(annotationsInfo)
            #now get all annotations
            nodes = self.__web_call("post","_getleaves",self.path+".hasAnnotation.annotations")
            #self.logger.debug("ANNOTATIONS"+json.dumps(nodes,indent=4))
            #now parse the stuff and build up our information
            self.annotations={}
            for node in nodes:
                if node["type"]=="annotation":
                    self.annotations[node["browsePath"]]=get_const_nodes_as_dict(node["children"])

                    if "startTime" in self.annotations[node["browsePath"]]:
                        self.annotations[node["browsePath"]]["startTime"] = date2secs(self.annotations[node["browsePath"]]["startTime"])*1000
                    if "endTime" in self.annotations[node["browsePath"]]:
                        self.annotations[node["browsePath"]]["endTime"] = date2secs(self.annotations[node["browsePath"]]["endTime"]) * 1000
                    if self.annotations[node["browsePath"]]["type"] == "threshold":
                        #we also pick the target
                        self.annotations[node["browsePath"]]["variable"]=self.annotations[node["browsePath"]]["variable"][0]
            #self.logger.debug("server annotations" + json.dumps(self.annotations, indent=4))
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


        #now compile info for the observer, we expect a direct pointer
        observ = {}
        if self.settings["observerEnabled"]==True:
            for node in info[0]["children"]:
                if node["name"] == "observerBackground":
                    observ["observerBackground"]=node["forwardRefs"].copy()
                if node["name"] == "observerUpdate":
                    observ["observerUpdate"]=node["value"].copy()
            if observ!={}:
                self.settings["observer"]=copy.deepcopy(observ)
        else:
            #we dont't put the "observer" key in the settings, so the widget knows, there is not observer
            pass


        background={}
        #now grab the info for the backgrounds
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


        self.logger.debug("SERVER.SETTINGS-------------------------")
        self.logger.debug("%s",json.dumps(self.settings,indent=4))


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
        }
        r=self.__web_call("POST","_getdata",body)
        #convert the time to ms since epoch
        r["__time"]=(numpy.asarray(r["__time"])*1000).tolist()
        #make them all lists and make all inf/nan etc to nan
        for k,v in r.items():
            r[k]=[value if numpy.isfinite(value) else numpy.nan for value in v]
        #self.logger.debug(str(r))
        return r

    def get_time_node(self):
        return self.timeNode


    def get_variables_selectable(self):
        """ returns the selectable variables from the cache"""
        return copy.deepcopy(self.selectableVariables)

    def get_variables_selected(self):
        """ return list of selected variables from the cache"""
        return copy.deepcopy(self.selectedVariables)

    def get_annotations(self):
        return copy.deepcopy(self.annotations)

    def bokeh_time_to_string(self,epoch):
        localtz =  timezone(self.settings["timeZone"])
        dt = datetime.datetime.fromtimestamp(epoch/1000, localtz)
        return dt.isoformat()

    #start and end are ms(!) sice epoch, tag is a string
    def add_annotation(self,start=0,end=0,tag="unknown",type="time",min=0,max=0):
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
                {"browsePath": annoPath + '.variable', "type": "referencer", "targets": [self.get_variables_selected()[0]]}

            ]
        self.logger.debug("creating anno %s",str(nodesToCreate))
        res = self.__web_call('POST','_create',nodesToCreate)

        #now also update our internal list
        self.annotations[annoPath] = {"startTime":start,"endTime":end,"tags":[tag],"min":min,"max":max,"type":type,"variable":self.get_variables_selected()[0]}
        return annoPath




    def delete_annotations(self,deleteList):
        """ delete existing annotation per browsePath from model and cache"""
        for nodePath in deleteList:
            del self.annotations[nodePath]
        self.__web_call("POST","_delete",deleteList)
        pass

    def set_variables_selected(self, varList):
        """ update the currently selected variables to cache and backend """
        query={"deleteExisting":True,"parent":self.path+".selectedVariables","add":varList}
        self.__web_call("POST","_references",query)
        self.selectedVariables=varList.copy()
        return

    def get_settings(self):
        return copy.deepcopy(self.settings)

    def refresh_settings(self):
        self.__get_settings()




class TimeSeriesWidget():
    def __init__(self, dataserver):
        self.__init_logger()
        self.logger.debug("__init TimeSeriesWidget()")
        self.server = dataserver
        self.height = 600
        self.width = 900
        self.lines = {} #keeping the line objects
        self.legendItems ={} # keeping the legend items
        self.legend ={}
        self.hasLegend = False
        self.data = None
        self.dispatchList = [] # a list of function to be executed in the bokeh app look context
                                # this is needed e.g. to assign values to renderes etc
        self.dispatchLock = threading.Lock() # need a lock for the dispatch list
        self.dispatcherRunning = False # set to true if a function is still running
        self.observerThreadRunning = False
        self.annotationTags = []
        self.hoverTool = None
        self.showThresholds = True # initial value to show or not the thresholds (if they are enabled)

        self.__init_figure() #create the graphical output

        self.__init_observer() #create the observer: do we need to watch something periodically?

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

    def __stop_observer(self):
        self.logger.debug("__stop_observer " +str(self.observerThreadRunning))
        if self.observerThreadRunning:
            self.observerThreadRunning = False
            self.observerThread.join()  # wait for finish
            self.logger.debug("joined")

    def __init_observer(self):
        """
        # the widget.observer (referencer) points to the variables to watch, if they change (increase), we reload
        # the elements given in widget.observerUpdate
        """
        settings = self.server.get_settings()
        if "observer" in settings:
            self.logger.info("must observ %s",settings["observer"]["observerUpdate"])
            self.__stop_observer()      #stop it, in case it's running
            self.observerStatus = {}

            if (settings["observerEnabled"] != True):
                self.logger.info("observerthread will not be started")
                pass # we don't start the thread
            else:
                if "background" in settings["observer"]["observerUpdate"]:
                    #we must observ the background
                    self.observerStatus["background"]=None # initialize with none
                if "variables" in settings["observer"]["observerUpdate"]:
                    self.observerStatus["variables"]=None

                self.logger.info("we start the observer thread")
                self.observerThreadRunning = True
                self.observerThread = threading.Thread(target=self.__observer_thread_function)
                self.observerThread.start()


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
        self.buttonWidth = 160

        #layoutControls = []# this will later be applied to layout() function

        settings = self.server.get_settings()

        if "width" in settings:
            self.width = settings["width"]
        if "height" in settings:
            self.height = settings["height"]
        #self.cssClasses = {"button":"button_21","groupButton":"group_button_21","multiSelect":"multi_select_21"}
        #self.cssClasses = {"button": "button_21_sm", "groupButton": "group_button_21_sm", "multiSelect": "multi_select_21_sm"}
        #self.layoutSettings = {"controlPosition":"bottom"} #support right and bottom, the location of the buttons and tools


        #initial values
        self.rangeStart = settings["startTime"]
        self.rangeEnd = settings["endTime"]

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

        tools = [WheelZoomTool(dimensions="width"), PanTool(dimensions="width")]
        if settings["hasAnnotation"] == True:
            self.boxSelectTool = BoxSelectTool(dimensions="width")
            tools.append(self.boxSelectTool)
        elif settings["hasThreshold"] == True:
            self.boxSelectTool = BoxSelectTool(dimensions="height")
            tools.append(self.boxSelectTool)
        tools.append(ResetTool())

        fig = figure(toolbar_location=None, plot_height=self.height,
                     plot_width=self.width,
                     sizing_mode="scale_width",
                     x_axis_type='datetime', y_range=Range1d())
        self.plot = fig

        for tool in tools:
            fig.add_tools(tool) # must assign them to the layout to have the actual use hooked
        toolBarBox = ToolbarBox()  #we need the strange creation of the tools to avoid the toolbar to disappear after
                                   # reload of widget, then drawing an annotations (bokeh bug?)
        toolBarBox.toolbar = Toolbar(tools=tools)
        toolBarBox.toolbar_location = "right"
        toolBarBox.toolbar.logo = None # no bokeh logo

        self.tools = toolBarBox
        self.toolBarBox = toolBarBox

        self.plot.xaxis.formatter = FuncTickFormatter(code = """ 
            let local = moment(tick).tz('%s');
            let datestring =  local.format();
            return datestring.slice(0,-6);
            """%settings["timeZone"])

        self.plot.xaxis.ticker = DatetimeTicker(desired_num_ticks=4)# give more room for the date time string (default was 6)
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


        #make the controls
        layoutControls =[]

        #Annotation drop down
        labels=[]
        if settings["hasAnnotation"] == True:
            labels = settings["tags"]
            labels.append("-erase-")
        if settings["hasThreshold"] == True:
            labels.extend(["threshold","-erase threshold-"])
        if labels:
            menu = [(label,label) for label in labels]
            self.annotationDropDown = Dropdown(label="Annotate: "+str(labels[0]), menu=menu,width=self.buttonWidth)
            self.currentAnnotationTag = labels[0]
            self.annotationDropDown.on_change('value', self.annotation_drop_down_on_change_cb)
            #self.annotation_drop_down_on_change_cb() #call it to set the box select tool right and the label
            layoutControls.append(self.annotationDropDown)

        # show Buttons
        # initially everything is disabled
        # check background, threshold, annotation
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
        self.showGroup = CheckboxButtonGroup(labels=self.showGroupLabelsDisplay)
        self.showGroup.on_change("active",self.show_group_on_click_cb)
        layoutControls.append(self.showGroup)

        #make the custom buttons
        self.customButtonsInstances = []
        if "buttons" in settings:
            self.logger.debug("create user buttons")
            #create the buttons
            for entry in settings["buttons"]:
                button = Button(label=entry["name"],width=self.buttonWidth)#,css_classes=['button_21'])
                instance = self.ButtonCb(self,entry["targets"])
                button.on_click(instance.cb)
                layoutControls.append(button)
                self.customButtonsInstances.append(instance)

        #make the debug button
        if "hasReloadButton" in self.server.get_settings():
            if self.server.get_settings()["hasReloadButton"] == True:
                #we must create a reload button
                button = Button(label="reload",width=self.buttonWidth)#, css_classes=['button_21'])
                button.on_click(self.reset_all)
                layoutControls.append(button)

        #build the layout
        self.layout = layout( [row(children=[self.plot,self.tools],sizing_mode="fixed")],row(layoutControls,width=self.width ,sizing_mode="scale_width"))

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


    def annotations_radio_group_cb(self,args):
        """called when a selection is done on the radio button for the annoations"""
        option = self.annotationButtons.active  # gives a 0,1 list, get the label now
        # tags = self.server.get_settings()["tags"]
        mytag = self.annotationTags[option]
        self.logger.debug("annotations_radio_group_cb "+str(mytag))
        if "threshold" in mytag:
            #we do a a threshold annotation, adjust the tool
            self.boxSelectTool.dimensions = "height"
        else:
            self.boxSelectTool.dimensions = "width"

    def testCb(self, attr, old, new):
        self.logger.debug("testCB "+"attr"+str(attr)+"\n old"+str(old)+"\n new"+str(new))
        self.logger.debug("ACTIVE: "+str(self.plot.toolbar.active_drag))

    def __make_tooltips(self):
        #make the hover tool
        """
            if we create a hover tool, it only appears if we plot a line, we need to hook the hover tool to the figure and the toolbar separately:
            to the figure to get the hover functionality, there we also need to add all renderers to the hover by hand if we create line plots later on
            still haven't found a way to make the hover tool itself visible when we add it to the toolbar; it does appear when we draw a new line,
            if we change edit/del and add lines, (including their renderers, we need to del/add those renderes to the hover tools as well

        """

        if not self.hoverTool:
            #we do this only once

            self.logger.info("MAKE TOOLTIPS"+str(self.hoverCounter))
            hover = HoverTool(renderers=[])
            #hover.tooltips = [("name","$name"),("time", "@__time{%Y-%m-%d %H:%M:%S.%3N}"),("value","@$name{0.000}")] #show one digit after dot
            hover.tooltips = [("name", "$name"), ("time", "@{__time}{%f}"),
                             ("value", "@$name{0.000}")]  # show one digit after dot
            #hover.formatters={'__time': 'datetime'}
            custom = """var local = moment(value).tz('%s'); return local.format();"""%self.server.get_settings()["timeZone"]
            hover.formatters = {'__time': CustomJSHover(code=custom)}
            if self.server.get_settings()["hasHover"] in ['vline','hline','mouse']:
                hover.mode = self.server.get_settings()["hasHover"]
            hover.line_policy = 'nearest'
            self.plot.add_tools(hover)
            self.hoverTool = hover
            self.toolBarBox.toolbar.tools.append(hover)  # apply he hover tool to the toolbar

        # we do this every time
        # reapply the renderers to the hover tool
        renderers = []
        self.hoverTool.renderers = []
        renderers = []
        for k, v in self.lines.items():
            renderers.append(v)
        self.hoverTool.renderers = renderers



    def __observer_thread_function(self):
        """ the periodic thread function"""
        self.logger.info("starting observer thread functino")
        counter = 0 # for debugging
        while (self.observerThreadRunning):
            counter+=1
            self.__check_observed(counter)
            time.sleep(0.5)
        self.logger.debug("exit observer thread")

    def __check_observed(self,counter):
        """
            this function is periodically called from a threading.thread
            we check if some data if the backend has changed and if we need to do something on change
        """
        self.logger.debug("enter __check_observed() "+str(counter))
        try:
            #now see what we have to do
            if "background" in self.observerStatus:
                #check the background counter for update
                backgroundCounter = self.server.get_values(self.server.get_settings()["observer"]["observerBackground"])
                #self.logger.debug("background observer Val"+str(backgroundCounter))
                if self.observerStatus["background"] != None and self.observerStatus["background"] != backgroundCounter:
                    #we have a change in the background:
                    self.logger.debug("observer background changed")
                    self.__dispatch_function(self.refresh_backgrounds)
                self.observerStatus["background"] = backgroundCounter
            if "variables" in self.observerStatus:
                variables = self.server.get_selected_variables_sync()
                if self.observerStatus["variables"] != None and self.observerStatus["variables"]!=variables:
                    #we have a change in the selected variables
                    self.logger.debug("variables selection observer changed"+str(self.observerStatus["variables"] )+"=>"+str(variables))
                    self.__dispatch_function(self.refresh_plot)
                self.observerStatus["variables"] = variables

            #now we also check if we have a legend click which means that we must delete a variable from the selection
            self.logger.debug("RENDERERS CHECK --------------------------")
            deleteList=[]
            for r in self.plot.renderers:
                if r.name and r.name in self.server.get_variables_selected() and r.visible == False:
                    #there was a click on the legend to hide the variables
                    self.logger.debug("=>>>>>>>>>>>>>>>>>DELETE FROM plot:"+r.name)
                    deleteList.append(r.name)
            if deleteList != []:
                #now prepare the new list:
                newVariablesSelected = [var for var in self.server.get_variables_selected() if var not in deleteList]
                self.logger.debug("new var list"+str(newVariablesSelected))
                self.server.set_variables_selected(newVariablesSelected)
                self.__dispatch_function(self.refresh_plot)
        except Exception as ex:
            self.logger.error("problem during __check_observed"+str(ex)+str(sys.exc_info()[0]))

        self.logger.debug("leave __check_observed()")

    def reset_all(self):
        """
            this is an experimental function that reloads the widget in the frontend
            it should be executed as dispatched
        """
        self.__stop_observer()
        self.logger.debug("self.reset_all()")
        self.server.refresh_settings()

        #clear out the figure
        self.hasLegend = False # to make sure the __init_figure makes a new legend
        self.plot.renderers = [] # no more renderers
        self.data = None #no more data
        self.lines = {} #no more lines



        self.__init_figure()
        self.__init_observer()
        self.curdoc().clear()
        self.curdoc().add_root(self.get_layout())

    def __dispatch_function(self,function):
        """
            queue a function to be executed in the periodic callback from the bokeh app main loop
            this is needed for functions which are triggered from a separate thread but need to be
            executed in the context of the bokeh app loop

        Args:
            function: functionpointer to be executed
        """
        with self.dispatchLock:
            self.dispatchList.append(function)


    def adjust_y_axis_limits(self):
        """
            this function automatically adjusts the limts of the y-axis that the data fits perfectly in the plot window
        """
        self.logger.debug("adjust_y_axis_limits")

        lineData = []
        selected = self.server.get_variables_selected()
        for item in self.data.data:
            if item in selected:
                lineData.extend(self.data.data[item])

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

        else:
            self.logger.warning("not y axix to arrange")



    def periodic_cb(self):
        """
            called periodiaclly by the bokeh system
            here, we execute function that we want to execute based on our own thread timer.
            this is needed, as modifications to data or parameters in the bokeh objects
            are only possible withing the bokeh thread, not from any other.

        """
        executelist=[]
        #first copy over the dispatch list, this #todo: this must be done under lock
        with self.dispatchLock:
            if not self.dispatcherRunning:
                if self.dispatchList:
                    executelist = self.dispatchList.copy()
                    self.dispatchList = []
                self.dispatcherRunning = True

        for fkt in executelist:
            self.logger.info("now executing dispatched %s",str(fkt))
            fkt() # execute the functions which wait for execution and must be executed from this context
        with self.dispatchLock:
            self.dispatcherRunning = False # free this to run the next

    def __get_free_color(self):
        """
            get a currently unused color from the given palette, we need to make this a function, not just a mapping list
            as lines come and go and therefore colors become free again

            Returns:
                a free color code

        """
        usedColors =  [self.lines[lin].glyph.line_color for lin in self.lines]
        for color in themes.lineColors:
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
        #self.logger.debug("@__plot_lines:from server var selected %s",str(newVars))
        variablesRequest = variables.copy()
        variablesRequest.append("__time")   #make sure we get the time included
        #self.logger.debug("@__plot_lines:self.variables, bins "+str(variablesRequest)+str( settings["bins"]))
        getData = self.server.get_data(variablesRequest,self.rangeStart,self.rangeEnd,settings["bins"]) # for debug
        #self.logger.debug("GETDATA:"+str(getData))

        if newVars == []:
            self.data.data = getData  # also apply the data to magically update
        else:
            self.logger.debug("new column data source")
            if self.data is None:
                #first time
                self.data = ColumnDataSource(getData)  # this will magically update the plot, we replace all data
            else:
                #add more data
                for variable in getData:
                    if variable not in self.data.data:
                        self.data.add(getData[variable],name=variable)


        timeNode = "__time"
        #now plot var
        for variableName in newVars:
            color = self.__get_free_color()
            self.logger.debug("new color ist"+color)
            if variableName != timeNode:
                self.lines[variableName] = self.plot.line(timeNode, variableName, color=color,
                                                  source=self.data, name=variableName,line_width=2)  # x:"time", y:variableName #the legend must havee different name than the source bug
                self.legendItems[variableName] = LegendItem(label=variableName,renderers=[self.lines[variableName]])
                if self.showThresholds:
                    self.show_thresholds_of_line(variableName)

        #now make a legend
        #legendItems=[LegendItem(label=var,renderers=[self.lines[var]]) for var in self.lines]
        legendItems = [v for k,v in self.legendItems.items()]
        if not self.hasLegend:
            #at the first time, we create the "Legend" object
            self.plot.add_layout(Legend(items=legendItems))
            self.plot.legend.location = "top_right"
            self.plot.legend.click_policy = "hide"
            self.hasLegend = True
        else:
            self.plot.legend.items = legendItems #replace them

        self.adjust_y_axis_limits()


    def range_cb(self, attribute,old, new):
        """
            callback by bokeh system when the scaling have changed (roll the mouse wheel), see bokeh documentation
        """
        #we only store the range, and wait for an LOD or PANEnd event to refresh
        if attribute == "start":
            self.rangeStart = new
        if attribute == "end":
            self.rangeEnd = new
        #print("range cb"+str(attribute),self.rangeStart,self.rangeEnd)

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
        self.logger.debug("diffanalysis new"+str(newLines)+"  del "+str(deleteLines))

        #now delete the ones to delete
        for key in deleteLines:
            self.lines[key].visible = False
            del self.lines[key]
            del self.legendItems[key]
        #remove the legend
        legendItems = [v for k, v in self.legendItems.items()]
        self.plot.legend.items = legendItems
        #remove the lines
        self.remove_renderes(deleteLines)
        #remove the according thresholds if any
        for lin in deleteLines:
            self.remove_renderes(self.find_thresholds_of_line(lin))


        #create the new ones
        self.__plot_lines(newLines)

        #xxxtodo: make this differential as well
        if self.server.get_settings()["background"]["hasBackground"]:
            self.refresh_backgrounds()

        if self.server.get_settings()["hasHover"] not in [False,None]:
            self.__make_tooltips() #must be the last in the drawings

    def refresh_backgrounds(self):
        """ check if backgrounds must be drawn if not, we just hide them"""
        self.hide_backgrounds()
        if self.showBackgrounds:
            self.show_backgrounds()


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

        if eventType == "PanEnd":
            #self.refresh_plot()
            pass
        if eventType == "LODEnd":
            self.refresh_plot()

        if eventType == "Reset":
            self.reset_plot_cb()

        if eventType == "SelectionGeometry":
            #option = self.annotationButtons.active # gives a 0,1 list, get the label now
            #tags = self.server.get_settings()["tags"]
            #mytag = self.annotationTags[option]
            mytag =self.currentAnnotationTag
            #self.logger.info("TAGS"+str(self.annotationTags)+"   "+str(option))
            self.edit_annotation_cb(event.__dict__["geometry"]["x0"],event.__dict__["geometry"]["x1"],mytag,event.__dict__["geometry"]["y0"],event.__dict__["geometry"]["y1"])

    def reset_plot_cb(self):
        self.logger.debug("reset plot")
        self.rangeStart = None
        self.rangeEnd = None
        self.refresh_plot()


    def remove_renderes(self,deleteList=[],deleteMatch=""):
        """
         this functions removes renderers (plotted elements from the widget), we find the ones to delete based on their name attribute
         Args:
            deletelist: a list or set of renderer names to be deleted
            deleteMatch(string) a part of the name to be deleted, all renderer that have this string in their names will be removed
        """
        newRenderers = []
        for r in self.plot.renderers:
            if r.name:
                if r.name in deleteList:
                    pass  # we ignore this one and do NOT add it to the renderers, this will hide the object
                elif deleteMatch != "" and deleteMatch in r.name:
                    pass  # we ignore this one and do NOT add it to the renderers, this will hide the object
                else:
                    newRenderers.append(r)  # we keep this one, as it doesnt mathc the deletersl
            else:
                newRenderers.append(r)  # if we have no name, we can't filter, keep this
        self.plot.renderers = newRenderers

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
        if not self.showThresholds:
            return

        for annoName,anno in self.server.get_annotations().items():
            self.logger.debug("@show_thresholds "+annoName+" "+anno["type"])
            if anno["type"]=="threshold":
                # we only show the annotations where the lines are also there
                self.logger.debug("and the lines are currently"+str(list(self.lines.keys())))
                if anno["variable"] in self.lines:
                    self.draw_threshold(annoName,anno["variable"])


    def hide_thresholds(self):
        """ hide the current annotatios in the widget of type time"""
        annotations = self.server.get_annotations()
        timeAnnos = [anno for anno in annotations.keys() if annotations[anno]["type"]=="threshold" ]
        self.remove_renderes(deleteList=timeAnnos)
        pass


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


    def show_annotations(self):
        """ show the current annotatios in the widget of type time """
        mylist = []
        for annoname,anno in self.server.get_annotations().items():
            if "type" in anno and anno["type"]!="time":
                continue
            mylist.append(self.draw_annotation(annoname,add_layout=False))

        #getattr(self.plot,'center').extend(mylist)
        self.plot.renderers.extend(mylist)
        #for anno in mylist:
        #    self.plot.add_layout(anno)

    def hide_annotations(self):
        """ hide the current annotatios in the widget of type time"""
        annotations = self.server.get_annotations()
        timeAnnos = [anno  for anno in annotations.keys() if annotations[anno]["type"]=="time" ]
        self.remove_renderes(deleteList=timeAnnos)

    def get_layout(self):
        """ return the inner layout, used by the main"""
        return self.layout
    def set_curdoc(self,curdoc):
        self.curdoc = curdoc

    def draw_annotation(self, modelPath, add_layout = True):
        """
            draw one time annotation on the plot
            Args:
             modelPath(string): the path to the annotation, the modelPath-node must contain children startTime, endTime, colors, tags
        """
        try:
            #self.logger.debug("draw_annotation "+modelPath)
            annotations = self.server.get_annotations()
            if annotations[modelPath]["type"]!= "time":
                return # we only want the time annotations

            #now get the first tag, we only use the first
            tag = annotations[modelPath]["tags"][0]

            settings = self.server.get_settings()
            tagIndex = settings["tags"].index(tag)
            color = settings["colors"][tagIndex]
            start = annotations[modelPath]["startTime"]
            end = annotations[modelPath]["endTime"]

            #print("draw new anno",color,start,end,modelPath)

            newAnno = BoxAnnotation(left=start,right=end,
                                fill_color=color,
                                fill_alpha=0.2,
                                name=modelPath) #+"_annotaion

            if add_layout:
                self.plot.add_layout(newAnno)
            else:
                return newAnno
        except Exception as ex:
            self.logger.error("error draw annotatino ",str(ex))

        #this is an example for labelling
        #label = Label(x=((end-start)*0.25+start), y=50, y_units='screen', text=modelPath,text_font_size='0.8em', angle=3.1415/2)
        #self.plot.add_layout(label)


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

    def show_thresholds_of_line(self,path):
        self.logger.debug("@show_threasholds_of_line "+path)
        thresholds = self.find_thresholds_of_line(path)
        for threshold in thresholds:
            self.draw_threshold(threshold,path)

    def hide_thresholds_of_line(self,path):
        thresholds = self.find_thresholds_of_line(path)
        self.remove_renderes(deleteList=thresholds)

    def draw_threshold(self, modelPath, linePath=None):
        """ draw the boxannotation for a threshold
            Args:
                 modelPath(string): the path to the annotation, the modelPath-node must contain children startTime, endTime, colors, tags
        """

        try:
            annotations = self.server.get_annotations()
            # now get the first tag, we only use the first
            tag = annotations[modelPath]["tags"][0]



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
                                    fill_alpha=0.1,
                                    name=modelPath)  # +"_annotaion

            self.plot.add_layout(newAnno)
        except Exception as ex:
            self.logger.error("error draw threshold "+str(modelPath)+ " "+linePath+" "+str(ex))

    def show_backgrounds(self,data=None):
        """
            show the current backgrounds
            Args:
                data(dict):  contains a dict holding the nodeid with of the background and the __time as keys and the lists of data
                    if te data is not given, we get the backgrounds fresh from the data server
        """

        self.logger.debug("__show backgrounds()")
        backGroundNodeId = self.server.get_settings()["background"]["background"]

        if not data:
            #we have to pick up the background data first
            self.logger.debug("get fresh background data from the model server %s",backGroundNodeId)
            bins = self.server.get_settings()["bins"]
            #bins = 30
            #bins = 30
            getData = self.server.get_data([backGroundNodeId], start=self.rangeStart, end=self.rangeEnd,
                                           bins=bins)  # for debug
            data = getData

        #now make the new backgrounds
        # we create a list of dicts containing annotation-style info: start
        #startTime = data["__time"][0] # initialize with the first time
        startTime = None
        currentBackGroundValue = data[backGroundNodeId][0]

        startTime = None
        backgrounds = []
        colorMap = self.server.get_settings()["background"]["backgroundMap"]
        for value,time in zip(data[backGroundNodeId],data["__time"]):
            #must set the startTime?
            if not startTime:
                if not numpy.isfinite(value):
                    continue # can't use inf/nan
                else:
                    startTime = time
                    currentBackGroundValue = value
            else:
                #now we are inside a region, let's see when it ends
                 if value != currentBackGroundValue:
                    #a new entry starts, finish the last and add it to the list of background
                    try:
                        color = colorMap[str(int(currentBackGroundValue))]
                    except:
                        color = "red"
                    entry = {"start":startTime,"end":time,"value":currentBackGroundValue,"color":color}
                    self.logger.debug("ENTRY"+json.dumps(entry))
                    backgrounds.append(entry)
                    #now check if current value is finite, then we can start
                    if numpy.isfinite(value):
                        currentBackGroundValue = value
                        startTime = time
                    else:
                        startTime = None # look for the next start
        #now also add the last, if we have one running
        if startTime:
            try:
                color = colorMap[str(int(currentBackGroundValue))]
            except:
                color = "red"
            entry = {"start": startTime, "end": time, "value": currentBackGroundValue, "color": color}
            backgrounds.append(entry)
        #now we have a list of backgrounds
        self.logger.info("have %i background entries",len(backgrounds))
        #now plot them

        for back in backgrounds:
            name = "__background"+str('%8x'%random.randrange(16**8))
            newBack = BoxAnnotation(left=back["start"], right=back["end"],
                                    fill_color=back["color"],
                                    fill_alpha=0.2,
                                    name=name)  # +"_annotaion
            self.plot.add_layout(newBack)

    def hide_backgrounds(self):
        """ remove all background from the plot """
        self.remove_renderes(deleteMatch="__background")




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
            self.remove_renderes(deleteList=deleteList)
            self.server.delete_annotations(deleteList)
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
            self.remove_renderes(deleteList=deleteList)
            self.server.delete_annotations(deleteList)


        elif "threshold" not in tag:
            #create a time annotation one

            newAnnotationPath = self.server.add_annotation(start,end,tag,type="time")
            #print("\n now draw"+newAnnotationPath)
            self.draw_annotation(newAnnotationPath)
            #print("\n draw done")
        else:
            #create a threshold annotation, but only if ONE variable is currently selected
            variable = self.server.get_variables_selected()
            if len(variable) != 1:
                self.logger.error("can't create threshold anno, len(vars"+str(len(variable)))
                return


            newAnnotationPath = self.server.add_annotation(start,end,tag,type ="threshold",min=min,max=max)
            self.draw_threshold(newAnnotationPath,variable[0])



if __name__ == '__main__':

    ts_server = TimeSeriesWidgetDataServer('http://localhost:6001/',"root.visualization.widgets.timeseriesOne")
    t=TimeSeriesWidget(ts_server)
