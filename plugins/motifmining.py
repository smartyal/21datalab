#21datalabplugin

import numpy
import numpy as np
import time
from scipy.ndimage import gaussian_filter
from system import __functioncontrolfolder
from model import date2secs
from model import epochToIsoString
from mininghelper import *
from pytz import timezone
from model import date2secs
import copy
from model import date2secs,secs2date
import mininghelper as mnh


# use a list to avoid loading of this in the model
mycontrol = [copy.deepcopy(__functioncontrolfolder)]
mycontrol[0]["children"][-1]["value"]="threaded"

"""
HOW TO USE the motif miner


prepare the template
- add the template to the model
- connect the referencer MotifMiner.widget
- connect the referencer MotifMiner.table
- add the MotifMiner.annotations folder to the referencer of your annotations (typically widget.hasAnnotation.annotaions)


prepare the widget:
- widget.hasAnnotation.colors: add this entry:
    "pattern_match": {"color": "#808080","pattern": "v"} 
- hasAnnotation.visibleTags need an entry "pattern_match"
- also make sure the widget.startTime,widget.endTime is being watched by the visibleElement observer (so we can use the "jump" function in the cockpit) 



- selecte the motif
- either in the tree or:
    open the cockpit (hook it to the context menu first)
    select the motif in the time series view
    click 
    
- prepare the output 
- hit run, wait 3 sec, hit stop
- now the score variable should show the right length, it can be used to display

"""





"""
motifMinerTemplate = {
    "name": "motifMiner",
    "type": "function",
    "functionPointer": "motifmining.motif_miner",  # filename.functionname
    "autoReload": True,  # set this to true to reload the module on each execution
    "children": [
        {"name": "motif", "type": "referencer"},        # the one motif we are using
        {"name": "score", "type": "column"},
        {"name": "algorithm", "type": "const"},         # the alorithm used, one of ...
        {"name": "widget","type":"referencer"} ,        # the widget to which this miner belongs which is used (to find the selected motif
        {"name": "table","type":"referencer"},          # for the variables and times
        {"name": "peakThreshold","type":"const"},
        mycontrol[0]
    ]
}

motifJumperTemplate = {
    "name": "motifJumper",
    "type": "function",
    "functionPointer": "motifmining.motif_jumper",  # filename.functionname
    "autoReload": True,  # set this to true to reload the module on each execution
    "children": [
        {"name": "miner", "type": "referencer"},  # the one motif we are using
        {"name": "jumpPos", "type": "variable", "value":0},
        {"name": "jumpInc", "type": "const", "value":1},  # 1,-1 for forward backwards
        {"name": "table", "type": "referencer"},  # for the variables and times
        __functioncontrolfolder
    ]
}

"""

