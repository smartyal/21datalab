#21datalabplugin
from system import __functioncontrolfolder
import dates
import modelhelper as mh
import numpy


deleterTemplate = {
    "name": "deleter",
    "type": "function",
    "functionPointer": "clean.deleter",  # filename.functionname
    "autoReload": True,  # set this to true to reload the module on each execution
    "children": [
        {"name": "elements", "type": "referencer" },  # elements to delete (annos, event, time series)
        {"name": "whiteListAnnotationSelection", "type": "referencer"},  # pointer to annotations giving the areas
        {"name": "tags","type":"const","value":[]},          #selector of the annotation tags
        __functioncontrolfolder
    ]
}

def is_inside(annotation,annotations):
    """ check if annotation is completely inside one of the annotations"""
    start = dates.date2secs(annotation.get_child("startTime").get_value())
    end = dates.date2secs(annotation.get_child("endTime").get_value())

    for anno in annotations:
        thisStart = dates.date2secs(anno.get_child("startTime").get_value())
        thisEnd = dates.date2secs(anno.get_child("endTime").get_value())
        if thisStart<=start and thisEnd>=end:
            return True
    return False

def deleter(functionNode):
    """
        delete values, events, and annotations of a time outside of given annotation(s)
    """
    logger = functionNode.get_logger()
    logger.info("==>>>> deleter "+functionNode.get_browse_path())
    progressNode = functionNode.get_child("control").get_child("progress")


    elements = functionNode.get_child("elements").get_leaves()
    whiteList = functionNode.get_child("whiteListAnnotationSelection").get_leaves()
    tags = functionNode.get_child("tags").get_value()
    whiteList = mh.filter_annotations(whiteList,tags)

    progressNode.set_value(0)
    total = len(elements)

    for idx,element in enumerate(elements):
        progressNode.set_value(float(idx)/float(total))
        logger.debug(f"work on {element.get_browse_path()} {element.get_type()} ")

        if element.get_type()=="annotation":
            if element.get_child("type").get_value()=="time":
                if not is_inside(element,whiteList):
                    element.delete()
        elif element.get_type() == "timeseries":
            data = element.get_time_series()# get full data
            mask = mh.annotations_to_class_vector(whiteList,data["__time"], ignoreTags=[])#label for inside, nan for outside
            mask = numpy.isfinite(mask)
            values = data["values"][mask]
            times = data["__time"][mask]
            element.set_time_series(values,times)
        elif element.get_type() == "eventseries":
            data = element.get_event_series()
            mask = mh.annotations_to_class_vector(whiteList,data["__time"],ignoreTags = [])#label for inside, nan for outside
            mask = numpy.isfinite(mask)
            values = data["values"][mask]
            times = data["__time"][mask]
            element.set_event_series(values,times)
        elif element.get_type() == "variable":
            element.set_value(None)
        else:
            logger.error(f"cannot process {element.get_name()} type {element.get_type()}")


    return True