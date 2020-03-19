from system import __functioncontrolfolder
from model import date2secs

importPreviewTemplate = {
    "name":"importPreview",
    "type":"function",
    "functionPointer":"importer.import_preview",   #filename.functionname
    "autoReload":True,                             #set this to true to reload the module on each execution
    "children":[
        {"name":"default","type":"variable"},      # the outputs
        __functioncontrolfolder
    ]
}

def import_preview(functionNode):
    logger = functionNode.get_logger()
    logger.info("==> import_preview hello world")
    return True
