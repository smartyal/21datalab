import flask
import json
import logging
import model
import sys
import datetime
import dateutil.parser
import random
import requests
from gevent.pywsgi import WSGIServer

from flask import  render_template, render_template_string
from bokeh.client import pull_session
from bokeh.embed import server_session,server_document



'''
TODO:
have a key to add the time in the answer when query data
 - you can put the variable for time if you know it
 - you can say "addTimeValue=True" in the query to get the time as "time"=....., sometimes you don't know what is the time variable, you just have the variables


'''



#init the logger

logger = logging.getLogger("restservice")
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logfile = logging.FileHandler("./log/restservice.log")
logfile.setFormatter(formatter)
logger.addHandler(logfile)



logger.setLevel(logging.INFO)


bokehPath = "http://localhost:5006/"



web = flask.Flask(__name__)

'''

WEBCODES ---------------------
200 ok
201 ok, created
400 bad request malformed
404 not found
405 not allowed

WEBAPI -----------------------
path                    REQUEST BOY               RESPONSE BODY
POST /_create       [<createnode.json>]         [<node.json>]           ## give a list of new nodes, result contains all the created nodes  
POST /_delete       [<nodedescriptor>]          [<nodedescriptor>]      ## give list of deleted nodes back
POST /_getall       -                           [<node.json>]           ## give the whole address space
POST /setProperties   [<node.json>]               [<node.json>]         ## the node.json only contains properties to change
POST /_get          [<nodescriptor>]            [<node.json>]           ## get node including children as json
POST /_getvalue     [<nodedescriptor>]          [<values>]              ## get a list of values, not available are returned as none
POST /_getleaves    <nodedescriptor>            [<node.json>]           ## get the leaves of a referencer
GET  /pipelines      -                          [<pipeline.json>]       ## get the pipelines
POST /_load         fileName (str)              -
POST /_save         fileName (str)              -
POST /_getdata      <dataquery.json>]
POST /_appendRow     [<data.json>]
POST /_references <referencequery.json>
POST /_execute      <nodedescriptor>            //nothing                ## execute a function
GET  /templates      -                           [templatename]          ## get all available templates to be created
POST /_createTemplate  <createtemplate.json>     -                       #create a template at a path given
GET  /models         -                           [string]                #  a list of available models from the /model folder 
GET  /modelinfo      -                           <modelinfo.json>        # get the current name of the model, path etc
GEt  /embedbokeh     <urlstring>                 <bokeh session>         # pull a bokeh session for forwarding to a div, url string is eg. http://localhost:5006/bokeh_web
POST /dropnodes      <dropquery.json>                                         # inform that nodes have been dropped on the frontend on a certain widget
data:





JSONS ------------------------
nodedescriptor // a string with the nodeid (number) or the browsepath 

node.json =
{
    "name": "myname",
    "id": nodeid                        ##ignored on create request
    "parent": <nodedescriptor>
    "type":"variable",
    "value":1234,
    "children":[<node.json>]            ##not given on responses
}


createnode.json =
{
  "browsePath":"root.myder..."          #mandatory the path  
  "type":                               #mandatory 
  "value":                              #optional     
  ######  
  dont't put "children"
  
}

createtemplate.json
{
    "browsePath":"root.myfolder..."         # the path of the root of the template, this is a node to be created!
    "type": "templates.button"      # a well-known template name
}

dataquery.json
{
    nodes :[<nodedescriptor>],
    startTime : 2018.01.01T00:10:08.445+02:00 //optional
    endTime :   2018.01.01T01:10:08.445+02:00 //optional
    bins : 300
    includeTimeStamps: xxx                      //optional: if this is includes the timestamps are delivered as variable "time" in epoch style, todo: we can have different formats required in xxx
}
#example
{
    "nodes" :["root.variables.f0","root.variables.f1"],
    "startTime" : "2018.01.01T00:10:08.445+02:00",
    "endTime" :   "2018.01.01T01:10:08.445+02:00",
    "bins" : 300
}

data.json
{
    "root.folder1.var1": 1.3456,
    "root.folder1.var2": 15,
    "root.folder1.var3": -0.4,
    "root.folder1.time": 1546437120.22644
}


dataresponse.json
{   
    root.myfolder.mynode: 1.345
    root.myfolder.mynode2: -10
    time : 2018.5.6T5:9:8
    epochTime : 
}       
   
pipelines.json
{ 
  "mypipeline":{"url":"http://localhost:5005"}, //one line has the name and all the properties (we return the const-children in the model)
  "mypipeline":{"url":"http://localhost:5005","anothertab","whatistthi"}
}
 
referencequery.json
{
    "node": <nodedescriptor> # must be a referencer
    "add": [<nodedescriptors>]
    "deleteExisting" : one of True/False # if set, all existings references are deleted
    "remove" :[<nodedescriptors>]
}


modelinfo.json
{
    "name" : "myfirstModel" # the name of the model
}


dropquery.json
{
   "nodes": list of node ids
   "path": the widget on which the nodes have been dropped in the ui
}
'''



