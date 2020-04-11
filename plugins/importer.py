from system import __functioncontrolfolder
from model import date2secs
import pandas as pd 
import os

importerPreviewTemplate = {
    "name":"importerPreview",
    "type":"function",
    "functionPointer":"importer.importer_preview",   # filename.functionname
    "autoReload":True,                             # set this to true to reload the module on each execution
    "children":[
        {"name":"default","type":"variable"},      # the outputs
        {"name":"data_preview","type":"variable"},
        __functioncontrolfolder
    ]
}

importerImportTemplate = {
    "name":"importImport",
    "type":"function",
    "functionPointer":"importer.importer_import",     # filename.functionname
    "autoReload":True,                             # set this to true to reload the module on each execution
    "children":[
        {"name":"table","type":"table"},      # the outputs
        __functioncontrolfolder
    ]
}

def importer_preview(functionNode):

    # --- initialize logger
    logger = functionNode.get_logger()
    logger.info("==> importer_preview hello world")

    # --- set some example data
    data = {
        "time": [ "2020-01-03T08:00:00.000+02:00", "2020-01-03T08:00:00.000+02:00" ],
        "val1": [ 11.1, 12.4 ],
        "val2": [ 1, 2 ],
    }

    # --- get filename
    fileName = 'upload/' + functionNode.get_child("fileName").get_value()
    logger.info(f"==> fileName {fileName}")

    # --- read file
    pathBase = os.getcwd()
    logger.info(f"==> pathBase {pathBase}")

    dataFile = pd.read_csv(fileName)
    previewData = dataFile.head()
    logger.info(f"==> previewData {previewData}")
    previewDataType = type(previewData)
    logger.info(f"==> previewDataType {previewDataType}")
    previewDataString = previewData.to_json(orient='table')


    # --- update node with preview data
    node = functionNode.get_child("data_preview")
    logger.info(f"==> node {node}")
    node.set_value(previewDataString)

    # --- return
    return True

def importer_import(functionNode):
    logger = functionNode.get_logger()
    logger.info("=========================================================> importer_import")

    logger.info(f"=========================================================> functionNode {functionNode}")

    # Node apis
    table = functionNode.get_child("table")
    logger.info(f"========================================================> tableNode {table}")

    #  table = tableNode.get_target()
    logger.info(f"========================================================> table {table}")

    vars = table.get_child("variables")
    cols = table.get_child("columns")

    # delete var (later)

    # add var
    val1 = vars.create_child("val1", type="timeseries")
    val2 = vars.create_child("val2", type="timeseries")

    # add cols
    cols.add_references([ val1, val2 ])

    # create values
    data = {
        "time": [ "2020-01-03T08:00:00.000+02:00", "2020-01-03T09:00:00.000+02:00" ],
        "val1": [ 11.1, 12.4 ],
        "val2": [ 1, 2 ],
    }

    # list comprehension
    epochs = [date2secs(time) for time in data["time"]]

    # set values
    val1.set_time_series(values=data["val1"],times=epochs)
    val2.set_time_series(values=data["val2"],times=epochs)

    logger.info(f"========================================================> IMPORTER DONE")

    return True
