from system import __functioncontrolfolder
from model import date2secs
#  from tqdm import tqdm
import logging
import pandas as pd 
import os
import json
import datetime as dt
import time

previewFileTemplate = {
    "name":"preview_file",
    "type":"function",
    "functionPointer":"importer.preview_file",   # filename.functionname
    "autoReload":True,                             # set this to true to reload the module on each execution
    "children":[
        {"name":"previewdata","type":"variable"},
        {"name":"filename","type":"variable"},
        __functioncontrolfolder
    ]
}

importRunTemplate = {
    "name":"import_run",
    "type":"function",
    "functionPointer":"importer.import_run",        # filename.functionname
    "autoReload":True,                              # set this to true to reload the module on each execution
    "children":[
        {"name":"tablename","type":"variable"},     # ...
        {"name":"metadata","type":"variable"},      # ...
        __functioncontrolfolder
    ]
}

pipeline = {
    "name": "pipeline",
    "type": "folder",
    "children": [
        { "name": "imports", "type": "folder" },
        { "name": "cockpit", "type": "const", "value": "customui/importer.htm" },
        previewFileTemplate,
        { "name":"preview_observer",
          "type": "observer", "children": [           # observer for the selected variables (not the values)
            {"name": "enabled", "type": "const", "value": True},                # on by default to enable drag + drop
            {"name": "triggerCounter", "type": "variable", "value": 0},         # increased on each trigger
            {"name": "lastTriggerTime", "type": "variable", "value": ""},       # last datetime when it was triggered
            {"name": "targets", "type": "referencer", "references":["importer.preview_file.control.executionCounter"]},  # pointing to the nodes observed
            {"name": "properties", "type": "const", "value": ["value"]},  # properties to observe [“children”,“value”, “forwardRefs”]
            {"name": "onTriggerFunction", "type": "referencer"},                # the function(s) to be called when triggering
            {"name": "hasEvent", "type": "const", "value": True},               # set to true if we want an event as well
            {"name": "eventString", "type": "const", "value": "importer.preview_file.data_imported"}  # the string of the event
            ]
        },
        importRunTemplate,
    ]
}

def preview_file(iN):

    _helper_log(f"PREVIEW FILE STARTED")

    # --- define vars
    observer = iN.get_parent().get_child("preview_observer")
    event = observer.get_child("eventString")
    parentName = iN.get_parent().get_name()
    event.set_value(f"{parentName}.preview_file.data_imported")

    # --- set vars
    filename = 'upload/' + iN.get_child("filename").get_value()
    pathBase = os.getcwd()

    # --- load csv data
    dataFile = pd.read_csv(filename, nrows=5)
    previewData = dataFile.head()
    previewDataString = previewData.to_json(orient='table')

    # --- update node with preview data
    node = iN.get_child("previewdata")
    node.set_value(previewDataString)

    _helper_log(f"PREVIEW FILE FINISHED")

    # --- return
    return True

def import_run(iN):

    _helper_log(f"IMPORT STARTED")
    timeStartImport = dt.datetime.now()

    # --- define vars
    importerNode = iN.get_parent()

    # --- [vars] define
    tablename = iN.get_child("tablename").get_value()
    _helper_log(f"tablename: {tablename}")

    #  # --- create needed nodes
    importerNode.create_child('imports', type="folder")
    importsNode = importerNode.get_child("imports")

    # TODO importsNode.get_child(tablename).delete()
    importsNode.create_child(tablename, type="table")
    table = importsNode.get_child(tablename)
    table.create_child('variables', type="folder")
    table.create_child('columns', type="referencer")
    table.create_child('metadata', type="const")
    vars = table.get_child("variables")
    cols = table.get_child("columns")

    # --- read metadata and fields
    metadataRaw = iN.get_child("metadata").get_value()
    metadata = json.loads(metadataRaw)
    table.get_child("metadata").set_value(metadata)
    fields = metadata["fields"] 
    timefield = int(metadata["timefield"]) - 1
    filename = metadata["filename"]
    headerexists = metadata["headerexists"]
    filepath = 'upload/' + filename 

    # --- load csv data
    # * https://www.shanelynn.ie/python-pandas-read_csv-load-data-from-csv-files/
    # * [ ] optimize speed? https://stackoverflow.com/questions/16476924/how-to-iterate-over-rows-in-a-dataframe-in-pandas
    # * [ ] vectorize a loop https://stackoverflow.com/questions/27575854/vectorizing-a-function-in-pandas
    df = pd.read_csv(filepath)

    # --- define time list
    # * select rows and columns from dataframe https://thispointer.com/select-rows-columns-by-name-or-index-in-dataframe-using-loc-iloc-python-pandas/
    timeList = df.iloc[:,timefield].to_list()
    epochs = [date2secs(time) for time in timeList]
    print(epochs) 

    # --- import data, set vars and columns
    data = {}
    for field in fields:
        fieldno = int(field["no"]) - 1
        fieldname = field["val"]
        fieldvar = vars.create_child(fieldname, type="timeseries")
        if timefield != fieldno:
            data[fieldname] = df.iloc[ :, fieldno].to_list()
            fieldvar.set_time_series(values=data[fieldname],times=epochs)
        cols.add_references(fieldvar)
        _helper_log(f"val: {fieldname}")
        print(fieldvar) 

    _helper_log(f"IMPORT DONE (seconds: {(dt.datetime.now()-timeStartImport).seconds})")
    return True

def _helper_log(text):
    logging.warning('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    logging.warning(text)
    logging.warning('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
