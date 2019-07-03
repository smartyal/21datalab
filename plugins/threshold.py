
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

import numpy
from system import __functioncontrolfolder
from model import date2secs



thresholdScorer= {
    "name":"thresholdScorer",
    "type":"function",
    "functionPointer":"threshold.threshold_scorer",   #filename.functionname
    "autoReload":True,                                 #set this to true to reload the module on each execution
    "children":[
        {"name":"input","type":"referencer"},                  # the output column
        {"name":"output","type":"referencer"},
        {"name":"streaming","type":"const","value":False},    #if set to true, we only update the values in the output which are not finite
        {"name":"annotations","type":"referencer"},             #the user annotations
        __functioncontrolfolder
    ]
}


def threshold_scorer(functionNode):

    """
        # the threshold scorer can be used in standard or streaming,
        # if used in streaming (streaming = True), we only set the missing values in the output
        # (the points which are numpy.inf)
        # it can evaluate just one input or multiple
        # for multiple: it takes the order of the inputs the same as the outputs
        # the output is inf for no problem and a value for problem
        # currently, streamingMode is not supported
    """

    logger = functionNode.get_logger()
    logger.info(f">>>> in threshold_scorer {functionNode.get_browse_path()}")

    streamingMode = functionNode.get_child("streaming").get_value()

    #now get the input and outputs, check if number is the same
    inputNodesList = functionNode.get_child("input").get_leaves()
    outputNodesList =  functionNode.get_child("output").get_leaves()
    if len(inputNodesList) != len(outputNodesList):
        logger.error(f"input len {len(inputNodesList)} does not match output len {len(outputNodesList)}")
        return False

    inputNodes = {node.get_id():node for node in inputNodesList} # {nodeid:nodeObject}
    outputNodes ={node.get_id():node for node in outputNodesList}  # {nodeid:nodeObject}
    inoutNodes = {input.get_id():output for input,output in zip(inputNodesList,outputNodesList)}

    tableLen = len(inputNodes[list(inputNodes.keys())[0]].get_value())

    # get annotations remove all which we don't need
    # prepare a dict of {annotationId: {"annotation":annoobject,"input":inputobjece","output"
    annotationsList =  functionNode.get_child("annotations").get_leaves()
    #annotations = {node.get_id():node for node in annotationsList}
    thresholds = {}
    for anno in functionNode.get_child("annotations").get_leaves():
        if anno.get_child('tags').get_value()[0] == "threshold":
            targetNodeId = anno.get_child("variable").get_leaves()[0].get_id()
            if targetNodeId in inputNodes:
                #this annotation is a threshold and points to one of our inputs, we take it
                thresholds[anno.get_id()] = {"annotation":anno,"input":inputNodes[targetNodeId],"output":inoutNodes[targetNodeId]}

    if not thresholds:
        logger.error(f"we have no annotations for the thresholds of our variables")
        return False



    #now we have in thresholds what we have to process
    for thresholdId,info in thresholds.items():
        values = info["input"].get_value()
        min = info["annotation"].get_child("min").get_value()
        max = info["annotation"].get_child("max").get_value()

        score = numpy.full(tableLen,numpy.inf)

        if type(min) is type(None):
            min = -numpy.inf
        if type(max) is type(None):
            max = numpy.inf

        #set an numpy.inf where the score is ok and the value of the data where the score is not ok
        score = numpy.where(numpy.logical_and(values > min,values<max), numpy.inf, values)
        info["output"].set_value(score)


    return True
