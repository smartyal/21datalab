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
                 {"name":"colors","type":"const","value":["yellow","brown","grey","green","red"]}, # the colors for annotations
            ]
        },
        {"name":"table","type":"referencer"},                                   # the data table where the time series data resides to be used in this widget (it must be only one)
        {"name":"lineColors","type": "const", "value": [
            "blue", "yellow", "brown", "grey", "red"]},                         # colors of the lines
        {"name":"observerBackground","type":"referencer"},                      # the location of the variable to watch to find out the change of the background (typically a function execution counter)
        {"name":"observerUpdate","type": "const","value":["variables","background"]}, #content to be watched by the observer, select from ["variables", "background"]
        {"name":"observerEnabled","type":"const","value":True},                 # enable/disable the observer
        {"name":"buttons","type":"folder"},                                     # user buttons, place buttons-templates here
        {"name":"hasBackground","type": "const", "value": True},                # use background coloring or not
        {"name":"background","type":"referencer"},                              # the location of the background column (must be part of the table as well)
        {"name":"backgroundMap","type": "const", "value": {
            "1": "yellow", "0": "brown", "-1": "blue", "default": "white"}},    # color map for the background
        {"name":"hasReloadButton","type":"const","value":True},                 # show/hide the reload button (show is only for dev-mode)
        {"name":"hasHover","type":"const","value":False}                        # show/hide the hover-tool of [False, 'mouse','vline','hline'
    ]
}
