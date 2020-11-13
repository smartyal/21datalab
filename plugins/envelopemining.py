#21datalabplugin

import time
import copy
from system import __functioncontrolfolder
import dates
import numpy


# use a list to avoid loading of this in the model as template
mycontrol = [copy.deepcopy(__functioncontrolfolder)]
mycontrol[0]["children"][-1]["value"]="threaded"


envelopeMinerTemplate = {
    "name": "EnvelopeMiner",
    "type": "folder",
    "children":[
        {
            "name": "EnvelopeMiner",
            "type": "function",
            "functionPointer": "envelopemining.envelope_miner",  # filename.functionname
            "autoReload": True,  # set this to true to reload the module on each execution
            "children": [
                {"name": "motif", "type": "referencer"},        # the one motif we are using
                {"name": "widget","type":"referencer"} ,        # the widget to which this miner belongs which is used (to find the selected motif
                {"name": "annotations","type":"folder"},        # the results
                {"name": "results","type":"variable"},
                mycontrol[0]
            ]
        },
        {
            "name": "create",
            "type": "function",
            "functionPointer": "envelopemining.create",  # filename.functionname
            "autoReload": True,  # set this to true to reload the module on each execution
            "children": [
                mycontrol[0]
            ]
        },
        {
            "name": "update",
            "type": "function",
            "functionPointer": "envelopemining.update",  # filename.functionname
            "autoReload": True,  # set this to true to reload the module on each execution
            "children": [
                mycontrol[0]
            ]
        },
        {
            "name": "show",
            "type": "function",
            "functionPointer": "envelopemining.show",  # filename.functionname
            "autoReload": True,  # set this to true to reload the module on each execution
            "children": [
                mycontrol[0]
            ]
        },
        {
            "name": "hide",
            "type": "function",
            "functionPointer": "envelopemining.hide",  # filename.functionname
            "autoReload": True,  # set this to true to reload the module on each execution
            "children": [
                mycontrol[0]
            ]
        },
        {
            "name": "select",
            "type": "function",
            "functionPointer": "envelopemining.select",  # filename.functionname
            "autoReload": True,  # set this to true to reload the module on each execution
            "children": [
                mycontrol[0]
            ]
        },
        {
            "name": "delete",
            "type": "function",
            "functionPointer": "envelopemining.delete",  # filename.functionname
            "autoReload": True,  # set this to true to reload the module on each execution
            "children": [
                mycontrol[0]
            ]
        },
        {
            "name": "recreate",
            "type": "function",
            "functionPointer": "envelopemining.recreate",  # filename.functionname
            "autoReload": True,  # set this to true to reload the module on each execution
            "children": [
                mycontrol[0]
            ]
        },
        {
            "name": "progress",
            "type": "observer",
            "children": [
                {"name": "enabled", "type": "const", "value": True},  # turn on/off the observer
                {"name": "triggerCounter", "type": "variable", "value": 0},  # increased on each trigger
                {"name": "lastTriggerTime", "type": "variable", "value": ""},  # last datetime when it was triggered
                {"name": "targets", "type": "referencer","references":["EnvelopeMiner.EnvelopeMiner.control.progress"]},  # pointing to the nodes observed
                {"name": "properties", "type": "const", "value": ["value"]},
                # properties to observe [“children”,“value”, “forwardRefs”]
                {"name": "onTriggerFunction", "type": "referencer"},  # the function(s) to be called when triggering
                {"name": "triggerSourceId", "type": "variable"},
                # the sourceId of the node which caused the observer to trigger
                {"name": "hasEvent", "type": "const", "value": True},
                # set to event string iftrue if we want an event as well
                {"name": "eventString", "type": "const", "value": "envelopemining.progress"},  # the string of the event
                {"name": "eventData", "type": "const", "value": {"text": "observer status update"}}
                # the value-dict will be part of the SSE event["data"] , the key "text": , this will appear on the page,
            ]
        },

        {"name":"defaultParameters","type":"const","value":{"filter":[0,20,2],"samplingPeriod":[1,60,10],"freedom":[0,1,0.5],"dynamicFreedom":[0,1,0.5],"numberSamples":[1,100,1],"step":[1,100,1]}}, # the default contain each three values: min,max,default
        {"name": "cockpit", "type": "const", "value": "/customui/envelopeminer.htm"}  #the cockpit for the motif miner
    ]
}




def envelope_miner(functionNode):

    logger = functionNode.get_logger()
    signal = functionNode.get_child("control.signal")
    logger.info("==>>>> in envelope_miner " + functionNode.get_browse_path())
    progressNode = functionNode.get_child("control").get_child("progress")
    functionNode.get_child("results").set_value([])
    progressNode.set_value(0)
    signal.set_value(None)
    total = 15
    for i in range(total):
        time.sleep(1)
        progressNode.set_value(float(i)/total)
        if signal.get_value()=="stop":
            break

    functionNode.get_child("results").set_value([{"time":"1234","match":1.2},{"time":"1235","match":1.6}])
    progressNode.set_value(1)
    return True


