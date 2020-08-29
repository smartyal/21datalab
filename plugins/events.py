#21datalabplugin

from system import __functioncontrolfolder
import time
import dates
import numpy
import streaming



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
        {"name": "interleaved","type":"const","value":False},           #when set to true, we allow interleaved events, that means one event is running while another starts, if set true this is not allowed and events can never overlap
        {"name": "eventSelection","type":"const","value":{              #name of the resulting anno: [start,end] names of the events
                "busy": ["busy_start","busy_end"],
                "free": ["free_start","free_end"]}},
        __functioncontrolfolder
    ]

}



events2State = {
    "name":"events2State",
    "type": "object",
    "class":"events.Events2StateClass",  # filename.functionname
    "autoReload": True,  # set this to true to reload the module on each execution
    "children": [
        {"name": "annotations", "type": "folder" },  # this is where we put the result annos
        {"name": "eventSeries", "type": "referencer"},  # pointer to an eventseries
        {"name": "eventSelection","type":"const","value":{              #name of the resulting anno: [start,end] names of the events
                "busy": ["busy_start","busy_end"],
                "free": ["free_start","free_end"]}},
        __functioncontrolfolder,
        {"name":"processAll","type":"function","functionPointer":"events.events_to_state_all","autoReload":False,"children":[
            __functioncontrolfolder]}
    ]

}


def events_to_state_all(functionNode):
    logger = functionNode.get_logger()
    logger.debug("==>>>> events_to_state_all" + functionNode.get_browse_path())
    return True

