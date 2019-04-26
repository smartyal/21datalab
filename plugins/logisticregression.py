
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
    print("==>>>> in logisticregression",functionNode.get_browse_path())

    #now get the input and outputs
    inputNodes = functionNode.get_child("input").get_leaves()
    for node in inputNodes:
        print("input node",node.get_browse_path())

    outputNode = functionNode.get_child("output").get_leaves()[0]
    print("outputnode",outputNode.get_browse_path())

    annotations = functionNode.get_child("annotations").get_leaves()
    print("annotations")
    if annotations:
        for anno in annotations:
            print("annotation",anno.get_browse_path())

    timeNode = inputNodes[0].get_table_time_node()   #if the node is a column belonging to a time series table, we now get the time node of that table
    print ("the time node is",timeNode.get_browse_path())

    """
        now prepare the data for processing:
        * make a map (tags of the annotations vs class value) put that map in the model
        for the training phase
        1.1) take the annotated areas, collect all start and end times and get all indices of time inside the annotations
        1.2) make a map (tag vs class value) put that map in the model
        1.3) cut out the input data from the variable based on the indices from 1.1)
        1.4) train the model
        1.5) score on the full data
        1.6) write back the score to the output
    """

    #make the annotation map
    tags = set()
    for anno in annotations:
        tags.add(anno.get_child('tags').get_value()[0]) # we expect the annotation to have a "tags" field and we only take the first tag
    print("now the tags are",tags)
    tagsMap = functionNode.get_child("categoryMap").get_value()# pick the category mapping from the model


    indices = [] # a list of indices which give the points in time that were labelled
    training =[]   #the training values are the tags from the annoations translated via the tagsmap
    for anno in annotations:
        startTime = anno.get_child("startTime").get_value()
        endTime = anno.get_child("endTime").get_value()
        annoIndices = list(timeNode.get_time_indices(startTime,endTime))
        annoValue = tagsMap[anno.get_child('tags').get_value()[0]]
        annoValues = [annoValue]*len(annoIndices)
        indices.extend(annoIndices)
        training.extend(annoValues)
        #print("found indices for annot",anno.get_browse_path()," the indices are",str(indices))

    print("indices,values",indices,training)

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

    #try some scoring
    print("score now again")
    scoreData = []
    # now grab the values from the columns
    for node in inputNodes:
        scoreData.append(node.get_value())
    scoreTable = numpy.stack(scoreData, axis=0)

    score = model.predict(scoreTable.T)
    #now write the score back to the ouput
    outputNode.set_value(list(score))


    return