motifMinerTemplate = {
    "name": "MotifMiner1",
    "type": "folder",
    "children":[
        {
            "name": "MotifMiner",
            "type": "function",
            "functionPointer": "motifmining.motif_miner",  # filename.functionname
            "autoReload": True,  # set this to true to reload the module on each execution
            "children": [
                {"name": "motif", "type": "referencer"},        # the one motif we are using
                {"name": "score", "type": "column"},
                {"name": "algorithm", "type": "const","value":"pearson",
                    "validation":{"values":["euclidean","pearson","pearson_center","convolution"]}},         # the alorithm used, one of ...
                {"name": "widget","type":"referencer"} ,        # the widget to which this miner belongs which is used (to find the selected motif
                {"name": "table","type":"referencer"},          # for the variables and times
                {"name": "table","type":"referencer"},          # for the variables and times
                {"name": "peaks","type":"variable"},
                {"name": "addNoise","type":"const","value":0.001},
                {"name": "subSamplingFactor","type":"const","value":2},
                {"name": "subtractPolynomOrder", "type": "const", "value": 2,"validation":{"values":["none",1,2,3]}},
                {"name": "annotations","type":"folder"},        # the results
                mycontrol[0]
            ]
        },
        {
            "name": "peakSearch",
            "type": "function",
            "functionPointer": "motifmining.motif_jumper",  # filename.functionname
            "autoReload": True,  # set this to true to reload the module on each execution
            "children": [
                {"name": "miner", "type": "referencer","references":["MotifMiner1.MotifMiner"]},  # the one motif we are using
                {"name": "jumpPos", "type": "variable", "value":0},
                {"name": "jumpInc", "type": "const", "value":1},  # 1,-1 for forward backwards
                {"name": "threshold", "type": "const","value":0.5},  # the detection threshold
                __functioncontrolfolder
            ]
        },
        {
            "name": "progress",
            "type": "observer",
            "children": [
                {"name": "enabled", "type": "const", "value": True},  # turn on/off the observer
                {"name": "triggerCounter", "type": "variable", "value": 0},  # increased on each trigger
                {"name": "lastTriggerTime", "type": "variable", "value": ""},  # last datetime when it was triggered
                {"name": "targets", "type": "referencer","references":["MotifMiner1.MotifMiner.control.progress"]},  # pointing to the nodes observed
                {"name": "properties", "type": "const", "value": ["value"]},
                # properties to observe [“children”,“value”, “forwardRefs”]
                {"name": "onTriggerFunction", "type": "referencer"},  # the function(s) to be called when triggering
                {"name": "triggerSourceId", "type": "variable"},
                # the sourceId of the node which caused the observer to trigger
                {"name": "hasEvent", "type": "const", "value": True},
                # set to event string iftrue if we want an event as well
                {"name": "eventString", "type": "const", "value": "motifminer.progress"},  # the string of the event
                {"name": "eventData", "type": "const", "value": {"text": "observer status update"}}
                # the value-dict will be part of the SSE event["data"] , the key "text": , this will appear on the page,
            ]
        },
        {"name": "cockpit", "type": "const", "value": "/customui/motifminer1cockpit.htm"}  #the cockpit for the motif miner
    ]
}




