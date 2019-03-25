import numpy

timeseriesWidget = [
    {"name":"selectableVariables","type":"referencer"},
    {"name":"selectedVariables","type":"referencer"},
    {"name":"startTime","type":"variable"},
    {"name":"endTime","type":"variable"},
    {"name":"bins","type":"const","value":300},
    {"name":"hasAnnotation","type":"const","value":True,"children":[
             {"name":"annotations","type":"referencer"},
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
    {"name":"backgroundMap","type": "const", "value": {"1": "yellow", "0": "brown", "-1": "blue", "default": "white"}}
]

button=[
    {"name":"caption","type":"const","value":"learn"},
    {"name":"counter","type":"variable"},
    {"name":"onClick","type":"referencer"}]

dataTable = [
    {
        "name": "description",
        "type": "const",
        "value": "this is a table generated from the template"
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
    },
    {
        "name":"variables",
        "type":"folder"
    },
    {
        "name":"time",
        "type":"column",
        "value":[]
    }
]


def create_table(model,newTablePath="root.newTable",variableNames=["var1","var2"]):
    model.create_node_from_path(newTablePath, {"type": "table"})
    model.create_nodes_from_template(newTablePath, template=dataTable)
    for var in variableNames:
        variablePath = newTablePath+'.variables.'+var
        #model.create_node_from_path(variablePath,{"type":"column","value":numpy.empty([0],dtype=numpy.float64)})
        model.create_node_from_path(variablePath, {"type": "column", "value": None})
        model.add_forward_refs(newTablePath+'.columns',[variablePath])
    model.add_forward_refs(newTablePath+'.timeField',[newTablePath+'.time'])
    model.add_forward_refs(newTablePath+'.columns', [newTablePath + '.time'])


def create_ts_visu_for_table(model,tablePath="root.newTable",visuPath="root.visu"):
    """
        adds a stardard ts visu for an existing table, makes all the hooks right
        no background, no buttons, all variables selectable, first variable selected
    """
    # create another TS-widget
    model.create_node_from_path(visuPath, {"type": "widget"})
    model.create_nodes_from_template(visuPath,timeseriesWidget)
    model.delete_node(visuPath+'.buttons.button1')
    leaves = model.get_leaves_ids(tablePath+'.columns')
    model.add_forward_refs(visuPath+'.selectedVariables',[leaves[0]])
    model.add_forward_refs(visuPath+'.selectableVariables',[tablePath+'.columns'])
    model.add_forward_refs(visuPath+'.table', [tablePath])
    model.set_value(visuPath+".hasBackground",False)