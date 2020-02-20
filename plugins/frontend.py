#21datalabplugin

from system import __functioncontrolfolder


multiwidgetSyncer= {
    "name":"tsWidgetSync",
    "type":"function",
    "functionPointer":"frontend.widget_sync",                   #filename.functionname
    "autoReload":True,                                          #set this to true to reload the module on each execution
    "children":[
        {"name":"widgets","type":"referencer"},                #logistic regression work on categories, this is the number mapper, INPUT
        __functioncontrolfolder
    ]
}




def widget_sync(functionNode):
    logger = functionNode.get_logger()

    #first, get the observer Node which is pointing to me
    model = functionNode.get_model()
    referencers = model.get_referencers(functionNode.get_id()) #look back through the backrefs

    source = None
    for id in referencers:
        if model.get_node_info(id)["name"] == "onTriggerFunction":
            #we assume this is the observer pointing to us
            observer = model.get_node(id).get_parent()
            sourceId = observer.get_child("triggerSourceId").get_value()
            source = model.get_node(sourceId)
            break

    if source:
        sourceWidget = source.get_parent()
        start = sourceWidget.get_child("startTime").get_value()
        end = sourceWidget.get_child("endTime").get_value()

        observer.get_child("enabled").set_value(False) # avoid retrigger
        for widget in functionNode.get_child("widgets").get_leaves():
            observer.get_child("enabled").set_value(False)
            if widget.get_id() != sourceWidget.get_id():
                widget.get_child("startTime").set_value(start)
                widget.get_child("endTime").set_value(end)

        observer.get_child("enabled").set_value(True)



