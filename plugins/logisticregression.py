
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

import numpy
from system import __functioncontrolfolder
from model import date2secs



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
    logger.info("==>>>> in logisticregression_ "+functionNode.get_browse_path())

    #now get the input and outputs
    inputNodes = functionNode.get_child("input").get_leaves()
    for node in inputNodes:
        logger.debug("input node"+node.get_browse_path())

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
        if anno.get_child("type").get_value() !="time":
            continue # we only take time annotations, ignore thresholds etc
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

logisticRegressionTemplate2= {
    "name":"logisticRegression2",
    "type":"function",
    "functionPointer":"logisticregression.logistic_regression2",   #filename.functionname
    "autoReload":True,                                 #set this to true to reload the module on each execution
    "children":[
        {"name":"input","type":"referencer"},                  # the outputs
        {"name":"output","type":"referencer"},
        {"name":"annotations","type":"referencer"},             #the user annotations
        {"name":"categoryMap","type":"const"},                  #logistic regression work on categories, this is the number mapper, INPUT
        {"name":"confusion","type":"variable"},                 #to hold the confusion matrix as result (output)
        __functioncontrolfolder
    ]
}


def logistic_regression2_old(functionNode):
    """
     new version of the logistic regression:
     we are following the approach of a n-class classification where n-1 classes are given in the categoryMap starting at number 1,
     all data inside the regions (we support only one here) will be treated as category 0
    """
    logger = functionNode.get_logger()
    logger.info("==>>>> in logisticregression 2: " + functionNode.get_browse_path())

    # now get the input and outputs
    inputNodes = functionNode.get_child("input").get_leaves()
    for node in inputNodes:
        logger.debug("input node" + node.get_browse_path())

    outputNode = functionNode.get_child("output").get_leaves()[0]
    logger.debug("outputnode " + outputNode.get_browse_path())

    annotations = functionNode.get_child("annotations").get_leaves()

    if annotations:
        logger.debug("no annotations: " +str(len(annotations)))

    timeNode = inputNodes[ 0].get_table_time_node()  # if the node is a column belonging to a time series table, we now get the time node of that table
    logger.debug("the time node is " + timeNode.get_browse_path())

    """
        now prepare the data for processing:

        1.1) take the annotated areas, collect all start and end times and get all indices of time inside the annotations
        1.2) use the map to match the tag labels to values 
        1.3) cut out the input data from the variable based on the indices from 1.1)
        1.4) train the model
        1.5) score on the full data
        1.6) write back the score to the output
    """

    # get the annotation map
    tagsMap = functionNode.get_child("categoryMap").get_value()  # pick the category mapping from the model

    hasRegion = False
    # see if we have a "region" annotation (we only support one)
    for anno in annotations:
        if anno.get_child('tags').get_value()[0] == "region":
            regionStartTime = anno.get_child("startTime").get_value()
            regionEndTime = anno.get_child("endTime").get_value()
            hasRegion = True
            logger.debug("has Region:"+str(regionStartTime)+" "+str(regionEndTime))
            regionIndices = timeNode.get_time_indices(regionStartTime, regionEndTime)
            break  # only one supported

    indices = []  # a list of indices which give the points in time that were labelled
    training = []  # the training values are the tags from the annoations translated via the tagsmap
    for anno in annotations:
        startTime = anno.get_child("startTime").get_value()
        endTime = anno.get_child("endTime").get_value()
        if anno.get_child('tags').get_value()[0] == "region":
            continue  # we ignore "region" entries
        if hasRegion:
            if startTime < regionStartTime or endTime > regionEndTime:
                continue  # skip this entry, it's outside the region
        annoIndices = list(timeNode.get_time_indices(startTime,
                                                     endTime))  # this gives us the indices in the table between start and end time
        annoTag =  anno.get_child('tags').get_value()[0]
        if annoTag in tagsMap:
            annoValue = tagsMap[annoTag]
        else:
            annoValue = 0
        annoValues = [annoValue] * len(annoIndices)
        indices.extend(annoIndices)
        training.extend(annoValues)

    #now also grab the remaining indices
    if hasRegion:
        allIndices = timeNode.get_time_indices(regionStartTime, regionEndTime)
    else:
        allIndices = numpy.arange(0,len(timeNode.get_value()))

    #fill them in with 0
    for index in allIndices:
        if index in indices:
            pass
        else:
            indices.append(index) # add this index ..
            training.append(0)    # with a zero value




    trainingData = []
    # now grab the values from the columns
    finiteNodes = []

    for node in inputNodes:
        values = numpy.asarray(node.get_value())
        if numpy.isfinite(values).all():
            values = values[indices]  # fancy indexing, we only pick the values inside the annotation areas
            trainingData.append(list(values))
            finiteNodes.append(node)
            logger.debug("has good finite values"+node.get_name())
        else:
            logger.warning("some infinite values in "+node.get_name())
            #now pad with zero
            values[False == numpy.isfinite(values)] = 0
            trainingData.append(list(values))
            finiteNodes.append(node)
    table = numpy.stack(trainingData, axis=0)

    # now fit the model
    model = LogisticRegression()
    model.fit(table.T, numpy.asarray(training))

    #
    # scoring
    #

    if hasRegion:
        regionIndices = timeNode.get_time_indices(regionStartTime, regionEndTime)
        tableNode = timeNode.get_table_node()
        tableLen = tableNode.get_table_len()

    # try some scoring
    logger.info("now score")
    scoreData = []
    # now grab the values from the columns
    for node in finiteNodes:
        if hasRegion:
            values = node.get_value()[regionIndices]
        else:
            values = node.get_value()
        values[False == numpy.isfinite(values)] = 0 #pad inf as zero
        scoreData.append(values)

    scoreTable = numpy.stack(scoreData, axis=0)
    score = model.predict(scoreTable.T)

    # now write the score back to the ouput
    if hasRegion:
        # we need to fill in the remainings with Nan
        scoreFill = numpy.full(tableLen, numpy.inf)
        scoreFill[regionIndices] = score
        outputNode.set_value(list(scoreFill))
    else:
        outputNode.set_value(list(score))

    return