def motif_miner(functionNode):

    logger = functionNode.get_logger()
    logger.info("==>>>> in motif_miner " + functionNode.get_browse_path())
    progressNode = functionNode.get_child("control").get_child("progress")
    progressNode.set_value(0)
    tableNode = functionNode.get_child("table").get_targets()[0]
    timeNode = tableNode.get_child("timeField").get_targets()[0]
    subSamplingFactor = functionNode.get_child("subSamplingFactor").get_value()
    sigmaNoise = functionNode.get_child("addNoise").get_value()
    annotations = functionNode.get_child("annotations")
    myModel = functionNode.get_model()
    signalNode = functionNode.get_child("control").get_child("signal")

    polynomPre = functionNode.get_child("subtractPolynomOrder").get_value()
    if polynomPre != "none":
        polynomPre = "subtract_poly_"+str(int(polynomPre))
    logger.debug(f"polynome pre is {polynomPre}")
    algo = functionNode.get_child("algorithm").get_value()




    """
        preparation:
            - find the current widget, take the current selected selection for my motif
            - if not available
            - connect the result to the table
    """

    myWidget = functionNode.get_child("widget").get_targets()[0]
    motifs = myWidget.get_child("hasAnnotation").get_child("selectedAnnotations").get_leaves()
    motif = None
    if motifs:
        motif = motifs[0]
        functionNode.get_child("motif").add_references(motif,deleteAll=True) # take this annotation
    else:
        #there is currently no selection, we take the motif from last time if we have one
        motifs = functionNode.get_child("motif").get_targets()
        if motifs:
            motif = motifs[0]
    if not motif:
        logger.error("have no motif")
        return False


    # prepare the result: delete previous scores and annotations
    scoreNode = functionNode.get_child("score")
    functionNode.get_child("peaks").set_value([])
    scoreNode.connect_to_table(tableNode)  # this will make it part of the table and write it all to numpy.inf
    try:
        myModel.disable_observers()
        annos = annotations.get_children()
        if annos:
            for anno in annos:
                anno.delete()
    except:
        myModel.enable_observers()
        return False

    myModel.enable_observers()
    myModel.notify_observers(annotations.get_id(), "children")  # trigger the widgets to delete the annotations




    #prepare the motif
    motifVariable = motif.get_child("variable").get_targets()[0]
    start = motif.get_child("startTime").get_value()
    end = motif.get_child("endTime").get_value()
    motifEpochStart = date2secs(start)
    motifEpochEnd = date2secs(end)
    logger.debug(f"motif: {motifVariable.get_browse_path()},  {start} .. {end} ")
    timeIndices = timeNode.get_time_indices(start,end)
    logger.debug(f" motif len {len(timeIndices)}")
    y = motifVariable.get_value().copy()    # y holds the full data
    y = gaussian_filter(y, sigma=2)         # smoothen it
    #normalize y
    #y = normalize_range(y,0,1)              #normalize
    t = timeIndices[::subSamplingFactor]    #downsampling of the data
    yMotif = y[t].copy()                    # yMotif holds the motif data downsampled
    noise = np.random.normal(0, sigmaNoise, len(yMotif))
    yMotif = yMotif + noise                 # adds a small amount of noise to the template in order to not create pathological results


    # prepare the result
    motifTimeLen = (timeIndices[-1]-timeIndices[0])
    scoreIndices = numpy.arange(timeIndices[0]-1*motifTimeLen, timeIndices[-1]+ 200*motifTimeLen   )
    scoreTimes = scoreIndices[::subSamplingFactor]



    #y = y[::subSamplingFactor] # full data
    #y=y[scoreTimes]

    #we will now go through the data and each 2 seconds update the results with the new results
    runningR = True
    runningL = True
    blockSize = 10 # times the motif len
    blockStartR = timeIndices[0]        # start is the motif start time for the serach to the right
    blockStartL = timeIndices[0]-(blockSize-1)*motifTimeLen        # start is the motif start time for the search to the left

    signalNode.set_value("none")

    while runningR or runningL:
        percentR = float((blockStartR-timeIndices[0])/(len(t) - blockStartR))
        percentL = float(timeIndices[0]-blockStartL)/float(timeIndices[0])
        progressNode.set_value(max(percentL,percentR))

        logger.debug(f"processing block {blockStartR} {len(y)}")

        oldResult = scoreNode.get_value().copy()
        resultVector = numpy.full(len(oldResult),numpy.inf,dtype=numpy.float64)

        if runningR:
            #search to the right
            scoreIndices = numpy.arange(blockStartR, blockStartR+blockSize * motifTimeLen)
            scoreTimes = scoreIndices[::subSamplingFactor]
            yWindow = y[scoreTimes]
            result = motif_mining(template=yMotif, y=yWindow, preprocesssing_method=polynomPre, sim_method=algo,
                          normalize=False, progressNode=progressNode)


            #resultVector = scoreNode.get_value()
            indices = numpy.asarray(list(range(0,len(resultVector),subSamplingFactor)))

            if 0: # for full
                for i in range(subSamplingFactor):
                    resultVector[indices+i]=result
            else:
                for i in range(subSamplingFactor):
                    resultVector[scoreTimes+i]=result
            #scoreNode.set_value(resultVector)

            blockStartR += (blockSize-1)*motifTimeLen
            if blockStartR > (len(y)-(blockSize*motifTimeLen)):
                runningR=False

        if runningL:
            #search to the right
            scoreIndices = numpy.arange(blockStartL, blockStartL+blockSize * motifTimeLen)
            scoreTimes = scoreIndices[::subSamplingFactor]
            yWindow = y[scoreTimes]
            result = motif_mining(template=yMotif, y=yWindow, preprocesssing_method=polynomPre, sim_method=algo,
                          normalize=False, progressNode=progressNode)


            #resultVector = scoreNode.get_value()
            indices = numpy.asarray(list(range(0,len(resultVector),subSamplingFactor)))

            if 0: # for full
                for i in range(subSamplingFactor):
                    resultVector[indices+i]=result
            else:
                for i in range(subSamplingFactor):
                    resultVector[scoreTimes+i]=result
            #scoreNode.set_value(resultVector)

            blockStartL -= (blockSize-1)*motifTimeLen
            if blockStartL < 0:
                runningL=False

        transferIndices = numpy.isfinite(resultVector)  # set the inf to 0 where we have new results
        oldResult[transferIndices]=resultVector[transferIndices]
        scoreNode.set_value(oldResult)

        if signalNode.get_value()=="stop":
            runningR = False
            runningL = False

        generate_peaks(resultVector, functionNode, logger, timeNode, (len(yMotif) * subSamplingFactor), motifEpochStart,
                       motifEpochEnd)
        time.sleep(0.8) # this makes a yield to other threads

    #generate_peaks(resultVector,functionNode,logger,timeNode,(len(yMotif) * subSamplingFactor),motifEpochStart,motifEpochEnd)


    return True

