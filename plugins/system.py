import datetime
import time
import json
import copy
import dates
from model import getRandomId

__functioncontrolfolder = {
    "name":"control","type":"folder","children":[
        {"name":"status","type":"variable","value":"idle"},                 # one of ["finished","running"]
        {"name":"progress","type":"variable","value":0},                    # a value between 0 and 1 ( for showing progress in the ui
        {"name":"result","type":"variable","value":"ok"},                   # of ["ok","error","pending" or a last error message]
        {"name":"signal","type":"variable","value":"nosignal"},             # of ["nosignal","interrupt"]
        {"name":"executionCounter","type":"variable","value":0},            # a counter which is increased on each execution of this function
        {"name":"lastExecutionDuration", "type": "variable", "value": 0},   #in float seconds
        {"name":"lastStartTime","type":"variable","value":"not yet"},       # in isoforma-string
        {"name":"executionCounter","type":"variable","value":0},            # increases on each SUCESSFUL completion
        {"name":"executionType","type":"const","value":"async"}             # one of ["sync", "async"] sync: is executed on the main server thread, async: in separate thread
    ]
}
__functioncontrolfolder_threaded = {
    "name":"control","type":"folder","children":[
        {"name":"status","type":"variable","value":"idle"},                 # one of ["finished","running"]
        {"name":"progress","type":"variable","value":0},                    # a value between 0 and 1 ( for showing progress in the ui
        {"name":"result","type":"variable","value":"ok"},                   # of ["ok","error","pending" or a last error message]
        {"name":"signal","type":"variable","value":"nosignal"},             # of ["nosignal","interrupt"]
        {"name":"executionCounter","type":"variable","value":0},            # a counter which is increased on each execution of this function
        {"name":"lastExecutionDuration", "type": "variable", "value": 0},   #in float seconds
        {"name":"lastStartTime","type":"variable","value":"not yet"},       # in isoforma-string
        {"name":"executionCounter","type":"variable","value":0},            # increases on each SUCESSFUL completion
        {"name":"executionType","type":"const","value":"threaded"}             # one of ["sync", "async"] sync: is executed on the main server thread, async: in separate thread
    ]
}

"""
systemFolder = {
    {"name":"system","type":"folder","children":[
        {"name":"enableTreeUpdateEvents","type":"const","value":True},
        {"name":"enableAutoReload","type":"const","value":True},
        {"name": "progress", "type": "observer", "children": [
            {"name": "enabled", "type": "const", "value": True},  # turn on/off the observer
            {"name": "triggerCounter", "type": "variable", "value": 0},  # increased on each trigger
            {"name": "lastTriggerTime", "type": "variable", "value": ""},  # last datetime when it was triggered
            {"name": "targets", "type": "referencer"},  # pointing to the nodes observed
            {"name": "properties", "type": "const", "value": ["value"]},
            {"name": "onTriggerFunction", "type": "referencer"},  # the function(s) to be called when triggering
            {"name": "triggerSourceId", "type": "variable"},
            {"name": "hasEvent", "type": "const", "value": True},
            {"name": "eventString", "type": "const", "value": "system.progress"},  # the string of the event
            {"name": "eventData", "type": "const", "value": {"text": ""}}
            ]
        },
        {"name": "streaming", "type": "observer", "children": [
            {"name": "enabled", "type": "const", "value": True},  # turn on/off the observer
            {"name": "triggerCounter", "type": "variable", "value": 0},  # increased on each trigger
            {"name": "lastTriggerTime", "type": "variable", "value": ""},  # last datetime when it was triggered
            {"name": "targets", "type": "referencer","references":["system.timeSeriesValues.targets","system.timeSeriesEvents.targets"]},  # pointing to the nodes observed
            {"name": "properties", "type": "const", "value": ["stream"]},
            {"name": "onTriggerFunction", "type": "referencer"},  # the function(s) to be called when triggering
            {"name": "triggerSourceId", "type": "variable"},
            {"name": "hasEvent", "type": "const", "value": True},
            {"name": "eventString", "type": "const", "value": "global.series.stream"},  # the string of the event
            {"name": "eventData", "type": "const", "value": {"text": ""}}
            ]
        },
        {"name": "annotations", "type": "observer", "children": [
            {"name": "enabled", "type": "const", "value": True},  # turn on/off the observer
            {"name": "triggerCounter", "type": "variable", "value": 0},  # increased on each trigger
            {"name": "lastTriggerTime", "type": "variable", "value": ""},  # last datetime when it was triggered
            {"name": "targets", "type": "referencer"},
            {"name": "properties", "type": "const", "value": ["value","children"]},
            {"name": "onTriggerFunction", "type": "referencer"},  # the function(s) to be called when triggering
            {"name": "triggerSourceId", "type": "variable"},
            {"name": "hasEvent", "type": "const", "value": True},
            {"name": "eventString", "type": "const", "value": "global.annotations"},  # the string of the event
            {"name": "eventData", "type": "const", "value": {"text": ""}}
            ]
         },
        {"name": "timeSeriesValues", "type": "observer", "children": [
            {"name": "enabled", "type": "const", "value": True},  # turn on/off the observer
            {"name": "triggerCounter", "type": "variable", "value": 0},  # increased on each trigger
            {"name": "lastTriggerTime", "type": "variable", "value": ""},  # last datetime when it was triggered
            {"name": "targets", "type": "referencer"},
            {"name": "properties", "type": "const", "value": ["value"]},
            {"name": "onTriggerFunction", "type": "referencer"},  # the function(s) to be called when triggering
            {"name": "triggerSourceId", "type": "variable"},
            {"name": "hasEvent", "type": "const", "value": True},
            {"name": "eventString", "type": "const", "value": "global.timeSeries.value"},  # the string of the event
            {"name": "eventData", "type": "const", "value": {"text": ""}}
            ]
        },
        {"name": "eventSeriesValues", "type": "observer", "children": [
            {"name": "enabled", "type": "const", "value": True},  # turn on/off the observer
            {"name": "triggerCounter", "type": "variable", "value": 0},  # increased on each trigger
            {"name": "lastTriggerTime", "type": "variable", "value": ""},  # last datetime when it was triggered
            {"name": "targets", "type": "referencer"},
            {"name": "properties", "type": "const", "value": ["value"]},
            {"name": "onTriggerFunction", "type": "referencer"},  # the function(s) to be called when triggering
            {"name": "triggerSourceId", "type": "variable"},
            {"name": "hasEvent", "type": "const", "value": True},
            {"name": "eventString", "type": "const", "value": "global.eventSeries.value"},  # the string of the event
            {"name": "eventData", "type": "const", "value": {"text": ""}}
            ]
        },


    ]}

}
"""


