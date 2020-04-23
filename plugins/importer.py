from system import __functioncontrolfolder
from model import date2secs
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
    model = iN.get_model()
    tablename = model.get_node("root").get_child('importer').get_child('tablename').get_value()
    table = model.get_node("root").get_child('imports').get_child(tablename)

    # --- create needed nodes
    model.delete_node(f'root.imports.{tablename}.variables')
    model.delete_node(f'root.imports.{tablename}.columns')
    table.create_child('variables', type="folder")
    table.create_child('columns', type="referencer")
    vars = table.get_child("variables")
    cols = table.get_child("columns")

    # --- read metadata and fields
    metadataRaw = table.get_child('metadata').get_value()
    metadata = json.loads(metadataRaw)
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

    # --- log
    _helper_log(f"filename: {filename}")
    _helper_log(f"timefield: {timefield}")
    _helper_log(f"fields: {fields}")
    _helper_log(f"data: {data}")
    #  _helper_log(f"filepath: {filepath}")
    #  _helper_log(f"dataFrame: {df}")
    #  _helper_log(f"timeList: {timeList}")

    for attr, value in data.items():
        print(attr, value)

    #  # create values
    #  data = {
    #      "time": [ "2020-01-03T08:00:00.000+02:00", "2020-01-03T09:00:00.000+02:00" ],
    #      "val1": [ 11.1, 12.4 ],
    #      "val2": [ 1, 2 ],
    #  }

    #  # list comprehension
    #  epochs = [date2secs(time) for time in data["time"]]

    #  # set values
    #  val1.set_time_series(values=data["val1"],times=epochs)
    #  val2.set_time_series(values=data["val2"],times=epochs)

    time.sleep(1)
    _helper_log(f"IMPORT DONE (seconds: {(dt.datetime.now()-timeStartImport).seconds})")
    return True

def _helper_log(text):
    logging.warning('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    logging.warning(text)
    logging.warning('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

#  val1 = vars.create_child("val1", type="timeseries")
#  val2 = vars.create_child("val2", type="timeseries")
#  cols.add_references([ val1, val2 ])
#  for index, row in df.iterrows():
    #  print(row[0])

