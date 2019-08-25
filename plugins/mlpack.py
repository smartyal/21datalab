from system import __functioncontrolfolder



mlPackTemplate= {
    "name":"mlPack",
    "type":"function",
    "functionPointer":"mlpack.ml_pack",   #filename.functionname
    "autoReload":True,                                 #set this to true to reload the module on each execution
    "children":[
        #inputs
        {"name":"classAnnotations","type":"referencer"},                    # the user annotations
        {"name":"annotationsFilter","type":"const","value":[]},             # list of string with positive match filter e.g. ["idle","run"], if empty, no filtering
        {"name":"learnAnnotations","type":"referencer"},                    # annotations containing a "region" tag to filter the learn area
        {"name":"scoreAnnotations","type":"referencer"},                    # annotations containing a "region" tag to filter the score area
        {"name":"inputDataTable","type":"referencer"},                      # pointer to the data table
        {"name":"variablesFilter","type":"const","value":[]},               # list of positive match filter, if empty no filteringa
        {"name":"algorithm","type":"const","value":"logreg"},               # selector for the ml algorithm, one of ["logreg"...
        {"name":"parameter","type":"const","value":{"k":5}},                # parameter dict for the algorithm
        #outputs
        {"name":"categoryMap","type":"variable","value":{"idle":0,"run":1}},      #value mapper for the classifiction
        {"name":"score","type":"column","value":[]},                        # the classification score
        {"name":"confidence","type":"column","value":[]},                    # the classificatino confidence measure/class probability
        __functioncontrolfolder
    ]
}






def ml_pack(functionNode):

    logger = functionNode.get_logger()
    logger.info("==>>>> in ml_pack, nothing to do  "+functionNode.get_browse_path())
    return True