def generate_peaks(resultVector,functionNode,logger,timeNode,MotifLen,MotifStart,MotifEnd):
    v = resultVector.copy()
    motifTimeLen = MotifEnd-MotifStart
    v[False == numpy.isfinite(v)] = 0  # pad inf as zero for the peak detector
    level = numpy.float(functionNode.get_parent().get_child("peakSearch").get_child("threshold").get_value())
    peakIndices = detect_peaks(v, min_dist=3 * MotifLen, min_level = level)
    logger.debug(f"found {len(peakIndices)} peaks")
    peaksValues = v[peakIndices]
    if 0: #sort
        sortIndices = numpy.argsort(peaksValues)[::-1]
        sortedPeakIndices = peakIndices[sortIndices]
        sortedPeakIndices = sortedPeakIndices[0:min(len(sortedPeakIndices), 10)]  # max 10 peaks
    else:
        sortedPeakIndices = peakIndices
    peakepochs = timeNode.get_value()[sortedPeakIndices]


    peakDates = [epochToIsoString(peak, zone=timezone('Europe/Berlin')) for peak in peakepochs]
    if peakDates:
        print(f"peakDATES {peakDates}")
        current = functionNode.get_child("peaks").get_value()
        if not type(current) is list:
            current = []
        current.extend(peakDates)
        print(f"update current {current}")
        functionNode.get_child("peaks").set_value(current)

    #now generate annotations
    annotations = functionNode.get_child("annotations")
    myModel = functionNode.get_model()

    newAnnotations=[]
    for peak in peakepochs:
        if peak > (MotifEnd+motifTimeLen/2) or peak < (MotifStart-motifTimeLen/2):
            anno={"type":"time","startTime":"","endTime":"","tags":["pattern_match"]}
            anno["startTime"]=epochToIsoString(peak, zone=timezone('Europe/Berlin'))
            anno["endTime"] = epochToIsoString(peak+motifTimeLen, zone=timezone('Europe/Berlin'))
            newAnnotations.append(anno)

    myModel.disable_observers()
    for anno in newAnnotations:
        # create the annotation in the model
        newAnno = annotations.create_child(type="annotation")
        for k, v in anno.items():
            newAnno.create_child(properties={"name": k, "value": v, "type": "const"})



    myModel.enable_observers()
    myModel.notify_observers(annotations.get_id(), "children")




