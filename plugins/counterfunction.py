





counterFunctionTemplate = {
        "name":"counterFunction",
        "type":"function",
        "functionPointer":"counterfunction.counterfkt",   #filename.functionname
        "autoReload":False,                                 #set this to true to reload the module on each execution
        "children":[
            {"name":"status","type":"variable","value":"idle"},     # one of ["finished","running"]
            {"name":"progress","type":"variable","value":0},          # a value between 0 and 1
            {"name":"result","type":"variable","value":"ok"},       # of ["ok","error","pending" or a last error message]
            {"name":"output","type":"variable","value":0},                  # the outputs
            {"name":"signal","type":"variable","value":"nosignal"}# of ["nosignal","interrupt"]
        ]
}






def counterfkt(functionNode):
    print("==>>>> in counterfkt",functionNode.get_browse_path())

    output = functionNode.get_child("output")
    output.set_value(output.get_value()+1)

    return True