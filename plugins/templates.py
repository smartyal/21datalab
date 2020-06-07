# this file contains templates which are imported into the model under the templates


button = {
    "name": "button",
    "type": "folder",
    "children": [
        {"name": "caption", "type": "const", "value": "mycaption"},
        {"name": "counter", "type": "variable", "value": 0},
        {"name": "onClick", "type": "referencer"}
    ]
}



timeseriesWidget = {
    "name": "timeseriesWidget",
    "type": "widget",
    "children":
    [
        {"name":"widgetType","type":"const","value":"timeSeriesWidget"},        #the type of the widget, this is used by the backend to choose the right service to run
        {"name":"selectableVariables","type":"referencer"},                     # the variables to appear in the select box
        {"name":"selectedVariables","type":"referencer"},                       # the currently selected variables to be shown in the plot
        {"name":"hasSelection","type":"const","value":True},                    # show/hide the variable selection area selectbox
        {"name":"startTime","type":"variable"},                                 # the current start time of the view zoom
        {"name":"endTime","type":"variable"},                                   # the current end time of the view zoom
        {"name":"bins","type":"const","value":300},                             # the bins (number of points) used on the screen on the x-axis
        {"name":"hasAnnotation","type":"const","value":True,"children":[        # show/hide annotations and annotations buttons
                 {"name":"annotations","type":"referencer","references":[       # the locations where to find annotations
                     "timeseriesWidget.hasAnnotation.newAnnotations"]},
                 {"name":"newAnnotations","type":"folder"},                     # the folder where annotations created by the users are put
                 {"name":"tags","type":"const","value":["one","two"]},          # the tags available for annotations
                 {"name":"colors","type":"const","value":["yellow","brown","grey","green","red"]}, # the colors for annotations, can also be a dict with {"tag":{"color":"color","pattern":patter"},"tag2":{..}}
                 {"name":"selectedAnnotations","type":"referencer"},            # the currently selected annotation(s)
                 {"name":"visibleTags","type":"variable","value":{
                     "one":True,"two":True,"region":True}}                      # a dict holding info which tags of annotations are currently visible
            ]
        },
        {"name":"table","type":"referencer"},                                   # the data table where the time series data resides to be used in this widget (it must be only one)
        {"name":"lineColors","type": "const", "value": [
            "blue", "yellow", "brown", "grey", "red"]},                         # colors of the lines
        {"name":"buttons","type":"folder"},                                     # user buttons, place buttons-templates here
        {"name":"hasBackground","type": "const", "value": True},                # use background coloring or not
        {"name":"background","type":"referencer"},                              # the location of the background column (must be part of the table as well)
        {"name":"backgroundMap","type": "const", "value": {
            "1": "yellow", "0": "brown", "-1": "blue", "default": "white"}},    # color map for the background
        {"name":"hasReloadButton","type":"const","value":True},                 # show/hide the reload button (show is only for dev-mode)
        {"name":"hasHover","type":"const","value":False},                       # show/hide the hover-tool of [False, 'mouse','vline','hline'
        {"name":"width","type":"const","value":900},                            # the display width of the plot in pixel
        {"name":"height","type":"const","value":600},                           # the display height of the plot in pixel
        {"name":"controlPosition","type":"const","value":"right"}  ,            # the position of the button controls of ["bottom","right]
        {"name":"timeZone","type":"const","value":"Europe/Berlin"},             # the timezone of the display
        {"name":"hasThreshold","type":"const","value":False},                   # horizontal thresholds (min/max) are supported for the annotations
        {"name":"hasStreaming", "type": "const", "value": False},               # horizontal thresholds (min/max) are supported for the annotations
        {"name":"scoreVariables", "type": "referencer"},                        # pointing to variables which are scores, (they are rendered with markers)
        {"name": "scoreMap", "type": "const","value":{                          # color map for score markers
            "0": "green", "1": "red", "default": "blue"}},
        {"name": "theme", "type": "const", "value": "dark"},                    # the theme color

        {"name":"observerVariables","type": "observer", "children": [           # observer for the selected variables (not the values)
            {"name": "enabled", "type": "const", "value": True},                # on by default to enable drag + drop
            {"name": "triggerCounter", "type": "variable", "value": 0},         # increased on each trigger
            {"name": "lastTriggerTime", "type": "variable", "value": ""},       # last datetime when it was triggered
            {"name": "targets", "type": "referencer", "references":["timeseriesWidget.selectedVariables"]},  # pointing to the nodes observed
            {"name": "properties", "type": "const", "value": ["forwardRefs"]},  # properties to observe [“children”,“value”, “forwardRefs”]
            {"name": "onTriggerFunction", "type": "referencer"},                # the function(s) to be called when triggering
            {"name": "hasEvent", "type": "const", "value": True},               # set to true if we want an event as well
            {"name": "eventString", "type": "const", "value": "timeSeriesWidget.variables"}  # the string of the event
            ]
        },
        {"name": "observerBack", "type": "observer", "children": [              # observer for the change of the background value
            {"name": "enabled", "type": "const", "value": False},                # turn on/off the observer
            {"name": "triggerCounter", "type": "variable", "value": 0},         # increased on each trigger
            {"name": "lastTriggerTime", "type": "variable", "value": ""},       # last datetime when it was triggered
            {"name": "targets", "type": "referencer","references":["timeseriesWidget.background"]},                          # pointing to the nodes observed, must be set correctly, typically the execution counter of the function
            {"name": "properties", "type": "const", "value": ["value"]},        # properties to observe [“children”,“value”, “forwardRefs”]
            {"name": "onTriggerFunction", "type": "referencer"},                # the function(s) to be called when triggering
            {"name": "hasEvent", "type": "const", "value": True},               # set to true if we want an event as well
            {"name": "eventString", "type": "const", "value": "timeSeriesWidget.background"}  # the string of the event
            ]
        },
        {"name": "observerStream", "type": "observer", "children": [            # observer for the value change of selected vars (especialy for streaming)
            {"name": "enabled", "type": "const", "value": False},                # turn on/off the observer
            {"name": "triggerCounter", "type": "variable", "value": 0},         # increased on each trigger
            {"name": "lastTriggerTime", "type": "variable", "value": ""},       # last datetime when it was triggered
            {"name": "targets", "type": "referencer","references":["timeseriesWidget.selectableVariables"]},    # pointing to the all nodes,
            {"name": "properties", "type": "const", "value": ["value"]},        # look for value change properties to observe [“children”,“value”, “forwardRefs”]
            {"name": "onTriggerFunction", "type": "referencer"},                # the function(s) to be called when triggering
            {"name": "hasEvent", "type": "const", "value": True},               # set to true if we want an event as well
            {"name": "eventString", "type": "const", "value": "timeSeriesWidget.stream"}  # the string of the event
            ]
        },
        {"name":"visibleElements","type":"variable","value":{                   # which elements of the widget are currently visible
            "thresholds":True,
            "annotations":True,
            "scores":True,
            "background":True,
            "variables":True
            }
        },
        {"name":"contextMenuFunctions","type":"referencer"},                    # pointing to functions which should be displayed and callable from context menu
        {"name": "observerAnnotations", "type": "observer", "children": [       # observer for the value change of selected vars (especialy for streaming)
            {"name": "enabled", "type": "const", "value": True},                # turn on/off the observer
            {"name": "triggerCounter", "type": "variable", "value": 0},         # increased on each trigger
            {"name": "lastTriggerTime", "type": "variable", "value": ""},       # last datetime when it was triggered
            {"name": "targets", "type": "referencer","references":["timeseriesWidget.hasAnnotation.annotations"]},    # pointing to the all nodes,
            {"name": "properties", "type": "const", "value": ["children","value"]},        # look for value change properties to observe [“children”,“value”, “forwardRefs”]
            {"name": "onTriggerFunction", "type": "referencer"},                # the function(s) to be called when triggering
            {"name": "hasEvent", "type": "const", "value": True},               # set to true if we want an event as well
            {"name": "eventString", "type": "const", "value": "timeSeriesWidget.annotations"}  # the string of the event
            ]
        },
        {"name": "observerVisibleElements", "type": "observer", "children": [   # observer for the value change of selected vars (especialy for streaming)
            {"name": "enabled", "type": "const", "value": True},                # turn on/off the observer
            {"name": "triggerCounter", "type": "variable", "value": 0},         # increased on each trigger
            {"name": "lastTriggerTime", "type": "variable", "value": ""},       # last datetime when it was triggered
            {"name": "targets", "type": "referencer","references":[
                "timeseriesWidget.visibleElements",
                "timeseriesWidget.hasAnnotation.visibleTags",
                "timeseriesWidget.autoScaleY"
                ]
            },
            {"name": "properties", "type": "const", "value": ["value"]},        # look for value change properties to observe [“children”,“value”, “forwardRefs”]
            {"name": "onTriggerFunction", "type": "referencer"},                # the function(s) to be called when triggering
            {"name": "hasEvent", "type": "const", "value": True},               # set to true if we want an event as well
            {"name": "eventString", "type": "const", "value": "timeSeriesWidget.visibleElements"}  # the string of the event
            ]
        },
        {"name": "nextNewAnnotation", "type": "variable", "value":{}},          # the value must be a dict like {"type":"time","tag":"one"}
        {"name": "observerNewAnnotation", "type": "observer", "children": [     # observer for the value change of selected vars (especialy for streaming)
             {"name": "enabled", "type": "const", "value": True},              # turn on/off the observer
             {"name": "triggerCounter", "type": "variable", "value": 0},        # increased on each trigger
             {"name": "lastTriggerTime", "type": "variable", "value": ""},      # last datetime when it was triggered
             {"name": "targets", "type": "referencer", "references": ["timeseriesWidget.nextNewAnnotation"]},
             {"name": "properties", "type": "const", "value": ["value"]},
             {"name": "onTriggerFunction", "type": "referencer"},               # the function(s) to be called when triggering
             {"name": "hasEvent", "type": "const", "value": True},              # set to true if we want an event as well
             {"name": "eventString", "type": "const", "value": "timeSeriesWidget.newAnnotation"}  # the string of the event
            ]
        },
        {"name": "currentColors", "type": "variable", "value":{"entry":{"lineColor":"red"}}},   #put the current colors here
        {"name": "autoScaleY", "type": "variable", "value":True},                   # turn y axis autoscale on/off during runtime
        {"name": "panOnlyX","type":"const","value":False},                              # if this is set true, the pan and wheel zoom only zooms in x-direction
        {"name": "streamingMode","type":"const","value":False},                       # if this is set true, the pan and wheel zoom only zooms in x-direction
        {"name": "showMarker","type":"const","value":False},
        {"name": "contextMenuSettings","type":"folder"},                         # configure here the "settings" submenu of the context menu: each child should be a referencer pointing to a bool variable
                                                                                # the entry displayed in the context menu will be the name of the referencder
        {"name": "contextMenuPipelines","type":"referencer"},
        {"name":"showLegend","type":"const","value":True}


    ]
}
