

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


from bokeh.models import DatetimeTickFormatter, ColumnDataSource, BoxSelectTool, BoxAnnotation, Label, LegendItem, Legend
from bokeh.models import Range1d,DataRange1d
from bokeh import events
from bokeh.models.widgets import RadioButtonGroup, Paragraph, Toggle, MultiSelect, Button
from bokeh.plotting import figure, curdoc
from bokeh.layouts import layout,widgetbox
from bokeh.models import Range1d, PanTool, WheelZoomTool, ResetTool, ToolbarBox, Toolbar


haveLogger = False



def setup_logging(loglevel=logging.DEBUG):
    global haveLogger
    if not haveLogger:
        # fileName = 'C:/Users/al/devel/ARBEIT/testmyapp.log'


        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        console = logging.StreamHandler()
        console.setLevel(loglevel)
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)

        #logfile = logging.FileHandler('./log/widget_'+'%08x' % random.randrange(16 ** 8)+".log")
        logfile = logging.FileHandler('./widget_' + '%08x' % random.randrange(16 ** 8) + ".log")
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
    return consts




class TimeSeriesWidgetDataServer():
    """
        a helper class for the time series widget dealing with the connection to the backend rest model server
        it also caches settings which don't change over time
    """
    def __init__(self,modelUrl,avatarPath):
        self.__init_logger()
        self.__init_proxy()
        self.url = modelUrl # get the data from here
        self.path = avatarPath # here is the struct for the timeserieswidget
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
        setup_logging()
        self.logger = logging.getLogger("TSWidgetDataServer")
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
        elif method.upper() =="POST":
            now = datetime.datetime.now()
            for timeout in [0.001, 0.1, 1, 10]:
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
            #
            #now parse the stuff and build up our information
            self.annotations={}
            for node in nodes:
                if node["type"]=="annotation":
                    self.annotations[node["browsePath"]]=get_const_nodes_as_dict(node["children"])
                    self.annotations[node["browsePath"]]["startTime"] = date2secs(self.annotations[node["browsePath"]]["startTime"])*1000
                    self.annotations[node["browsePath"]]["endTime"] = date2secs(self.annotations[node["browsePath"]]["endTime"]) * 1000

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
        for node in info[0]["children"]:
            if node["name"] == "observer":
                observ["targets"]=node["forwardRefs"].copy()
            if node["name"] == "observerUpdate":
                observ["observerUpdate"]=node["value"].copy()
        if observ!={}:
            self.settings["observer"]=copy.deepcopy(observ)

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
            "bins": self.settings["bins"],
            "includeTimeStamps": "02:00",
        }
        r=self.__web_call("POST","_getdata",body)
        #convert the time to ms since epoch
        r["__time"]=(numpy.asarray(r["__time"])*1000).tolist()
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

    #start and end are ms(!) sice epoch, tag is a string
    def add_annotation(self,start,end,tag):
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
        nodesToCreate = [
            {"browsePath": annoPath,"type":"annotation"},
            {"browsePath": annoPath + '.startTime',"type":"const","value":secs2dateString(start/1000)},
            {"browsePath": annoPath + '.endTime', "type": "const", "value":secs2dateString(end/1000)},
            {"browsePath": annoPath + '.tags', "type": "const", "value": [tag]}
            ]
        self.logger.debug("creating anno %s",str(nodesToCreate))
        res = self.__web_call('POST','_create',nodesToCreate)

        #now also update our internal list
        self.annotations[annoPath] = {"startTime":start,"endTime":end,"tags":[tag]}
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
        self.server = dataserver
        self.height = 600
        self.width = 900
        self.lines = {} #keeping the line objects
        self.legend ={}
        self.hasLegend = False
        self.data = None
        self.dispatchList = [] # a list of function to be executed in the bokeh app look context
                                # this is needed e.g. to assign values to renderes etc
        self.dispatchLock = threading.Lock() # need a lock for the dispatch list
        self.observerThreadRunning = False
        self.annotationTags = []

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
        self.logger.debug("__stop_observer")
        if self.observerThreadRunning:
            self.observerThreadRunning = False
            self.observerThread.join()  # wait for finish

    def __init_observer(self):
        """
        # the widget.observer (referencer) points to the variables to watch, if they change (increase), we reload
        # the elements given in widget.observerUpdate
        """
        settings = self.server.get_settings()
        if "observer" in settings:
            self.logger.info("must observ %s",settings["observer"]["targets"])
            #get the initial values
            self.observed = {}
            values = self.server.get_values(settings["observer"]["targets"])
            for k,v in zip(settings["observer"]["targets"],values):
                self.observed[k]=v
            #start the observer thread, if it's running, we stop it here
            self.__stop_observer()

            if ("observerEnabled" in settings and settings["observerEnabled"] == False):
                self.logger.info("observerthread will not be started")
                pass # we don't start the thread
            else:
                self.logger.info("we start the observer thread")
                self.observerThreadRunning = True
                self.observerThread = threading.Thread(target=self.__observer_thread_function)
                self.observerThread.start()


    def __init_figure(self):

        """
            initialize the time series widget, plot the lines, create controls like buttons and menues
            also hook the callbacks
        """


        layoutControls = []# this will later be applied to layout() function

        settings = self.server.get_settings()

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
            tools.append(BoxSelectTool(dimensions="width"))
        tools.append(ResetTool())
        fig = figure(toolbar_location=None, plot_height=self.height,
                     plot_width=self.width,
                     sizing_mode="scale_width",
                     x_axis_type='datetime', y_range=Range1d())
        for tool in tools:
            fig.add_tools(tool) # must assign them to the layout to have the actual use hooked
        toolBarBox = ToolbarBox()
        toolBarBox.toolbar = Toolbar(tools=tools)
        toolBarBox.toolbar_location = "right"
        toolBarBox.toolbar.logo = None # no bokeh logo
        self.plot = fig
        self.tools = toolBarBox


        datetimeFormat = ["%Y-%m-%d %H:%M:%S"]
        datetimeTickFormat = DatetimeTickFormatter(
            years=datetimeFormat,
            months=datetimeFormat,
            days=datetimeFormat,
            hourmin=datetimeFormat,
            hours=datetimeFormat,
            minutes=datetimeFormat,
            minsec=datetimeFormat,
            seconds=datetimeFormat,
            milliseconds=datetimeFormat
        )  # use the same time legend style for all zoom levels
        self.plot.xaxis.formatter = datetimeTickFormat
        self.__plot_lines()

        #hook in the callback of the figure
        self.plot.x_range.on_change('start', self.range_cb)
        self.plot.x_range.on_change('end', self.range_cb)
        self.plot.on_event(events.Pan, self.event_cb)
        self.plot.on_event(events.PanStart, self.event_cb)
        self.plot.on_event(events.PanEnd, self.event_cb)
        self.plot.on_event(events.LODEnd, self.event_cb)
        self.plot.on_event(events.Reset, self.event_cb)
        self.plot.on_event(events.SelectionGeometry, self.event_cb)


        # make the variableSelector
        options = [(x, x) for x in self.server.get_variables_selectable()]
        self.variablesMultiSelect = MultiSelect(title="Select Variables", value=self.server.get_variables_selected(),
                                                options=options,size = 5,css_classes=['multi_select_21'])
        self.variablesSelectButton = Button(label="apply",css_classes=['button_21'])
        self.variablesSelectButton.on_click(self.var_select_button_cb)

        selectWidget = widgetbox(self.variablesMultiSelect,self.variablesSelectButton)
        layoutControls.append(selectWidget)



        #make the annotation controls
        if settings["hasAnnotation"] == True:
            #self.plot.add_tools(BoxSelectTool(dimensions="width"))
            #also add a drop down for the creation
            labels = settings["tags"]
            labels.append("-erase-")
            self.annotationTags=copy.deepcopy(labels)
            print("HAVE SET ANNOT"+str(labels)+"   "+str(self.annotationTags))
            self.annotationButtons = RadioButtonGroup(labels=labels,active=0,css_classes=['group_button_21'])
            self.annotationOptions = widgetbox(Paragraph(text="Select Annotation Tag"),self.annotationButtons)
            self.showAnnotationToggle = Toggle(label="hide Annotations", active=True,css_classes=['button_21'])#, button_type="success")
            self.showAnnotationToggle.on_click(self.annotation_toggle_click_cb)
            annoWidget = widgetbox(Paragraph(text="Select Annotation Tag"),self.annotationButtons,self.showAnnotationToggle)
            layoutControls.append(annoWidget)
        #now do the annotations
        for anno in self.server.get_annotations():
            self.draw_annotation(anno)

        if self.server.get_settings()["background"]["hasBackground"]:
            #create the controls and plot the backgrounds as boxannotations
            self.backgroundbutton = Toggle(label="show Backgrounds",css_classes=['button_21'],active=False)
            self.backgroundbutton.on_click(self.backgroundbutton_cb)
            self.showBackgrounds = False
            layoutControls.append(self.backgroundbutton)
            self.refresh_backgrounds()  #draw the backgrounds or not (check if needed)


        #make the custom buttons
        self.customButtonsWidgets=[]
        self.customButtonsInstances = []
        if "buttons" in settings:
            self.logger.debug("create user buttons")
            #create the buttons
            for entry in settings["buttons"]:
                button = Button(label=entry["name"],css_classes=['button_21'])
                instance = self.ButtonCb(self,entry["targets"])
                button.on_click(instance.cb)
                self.customButtonsInstances.append(instance)
                self.customButtonsWidgets.append(button)

            layoutControls.extend(self.customButtonsWidgets)

        #make the debug button
        if "hasReloadButton" in self.server.get_settings():
            if self.server.get_settings()["hasReloadButton"] == True:
                #we must create a reload button
                button = Button(label="reload widget", css_classes=['button_21'])
                button.on_click(self.reset_all)
                layoutControls.append(button)



        #apply all to the layout
        #self.plot.sizing_mode = "scale_width"
        #for elem in layoutControls:
        #    if type(elem) is list:
        #        for subelem in elem:
        #            subelem.sizing_mode = "scale_both"
        #    else:
        #        elem.sizing_mode = "scale_both"
        self.layout = layout([[self.plot,self.tools,layoutControls]])#,sizing_mode="scale_width")


    def __observer_thread_function(self):
        """ the periodic thread function"""
        self.logger.info("starting observer thread functino")
        while (self.observerThreadRunning):
            self.__check_observed()
            time.sleep(0.5)
        self.logger.debug("exit observer thread")

    def __check_observed(self):
        """
            this function is periodically called from a threading.thread
            we check if some data if the backend has changed and if we need to do something on change
        """
        try:
            toObserve = list(self.observed.keys())
            if not toObserve:
                print("nothing to observe")
                return
            values = self.server.get_values(list(self.observed.keys()))
            for k, v in zip(self.observed.keys(), values):
                if self.observed[k]!=v:
                    self.logger.debug("!trigger on %s",str(k))
                    self.observed[k]=v
                    #now we must redraw what is defined
                    if "background" in self.server.get_settings()["observer"]["observerUpdate"]:
                        self.logger.debug("observer updates the background")
                        self.__dispatch_function(self.refresh_backgrounds)
        except:
            self.logger.error("problem during __check_observed")

    def reset_all(self):
        """
            this is an experimental function that reloads the widget in the frontend
            it should be executed as dispatched
        """
        self.__stop_observer()
        self.logger.debug("self.reset_all()")
        self.server.refresh_settings()
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
            if self.dispatchList:
                executelist = self.dispatchList.copy()
                self.dispatchList = []

        for fkt in executelist:
            self.logger.info("now executing dispatched %s",str(fkt))
            fkt() # execute the functions which wait for execution and must be executed from this context

    def __plot_lines(self):
        """ plot the currently selected variables as lines, update the legend """
        self.logger.debug("@__plot_lines")
        settings= self.server.get_settings()
        self.variables = self.server.get_variables_selected().copy()
        self.logger.debug("@__plot_lines:from server var selected %s",str(self.variables))
        variablesRequest = self.variables.copy()
        variablesRequest.append("__time")   #make sure we get the time included
        self.logger.debug("@__plot_lines:self.variables, bins "+str(variablesRequest)+str( settings["bins"]))
        getData = self.server.get_data(variablesRequest,self.rangeStart,self.rangeEnd,settings["bins"]) # for debug

        self.data=ColumnDataSource(getData) # this will magically update the plot

        timeNode = "__time"
        #now plot
        colors = themes.lineColors
        for idx, variableName in enumerate(self.variables):
            if idx > len(colors) - 1:
                color = "white"
            else:
                color = colors[idx]
            if variableName != timeNode:
                self.lines[variableName] = self.plot.line(timeNode, variableName, color=color,
                                                  source=self.data, name=variableName,line_width=2)  # x:"time", y:variableName #the legend must havee different name than the source bug
        #now make a legend
        legendItems=[LegendItem(label=var,renderers=[self.lines[var]]) for var in self.variables]
        if not self.hasLegend:
            #at the first time, we create the "Legend" object
            self.plot.add_layout(Legend(items=legendItems))
            self.plot.legend.location = "top_right"
            self.hasLegend = True
        else:
            self.plot.legend.items = legendItems #replace them
        #self.data.data = getData #xxxtest
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
        if self.variables != self.server.get_variables_selected():
            #must redraw

            self.logger.debug("must rebild lines, old vars" +str(self.variables))

            # iterate and turn off all lines to hide
            for key in self.lines:
                self.lines[key].visible=False

            #let's try a full replacement
            self.__plot_lines()
            self.variables = self.server.get_variables_selected().copy() # update to current status
        else:
            self.logger.debug("use old lines")

            bins = self.server.get_settings()["bins"]
            requestVariables = self.server.get_variables_selected()
            requestVariables.append(self.server.get_time_node())  # make sure we get the time included
            self.logger.debug("self.variables, bins " + str(requestVariables) + str(bins))
            #print("make request to get new data from to ",self.rangeStart,self.rangeEnd)
            getData = self.server.get_data(requestVariables, start=self.rangeStart, end=self.rangeEnd,
                                           bins=bins)  # for debug
            self.data.data = getData  # this one magically refreshes the plot
            self.adjust_y_axis_limits()
            if self.server.get_settings()["background"]["hasBackground"]:
                self.refresh_backgrounds()
        pass

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

    def test_button_cb(self):
        self.plot.legend.items = self.legendItems[:-1]

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
            option = self.annotationButtons.active # gives a 0,1 list, get the label now
            #tags = self.server.get_settings()["tags"]
            mytag = self.annotationTags[option]
            self.logger.info("TAGS"+str(self.annotationTags)+"   "+str(option))
            self.edit_annotation_cb(event.__dict__["geometry"]["x0"],event.__dict__["geometry"]["x1"],mytag)

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
        """ show the current annotatios in the widget """
        for anno in self.server.get_annotations():
            self.draw_annotation(anno)

    def hide_annotations(self):
        """ hide the current annotatios in the widget """
        self.remove_renderes(deleteList=(self.server.get_annotations().keys()))

    def get_layout(self):
        """ return the inner layout, used by the main"""
        return self.layout
    def set_curdoc(self,curdoc):
        self.curdoc = curdoc

    def draw_annotation(self, modelPath):
        """
            draw one annotation on the plot
            Args:
             modelPath(string): the path to the annotation, the modelPath-node must contain children startTime, endTime, colors, tags
        """
        annotations = self.server.get_annotations()
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

        self.plot.add_layout(newAnno)

        #this is an example for labelling
        #label = Label(x=((end-start)*0.25+start), y=50, y_units='screen', text=modelPath,text_font_size='0.8em', angle=3.1415/2)
        #self.plot.add_layout(label)


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
            getData = self.server.get_data([backGroundNodeId], start=self.rangeStart, end=self.rangeEnd,
                                           bins=bins)  # for debug
            data = getData

        #now make the new backgrounds
        # we create a list of dicts containing annotation-style info: start
        startTime = data["__time"][0] # initialize with the first time
        currentBackGroundValue = data[backGroundNodeId][0]
        backgrounds = []
        colorMap = self.server.get_settings()["background"]["backgroundMap"]
        for value,time in zip(data[backGroundNodeId],data["__time"]):
            if value != currentBackGroundValue:
                #a new entry starts, finish the last and add it to the list of background
                try:
                    color = colorMap[str(int(currentBackGroundValue))]
                except:
                    color = "red"
                entry = {"start":startTime,"end":time,"value":currentBackGroundValue,"color":color}
                backgrounds.append(entry)
                currentBackGroundValue = value
                startTime = time
        #now also add  the last
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
    def edit_annotation_cb(self,start,end,tag):
        """
            call as a callback from the UI when a user adds or removes an annotation
            Args:
                start(float): the start time in epoch ms
                end (float): the end time in epoch ms
                tag (string): the currently selected tag by the UI, for erase there is the "-erase-" tag
        """
        self.logger.debug("edit anno %s %s %s",str(start),str(end),str(tag))
        if tag == '-erase-':
            #remove all annotations which are inside
            deleteList = []
            annotations=self.server.get_annotations()
            for annoPath,annotation in annotations.items():
                if annotation["startTime"]>start and annotation["startTime"]<end:
                    self.logger.debug("delete "+annoPath)
                    deleteList.append(annoPath)
            #now hide the boxes
            self.remove_renderes(deleteList=deleteList)
            self.server.delete_annotations(deleteList)
        else:
            #create a new one

            newAnnotationPath = self.server.add_annotation(start,end,tag)
            #print("\n now draw"+newAnnotationPath)
            self.draw_annotation(newAnnotationPath)
            #print("\n draw done")


if __name__ == '__main__':

    ts_server = TimeSeriesWidgetDataServer('http://localhost:6001/',"root.visualization.widgets.timeseriesOne")
    t=TimeSeriesWidget(ts_server)
