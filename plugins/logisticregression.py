
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

import numpy
from system import __functioncontrolfolder
from model import date2secs
import modelhelper as mh



logisticRegressionTemplate= {
    "name":"logisticRegression",
    "type":"function",
    "functionPointer":"logisticregression.logistic_regression",   #filename.functionname
    "autoReload":True,                                 #set this to true to reload the module on each execution
    "children":[
        {"name":"input","type":"referencer"},                  # the outputs
        {"name":"output","type":"referencer"},
        {"name":"annotations","type":"referencer"},             #the user annotations
        {"name":"categoryMap","type":"const"},                  #logistic regression work on categories, this is the number mapper, INPUT
        {"name":"resamplePeriod","type":"const","value":None},   #reampling, if null, we take times from the first variable
        __functioncontrolfolder
    ]
}



def logistic_regression(functionNode):
    logger = functionNode.get_logger()
    m=functionNode.get_model()
    logger.info("==>>>> in logisticregression_ " + functionNode.get_browse_path())

    # now get the input and outputs
    inputNodes = functionNode.get_child("input").get_leaves()
    for node in inputNodes:
        logger.debug("input node" + node.get_browse_path())

    progressNode = functionNode.get_child("control").get_child("progress")
    progressNode.set_value(0)
    outputNode = functionNode.get_child("output").get_leaves()[0]
    logger.debug("outputnode " + outputNode.get_browse_path())

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
    # we assume all data from the same timing, we take the times from the first variable and do not resample the data
    period = functionNode.get_child("resamplePeriod").get_value()
    times = m.time_series_get_table(inputNodes[0].get_id())["__time"]
    if period:
        times = numpy.arange(times[0],times[-1],period)

    # get the annotation map
    tagsMap = functionNode.get_child("categoryMap").get_value()  # pick the category mapping from the model


    labels = mh.annotations_to_class_vector(annotations,times,regionTag="region",tagsMap=tagsMap)
    inputMask = numpy.isfinite(labels)


    trainingData = []
    # now grab the values from the columns
    for node in inputNodes:
        #values = numpy.asarray(node.get_value())
        values = m.time_series_get_table(node.get_id(),resampleTimes=times)["values"]
        trainingData.append(list(values[inputMask]))
    table = numpy.stack(trainingData, axis=0)

    progressNode.set_value(0.3)
    #
    # now fit the model
    #
    model = LogisticRegression()
    model.fit(table.T, labels[inputMask])
    progressNode.set_value(0.6)
    #
    # scoring
    #
    # we score on the whole times or the selection by a region
    # do  we have a region?
    regions = mh.filter_annotations(annotations,"region")
    if regions:
        regionMask = numpy.isfinite(mh.annotations_to_class_vector(regions,times))
        scoreTimes = times[regionMask]
    else:
        scoreTimes = times


    # now grab the values from the columns
    scoreData = []
    for node in inputNodes:
        data = m.time_series_get_table(node.get_id(),resampleTimes=scoreTimes)["values"]
        scoreData.append(data)

    scoreTable = numpy.stack(scoreData, axis=0)
    score = model.predict(scoreTable.T)

   #write back the output
    m.time_series_set(outputNode.get_id(),times=scoreTimes,values=score)
    progressNode.set_value(1)


    return True