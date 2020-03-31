from system import __functioncontrolfolder
from model import date2secs

importPreviewTemplate = {
    "name":"importPreview",
    "type":"function",
    "functionPointer":"importer.import_preview",   #filename.functionname
    "autoReload":True,                             #set this to true to reload the module on each execution
    "children":[
        {"name":"default","type":"variable"},      # the outputs
        {"name":"data_preview","type":"variable"},
        __functioncontrolfolder
    ]
}

importWriteTemplate = {
    "name":"importWrite",
    "type":"function",
    "functionPointer":"importer.import_write",   #filename.functionname
    "autoReload":True,                             #set this to true to reload the module on each execution
    "children":[
        {"name":"default","type":"variable"},      # the outputs
        {"name":"table","type":"referencer"},      # the outputs
        __functioncontrolfolder
    ]
}

def import_preview(functionNode):
    logger = functionNode.get_logger()
    logger.info("==> import_preview hello world")

    data = {
        "time": [ "2020-01-03T08:00:00.000+02:00", "2020-01-03T08:00:00.000+02:00" ],
        "val1": [ 11.1, 12.4 ],
        "val2": [ 1, 2 ],
    }

    node = functionNode.get_child("data_preview")

    logger.info(f"==> node {node}")

    node.set_value(data)

    return True

def import_write(functionNode):
    logger = functionNode.get_logger()
    logger.info("==> import_write")

    # Node apis
    tableNode = functionNode.get_child("table")
    logger.info(f"==> tableNode {tableNode}")

    table = tableNode.get_target()
    logger.info(f"==> table {table}")

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

    return True
