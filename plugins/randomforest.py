
import numpy
from system import __functioncontrolfolder
from model import date2secs
import modelhelper as mh
from sklearn.ensemble import RandomForestClassifier


randomForest= {
    "name":"randomForest",
    "type":"function",
    "functionPointer":"randomforest.random_forest",   #filename.functionname
    "autoReload":True,                                 #set this to true to reload the module on each execution
    "children":[
        {"name":"variables","type":"referencer"},                  # the outputs
        {"name":"output","type":"timeseries"},
        {"name":"annotations","type":"referencer"},             #the user annotations, if there is a "region", we do it only in the region
        {"name":"annotationFilter","type":"const","value":[]},                  #a list of tags to take, empty for all
        {"name":"resamplePeriod","type":"const","value":None},   #resampling, if null, we take times from the first variable
        {"name":"widget","type":"referencer"},                  #from where to take the tags info and to connect the result into
        __functioncontrolfolder
    ]
}



def random_forest(functionNode):
    logger = functionNode.get_logger()
    m=functionNode.get_model()
    logger.info("==>>>> in random_forest " + functionNode.get_browse_path())
    progressNode = functionNode.get_child("control").get_child("progress")
    progressNode.set_value(0)

    # now get the input and outputs
    inputNodes = functionNode.get_child("variables").get_leaves()
    outputNode = functionNode.get_child("output")

    annotations = functionNode.get_child("annotations").get_leaves()

    if annotations:
        for anno in annotations:
            logger.debug("annotation " + anno.get_browse_path())


    """
        now prepare the data for processing:

        1.1) define the sample times "times" from the data or generated
        1.2) use the map to match the tag labels to values 
        1.3) resample and select data based on annotations, region and the "times"
        1.4) train the model, score on region or full data 
    """

    # two ways to define the sampling:
    # if resamplePeriod is given, we take the interval for the sampling, if not given
    # we assume all data from the same timing, we take the times from the first variable as resampling
    period = functionNode.get_child("resamplePeriod").get_value()
    times = inputNodes[0].get_time_series()["__time"]
    if period:
        times = numpy.arange(times[0],times[-1],period)

    # get the annotation map
    tagsFilter = functionNode.get_child("annotationFilter").get_value()  # pick the tags to take

    # the annotations_to_class_vector takes all annotations in the positive list
    # and will also take the ones which are not explicitly ignored and extend the tags list with it,so we
    # prepare:

    tagsMap = {tag:idx for idx,tag in enumerate(tagsFilter)}
    labels = mh.annotations_to_class_vector(annotations,times,regionTag="region",tagsMap=tagsMap,autoAdd=False)
    inputMask = numpy.isfinite(labels)


    trainingData = []
    # now grab the values from the columns
    for node in inputNodes:
        #values = numpy.asarray(node.get_value())
        values = node.get_time_series(resampleTimes=times)["values"]
        trainingData.append(list(values[inputMask]))
    table = numpy.stack(trainingData, axis=0)

    progressNode.set_value(0.3)
    #
    # now fit the model
    #
    model =  RandomForestClassifier()
    model.fit(table.T, labels[inputMask])
    progressNode.set_value(0.6)
    #
    # scoring
    #
    # we score on the whole times or the selection by a region
    # do  we have a region?
    regions = mh.filter_annotations(annotations,"region")
    if regions:
        regionMask = numpy.isfinite(mh.annotations_to_class_vector(regions,times,ignoreTags=[]))
        scoreTimes = times[regionMask]
    else:
        scoreTimes = times


    # now grab the values from the columns
    scoreData = []
    for node in inputNodes:
        data = node.get_time_series(resampleTimes=scoreTimes)["values"]
        scoreData.append(data)

    scoreTable = numpy.stack(scoreData, axis=0)
    score = model.predict(scoreTable.T)

    #write back the output
    outputNode.set_time_series(times=scoreTimes,values=score)
    progressNode.set_value(1)

    #write back the info of the background node
    widget = functionNode.get_child("widget").get_target()
    if widget:
        currentBackground = widget.get_child("background").get_target()
        if currentBackground and currentBackground.get_id() == outputNode.get_id():
            #we have set the ref before already
            pass
        else:
            widget.get_child("background").add_references(functionNode.get_child("output"),deleteAll=True,allowDuplicates=False)


    #write the background classes coloring based on the annotation colors
    annoColors = widget.get_child("hasAnnotation.colors").get_value() #{"busy":{"color":"#ffe880","pattern":"/"},"free":{"color":"brown","pattern":"+"},"region":{"color":"grey","pattern":null},"pattern_match":{"color":"#808080","pattern":"v"}}
    backgroundColors = {str(no):annoColors[tag]["color"]  for tag,no in tagsMap.items() if tag in annoColors}
    backgroundColors["-1"]="red"         #these are typical default values
    backgroundColors["default"]="white"
    widget.get_child("backgroundMap").set_value(backgroundColors)



    return True