periodicTimer = {
    "name":"periodicTimer",
    "type":"function",
    "functionPointer":"system.periodic_timer",   #filename.functionname
    "autoReload":False,                                 #set this to true to reload the module on each execution
    "children":[
        {"name":"target","type":"referencer"},
        {"name":"periodSeconds","type":"const","value":1},
        {"name":"description","type":"const","value":"periodic timer"},
        {"name":"lastTimeout","type":"variable","value":"not yet"},
        {"name":"lastDuration","type":"variable","value":"not yet"},
        {"name":"executionCounter","type":"variable","value":0},
        __functioncontrolfolder,
    ]
}


alarmClock = {
    "name":"alarmClock",
    "type":"function",
    "functionPointer":"system.alarm_clock",
    "autoReload":False,
    "children": [
        {"name": "target", "type": "referencer"},
        {"name": "isRunning","type":"variable","value":False}, #show if it is running or note
        {"name": "periodSeconds", "type": "const","value":24*60*60},
        {"name": "nextTimeout","type":"const","value":"2021-01-15T08:00+02:00"},#first alarm in iso time
        {"name": "executionCounter", "type": "variable", "value": 0},
        __functioncontrolfolder_threaded,
    ]
}

counter = {
    "name":"counter",
    "type":"function",
    "functionPointer":"system.counter_f",   #filename.functionname
    "autoReload":False,                                 #set this to true to reload the module on each execution
    "children":[
        {"name":"counter","type":"variable"},
        __functioncontrolfolder,
    ]
}


observer = {
    "name":"observer",
    "type":"observer",
    "children":[
        {"name": "enabled", "type": "const", "value": False},           # turn on/off the observer
        {"name": "triggerCounter","type":"variable","value":0},         #  increased on each trigger
        {"name": "lastTriggerTime","type":"variable","value":""},       #  last datetime when it was triggered
        {"name": "targets","type":"referencer"},                        #  pointing to the nodes observed
        {"name": "properties","type":"const","value":["value"]},        #  properties to observe [“children”,“value”, “forwardRefs”]
        {"name": "onTriggerFunction","type":"referencer"},              #  the function(s) to be called when triggering
        {"name": "triggerSourceId","type":"variable"},                  #  the sourceId of the node which caused the observer to trigger
        {"name": "hasEvent","type":"const","value":False},              # set to event string iftrue if we want an event as well
        {"name": "eventString","type":"const","value":"observerdefaultevent"},              # the string of the event
        {"name": "eventData","type":"const","value":{"text":"observer status update"}}      # the value-dict will be part of the SSE event["data"] , the key "text": , this will appear on the page,
    ]
}