def motif_mining(template: np.ndarray, y: np.ndarray, sim_method: str = 'pearson_center',
                         preprocesssing_method: str = 'none', normalize: bool = True,progressNode = None):
    """
        Args: prepreocessing_method : "subtract
    """
    print("prepoc method is"+preprocesssing_method)
    intervalStart = time.time()

    m = len(template)
    n = len(y)
    c = np.zeros((n,))
    for i in np.arange(0, n-m):
        if time.time()>intervalStart+1:
            intervalStart = time.time()
            if progressNode:
                #progressNode.set_value(float(i)/n)
                pass

        x1 = i
        x2 = np.minimum(i + m, n)
        yi = y[x1:x2]
        #print(f"len {x1} {x2} {m} {n} {x2-x1} ")
        t = template[:(x2-x1)]

        if len(t) > 5:
            if "subtract_poly" in preprocesssing_method:

                degree = int(preprocesssing_method[-1:])
                #print(f"have degree {degree}")
                t, _ = subtract_polynomial_model(t, degree=degree)
                yi, _ = subtract_polynomial_model(yi, degree=degree)


        if sim_method == 'pearson':
            pc = pearson_correlation_coefficient(t, yi)
            c[i] = pc

        if sim_method == 'pearson_center':
            pc = pearson_center(t, yi)
            c[i] = pc


        if sim_method == 'convolution':
            c[i] = np.abs(np.dot(t, yi))

        if sim_method == 'euclidean':
            nd = 1.0 - normalized_euclidean_distance(t, yi)
            c[i] = nd  # np.maximum(np.minimum(1.0, nd), 0.0)

        if sim_method == 'dtw':
            d, _ = distance_by_dynamic_time_warping(t, yi)
            c[i] = 1.0 - d

        if sim_method == 'dtw2':
            d = distance_by_dynamic_time_warping2(t, yi)
            c[i] = 1.0 - d

    if normalize:
        c = normalize_range(c)

    return c



def motif_jumper(functionNode):

    logger = functionNode.get_logger()
    logger.info("==>>>> in motif_jumper " + functionNode.get_browse_path())

    minerNode = functionNode.get_child("miner").get_targets()[0]
    widgetNode = minerNode.get_child("widget").get_targets()[0]

    dates = minerNode.get_child("peaks").get_value()
    if type(dates) is not list:
        dates = []
    currentIndex = functionNode.get_child("jumpPos").get_value()
    inc = functionNode.get_child("jumpInc").get_value()

    nextIndex = currentIndex+inc
    if nextIndex>=len(dates):
        nextIndex=0
    functionNode.get_child("jumpPos").set_value(nextIndex)

    logger.debug(f"jump to index {nextIndex}  : {dates[nextIndex]}")

    if len(dates):
        motif = minerNode.get_child("motif").get_targets()[0]
        motifStart = motif.get_child("startTime").get_value()
        motifEnd = motif.get_child("endTime").get_value()

        currentViewStart = widgetNode.get_child("startTime").get_value()
        currentViewEnd = widgetNode.get_child("endTime").get_value()
        currentViewWidth = date2secs(currentViewEnd)- date2secs(currentViewStart)

        windowStart = date2secs(dates[nextIndex])-currentViewWidth/2
        windowEnd = date2secs(dates[nextIndex])+currentViewWidth/2



        widgetNode.get_child("startTime").set_value(epochToIsoString(windowStart,zone=timezone('Europe/Berlin')))
        widgetNode.get_child("endTime").set_value(epochToIsoString(windowEnd, zone=timezone('Europe/Berlin')))

    return True





