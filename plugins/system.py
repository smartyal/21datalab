import datetime
import time

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





periodicTimer = {
    "name":"periodicTimer",
    "type":"function",
    "functionPointer":"system.periodic_timer",   #filename.functionname
    "autoReload":True,                                 #set this to true to reload the module on each execution
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

counter = {
    "name":"counter",
    "type":"function",
    "functionPointer":"system.counter_f",   #filename.functionname
    "autoReload":True,                                 #set this to true to reload the module on each execution
    "children":[
        {"name":"counter","type":"variable"},
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