def events_to_annotations(functionNode):
    """
        this function creates annotations from events

    """
    logger = functionNode.get_logger()
    logger.info("==>>>> events_to_annotations "+functionNode.get_browse_path())

    progressNode = functionNode.get_child("control").get_child("progress")
    newAnnosNode = functionNode.get_child("annotations")
    differential = functionNode.get_child("differential").get_value()
    valueNotifyNodeIds = []  #this variable will hold node id to post a value notification (the nodes that were open before)

    interleaved = functionNode.get_child("interleaved")
    if interleaved:
        #if the node is there
        interleaved = interleaved.get_value()

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
    startEvents = {v[0]:k for k,v in eventSelection.items()} # always the first event
    endEvents = {v[1]:k for k, v in eventSelection.items()}  # always the second event
    #ev2Anno={ev:anno for anno,eventStrings in eventSelection.items() for ev in eventStrings}#a helper lookup dict for events to annotations {eventname:annotationsTags}

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
                openAnnotation = {
                    "tags": anno.get_child("tags").get_value(),   #using "tag" to note that an open annotation has only one tag
                    "startTime": anno.get_child("startTime").get_value(),
                    "node": anno
                }
                openAnnos.append(openAnnotation)


    #now collect all events filtered by the selection of events and the time (if differential process)
    #we build up a list of dicts with ["event"."hello", "startTime":1234494., "endTime":2345346.:
    filter = list(startEvents.keys())+list(endEvents.keys())


    #from now on we use these lists
    newAnnotations = []     # the annotations to be created new, a list of dicts, it will also contain "updates" for existing nodes
                            # those update entries will be found by the key "node" which holds the node that has to be updated
    #openAnnos : a list of # {"key":"litu":{"startTime":132412334,"node"} # will also hold the node if we have one already

    #put the open annotations in a fast look up table
    if len(openAnnos) > 1 and not interleaved:
        logger.error("there should be only one open annotation at max in non-interleaved mode")


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
            #tag = ev2Anno[evStr]
            print(r"ev:{evStr}, tag:{tag}, open Annos {openAnnos}")
            if evStr in startEvents:
                tag = startEvents[evStr]
                #this is a start of a new event
                print("is start")
                if openAnnos:
                    # we have at least on e annotation running already:
                    # in non-interleaved wo submitt all open annotations as anomaly
                    # in interleaved mode we only submit those with the same event as anomaly
                    # if the "open" entry was from an existing annotation in the tree, we also put that
                    # node handle to later use if for updating the annotation and not creating it new

                    newOpenAnnos = []
                    for openAnnotation in openAnnos:
                        if not interleaved or tag in openAnnotation["tags"]:
                            # we must close this open annotation as anomaly
                            # build the anomaly annotations
                            anno = {
                                "type": "time",
                                "endTime": dates.epochToIsoString(tim, zone='Europe/Berlin'),
                                "startTime": openAnnotation["startTime"],
                                "tags": ["anomaly",tag]
                            }
                            if "node" in openAnnotation:
                                anno["node"] = openAnnotation["node"]
                            newAnnotations.append(anno) # put the anomaly node there
                        else:
                            #keep this annotation
                            newOpenAnnos.append(openAnnotation)
                    openAnnos = newOpenAnnos

                #now remember the current as the open one
                openAnnotation = {
                    "startTime":dates.epochToIsoString(tim, zone='Europe/Berlin'),
                    "tags":[tag]
                }
                openAnnos.append(openAnnotation)

            #not an else if, because it can be in both start and end events
            if evStr in endEvents:
                print("is end")
                #this is an end event, see if we have a matching open annotation
                tag = endEvents[evStr]
                newOpenAnnos = []
                for openAnnotation in openAnnos:
                    if tag in openAnnotation["tags"]:
                        #take this annotation, we can close it
                        anno  = {
                            "type": "time",
                            "endTime": dates.epochToIsoString(tim, zone='Europe/Berlin'),
                            "startTime": openAnnotation["startTime"],
                            "tags": [tag]
                        }
                        if "node" in openAnnotation:
                            #  if it was an existing annotation, we also put the anno handle to make an "update"
                            #  instead of a new creation further down
                            anno["node"]=openAnnotation["node"]
                        newAnnotations.append(anno)
                    else:
                        newOpenAnnos.append(openAnnotation)#keep this one
                if len(newOpenAnnos) == len(openAnnos):
                    logger.warning(f"annotation creation ende without start {tim} {evStr}")
                openAnnos = newOpenAnnos
            #print(f"open annotations {openAnnos} new annos {newAnnotations}")



    #now create the annotations
    logger.debug(f"creating {len(newAnnotations)} annotation, have {openAnnos} open annotations")
    #print(f"creating {len(newAnnotations)} annotation, have {len(openAnnos)} open annotations")
    m.disable_observers()
    try:

        if differential:
            # in the open annotations list, we will find
            # - open annotations that have existed before and have not found an update yet and were not closed
            # - new open annotations that have started now
            for openAnnotation in openAnnos:
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
                        "tags": openAnnotation["tags"]+["open"]
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


