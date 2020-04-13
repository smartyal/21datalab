# this file contains helper functions for analytics and working with models

import numpy
import json
from model import date2secs
from scipy.ndimage import gaussian_filter

def filter_annotations(annotations, tagsFilter=[]):
    """
        Args:
            annotations: [list of Node()] the annotations to use
            tagsFilter [list of strings]: if an annotation contains one of the tagFilters, then we accept it
        Returns:
            list of accepted annotations
    """

    annosOut = []
    for anno in annotations:
        tags = anno.get_child("tags").get_value()
        for tag in tags:
            if tag in tagsFilter:
                annosOut.append(anno)
                continue
    return annosOut


def get_mask_from_interval(times,start,end):
    """
        give start and end time as epoch or iso string and a time vector, return a mask which points are inside
    """

    start= date2secs(start)
    end = date2secs(end)
    left = numpy.searchsorted(times,start) #this is the first value > start
    right = numpy.searchsorted(times,end)  #this is the first value > end
    mask = numpy.full(len(times),False)
    mask[left:right]=True
    return mask

def get_indices_from_interval(times,start,end):
    mask = get_mask_from_interval(times,start,end)
    return numpy.where(mask)[0]


def annotations_to_class_vector(annotations, times, tagsMap = {}, regionTag=None):
    """
        create a classification vector based on given time areas in the annotations
        for times where we don't classify, we return a numpy.nan
        Args:
            annotations: list of annotationNodes
            tagsMap: a dict with "tags":classId, classIds
            tagFilter: a list of strings to match, if one of them matches, we take the annotation, otherwise not

            regionTag: the tag to be used as region filter: we only take times inside annotations with the tag regionTag
                if not given, we take all, typically the region tag is "region"
    # Returns:
        {
            "values":list of class values, nan for undefined
            "__time": list of time values, this is either the input times, or a subset of the input times
        },
        tagMap: {tag:classid} the tagMap plus more entries if needed

    """
    times = numpy.asarray(times)
    values = numpy.full(len(times),numpy.nan,dtype=numpy.float64)


    if tagsMap != {}:
        #find the highestNumer
        maxClassId = max([v for k,v in tagsMap.items()])
    else:
        maxClassId = -1

    for anno in annotations:
        tag = anno.get_child("tags").get_value()[0]
        if tag == "region":
            continue
        if not anno.get_child("type").get_value() in ["time"]:
            continue # we void thresholds and others
        if tag not in tagsMap:
            maxClassId = maxClassId +1
            tagsMap[tag]= maxClassId #create entry

        classId = tagsMap[tag]

        startTime = anno.get_child("startTime").get_value()
        endTime = anno.get_child("endTime").get_value()
        indices = get_mask_from_interval(times,startTime, endTime)
        values[indices] = classId



    # now filter by region tag
    if regionTag:
        found = False
        regionFilter = numpy.full(len(times),False)
        for anno in annotations:
            tag = anno.get_child("tags").get_value()[0]
            if tag == "region":
                startTime = anno.get_child("startTime").get_value()
                endTime = anno.get_child("endTime").get_value()
                mask = get_mask_from_interval(times,startTime, endTime)
                regionFilter = regionFilter | mask
                found = True
        if found:
            values [regionFilter == False]=numpy.nan # delete the entries
        else:
            #we have no "region" found, so no more filtering
            pass

    return values




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



def build_table_2(variables,indices,imputation=["zero"], rejects=[], smoothFilter=None, diff=False,features =[]):
    """
        the imputation are the strategy for missing/non finite values:
        zero: we put a zero at the place and take the variable, if not given, the variable will be dismissed
        dismiss: we don't take the varialble at att
        marker: if set, we put a [0,1,0,0,0,..] marker variable where the missings are
        use this function for timeseries class-style
        features is a list of callbacks to be called that creates a feature vector from the data

    """
    table = []
    newVars = []
    for var in variables:

        if any (reject in var.get_browse_path() for reject in rejects):
            print(f"skip {var.get_browse_path()}")
            continue #skip this one, #these are the output, they are also part of the table, so they can appear here

        if indices !=[]:
            val = numpy.asarray(var.get_time_series()["values"], dtype=numpy.float64)[indices] # fancy indexing or mask
        else:
            val = numpy.asarray(var.get_time_series()["values"], dtype=numpy.float64)

        # what to do with missing values?
        if not numpy.isfinite(val).all():
            if "zero" in imputation:
                nonFiniteIndices = ~numpy.isfinite(val)
                val[nonFiniteIndices] = 0 # zero out the inf/nans


        if type(smoothFilter) is not type(None):
            val = gaussian_filter(val, sigma=smoothFilter)
        if diff:
            d = numpy.diff(val)
            val = numpy.append( d,d[-1])

        if features !=[]:
            for feature in features:
                feat = feature(val)
                #print("len of features",len(val),len(feat))
                table.append(feat)
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
    #print(f"confusion_percentage {confusionCount} , {totalCount} ")
    return float(confusionCount)/float(totalCount)



def movingaverage(values, window=10):
    weights = numpy.repeat(1.0, window)/window
    sma = numpy.convolve(values, weights, 'valid')
    return sma

def autocorr(x):
    result = numpy.correlate(x, x, mode='full')
    return result[result.size // 2:]