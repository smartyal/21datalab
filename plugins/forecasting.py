#21datalabplugin

from system import __functioncontrolfolder
import streaming




Forecaster={
    "name":"Forecaster",
    "type":"object",
    "class":"forecasting.ForecasterClass",
    "children": [
        __functioncontrolfolder,
        {"name":"output","type":"folder"},
        {"name":"widget","type":"referencer"},          #pointing to the widget where the forecaster is used
        {
            "name":"scoreAnnotation",
            "type":"function",
            "functionPointer": "forecasting.score_annotation",  # filename.functionname
            "autoReload": False,  # set this to true to reload the module on each execution
            "children":[__functioncontrolfolder],
        },

        {
            "name":"observerVariables",
            "type":"observer",
            "children":[
                {"name": "enabled", "type": "const", "value": False},           # turn on/off the observer
                {"name": "triggerCounter","type":"variable","value":0},         #  increased on each trigger
                {"name": "lastTriggerTime","type":"variable","value":""},       #  last datetime when it was triggered
                {"name": "targets","type":"referencer"},                        #  pointing to the nodes observed
                {"name": "properties","type":"const","value":["forwardRefs"]},        #  properties to observe [“children”,“value”, “forwardRefs”]
                {"name": "onTriggerFunction","type":"referencer","references":["Forecaster.syncUi"]},              #  the function(s) to be called when triggering
                {"name": "triggerSourceId","type":"variable"},                  #  the sourceId of the node which caused the observer to trigger
                {"name": "hasEvent","type":"const","value":False},              # set to event string iftrue if we want an event as well
                {"name": "eventString","type":"const","value":"observerdefaultevent"},              # the string of the event
                {"name": "eventData","type":"const","value":{"text":"observer status update"}}      # the value-dict will be part of the SSE event["data"] , the key "text": , this will appear on the page,
            ]
        },
        {
            "name":"observerContextMenu",
            "type":"observer",
            "children":[
                {"name": "enabled", "type": "const", "value": False},           # turn on/off the observer
                {"name": "triggerCounter","type":"variable","value":0},         #  increased on each trigger
                {"name": "lastTriggerTime","type":"variable","value":""},       #  last datetime when it was triggered
                {"name": "targets","type":"referencer"},                        #  pointing to the nodes observed
                {"name": "properties","type":"const","value":["value"]},        #  properties to observe [“children”,“value”, “forwardRefs”]
                {"name": "onTriggerFunction","type":"referencer","references":["Forecaster.syncUi"]},              #  the function(s) to be called when triggering
                {"name": "triggerSourceId","type":"variable"},                  #  the sourceId of the node which caused the observer to trigger
                {"name": "hasEvent","type":"const","value":False},              # set to event string iftrue if we want an event as well
                {"name": "eventString","type":"const","value":"observerdefaultevent"},              # the string of the event
                {"name": "eventData","type":"const","value":{"text":"observer status update"}}      # the value-dict will be part of the SSE event["data"] , the key "text": , this will appear on the page,
            ]
        },
        {
            "name":"syncUi",
            "type":"function",
            "functionPointer": "forecasting.sync_ui",  # filename.functionname
            "autoReload": False,  # set this to true to reload the module on each execution
            "children":[__functioncontrolfolder],
        },
    ]
}


def score_annotation(functionNode):
    logger = functionNode.get_logger()
    return True


def sync_ui(functionNode):
    logger = functionNode.get_logger()
    #check the current selected setting by comparing against the last selection in self.contextStatus


    objectNode = functionNode.get_parent()
    object = objectNode.get_object()
    #check for deleted entries

    old = object.lastShowHide
    new = object.showHide.get_value()
    selectedVarsNode = objectNode.get_child("widget").get_target().get_child("selectedVariables")

    for k,v in new.items():
        if v == True and old[k] == False:
            #this is a "turn on"
            #add all timeseries to the widget
            logger.debug(f"show forecasting nodes of {k}")
            forecastingNodes = functionNode.get_parent().get_child("output").get_child(k).get_children() # alist of nodes (the min, max, expected and scores)
            selectedVarsNode.add_references(forecastingNodes,allowDuplicates=False)

        if v == False and old[k] == True:
            #this is a "turn off"
            logger.debug(f"hide forecasting nodes of {k}")
            forecastingNodes = functionNode.get_parent().get_child("output").get_child(k).get_children()  # alist of nodes (the min, max, expected and scores)
            selectedVarsNode.del_references(forecastingNodes)

    object.lastShowHide = new
    return True


class ForecasterClass(streaming.Interface):
    """
    this class creates alarm messages when scores of variables trigger
    """
    def __init__(self, objectNode):
        self.objectNode = objectNode
        self.model = objectNode.get_model()
        self.logger = objectNode.get_logger()
        self.showHide = None #the showHide node of the widget


    def reset(self, data):
        # 1. create all out variables if needed
        # 2. mark the created scores as score variables in the widget
        # 3. create the showHide entry in the widget context menu
        # 4. setup the observer right

        #1.create the outputs if needed
        widget = self.objectNode.get_child("widget").get_target()
        self.widget = widget
        if not widget: return #not yet hooked correctly

        scoreVars = []
        submenuName = "anomalyForecast"

        #!!! FAKE Implementation, later: the deep learning model should know which variables it can score and create the outputs accordingly
        vars = widget.get_child("selectableVariables").get_leaves()
        for var in vars:
            folder = self.objectNode.get_child("output").create_child(var.get_name())
            folder.create_child(var.get_name() + "_limitMax",properties={"type":"timeseries"})
            folder.create_child(var.get_name() + "_limitMin", properties={"type": "timeseries"})
            folder.create_child(var.get_name() + "_expected", properties={"type": "timeseries"})
            scoreVars.append(folder.create_child(var.get_name() + "_anomalyScore", properties={"type": "timeseries","uiInfo":{"marker":"x"}}))


        #2. mark the created scores as score variables in the widget
        widget.get_child("scoreVariables").add_references(scoreVars,deleteAll=False,allowDuplicates=False)

        # 3. create the showHide entry in the widget context menu
        # and put all the switchable variables in
        showHide = widget.create_child("showHide")
        self.showHide = showHide.create_child(submenuName)
        self.showHide.set_value({v.get_name():False for v in vars}) #initially all are disabled

        # 4. setup the observer right
        self.objectNode.get_child("observerVariables.enabled").set_value(False)
        self.objectNode.get_child("observerContextMenu.enabled").set_value(False)
        self.objectNode.get_child("observerVariables.targets").add_references(widget.get_child("selectedVariables"),deleteAll=True)
        self.objectNode.get_child("observerContextMenu.targets").add_references(widget.get_child("showHide."+submenuName), deleteAll=True)
        self.objectNode.get_child("observerVariables.enabled").set_value(False) #for future use: we make a clever selection of the possible entries
        self.objectNode.get_child("observerContextMenu.enabled").set_value(True)

        self.lastShowHide = self.showHide.get_value() #remember this for later comparison



        pass

    def feed(self, blob=None):
        return blob


    def flush(self, blob=None):
        return blob
