import time

isInteractive = False
interruptSignal = None



testfunction={
    "myfunction" :{
        "type":"function",
        "value":"testfunction.testFunctionfkt",
        "children":{
            "status":{"type":"variable","value":"idle"},
            "progress":{"type":"variable","value":0},
            "result":{"type":"variable","value":"ok"}
        },
    },
    "input":{"type":"referencer"},
}

def testFunctionfkt(functionNode):
    print("==>>>> in testFunction",functionNode.get_browse_path())

    progress = functionNode.get_child("progress")

    for i in range(11):
        time.sleep(1)
        print("............. in test funktion thread", i)
        progress.set_value(1/10*i)




    return True