class Events2StateClass(streaming.Interface):

    def __init__(self,objectNode):
        self.logger=objectNode.get_logger()
        self.objectNode = objectNode
        self.model = objectNode.get_model()
        self.reset()

    def reset(self,data):
        return data

    def feed(self,blob):
        """
            expected format of blob
            {"type":"eventseries",
             "data":{
                        "__time":[11,12,13,14],
                        "23488923400":["p1.start","p2.start",...]
                    }
            }
            #the blob will have only one event variable
        """

        self.logger.debug("Events2StateClass.feed()")
        #we look for eventseries to switch the state:
        if blob["type"] == "eventseries":
            times = blob["data"]["__time"]
            evSeries = [v for k,v in blob["data"].items() if k!="__time"][0] # we take the first entry that is not __time, we expect there to be only ONE!
            newAnnos = self.process_event_series(times, evSeries)

            for anno in newAnnos:
                newAnno = self.newAnnosNode.create_child(type="annotation")
                for k, v in anno.items():
                    newAnno.create_child(properties={"name": k, "value": v, "type": "const"})
            return blob

        elif blob["type"] == "timeseries":
            """
            # we need to add the state to the timeseries in the form
            {
                "type": "timeseries",
                "data": {
                    "__time": [120, 130, 140, 150, 160, 170, ....]
                    "var1": [20, 30, 40, 50, 60, 70, ......] //
                    "var2":[2, 3, 4, 5, 6, ....]
                    "__states": {
                        "euv": [True, False, True, .....]
                        "evacuating": [False, False, False, ....]
                    }
                }
            }
            """
            times = blob["data"]["__time"]
            addStates = {}
            length = len(times)
            for tag,startTime in self.state.items():
                addStates[tag]=numpy.full(length,True)
            blob["data"]["__states"]=addStates
            return blob

        return blob

    def flush(self,data=None):
        return data

    def reset(self,data=None):
        self.progressNode = self.objectNode.get_child("control").get_child("progress")
        self.newAnnosNode = self.objectNode.get_child("annotations")

        # eventSelection is a dict to translate and select the events from the processed event series (stream or historical)
        # e.g. {"machine1.init":"Preparation", "machine1.op2":"Printing"}:
        #   we will select the "machine1.init and the "macine1.op2" events and name the annotation type as Preparation, Printing

        self.eventSelection = self.objectNode.get_child("eventSelection").get_value()
        self.startEvents = [v[0] for k, v in self.eventSelection.items()]  # always the first event
        self.endEvents = [v[1] for k, v in self.eventSelection.items()]  # always the second event
        self.ev2Anno = {ev: anno for anno, eventStrings in self.eventSelection.items() for ev in
                   eventStrings}  # a helper lookup dict for events to annotations {eventname:annotationsTags}


        self.state = {}
        # in self.openAnnos, we store the currently running system state in the form
        # { "state": epoch (the start time of the state



    def process_historical(self):

        self.logger.debug("process_historical")
        #delete the old results:
        annos = self.newAnnosNode.get_children()
        if annos:
            try:
                self.model.disable_observers()
                for anno in annos:
                    anno.delete()
            finally:
                self.model.enable_observers()
            self.model.notify_observers(self.newAnnosNode.get_id(), "children")



    def get_open_annos(self):

        openAnnos = []
        annos = self.newAnnosNode.get_children()
        for anno in annos:
            if "open" in anno.get_child("tags").get_value():
                openAnnotation = {
                    "tags": anno.get_child("tags").get_value(),# using "tag" to note that an open annotation has only one tag
                    "startTime": anno.get_child("startTime").get_value(),
                    "node": anno
                }
                openAnnos.append(openAnnotation)
        self.openAnnos = openAnnos


    def process_event_series(self,times,eventStrings):
        """
            process one event series

            we update the self.state according to the current events

            Args: times[ndarray] the epochs
                    eventStrings: [list of strings] of the events, which can be converted per map

        """

        newAnnotations = []

        for index in range(len(times)):
            evStr = eventStrings[index]
            tim = times[index]
            tag = self.ev2Anno[evStr]
            print(r"ev:{evStr}, tag:{tag}, open Annos {openAnnos}")
            if evStr in self.startEvents:
                # this is a start of a new event
                print("is start")
                if tag in self.state:
                    # we are in this state already, and get a repeated start event, this is an error
                    # so we submit an anomaly annotation
                    anno = {
                        "type": "time",
                        "endTime": dates.epochToIsoString(tim, zone='Europe/Berlin'),
                        "startTime": dates.epochToIsoString(self.state[tag], zone='Europe/Berlin'),
                        "tags": ["anomaly", tag]
                    }
                    newAnnotations.append(anno)  # put the anomaly node

                self.state[tag]=tim  #also update the current state

            # not an else if, because it can be in both start and end events
            if evStr in self.endEvents:
                print("is end")
                # this is an end event, see if we have a matching running state
                if tag in self.state:
                    anno = {
                        "type": "time",
                        "endTime": dates.epochToIsoString(tim, zone='Europe/Berlin'),
                        "startTime": dates.epochToIsoString(self.state[tag], zone='Europe/Berlin'),
                        "tags": [tag]
                    }
                    newAnnotations.append(anno)
                    del self.state[tag] # remove the state from the current states
                else:
                    self.logger.warning(f"end event without start {tim} {evStr} ")

        return newAnnotations