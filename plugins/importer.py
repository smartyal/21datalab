from system import __functioncontrolfolder
from model import date2secs
from tqdm import tqdm
import logging
import pandas as pd 
import os
import json
import datetime as dt
import time

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

    # --- set vars
    fileName = 'upload/' + functionNode.get_child("fileName").get_value()
    pathBase = os.getcwd()

    # --- load csv data
    dataFile = pd.read_csv(fileName)
    previewData = dataFile.head()
    previewDataString = previewData.to_json(orient='table')

    # --- update node with preview data
    node = functionNode.get_child("data_preview")
    node.set_value(previewDataString)

    # --- return
    return True

def importer_import(iN):

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
    try:
        importsNode.delete_node(tablename)
        importsNode.delete_node(f'{tablename}.variables')
        importsNode.delete_node(f'{tablename}.columns')
    except:
        print("[importer] error while trying to delete node table")
    importsNode.create_child(tablename, type="table")
    _helper_log("here") 
    table = importsNode.get_child(tablename)
    table.create_child('variables', type="folder")
    table.create_child('columns', type="referencer")
    table.create_child('metadata', type="const")
    vars = table.get_child("variables")
    cols = table.get_child("columns")
    _helper_log("there") 

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

    _helper_log(f"IMPORT DONE (seconds: {(dt.datetime.now()-timeStartImport).seconds})")
    return True

def _helper_log(text):
    logging.warning('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    logging.warning(text)
    logging.warning('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
