import time

#isInteractive = False
#interruptSignal = None




delayFunctionTemplate = {
    "name":"delayFunction",
    "type":"function",
    "functionPointer":"testfunction.testFunctionfkt",   #filename.functionname
    "autoReload":False,                                 #set this to true to reload the module on each execution
    "children":[
        {"name":"status","type":"variable","value":"idle"},     # one of ["finished","running"]
        {"name":"progress","type":"variable","value":0},          # a value between 0 and 1
        {"name":"result","type":"variable","value":"ok"},       # of ["ok","error","pending" or a last error message]
        {"name":"input","type":"referencer"},                  # the outputs
        {"name":"output","type":"referencer"},
        {"name":"signal","type":"variable","value":"nosignal"}# of ["nosignal","interrupt"]
    ]
}






def testFunctionfkt(functionNode):
    print("==>>>> in testFunction",functionNode.get_browse_path())

    progress = functionNode.get_child("progress")

    for i in range(11):
        time.sleep(1)
        print("............. in test funktion thread", i)
        progress.set_value(1/10*i)




    return True