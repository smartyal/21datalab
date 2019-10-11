# this file contains helper functions for analytics and working with models

import numpy
import json

def annotations_to_vector(annotations, timeNode, inMap={}):
    """
        converts a list of annotations into a label vector containing
        * a number where the annotations  give a label and
        * inf where no label is given
        Args:
            annotations: a list of node type annotations
            timeNode: the time node of the table, is needed to find the time indices
            for given times from the annotations
            inMap: a map with "tag":value entries to be used during the conversion, if not given, we will create one

        Returns: (map, labelvector)
            map: a dict of "tag":value with the tags found in the annotaions
            labelvector: a vector containing inf where no label was given with the annotations

            get annotations, create a map and one column holding the annotations
    totalLen: the len of the columns
    """
    values = numpy.full(len(timeNode.get_value()), numpy.inf, dtype=numpy.float64)
    #print(f"map {inMap}")
    if inMap == {}:
        map ={}
        mapValue = 1
        createMap = True
    else:
        createMap = False
        map = inMap

    for idx, anno in enumerate(annotations):
        if not idx%100:
            print(f"index {idx} of {len(annotations)}"+"\r",sep=' ', end='', flush=True)
        tag = anno.get_child('tags').get_value()[0]
        if tag not in map:
            if createMap:
                map[tag] = mapValue
                mapValue += 1
            else:
                print(f"tag {tag} not in map")
                return None,None
        value = map[tag]
        startTime = anno.get_child("startTime").get_value()
        endTime = anno.get_child("endTime").get_value()
        indices = timeNode.get_time_indices(startTime, endTime)
        values[indices] = value  # fancy indexing
    return values, map



def build_table(variables,indices,imputation=["zero"], rejects=[]):
    """
        the imputation are the strategy for missing/non finite values:
        zero: we put a zero at the place and take the variable, if not given, the variable will be dismissed
        dismiss: we don't take the varialble at att
        marker: if set, we put a [0,1,0,0,0,..] marker variable where the missings are

    """
    table = []
    newVars = []
    for var in variables:

        if any (reject in var.get_browse_path() for reject in rejects):
            print(f"skip {var.get_browse_path()}")
            continue #skip this one, #these are the output, they are also part of the table, so they can appear here

        if indices !=[]:
            val = numpy.asarray(var.get_value(), dtype=numpy.float64)[indices] # fancy indexing or mask
        else:
            val = numpy.asarray(var.get_value(), dtype=numpy.float64)
        # what to do with missing values?
        if not numpy.isfinite(val).all():
            if "zero" in imputation:
                nonFiniteIndices = ~numpy.isfinite(val)
                val[nonFiniteIndices] = 0 # zero out the inf/nans
                table.append(val)
                newVars.append(var)
            if "marker" in imputation:
                table.append(numpy.asarray(nonFiniteIndices,dtype=numpy.float64)) #additional marker
                newVars.append(var)
        else:
            table.append(val)
            newVars.append(var)
    Table =  numpy.stack(table, axis=0).T
    print(f"build_table() returns with table size {Table.shape}, numer of vars:{len(newVars)}")
    return Table,newVars


def confusion_percentage(confusionMatrix):
    totalCount = 0
    confusionCount = 0
    for row,rowIndex in zip(confusionMatrix,range(len(confusionMatrix))):
        for column, columnIndex in zip(row,range(len(row))):
            if columnIndex != rowIndex:
                confusionCount = confusionCount + column
            totalCount = totalCount + column
    print(f"confusion_percentage {confusionCount} , {totalCount} ")
    return float(confusionCount)/float(totalCount)