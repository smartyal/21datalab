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
        {"name":"selectableVariables","type":"referencer"},
        {"name":"selectedVariables","type":"referencer"},
        {"name":"startTime","type":"variable"},
        {"name":"endTime","type":"variable"},
        {"name":"bins","type":"const","value":300},
        {"name":"hasAnnotation","type":"const","value":True,"children":[
                 {"name":"annotations","type":"referencer","references":["timeseriesWidget.hasAnnotation.newAnnotations"]},
                 {"name":"newAnnotations","type":"folder"},
                 {"name":"tags","type":"const","value":["one","two"]},
                 {"name":"colors","type":"const","value":["yellow","brown","grey","green","red"]},
            ]
        },
        {"name":"table","type":"referencer"},
        {"name":"lineColors","type": "const", "value": ["blue", "yellow", "brown", "grey", "red"]},
        {"name":"observer","type":"referencer"},
        {"name":"observerUpdate","type": "const","value":["line","background","annotations"]},
        {"name":"buttons","type":"folder","children":[
            {"name":"button1","type":"folder"}
        ]},
        {"name":"hasBackground","type": "const", "value": True},
        {"name":"background","type":"referencer"},
        {"name":"backgroundMap","type": "const", "value": {"1": "yellow", "0": "brown", "-1": "blue", "default": "white"}},
        {"name":"hasReloadButton","type":"const","value":True}
    ]
}