def logistic_regression2_old2(functionNode):
    """
     new version of the logistic regression:
     we are following the approach of a n-class classification where n-1 classes are given in the categoryMap starting at number 1,
     all data inside the regions (we support only one here) will be treated as category 0
    """
    scaling = True
    algorithm = "rf" # of rf, lg

    logger = functionNode.get_logger()
    logger.info("==>>>> in logisticregression 2: " + functionNode.get_browse_path())

    # now get the input and outputs
    inputNodes = functionNode.get_child("input").get_leaves()
    for node in inputNodes:
        logger.debug("input node" + node.get_browse_path())

    outputNode = functionNode.get_child("output").get_leaves()[0]
    logger.debug("outputnode " + outputNode.get_browse_path())

    annotations = functionNode.get_child("annotations").get_leaves()

    if annotations:
        logger.debug("no annotations: " +str(len(annotations)))

    timeNode = inputNodes[ 0].get_table_time_node()  # if the node is a column belonging to a time series table, we now get the time node of that table
    logger.debug("the time node is " + timeNode.get_browse_path())

    """
        now prepare the data for processing:

        1.1) take the annotated areas, collect all start and end times and get all indices of time inside the annotations
        1.2) use the map to match the tag labels to values 
        1.3) cut out the input data from the variable based on the indices from 1.1)
        1.4) train the model
        1.5) score on the full data
        1.6) write back the score to the output
    """

    # get the annotation map
    tagsMap = functionNode.get_child("categoryMap").get_value()  # pick the category mapping from the model

    hasRegion = False
    # see if we have a "region" annotation (we only support one)
    for anno in annotations:
        if anno.get_child('tags').get_value()[0] == "region":
            regionStartDate = anno.get_child("startTime").get_value()
            regionEndDate = anno.get_child("endTime").get_value()
            hasRegion = True
            logger.debug("has Region:"+str(regionStartDate)+" "+str(regionEndDate))
            regionStartTime = date2secs(regionStartDate)
            regionEndTime = date2secs(regionEndDate)
            regionIndices = timeNode.get_time_indices(regionStartTime, regionEndTime)
            break  # only one supported

    # now prepare the training target values based on the given annotations,
    # the regions where no anno is given are set as 0
    # for simplicity we start with a training array of the full size of the table, later, we cut it
    # for the region

    tableLen = len(timeNode.get_value())
    training = numpy.full(tableLen,0) # set zero to all values as a padding

    #indices = []  # a list of indices which give the points in time that were labelled
    #training = []  # the training values are the tags from the annoations translated via the tagsmap
    for anno in annotations:
        startTime = date2secs(anno.get_child("startTime").get_value())
        endTime = date2secs(anno.get_child("endTime").get_value())

        tag = anno.get_child('tags').get_value()[0]
        if tag in tagsMap:
            #we take annotations that have a tag which was selected in the tagsMap
            if hasRegion == False or (startTime >= regionStartTime and endTime <= regionEndTime):
                #we only take annotations inside the region
                annoIndices = list(timeNode.get_time_indices(startTime,endTime))  # this gives us the indices in the table between start and end time
                #now set the values with fancy indexing
                training[annoIndices] = tagsMap[tag]


    #now cut the region if we have one via fancy indexing
    if hasRegion:
        training = training[regionIndices]


    trainingData = []
    # now grab the values from the columns
    finiteNodes = []

    for node in inputNodes:
        values = numpy.asarray(node.get_value())
        if hasRegion:
            values = values[regionIndices]

        if numpy.isfinite(values).all():
            trainingData.append(list(values))
            finiteNodes.append(node)
            logger.debug("has good finite values"+node.get_name())
        else:
            logger.warning("some infinite values in "+node.get_name())
            #now pad with zero
            values[False == numpy.isfinite(values)] = 0
            trainingData.append(list(values))
            finiteNodes.append(node)
    table = numpy.stack(trainingData, axis=0)

    # now fit the model
    #model = LogisticRegression()
    model =  RandomForestClassifier(n_estimators=50,max_features=10)

    scaler = StandardScaler()
    scaler.fit(table.T)
    if scaling:
        data = scaler.transform(table.T)
        model.fit(data, numpy.asarray(training))
    else:
        model.fit(table.T, numpy.asarray(training))

    #
    # scoring is on "scoreregion"
    #

    if hasRegion:
        tableNode = timeNode.get_table_node()
        tableLen = tableNode.get_table_len()

    # try some scoring
    logger.info("now score")
    scoreData = []
    # now grab the values from the columns
    for node in finiteNodes:
        if hasRegion:
            values = node.get_value()[regionIndices]
        else:
            values = node.get_value()
        values[False == numpy.isfinite(values)] = 0 #pad inf as zero
        scoreData.append(values)

    scoreTable = numpy.stack(scoreData, axis=0)

    if scaling:
        data = scaler.transform(scoreTable.T)
        score = model.predict(data)
    else:
        score = model.predict(scoreTable.T)

    # now write the score back to the ouput
    if hasRegion:
        # we need to fill in the remainings with Nan
        scoreFill = numpy.full(tableLen, numpy.inf)
        scoreFill[regionIndices] = score
        outputNode.set_value(list(scoreFill))
    else:
        outputNode.set_value(list(score))


    #also get the confusion matrix
    matrix = {'00':0,'01':0,'11':0,'10':0}
    for val,score in zip(training,score):
        entry = str(val)+str(score)
        matrix[entry]=matrix[entry]+1
    for entry in matrix:
        matrix[entry]=float(matrix[entry])/float(len(training))
    logger.debug("Confusion Matrix"+str(matrix))


    return True


