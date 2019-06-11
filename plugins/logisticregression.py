
from sklearn.linear_model import LogisticRegression
import numpy
from system import __functioncontrolfolder



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
        __functioncontrolfolder
    ]
}





def logistic_regression(functionNode):

    logger = functionNode.get_logger()
    logger.info("==>>>> in logisticregression 2: "+functionNode.get_browse_path())

    #now get the input and outputs
    inputNodes = functionNode.get_child("input").get_leaves()
    for node in inputNodes:
        logger.debug("input node",node.get_browse_path())

    outputNode = functionNode.get_child("output").get_leaves()[0]
    logger.debug("outputnode "+outputNode.get_browse_path())

    annotations = functionNode.get_child("annotations").get_leaves()

    if annotations:
        for anno in annotations:
            logger.debug("annotation "+anno.get_browse_path())

    timeNode = inputNodes[0].get_table_time_node()   #if the node is a column belonging to a time series table, we now get the time node of that table
    logger.debug("the time node is "+timeNode.get_browse_path())

    """
        now prepare the data for processing:
        
        1.1) take the annotated areas, collect all start and end times and get all indices of time inside the annotations
        1.2) use the map to match the tag labels to values 
        1.3) cut out the input data from the variable based on the indices from 1.1)
        1.4) train the model
        1.5) score on the full data
        1.6) write back the score to the output
    """

    #get the annotation map
    tagsMap = functionNode.get_child("categoryMap").get_value()# pick the category mapping from the model

    hasRegion = False
    #see if we have a "region" annotation (we only support one)
    for anno in annotations:
        if anno.get_child('tags').get_value()[0] == "region":
            regionStartTime = anno.get_child("startTime").get_value()
            regionEndTime = anno.get_child("endTime").get_value()
            hasRegion = True
            break # only one supported

    indices = [] # a list of indices which give the points in time that were labelled
    training =[]   #the training values are the tags from the annoations translated via the tagsmap
    for anno in annotations:
        startTime = anno.get_child("startTime").get_value()
        endTime = anno.get_child("endTime").get_value()
        if anno.get_child('tags').get_value()[0] == "region":
            continue # we ignore "region" entries
        if hasRegion:
            if startTime < regionStartTime or endTime > regionEndTime:
                continue # skip this entry, it's outside the region
        annoIndices = list(timeNode.get_time_indices(startTime,endTime))  # this gives us the indices in the table between start and end time
        annoValue = tagsMap[anno.get_child('tags').get_value()[0]]
        annoValues = [annoValue]*len(annoIndices)
        indices.extend(annoIndices)
        training.extend(annoValues)

    trainingData = []
    #now grab the values from the columns
    for node in inputNodes:
        values = numpy.asarray(node.get_value())
        values = values[indices] # fancy indexing, we only pick the values inside the annotation areas
        trainingData.append(list(values))
    table = numpy.stack(trainingData,axis=0)

    #now fit the model
    model = LogisticRegression()
    model.fit(table.T,numpy.asarray(training))

    #
    # scoring
    #

    if hasRegion:
        regionIndices = timeNode.get_time_indices(regionStartTime,regionEndTime)
        tableNode = timeNode.get_table_node()
        tableLen = tableNode.get_table_len()

    #try some scoring
    logger.info("now score")
    scoreData = []
    # now grab the values from the columns
    for node in inputNodes:
        if hasRegion:
            scoreData.append(node.get_value()[regionIndices])
        else:
            scoreData.append(node.get_value())
    scoreTable = numpy.stack(scoreData, axis=0)
    score = model.predict(scoreTable.T)


    #now write the score back to the ouput
    if hasRegion:
        #we need to fill in the remainings with Nan
        scoreFill = numpy.full(tableLen,numpy.inf)
        scoreFill[regionIndices]=score
        outputNode.set_value(list(scoreFill))
    else:
        outputNode.set_value(list(score))


    return