#@web.route('/',defaults={'path':''},methods=['GET','POST'])
@web.route('/<path:path>', methods=['GET', 'POST'])
def all(path):
    #print("here")
    logger.info("http request "+str(flask.request.method) +"'"+str(path)+"'" +" DATA="+str(flask.request.data))
    data = None
    response="{}" #default is empty
    responseCode = 404 # default is not found

    try:

        try:
            #parse the incoming data
            data = flask.request.data.decode('utf-8') # just the string
            data = json.loads(flask.request.data.decode('utf-8'))
        except:
            pass

        #if the path has ending /, we remove it
        if path[-1]=='/':
            path = path[:-1]

        # server all the frontend stuff: js, css etc
        if any(extension in str(path) for extension in ['.js','.css','.htm','.img','.ico','.png','.gif','.map','.svg','.wof','.ttf']):

            logger.debug(" serve html "+ str(path))
            if "styles.css" in path:
                print("hier")
            for sourceFolder in ["web","bokeh_web","bokeh_web/templates"]:
                try:
                    obj = flask.send_from_directory(sourceFolder,path)
                    return obj
                except Exception as exc:
                    logger.error("file "+ str(path)+" not found on folder"+sourceFolder)
            code = 404

        elif (str(path) == "_getall") and str(flask.request.method) in ["POST","GET"]:
            logger.debug("execute getall")
            mymodel = m.get_model_for_web()
            response = json.dumps(mymodel,indent=4)# some pretty printing for debug
            responseCode = 200

        elif (str(path) == "pipelines") and str(flask.request.method) in ["GET"]:
            logger.debug("execute get pipelines")
            try:
                pipelinesNodeIds= m.get_node('root.visualization.pipelines').get_children()
                pipelines = {}
                for pipeNode in pipelinesNodeIds:
                    pipelines[pipeNode.get_name()]= {"url":pipeNode.get_child("url").get_property("value")}
                response = json.dumps(pipelines,indent=4)# some pretty printing for debug
                responseCode = 200
            except:
                logger.error("I have no pipelines")
                responseCode = 404

        elif (str(path) == "modelinfo") and str(flask.request.method) in ["GET"]:
            logger.debug("get modelinfo")
            response = json.dumps(m.get_info(), indent=4)
            responseCode = 200

        elif (str(path) == "templates") and str(flask.request.method) in ["GET"]:
            logger.debug(" get templates")
            templates = list(m.get_templates().keys())
            logger.debug(" templates are "+str(templates))
            response = json.dumps(templates)
            responseCode = 200

        elif (str(path) == "models") and str(flask.request.method) in ["GET"]:
            logger.debug(" get templates")
            models = m.get_models()
            response = json.dumps(models)
            responseCode = 200


        elif(str(path) == "_getleaves") and str(flask.request.method) in ["POST", "GET"]:
            logger.debug("execute get forward")
            nodes = m.get_leaves(data)
            response = json.dumps(nodes, indent=4)
            responseCode = 200

        elif(str(path) == "_delete") and str(flask.request.method) in ["POST"]:
            logger.debug("delete nodes")
            result = []
            responseCode = 200
            for nodePath in data:
                delResult = m.delete_node(nodePath)
                logger.debug("deleted " +nodePath + " result: "+str(delResult))
                result.append(delResult)
                if not delResult:
                    responseCode = 401
            response = json.dumps(result, indent=4)



        elif (str(path) == "_get") and str(flask.request.method) in ["POST", "GET"]:
            logger.debug("execute get"+str(data))
            nodes = []
            for nodeDesc in data:
                resNodes = m.get_node_with_children(nodeDesc)
                print(resNodes)
                nodes.append(resNodes)
            response = json.dumps(nodes, indent=4)  # some pretty printing for debug
            logger.debug("sending"+str(len(response)))
            responseCode = 200


        elif (str(path) == "_getvalue") and str(flask.request.method) in ["POST", "GET"]:
            logger.debug("execute getvalue")
            values = []
            for nodeDesc in data:
                values.append(m.get_value(nodeDesc))
            response = json.dumps(values, indent=4)  # some pretty printing for debug
            logger.debug("sending"+response)
            responseCode = 200



        elif (str(path) == "_load") and str(flask.request.method) in ["POST"]:
            logger.debug("load model:" + data)
            result = m.load(data)
            if result:
                responseCode = 200
            else:
                responseCode = 404

        elif (str(path) == "_save") and str(flask.request.method) in ["POST"]:
            logger.debug("save to model:" + data)
            result = m.save(data)
            if result:
                responseCode = 200
            else:
                responseCode = 404


        elif (str(path)=="_appendRow"):
            logger.debug("writeRow")
            for blob in data:
                result = m.append_table(blob)
                if not result:
                    responseCode = 400
                    break
            responseCode = 200
            m.show()


        elif (str(path)=="_getdata"):
            logger.debug("get data")
            startTime = None
            endTime = None
            if set(["bins","nodes"]).issubset(set(data.keys())):
                #we have both bins and nodes
                startTime = 0
                endTime = 0
                if "startTime" in data:
                    #try to parse it, we support iso format or epoch
                    if type(data["startTime"]) is str:
                        try:
                            startTime = dateutil.parser.parse(data["startTime"])
                        except:
                            logger.info("cant parse start time")
                    else:
                        startTime = data["startTime"]
                if "endTime" in data:
                    #try to parse it, we support iso format or epoch
                    if type(data["endTime"]) is str:
                        try:
                            startTime = dateutil.parser.parse(data["endTime"])
                        except:
                            logger.info("cant parse end time")
                    else:
                        endTime = data["endTime"]

                if "includeTimeStamps" in data:
                    includeTimeStamps = data["includeTimeStamps"]
                else:
                    includeTimeStamps= None

                if "includeBackGround" in data:
                    includeBackGround = data["includeBackGround"]
                else:
                    includeBackGround = None
                try:
                    result = m.get_timeseries_table(data["nodes"],startTime=startTime,endTime=endTime,noBins=int(data["bins"]),includeTimeStamps=includeTimeStamps,format="dict",includeBackGround=includeBackGround)
                    if type(result) != type(None):
                        if includeTimeStamps:
                            pass #XXX todo: include the timestamps converted to a certain format
                            #data["nodes"].append("time")
                        response = json.dumps(result,indent = 4)
                        responseCode = 200
                    else:
                        responseData = 400
                except:
                    logger.warn("get time series tables failed",sys.exc_info())
                    responseCode = 404
            else:
                responseCode = 400 # malformed

        elif (str(path) == "_create"):
            logger.debug("create ")
            result = []
            responseCode = 201
            for blob in data:
                newNodeId = m.create_node_from_path(blob["browsePath"],blob)
                logger.debug('creating'+blob["browsePath"]+', result:'+str(newNodeId))
                result.append(newNodeId)
                if not newNodeId:
                    responseCode = 400
            response = json.dumps(result)
            responseCode = 201

        elif (str(path) == "_createTemplate") and str(flask.request.method) in ["POST"]:
            logger.debug("craete Template ")

            templates = m.get_templates()
            if data["type"] in templates:
                m.create_template_from_path(data["browsePath"],templates[data["type"]])
                responseCode = 201
            else:
                responseCode = 404



        elif (str(path) == "setProperties"):
            logger.debug("set properties ")
            responseCode = 201
            result = True
            for blob in data:
                result = result and m.set_properties(blob)
            if not result:
                responseCode = 400

        elif (str(path) == "_references"):
            logger.debug("set new references")
            result = []
            if "deleteExisting" in data and data["deleteExisting"] == True:
                m.remove_forward_refs(data["parent"])
            if "add" in data:
                result = m.add_forward_refs(data["parent"],data["add"])
            if "remove" in data:
                result = m.remove_forward_refs(data["parent"], data["remove"])
            responseCode = 201

        elif (str(path) == "_execute"):
            logger.debug("execute function")
            result =[]
            launch = m.execute_function(data)
            if launch:
                responseCode = 200
            else:
                responseCode = 404

        elif (str(path) == "_diffUpdate") and str(flask.request.method) in ["GET","POST"]:
            logger.debug("get differential update")
            if not data or data["handle"] is None:
                #this is for creating a handle
                curModel = m.get_model_for_web()
                handle = m.create_differential_handle()
                res = {"handle":handle,"model":curModel}
                response = json.dumps(res)
                responseCode = 200
            else:
                #we have a handle
                res = m.get_differential_update(data["handle"])
                if res:
                    response = json.dumps(res)
                    responseCode = 200
                else:
                    logger.error("requested handle does not exist")
                    response ="requested handle does not exist"
                    responseCode = 404

        elif (str(path)=='embedbokeh'):
            # here, we must have the correct html file for rendering including css and html coloring
            # as the index.html is not relevant anymore
            embed = """     
                <!doctype html>
                <body>
                  <link rel="stylesheet" href="templates/styles.css">
                  {{ script|safe }}
                </body>
                </html>
            """

            app_url = data['url']#'http://localhost:5006/bokeh_web'
            try:
                with pull_session(url=app_url) as session:
                    # customize session here
                    script = server_session(session_id='12345', url=app_url)
                    #script = server_document('http://localhost:5006/bokeh_web')
                    temp = render_template_string(embed, script=script)
                    return temp
            except:
                logger.error("pulling session failed")
                responseCode = 404

        elif (str(path)=="dropnodes") and str(flask.request.method) in ["POST"]:
            logger.debug("dropnodes")
            try:
                nodeIds = data["nodes"]
                #for now, we assure it's a bokeh-ts widget, as we don't have any other
                selectNode = m.get_node(data["path"]).get_child("selectedVariables")
                #also check that the dropped nodes are columns
                if type(data["nodes"]) is not list:
                    data["nodes"]=[data["nodes"]]
                for nodeid in data["nodes"]:
                    if m.get_node_info(nodeid)["type"] != "column":
                        responseCode = 404
                        raise Exception(str(nodeid)+"is not a column")
                m.add_forward_refs(selectNode.get_id(),nodeIds)
                responseCode = 201
            except:
                logger.error("can't add the variables to the widget")
                responseCode = 404

        else:
            logger.error("CANNOT HANDLE REQUEST, is unknown"+str(path))
            responseCode = 404

        logger.info("response len is"+str(len(response))+" rspcodecode"+str(responseCode))
        return flask.Response(response, mimetype="text/html"), responseCode
    except Exception as ex:
        logger.error("general error " +str(sys.exc_info()[0])+".."+str(ex))
        return flask.Response("",mimetype="text/html"),501

if __name__ == '__main__':
    m = model.Model()
    if len(sys.argv) > 1:
        if sys.argv[1] == "occupancy":
            print("starting occupany demo")
            m.create_test(2)
        elif sys.argv[1] == "dynamictest":
            print("starting the dynamic test")
            m.create_test(3)
        else:
            print("load model from disk: "+sys.argv[1])
            m.load(sys.argv[1])
    else:
        m.create_test(1)

    web.run(host='0.0.0.0', port=6001, debug=False)

    #enable this to use wsgi web server instead
    #http_server = WSGIServer(('0.0.0.0', 6001), web)
    #http_server.serve_forever()