def create(functionNode):
    hide(functionNode) # if any is already visible, hide it

    logger = functionNode.get_logger()
    logger.debug("create_envelope()")
    motif = functionNode.get_parent().get_child("EnvelopeMiner").get_child("motif").get_target()
    widget = functionNode.get_parent().get_child("EnvelopeMiner").get_child("widget").get_target()
    name = motif.get_child("variable").get_target().get_name()
    defaults = functionNode.get_parent().get_child("defaultParameters").get_value()
    if motif and widget:
        envelope = motif.create_child("envelope",type="folder")
        envelope.create_child(name+"_limitMax",type="timeseries")
        envelope.create_child(name+"_limitMin",type="timeseries")
        envelope.create_child(name+"_expected",type="timeseries")
        for k,v in defaults.items():#["samplingPeriod","filter","freedom","dynamicFreedom"]:
            envelope.create_child(k,type="const",value=v[2],properties={"validation":{"limits":[v[0],v[1]]}})
        if not _connect(motif,widget):
            logger.error("can't connect motif envelope to widget")
        #also

    #override the value with better values
    #e.g the sampling period we take the average that we have and make 10 steps to the 10 times sampling rate


    #call update from here
    updateNode = functionNode.get_parent().get_child("update")
    update(updateNode)

    return True


"""
def _update_envelope(motif,widget):
    fil = motif.get_child("envelope.filter")
    sample = motif.get_child("envelope.samplingPeriod")
    lMax = None
    lMin = None
    exPe = None
    children = motif.get_children()
    for child in motif.get_children():
        if "_limitMax" in child.get_name():
            lMax = child
        elif "_limitMin" in child.get_name():
            lMin = child
        elif "_expected" in child.get_name():
            exPe = child

    #now create upper and lower
"""



def update(functionNode):
    motif = functionNode.get_parent().get_child("EnvelopeMiner").get_child("motif").get_target()
    widget = functionNode.get_parent().get_child("EnvelopeMiner").get_child("widget").get_target()
    #fil = motif.get_child("envelopeFilter")
    #sample = motif.get_child("envelopeSamplingPeriod")

    lMax = None
    lMin = None
    exPe = None
    #children = motif.get_get_children()
    for child in motif.get_child("envelope").get_children():
        if "_limitMax" in child.get_name():
            lMax = child
        elif "_limitMin" in child.get_name():
            lMin = child
        elif "_expected" in child.get_name():
            exPe = child


    #now get the data and write the new envelope
    start = dates.date2secs(motif.get_child("startTime").get_value())
    end = dates.date2secs(motif.get_child("endTime").get_value())
    period =  motif.get_child("envelope.samplingPeriod").get_value()
    times = numpy.arange(start,end,period)

    ts = motif.get_child("variable").get_target().get_time_series(start,end,resampleTimes = times)
    freedom = motif.get_child("envelope.freedom").get_value()
    dynFreedom = motif.get_child("envelope.dynamicFreedom").get_value()

    data = ts["values"]
    diff = max(data)-min(data)
    upper = data+diff*freedom
    lower = data-diff*freedom
    expect = data
    #xxx todo dynamic freedom


    numberSamples = len(times)
    motif.get_child("envelope.numberSamples").set_value(numberSamples) # the number of samples
    #also set the possible step size
    step = motif.get_child("envelope.step").get_value()
    if step > numberSamples:
        step = numberSamples
    #also set the limits
    motif.get_child("envelope.step").set_properties({"value":step,"validation":{"limits":[1,numberSamples]}})


    if lMax:
        lMax.set_time_series(upper,times)
    if lMin:
        lMin.set_time_series(lower,times)
    if exPe:
        exPe.set_time_series(expect,times)

    return True

def show(functionNode):
    motif = functionNode.get_parent().get_child("EnvelopeMiner").get_child("motif").get_target()
    widget = functionNode.get_parent().get_child("EnvelopeMiner").get_child("widget").get_target()
    return _connect(motif,widget)

def hide(functionNode):
    motif = functionNode.get_parent().get_child("EnvelopeMiner").get_child("motif").get_target()
    widget = functionNode.get_parent().get_child("EnvelopeMiner").get_child("widget").get_target()
    return _connect(motif,widget,False)

def delete(functionNode):
    hide(functionNode)
    motif = functionNode.get_parent().get_child("EnvelopeMiner").get_child("motif").get_target()
    motif.get_child("envelope").delete()
    #remove all envelope info from the motif

def recreate(functionNode):
    delete(functionNode)
    return create(functionNode)



def select(functionNode):
    logger = functionNode.get_logger()
    widget = functionNode.get_parent().get_child("EnvelopeMiner").get_child("widget").get_target()
    newMotif = widget.get_child("hasAnnotation").get_child("selectedAnnotations").get_target()
    if not newMotif:
        logger.error("no new motif given")
        return False
    motifPointer = functionNode.get_parent().get_child("EnvelopeMiner").get_child("motif")
    if motifPointer.get_target():
        hide(functionNode)
    motifPointer.add_references(newMotif,deleteAll=True)

    return True


def _connect(motif,widget,connect=True):
    """
        we expect to find min and max, expected is optional
        connect = True for connect, False for disconnect
    """
    if not motif or not widget:
        return False
    try:
        lMax = None
        lMin = None
        exPe = None
        #children = motif.get_children()
        for child in motif.get_child("envelope").get_children():
            if "_limitMax" in child.get_name():
                lMax = child
            elif "_limitMin" in child.get_name():
                lMin = child
            elif "_expected" in child.get_name():
                exPe = child
        if connect:
            if lMax and lMin:
                if exPe:
                    widget.get_child("selectedVariables").add_references([exPe,lMin,lMax],allowDuplicates=False)
                else:
                    widget.get_child("selectedVariables").add_references([lMin, lMax],allowDuplicates=False)
        else:
            #disconnect
            elems = [elem for elem in [lMin,lMax,exPe] if elem] #remove the nones
            if elems:
                widget.get_child("selectedVariables").del_references(elems)
        return True
    except Exception as ex:
        import traceback
        print(traceback.format_exc())
        return False