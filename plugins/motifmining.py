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

# use a list to avoid loading of this in the model
mycontrol = [__functioncontrolfolder]
mycontrol[0]["children"][-1]["value"]="threaded"




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



def motif_miner(functionNode):
    logger = functionNode.get_logger()
    logger.info("==>>>> in motif_miner " + functionNode.get_browse_path())
    progressNode = functionNode.get_child("control").get_child("progress")
    progressNode.set_value(0)
    tableNode = functionNode.get_child("table").get_targets()[0]
    timeNode = tableNode.get_child("timeField").get_targets()[0]


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

    # prepare the result variable
    scoreNode = functionNode.get_child("score")
    scoreNode.connect_to_table(tableNode)  # this will make it part of the table and write it all to numpy.inf





    #now get the actual motif data
    motifVariable = motif.get_child("variable").get_targets()[0]
    start = motif.get_child("startTime").get_value()
    end = motif.get_child("endTime").get_value()
    #motifEpochLen = date2secs(end)-date2secs(start)
    motifEpochStart = date2secs(start)
    motifEpochEnd = date2secs(end)
    logger.debug(f"motif: {motifVariable.get_browse_path()},  {start} .. {end} ")
    timeIndices = timeNode.get_time_indices(start,end)

    motifTimeLen = (timeIndices[-1]-timeIndices[0])
    scoreIndices = numpy.arange(timeIndices[0]-1*motifTimeLen, timeIndices[-1]+ 200*motifTimeLen   )

    logger.debug(f" motif len {len(timeIndices)} score region len {len(scoreIndices)}")

    y = motifVariable.get_value().copy()


    #preprocessing of the data
    sigmaGauss = 2
    subSamplingFactor = 2
    mu, sigmaNoise = 0.0, 0.001
    y = gaussian_filter(y, sigma=sigmaGauss)  #smoothen
    t = timeIndices[::subSamplingFactor]#downsampling of the data
    scoreTimes = scoreIndices[::subSamplingFactor]

    # preprocessing of the motif
    yMotif = y[t].copy()

    #y = y[::subSamplingFactor] # full data
    y=y[scoreTimes]

    #preprocessing of the motif
    # adds a small amount of noise to the template in order to not create pathological results
    noise = np.random.normal(mu, sigmaNoise, len(yMotif))
    yMotif = yMotif + noise

    result = motif_mining(template=yMotif, y=y, preprocesssing_method='subtract_poly_3', sim_method='euclidean', normalize=False,progressNode=progressNode)

    result[-len(yMotif):]=result[-len(yMotif)] #the end seams to be noisy, keep it stable
    result = normalize_range(result, 0, 1.0)

    #put result
    resultVector = scoreNode.get_value()
    indices = numpy.asarray(list(range(0,len(resultVector),subSamplingFactor)))

    if 0: # for full
        for i in range(subSamplingFactor):
            resultVector[indices+i]=result
    else:
        for i in range(subSamplingFactor):
            resultVector[scoreTimes+i]=result
    scoreNode.set_value(resultVector)

    generate_peaks(resultVector,functionNode,logger,timeNode,(len(yMotif) * subSamplingFactor),motifEpochStart,motifEpochEnd)


    return True

def generate_peaks(resultVector,functionNode,logger,timeNode,MotifLen,MotifStart,MotifEnd):
    v = resultVector.copy()
    motifTimeLen = MotifEnd-MotifStart
    v[False == numpy.isfinite(v)] = 0  # pad inf as zero for the peak detector
    peakIndices = detect_peaks(v, min_dist=0.7 * MotifLen)
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
    functionNode.get_child("peaks").set_value(peakDates)

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

    #delete previous annotations
    myModel.disable_observers()
    annos = annotations.get_children()
    if annos:
        for anno in annos:
            anno.delete()

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

    intervalStart = time.time()

    m = len(template)
    n = len(y)
    c = np.zeros((n,))
    for i in np.arange(0, n):
        if time.time()>intervalStart+1:
            intervalStart = time.time()
            if progressNode:
                progressNode.set_value(float(i)/n)

        x1 = i
        x2 = np.minimum(i + m, n)
        yi = y[x1:x2]
        t = template[:(x2-x1)]

        if len(t) > 5:
            if "subtract_poly" in preprocesssing_method:
                degree = int(preprocesssing_method[-1:])
                t, _ = subtract_polynomial_model(t, degree=degree)
                yi, _ = subtract_polynomial_model(yi, degree=degree)


        if sim_method == 'pearson':
            pc = pearson_correlation_coefficient(t, yi)
            c[i] = pc

        if sim_method == 'pearson_center':
            pc = pearson_center(t, yi)
            c[i] = pc


        if sim_method == 'conv':
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
    currentIndex = functionNode.get_child("jumpPos").get_value()
    inc = functionNode.get_child("jumpInc").get_value()

    nextIndex = currentIndex+inc
    if nextIndex>=len(dates):
        nextIndex=0
    functionNode.get_child("jumpPos").set_value(nextIndex)

    logger.debug(f"jump to index {nextIndex}  : {dates[nextIndex]}")

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