def pps_miner(functionNode):

    logger = functionNode.get_logger()
    logger.info("==>>>> in pps_miner " + functionNode.get_browse_path())

    myWidget = functionNode.get_child("widget").get_target()
    myModel = functionNode.get_model()
    motifs = myWidget.get_child("hasAnnotation").get_child("selectedAnnotations").get_leaves()
    annotations = functionNode.get_child("annotations")




    """
        preparation:
            - find the current widget, take the current selected selection for my motif
            - if not available
            - connect the result to the table
    """


    motif = None
    if motifs:
        motif = motifs[0]
        functionNode.get_child("motif").add_references(motif,deleteAll=True) # take this annotation
    else:
        #there is currently no selection, we take the motif from last time if we have one
        motifs = functionNode.get_child("motif").get_targets()
        if motifs:
            motif = motifs[0]
    if not motif:
        logger.error("have no motif")
        return False

    # prepare the result: delete previous annotations
    functionNode.get_child("peaks").set_value([])
    try:
        myModel.disable_observers()
        annos = annotations.get_children()
        if annos:
            for anno in annos:
                anno.delete()
    except:
        myModel.enable_observers()
        return False

    myModel.enable_observers()
    myModel.notify_observers(annotations.get_id(), "children")  # trigger the widgets to delete the annotations






    ####################################
    ## get the settings
    ####################################
    preFilter = functionNode.get_child("preFilter").get_value()
    postFilter = functionNode.get_child("postFilter").get_value()
    subtractPolynomOrder = functionNode.get_child("subtractPolynomOrder").get_value()
    differentiate = functionNode.get_child("differentiate").get_value()
    timeRanges = functionNode.get_child("timeRanges").get_value()
    timeRanges = {int(k):v for k,v in timeRanges.items()}
    valueRanges = functionNode.get_child("valueRanges").get_value()
    valueRanges = {int(k): v for k, v in valueRanges.items()}
    typeFilter = functionNode.get_child("typeFilter").get_value()



    ####################################
    #get the motif
    ####################################
    motifStartTime = date2secs(motif.get_child("startTime").get_value())
    motifEndTime = date2secs(motif.get_child("endTime").get_value())
    motifVariable = motif.get_child("variable").get_targets()[0]

    #motifStartTime = motifStartTime+0.2*(motifEndTime-motifStartTime)
    #print(f"{vars[varName].get_name()},{motifStartTime}")
    motif = motifVariable.get_time_series(start=motifStartTime,end=motifEndTime)
    #print(motif)
    motifX = motif["__time"]
    motifY0 = motif["values"]
    motifY1 = mnh.pps_prep(motifY0,filter=preFilter,poly=subtractPolynomOrder, diff=differentiate, postFilter = postFilter)
    motifPPS = mnh.prominent_points(motifY1,motifX)

    ####################################
    #get the time series
    ####################################
    # make the time series data and pps
    series = motifVariable.get_time_series()# the full time
    x=series["__time"]
    t0 = series["__time"][0]
    x=x-t0 # start time from 0
    y0=series["values"]
    y1=mnh.pps_prep(y0,filter=preFilter,poly=subtractPolynomOrder, diff=differentiate, postFilter = postFilter)
    pps = mnh.prominent_points(y1,x)

    ####################################
    # MINING
    ####################################
    matches = mnh.pps_mining(motifPPS['pps'], pps['pps'], timeRanges = timeRanges, valueRanges = valueRanges, typeFilter=typeFilter, motifStartIndex=0, debug=False)
    print(f"{len(matches)} matches: {[secs2date(t0+m['time']).isoformat() for m in matches]}")


    ####################################
    # create result Annotations
    ####################################

    annoTimeLen = motifEndTime -motifStartTime
    newAnnotations=[]
    for m in matches:
        anno={"type":"time","startTime":"","endTime":"","tags":["pattern_match"]}
        anno["startTime"]= epochToIsoString(m["time"]+t0-annoTimeLen, zone=timezone('Europe/Berlin'))
        anno["endTime"] = epochToIsoString(m["time"]+t0, zone=timezone('Europe/Berlin'))
        newAnnotations.append(anno)

    myModel.disable_observers()
    for anno in newAnnotations:
        # create the annotation in the model
        newAnno = annotations.create_child(type="annotation")
        for k, v in anno.items():
            newAnno.create_child(properties={"name": k, "value": v, "type": "const"})
    myModel.enable_observers()
    myModel.notify_observers(annotations.get_id(), "children")

    #also write the peaks
    peaks = [epochToIsoString(m["time"]+t0, zone=timezone('Europe/Berlin')) for m in matches]
    functionNode.get_child("peaks").set_value(peaks)