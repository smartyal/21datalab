# 21datalabplugin

#import numpy as np
import dates
import pandas as pd
import copy
import numpy
from system import __functioncontrolfolder
import requests
import json
import time



# use a list to avoid loading of this in the model
mycontrol = [copy.deepcopy(__functioncontrolfolder)]
mycontrol[0]["children"][-1]["value"] = "threaded"



"""
    how to use the replayer
    - put the template
    - connect the variables
    - connect either the widget or give an annotation 
    - if the widget is given, at run of the function we try to take the current annotation of te widget and write it as annotation
"""
Replayer = {
    "name": "Replayer",
    "type": "function",
    "functionPointer": "replay.replay",  # filename.functionname
    "autoReload": True,  # set this to true to reload the module on each execution
    "children": [
        {"name": "input", "type": "referencer"},  # the input variables [timeseries, eventseries] to replay
        {"name": "widget", "type": "referencer"},   #if the widget is given, we take the "current selection " of the widget
        {"name": "annotation", "type": "referencer"},       #the time annotation to replay
        {"name": "replaySpeed","type":"const","value":0},  #the time in seconds [float] between two data points sent, 0 for full speed
        {"name": "loop", "type": "const", "value": False},      #set this true to endless loop and append data
        {"name": "format", "type":"const","validation": {"values": ["21_insert", "21_execute"]},"value":"21_execute"},
        {"name": "url","type":"const","value":"http://127.0.0.1:6001/_execute"},
        {"name": "parameters","type":"const","value":"root.pipeline"}, #depending on the format, here are more params, for the format 21_execute it's the node
        {"name": "appendData","type":"const","value":True},
        {"name": "directApi", "type":"const","value":False}, # the this to true to use the local API if possible and not use the http call
        mycontrol[0]
    ]
}
def remove_dublicate_times(df):
    df.sort_values("__time", inplace=True)
    submitRow = None
    newDf = pd.DataFrame()
    for index, row in df.iterrows():
        if type(submitRow) is type(None):
            submitRow = row
            continue
        else:
            if submitRow["__time"] == row["__time"]:
                # this is a row with the same time entry
                for k, v in row.items():
                    if not numpy.isfinite(submitRow[k]):
                        submitRow[k] = v
            else:
                # submit row to new table
                #print("submit",submitRow)
                newDf = newDf.append(submitRow, ignore_index=True)
                submitRow = row
    if not type(submitRow) == type(None):
        #submit the last
        newDf = newDf.append(submitRow, ignore_index=True)
    return newDf



def replay(functionNode):
    logger = functionNode.get_logger()
    logger.info("==>>>> replay " + functionNode.get_browse_path())
    progressNode = functionNode.get_child("control").get_child("progress")
    progressNode.set_value(0)
    functionNode.get_child("control.signal").set_value(None)

    widget = functionNode.get_child("widget").get_target()
    if widget:
        #try to get the current anno
        annotation = widget.get_child("hasAnnotation.selectedAnnotations").get_target()
        if annotation:
            #remember the anno
            functionNode.get_child("annotation").add_references(annotation,deleteAll=True)
    annotation = functionNode.get_child("annotation").get_target()
    if not annotation:
        logger.error("replay:no annotation/widget given")
        return False
    startTime = dates.date2secs(annotation.get_child("startTime").get_value())
    endTime = dates.date2secs(annotation.get_child("endTime").get_value())

    #now get the data and build a table
    varNodes = functionNode.get_child("input").get_leaves()
    nodesLookup = {node.get_id():node for node in varNodes}

    #we build three array: timepoint, nodes in
    table = pd.DataFrame({"__time":[]})

    latestTime = 0
    for var in varNodes:
        if var.get_type() == "timeseries":
            data = var.get_time_series(startTime,endTime)
            new = pd.DataFrame({"__time":data["__time"],var.get_id():data["values"]})
            table = table.append(new,ignore_index=True)
            #now find the last time
            times = var.get_time_series()["__time"] #all the data
            if len(times):
                latestTime = max(latestTime,times[-1])
        elif var.get_type() == "eventseries":
            data = var.get_event_series(startTime,endTime)
            new = pd.DataFrame({"__time":data["__time"],var.get_id():data["eventstrings"]})
            table = table.append(new, ignore_index=True)
            #now find the last time
            times = var.get_event_series()["__time"] #all the data
            if len(times):
                latestTime = max(latestTime,times[-1])

    #table.sort_values("__time", inplace=True)
    table = remove_dublicate_times(table)
    #print(table)

    #now we have the data sorted and dublicates removed in the pd frame, let's replay
    offset = latestTime - table["__time"].iloc[-1]
    #logger.debug(f"latest Time {dates.epochToIsoString(latestTime)} , offset {offset}")
    repeatoffset = table["__time"].iloc[-1]-table["__time"].iloc[0]
    while 1:
        offset = offset+repeatoffset
        logger.debug(f"latest Time {dates.epochToIsoString(latestTime)} , offset {offset}")
        speed = functionNode.get_child("replaySpeed").get_value()
        url = functionNode.get_child("url").get_value()
        format = functionNode.get_child("format").get_value()
        params = functionNode.get_child("parameters").get_value()
        directApi = functionNode.get_child("directApi").get_value()
        if directApi:
            targetNode = functionNode.get_model().get_node(params)
        for index, row in table.iterrows():
            #build the data json
            #all timeseries

            if format == "21_execute":
                timeblob={}
                eventblob={}
                for k, v in row.items():
                    if k=="__time":
                        timeblob["__time"]=v+offset
                        eventblob["__time"]=v+offset
                    elif numpy.isfinite(v):
                        if nodesLookup[k].get_type()=="timeseries":
                            timeblob[k]=v
                        else:
                            eventblob[k]=v
                    else:
                        logger.warning("data not finite")

                body = {"node": params, "function": "feed", "parameter": []}#{"type": "timeseries", "data": blob}]}
                if len(timeblob)>1:
                    body["parameter"].append({"type":"timeseries","data":timeblob})
                if len(eventblob)>1:
                    body["parameter"].append({"type": "eventseries", "data": eventblob})
            else:
                logger.warning("replay:unknown format")
                body={}

            #try to send out
            if not directApi:
                try:
                    if body:
                        res = requests.post(url, data=json.dumps(body), timeout=5)
                        logger.debug("sent out replay packet")


                except Exception as ex:
                    logger.error(ex)
            else:
                #send this directly to the node in the tree
                targetNode.get_object().feed(body["parameter"])

            time.sleep(speed)

            if functionNode.get_child("control.signal").get_value()=="stop":
                break

        if functionNode.get_child("control.signal").get_value() == "stop" or not functionNode.get_child("loop").get_value():
            break
        else:
            logger.debug("loop replay")
    return True