def logistic_regression2(functionNode):
    """
     new version of the logistic regression:
     we are following the approach of a n-class classification where n-1 classes are given in the categoryMap starting at number 1,
     all data inside the regions (we support only one here) will be treated as category 0
    """
    scaling = True
    algorithm = "rf" # of rf, lg

    logger = functionNode.get_logger()
    logger.info("==>>>> in logisticregression 2: " + functionNode.get_browse_path())

    # now get the input and outputs
    inputNodes = functionNode.get_child("input").get_leaves()
    for node in inputNodes:
        logger.debug("input node" + node.get_browse_path())

    outputNode = functionNode.get_child("output").get_leaves()[0]
    logger.debug("outputnode " + outputNode.get_browse_path())

    annotations = functionNode.get_child("annotations").get_leaves()
    logger.debug("no annotations: " +str(len(annotations)))

    timeNode = inputNodes[0].get_table_time_node()  # if the node is a column belonging to a time series table, we now get the time node of that table
    logger.debug("the time node is " + timeNode.get_browse_path())

    tableNode = timeNode.get_table_node()
    tableLen = tableNode.get_table_len()

    """
        now prepare the data for processing:
        
        learning:
        find all annotations with tag "learn"
        inside them take all annotations that are tagged with a tag inside the tagsMap/categoryMap, the target values start at 1
        use them for learning, where all areas that are not tagged or tagged with something not in the category Map get the tagvalue 0
        
        for scoring, we use the annoations with "score" tagged
    """

    # get the annotation map
    tagsMap = functionNode.get_child("categoryMap").get_value()  # pick the category mapping from the model

    learnIndices = []
    learnTimes = []
    scoreIndices = []
    scoreTimes = []
    # see if we have a "region" annotation (we only support one)
    for anno in annotations:
        tag = anno.get_child('tags').get_value()[0]
        if tag in ["learn","score"]:
            regionStartDate = anno.get_child("startTime").get_value()
            regionEndDate = anno.get_child("endTime").get_value()
            logger.debug(tag +"region: "+str(regionStartDate)+" "+str(regionEndDate))
            regionStartTime = date2secs(regionStartDate)
            regionEndTime = date2secs(regionEndDate)
            #regionIndices = timeNode.get_time_indices(regionStartTime, regionEndTime)
            if tag == "learn":
                learnTimes.append({"start":regionStartTime,"end":regionEndTime})
                learnIndices.extend(timeNode.get_time_indices(regionStartTime, regionEndTime))
            elif tag == "score":
                scoreTimes.append({"start":regionStartTime,"end":regionEndTime})
                scoreIndices.extend(timeNode.get_time_indices(regionStartTime, regionEndTime))


    # now prepare the training target values based on the given annotations,
    # the regions where no anno is given are set as 0
    # for simplicity we start with a training array of the full size of the table, later, we cut it
    # for the region

    training = numpy.full(tableLen,0) # set zero to all values as a padding
    groundTruth = numpy.full(tableLen,0) #set zero, used for the confusion matrix

    allAnnoIndices =[] # all indices that are inside a learn region and inside an annotation region of interest

    #indices = []  # a list of indices which give the points in time that were labelled
    #training = []  # the training values are the tags from the annoations translated via the tagsmap
    for anno in annotations:
        startTime = date2secs(anno.get_child("startTime").get_value())
        endTime = date2secs(anno.get_child("endTime").get_value())
        tag = anno.get_child('tags').get_value()[0]
        if tag in tagsMap:
            #we take annotations that have a tag which was selected in the tagsMap
            #now check if it is inside any learn area
            for region in learnTimes:
                if startTime >= region["start"] and endTime <= region["end"]:
                    #the annotation is inside this region
                    annoIndices = list(timeNode.get_time_indices(startTime,endTime))  # this gives us the indices in the table between start and end time
                    allAnnoIndices.extend(annoIndices)
                    #now set the values with fancy indexing
                    training[annoIndices] = tagsMap[tag]
                    logger.debug("set training target %s as %i",tag,tagsMap[tag])
            for region in scoreTimes:
                if startTime >= region["start"] and endTime <= region["end"]:
                    annoIndices = list(timeNode.get_time_indices(startTime, endTime))
                    groundTruth[annoIndices] = tagsMap[tag]




    #now cut the region if we have one via fancy indexing
    #training = training[learnIndices]
    training = training[allAnnoIndices]



    trainingData = []
    # now grab the values from the columns
    finiteNodes = []

    for node in inputNodes:
        values = numpy.asarray(node.get_value())
        values = values[allAnnoIndices]

        if numpy.isfinite(values).all():
            trainingData.append(list(values))
            finiteNodes.append(node)
            logger.debug("has good finite values"+node.get_name())
        else:
            logger.warning("some infinite values in "+node.get_name())
            #now pad with zero
            values[False == numpy.isfinite(values)] = 0
            trainingData.append(list(values))
            finiteNodes.append(node)
    table = numpy.stack(trainingData, axis=0)

    # now fit the model
    model = LogisticRegression()
    #model =  RandomForestClassifier(n_estimators=50,max_features=10)

    scaler = StandardScaler()
    scaler.fit(table.T)
    if scaling:
        data = scaler.transform(table.T)
    else:
        data = table.T
    model.fit(data, numpy.asarray(training))


    #
    # scoring is on "scoreregion"
    #

    # try some scoring
    logger.info("now score")
    scoreData = []
    # now grab the values from the columns
    for node in finiteNodes:
        values = node.get_value()[scoreIndices]
        values[False == numpy.isfinite(values)] = 0 #pad inf as zero
        scoreData.append(values)

    scoreTable = numpy.stack(scoreData, axis=0)

    if scaling:
        data = scaler.transform(scoreTable.T)
    else:
        data = scoreTable.T

    score = model.predict(data)


    # now write the score back to the ouput
    # we need to fill in the remainings with Nan

    scoreFill = numpy.full(tableLen, numpy.inf)
    scoreFill[scoreIndices] = score
    outputNode.set_value(list(scoreFill))

    """
    #also get the confusion matrix
    matrix = {'00':0,'01':0,'11':0,'10':0}
    for val,score in zip(groundTruth[scoreIndices],score):
        entry = str(val)+str(score)
        matrix[entry]=matrix[entry]+1
    for entry in matrix:
        matrix[entry]=float(matrix[entry])/float(len(scoreIndices))
    logger.debug("Confusion Matrix"+str(matrix))
    functionNode.get_child("confusion").set_value(matrix)
    """


    return True



def featurize(data):
    """
     put in a data table and get one back including features

    """

    #try gradient