saveModel = {
    "name":"saveModel",
    "type":"function",
    "functionPointer":"system.save_model",              #filename.functionname
    "autoReload":False,                                 #set this to true to reload the module on each execution
    "children":[
        {"name":"autoName","type":"const","value":False},   #if autoName is on, we will use a new name each time
        {"name":"name","type":"variable","value":None},
        __functioncontrolfolder,
    ]
}




def counter_f(functionNode):
    counterNode = functionNode.get_child("counter")
    try:
        val = int(counterNode.get_value())
    except:
        val = 0
    counterNode.set_value(val+1)



def periodic_timer(functionNode):
    # this function never ends until we get the signal "stop"
    signalNode = functionNode.get_child("control").get_child("signal")
    timeoutNode = functionNode.get_child("lastTimeout")
    durationNode = functionNode.get_child("lastDuration")
    counterNode = functionNode.get_child("executionCounter")

    sleep_time = float(functionNode.get_child("periodSeconds").get_value())
    running = True
    while True:
        #execute the functions
        startTime = datetime.datetime.now()
        timeoutNode.set_value(startTime.isoformat())
        for node in functionNode.get_child("target").get_leaves():
            print("execute",node.get_name())
            node.execute()
        durationNode.set_value((datetime.datetime.now()-startTime).total_seconds())
        counterNode.set_value(counterNode.get_value()+1)
        if signalNode.get_value() == "stop":
            signalNode.set_value("nosignal")
            break
        time.sleep(sleep_time)
    return True

def alarm_clock(functionNode):
    # this function never ends until we get the signal "stop"
    # it works on an own thread
    signalNode = functionNode.get_child("control").get_child("signal")
    logger = functionNode.get_logger()

    functionNode.get_child("isRunning").set_value(True)
    while True:
        if signalNode.get_value() == "stop":
            signalNode.set_value("nosignal")
            break

        timeout =  dates.date2secs(functionNode.get_child("nextTimeout").get_value())
        now = time.time()
        if now>timeout:
            #set the next timeout
            period = functionNode.get_child("periodSeconds").get_value()
            timeout = timeout + period
            functionNode.get_child("nextTimeout").set_value(dates.epochToIsoString(timeout))


            for node in functionNode.get_child("target").get_leaves():
                logger.debug(f"alarm_clock executes",node.get_name())
                node.execute()

            counterNode = functionNode.get_child("executionCounter")
            counterNode.set_value(counterNode.get_value()+1)

        time.sleep(5) #only sleep short to be able to break the loop with the signal

    functionNode.get_child("isRunning").set_value(False)
    return True



def observer_function(functionNode):
    subjectNodes = functionNode.get_child("subject").get_targets() # this is the subject to watch
    properties = functionNode.get_child("properties").get_value()
    statusNode = functionNode.get_child("lastStatus")
    currentStatus = {}
    for node in subjectNodes:
        nodeStatus = {}
        if "leaves" in properties:
            nodeStatus["leaves"]=[child.get_id() for child in node.get_leaves()]
        if "value" in properties:
            nodeStatus["value"]=node.get_value()
        if "children" in properties:
            nodeStatus["children"] = [child.get_id() for child in node.get_children()]
        currentStatus[node.get_id()]=copy.deepcopy(nodeStatus)
    if statusNode.get_value() == None:
        #this is the first time
        statusNode.set_value(copy.deepcopy(currentStatus))
    else:
        #we must compare
        if json.dumps(statusNode.get_value()) != json.dumps(currentStatus):
            #a change!
            counterNode = functionNode.get_child("updateCounter")
            counterNode.set_value(counterNode.get_value()+1)
            for node in functionNode.get_child("onUpdate").get_leaves():
                node.execute()
            statusNode.set_value(copy.deepcopy(currentStatus))
    return True


def save_model(functionNode):
    logger = functionNode.get_logger()
    model = functionNode.get_model()

    if functionNode.get_child("autoName").get_value()==True:
        fileName = model.currentModelName
        if len(model.currentModelName)>9 and model.currentModelName[-9] == "_":
            fileName = fileName[:-9]
        fileName = fileName+ "_" + getRandomId()
        functionNode.get_child("name").set_value(fileName)
    else:
        if functionNode.get_child("name").get_value()==None:
            functionNode.get_child("name").set_value(model.currentModelName)

    #now save it
    fileName =  functionNode.get_child("name").get_value()
    logger.debug(f"saving the model as {fileName}")
    model.save(fileName)
    return True



