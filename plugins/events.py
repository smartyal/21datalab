#21datalabplugin

from system import __functioncontrolfolder
import time
import dates
import numpy



events2Annotation = {
    "name":"events2Annotation",
    "type": "function",
    "functionPointer": "events.events_to_annotations",  # filename.functionname
    "autoReload": True,  # set this to true to reload the module on each execution
    "children": [
        {"name": "annotations", "type": "folder" },  # this is where we put the result annos
        {"name": "eventSeries", "type": "referencer"},  # pointer to an eventseries
        {"name": "processedUntil","type":"variable","value":None},      # holds the time until the differential process has run, it is the timestamp of the last processed event
        {"name": "differential","type":"const","value":False},          #set true if differential execution is wanted
        {"name": "eventSelection","type":"const","value":{              #name of the resulting anno: [start,end] names of the events
                "busy": ["busy_start","busy_end"],
                "free": ["free_start","free_end"]}},
        __functioncontrolfolder
    ]

}



def events_to_annotations(functionNode):
    logger = functionNode.get_logger()
    logger.info("==>>>> events_to_annotations "+functionNode.get_browse_path())

    progressNode = functionNode.get_child("control").get_child("progress")
    newAnnosNode = functionNode.get_child("annotations")
    differential = functionNode.get_child("differential").get_value()
    valueNotifyNodeIds = []  #this variable will hold node id to post a value notification (the nodes that were open before)

    if differential:
        processedUntil = dates.date2secs(functionNode.get_child("processedUntil").get_value(),ignoreError=False)
        if not processedUntil:
            processedUntil = 0
    else:
        processedUntil = 0
    lastTimeSeen = processedUntil # initialize, this variable with find the latest time entry

    # eventSelection is a dict to translate and select the events from the event series
    # eg {"machine1.init":"Preparation", "machine1.op2":"Printing"}
    # we will select the "machine1.init and the "macine1.op2" events and name the annotation type as Preparation, Printing
    eventSelection = functionNode.get_child("eventSelection").get_value()
    progressNode.set_value(0)
    m = functionNode.get_model()
    startEvents = [v[0] for k,v in eventSelection.items()] # always the first event
    endEvents = [v[1] for k, v in eventSelection.items()]  # always the second event
    ev2Anno={ev:anno for anno,eventStrings in eventSelection.items() for ev in eventStrings}#a helper lookup dict for events to annotations

    evs = functionNode.get_child("eventSeries").get_targets() # a list of nodes where the events are located

    if not differential:
        #delete all old annos
        annos = newAnnosNode.get_children()
        if annos:
            try:
                m.disable_observers()
                for anno in annos:
                    anno.delete()
            finally:
                m.enable_observers()
            m.notify_observers(newAnnosNode.get_id(), "children")
        openAnnos = [] # no open annotatations per definition

    else:
        #differential process: we don't delete the old but get all open annotations
        openAnnos = []
        annos = newAnnosNode.get_children()
        for anno in annos:
            if "open" in anno.get_child("tags").get_value():
                openAnnos.append(anno)


    #now collect all events filtered by the selection of events and the time (if differential process)
    #we build up a list of dicts with ["event"."hello", "startTime":1234494., "endTime":2345346.:
    filter = startEvents+endEvents


    newAnnotations = []     # the annotations to be created new, a list of dicts, it will also contain "updates" for existing nodes
                            # those update entries will be found by the key "node" which holds the node that has to be updated
    openAnnotation = {}    # {"key":"litu":{"startTime":132412334,"node"} # will also hold the node if we have one already

    #put the open annotations in a fast look up table
    if len(openAnnos) > 1:
        logger.error("there should be only one")

    if openAnnos:
        openAnnotation = {
            "key": openAnnos[0].get_child("tags").get_value(),
            "startTime":openAnnos[0].get_child("startTime").get_value(),
            "node":anno
        }



    #now iterate over all events
    for ev in evs:
        data = ev.get_event_series(eventFilter = filter) #["__time":... "eventStrings"....]
        times = data["__time"]
        eventStrings = data["eventStrings"]
        if differential:
            #also filter by time
            new = times > processedUntil
            times = times[new]
            indexableEventStrings = numpy.asarray(eventStrings,dtype=numpy.str)
            eventStrings = indexableEventStrings[new]

        for index in range(len(times)):
            evStr = eventStrings[index]
            tim = times[index]
            if tim>lastTimeSeen:
                lastTimeSeen = tim
            key = ev2Anno[evStr]
            if evStr in startEvents:
                if openAnnotation:
                    # we have an annotation running already, this should not be the case, so we
                    # submit the currently open annotation as anomaly and start a new open annotaton
                    # with the current time
                    # if the "open" entry was from an existing annotation in the tree, we also put that
                    # node handle to later use if for updating the annotation and not creating it new

                    #build the anomaly annotations
                    anno = {
                        "type": "time",
                        "endTime": dates.epochToIsoString(tim, zone='Europe/Berlin'),
                        "startTime": openAnnotation["startTime"],
                        "tags": ["anomaly",key]
                    }
                    if "node" in openAnnotation:
                        anno["node"] = openAnnotation["node"]
                    newAnnotations.append(anno) # put the anomaly node there


                #now remember the current as the open one
                openAnnotation = {
                    "startTime":dates.epochToIsoString(tim, zone='Europe/Berlin'),
                    "key":key
                 }

            if evStr in endEvents:
                if openAnnotation and key in openAnnotation["key"]:
                    #take this annotation, we can close it
                    anno  = {
                        "type": "time",
                        "endTime": dates.epochToIsoString(tim, zone='Europe/Berlin'),
                        "startTime": openAnnotation["startTime"],
                        "tags": [ev2Anno[evStr]]
                    }
                    if "node" in openAnnotation:
                        #  if it was an existing annotation, we also put the anno handle to make an "update"
                        #  instead of a new creation further down
                        anno["node"]=openAnnotation["node"]
                    newAnnotations.append(anno)

                    openAnnotation = {} # no current open annotation
                else:
                    logger.warning(f"annotation creation ende without start {tim} {evStr}")

    #now create the annotations
    logger.debug(f"creating {len(newAnnotations)} annotation, have {openAnnotation} open annotations")
    m.disable_observers()
    try:

        #now the open annotations
        if differential:
            # in the open annotations list, we will find
            # - open annotations that have existed before and have not found an update yet and were not closed
            # - new open annotations that have started now
            if openAnnotation:
                nowIso = dates.epochToIsoString(time.time(),zone='Europe/Berlin')
                if "node" in openAnnotation:
                    # this existed before, we just update the endtime
                    node = openAnnotation["node"]
                    node.get_child("endTime").set_value(nowIso) # set the current time as end time
                    valueNotifyNodeIds.append(node.get_child("endTime").get_id())
                else:
                    #this is a new open anno:
                    entry = {
                        "type": "time",
                        "endTime": nowIso,
                        "startTime": openAnnotation["startTime"],
                        "tags": [ev2Anno[evStr],"open"]
                    }
                    newAnnotations.append(entry) # put it to the creation list

        #create and update new annotations
        for anno in newAnnotations:
            if not "node" in anno:
                newAnno = newAnnosNode.create_child(type="annotation")
                for k, v in anno.items():
                    newAnno.create_child(properties={"name": k, "value": v, "type": "const"})
            else:
                #this is an update, typically a "close" or an extension of an open annotation
                node = anno["node"]
                node.get_child("endTime").set_value(anno["endTime"])
                node.get_child("tags").set_value(anno["tags"])
                valueNotifyNodeIds.append(node.get_child("endTime").get_id())

    except Exception as ex:
        logger.error(f"error in events_to_annotations {ex}")

    m.enable_observers()
    m.notify_observers(newAnnosNode.get_id(), "children")
    #also notify the value changes of annotations that existed before
    if valueNotifyNodeIds:
        m.notify_observers(valueNotifyNodeIds,"value")# also notify the value change for the UI to adjust the annotation

    #if time.time()>lastTimeSeen:
    #    lastTimeSeen=time.time()

    isoDate = dates.epochToIsoString(lastTimeSeen,zone="Europe/Berlin")
    functionNode.get_child("processedUntil").set_value(isoDate) # this is for me, next time I can check what has been processed

    return True