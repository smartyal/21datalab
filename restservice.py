import argparse
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
import uuid
from bs4 import BeautifulSoup
import re
import traceback

from flask import  render_template, render_template_string
from bokeh.client import pull_session
from bokeh.embed import server_session,server_document
import numpy #for _Getvalue

# needed for upload
from flask import Flask, flash, request, redirect, url_for
from werkzeug.utils import secure_filename
import os
import argparse



UPLOAD_FOLDER = './upload'

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



logger.setLevel(logging.DEBUG)


bokehPath = "http://localhost:5006/"



web = flask.Flask(__name__)

# check if the upload folder exists, create it otherwise
if not os.path.isdir(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)
web.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

'''

WEBCODES ---------------------
200 ok
201 ok, created
400 bad request malformed
404 not found
429 too many requests
405 not allowed

WEBAPI -----------------------
path                    REQUEST BOY               RESPONSE BODY
POST /_create       [<createnode.json>]         [<node.json>]           ## give a list of new nodes, result contains all the created nodes, if exists, we modify instead  
POST /_delete       [<nodedescriptor>]          [<nodedescriptor>]      ## give list of deleted nodes back
POST /_getall       -                           [<node.json>]           ## give the whole address space, fof colums and files we get "len 34"
POST /_getallhashed   -                         [<node.json>]           ## give the whole address space, for columns and files we get a hash
POST /_getbranch    <nodedeccripttor>           {node.json}             ## get a part of the model
POST _getbranchpretty <nodedesciptor>           {prettybranch.json}     ## get a branch but easy internal access 
POST /_getbranchpretty <branchquery.json>       {prettybranch.json}     ## get a branch but easy internal access also giving more options
POST /_getnodes         <getnodes.json>         <getNodesresponse.json> ## various ways to query nodes
POST /setProperties   [<node.json>]               [<node.json>]         ## the node.json only contains properties to change
POST /_get          [<nodescriptor>]            [<node.json>]           ## get node including children as json
POST /_getvalue     [<nodedescriptor>]          [<values>]              ## get a list of values, not available are returned as none
POST /_getleaves    <nodedescriptor>            [<node.json>]           ## get the leaves of a referencer
GET  /pipelines      -                          [<pipeline.json>]       ## get the pipelines
POST /_load         fileName (str)              -
POST /_save         fileName (str)              -
POST /_getdata      <dataquery.json>]
POST /_appendRow     [<data.json>] #deprecated
POST /_insert       <datablob.json>
POST /_references <referencequery.json>                                  ## adjust references, details see json
POST /_execute      <nodedescriptor>            //nothing                ## execute a function
GET  /templates      -                           [templatename]          ## get all available templates to be created
POST /_createTemplate  <createtemplate.json>     -                       #create a template at a path given
GET  /models         -                           [string]                #  a list of available models from the /model folder 
GET  /modelinfo      -                           <modelinfo.json>        # get the current name of the model, path etc
GEt  /embedbokeh     <urlstring>                 <bokeh session>         # pull a bokeh session for forwarding to a div, url string is eg. http://localhost:5006/bokeh_web
POST /dropnodes      <dropquery.json>                                    # inform that nodes have been dropped on the frontend on a certain widget
POST /move           <movequery.json>                                    # moves nodes to new parent or/and create new references
POST /_getlayout     <layoutquery.json>          [html section]          # query the dynamic content of a layout part of the page
POST /_setlen        <setlenquery.json>           -                      # adjust the len of a column, extensions are inf-padded
POST /_push          [<nodedict.json>]                                   # push a list of nodes into the model, we accept the full dict, no checking whatsoever !! dangerous
GET  /_upload        -                          [<fileinfo.json>]        # get the list of files in the /upload folder
POST /_upload       <jquery file upload>                                 # upload files via jquery file upload module-style
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
  "targets: [desc,desc]                 #optional for referencers to create 
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

datablob.json
{
    table:"root.table",
    blobs:
        [{
            "var1": [1.3456,2,3]
            "var2": [15,16,17]
            "var3": [-0.4,0,0]
            "__time": [1546437120.2,1546437121.2,1546437122.2]
        },
        {...},..
        ]
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
    "parent": <nodedescriptor> # must be a referencer
    "add": [<nodedescriptors>] # always a list!!
    "deleteExisting" : one of True/False # if set, all existings references are deleted
    "remove" :[<nodedescriptors>] # always a list!!, we also delete duplicate references if they exist
}

movequery.json
{
    "nodes": [<nodedescriptor>]        # nodes to be moved
    "parent" <nodedescriptor>          # new parent for the nodes
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

layoutquery.json
{
    "layoutNode": nodedescriptor of the node in the layout section 
}

setlenquery.json
{
    <desc>:len,     # a nodedescriptor and the new len to set
    <desc>:len,     
}

fileinfo.json
{
    "name": filename,
    "time": string: time in the file system
}

prettybranch.json
//formatting a branch in a easy accessible way like
branch["visualization"]["workbench"]["hasAnnotation"][".properties]["value"]
{
    ".properties":
    {
        "value":1234,
        "type":"const
        "child2":
        { 
        ...
        }
    }
    "child1":
    "child2":

}
branchquery.json
{
    node:<desc>
    depth:x     //give a depth of the branch resolving
    ignore : ["observer"] ignore all nodes (and their children) containins "observer"
}


getnodes.json
{
    nodes : [<desc>] a list of nodes
    resultKey: one of "id", "browsePath"
    includeLongValues: True/False 
}
getNodesresponse.json
{
    node:nodedict
}

'''

# Special handler for Server Sent Events
@web.route('/event/stream')
def event_stream_handler():
    # Create a new Observer
    observer = m.create_observer()

    # Start processing the new events and send them to the client
    return flask.Response(observer.get_event(), mimetype="text/event-stream")

#@web.route('/',defaults={'path':''},methods=['GET','POST'])
@web.route('/<path:path>', methods=['GET', 'POST'])
def all(path):

    requestStartTime = datetime.datetime.now()
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
            sourceFolders = ["web","bokeh_web","bokeh_web/templates"]
            sourceFolders.extend(plugin_directories)
            for sourceFolder in sourceFolders:
                try:
                    obj = flask.send_from_directory(sourceFolder,path)
                    return obj
                except Exception as exc:
                    pass
                    #logger.error("file "+ str(path)+" not found on folder"+sourceFolder)
            logger.error(f"file  {path}  not found on folders {sourceFolders}")
            code = 404

        elif (str(path) == "_getall") and str(flask.request.method) in ["POST","GET"]:
            logger.debug("execute getall")
            mymodel = m.get_model_for_web()
            response = json.dumps(mymodel,indent=4)# some pretty printing for debug
            responseCode = 200

        elif (str(path) == "_getallhashed") and str(flask.request.method) in ["POST","GET"]:
            logger.debug("execute getall hashed")
            mymodel = m.get_model_for_web(getHash=True)
            response = json.dumps(mymodel,indent=4)# some pretty printing for debug
            responseCode = 200

        elif (str(path) == "_getbranch") and str(flask.request.method) in ["POST","GET"]:
            logger.debug("get branch")
            mymodel = m.get_branch(data)
            response = json.dumps(mymodel, indent=4)  # some pretty printing for debug
            responseCode = 200

        elif (str(path) == "_getnodes") and str(flask.request.method) in ["POST","GET"]:
            logger.debug(f"getnodes")
            includeLong = data["includeLongValues"]
            key = data["resultKey"]
            response = {}
            for node in data["nodes"]:
                dic=m.get_node_info(node,excludeValue=True)
                if key == "browsePath":
                    response[m.get_browse_path(node)]=dic
            response = json.dumps(response, indent=4)  # some pretty printing for debug
            responseCode = 200



        elif (str(path) == "_getbranchpretty") and str(flask.request.method) in ["POST","GET"]:
            logger.debug(f"get branch pretty {data}")
            if type(data) is str:
                mymodel = m.get_branch_pretty(data)
            elif type(data) is dict:
                ignore = []
                if "ignore" in data:
                    ignore = data["ignore"]
                mymodel= m.get_branch_pretty(data["node"],data["depth"],ignore)
            response = json.dumps(mymodel, indent=4)  # some pretty printing for debug
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
            #additionally, we provide browsepaths for the forward ids of referencers
            for node in nodes:
                if "forwardRefs" in node:
                    node["forwardPaths"]=[m.get_browse_path(id) for id in node["forwardRefs"]]
                if "children" in node:
                    for child in node["children"]:
                        child["forwardPaths"] = [m.get_browse_path(id) for id in child["forwardRefs"]]
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
            try:
                for nodeDesc in data:
                    value = m.get_value(nodeDesc)
                    if type(value) is numpy.ndarray:
                        value = list(value)
                    values.append(value)  # a list of lists
                response = json.dumps(values, indent=4)  # some pretty printing for debug
            except Exception as ex:
                logger.error("problem get value")
            logger.debug("sending "+str(len(response)))
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


        elif (str(path)=="_insert"):
            logger.debug("insert Blobs")
            table = data["table"]
            blobs = data["blobs"]
            result =  m.time_series_insert_blobs(table,blobs)
            if not result:
                responseCode = 400
            else:
                responseCode = 200
                #m.show()


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
                if "includeIntervalLimits":#we include one more data point left and right of the actal start and end time
                    includeIntervalLimits = True
                else:
                    includeIntervalLimits = False

                try:
                    #result = m.get_timeseries_table(data["nodes"],startTime=startTime,endTime=endTime,noBins=int(data["bins"]),includeTimeStamps=includeTimeStamps,format="dict",includeBackGround=includeBackGround)
                    result = m.time_series_get_table(data["nodes"], start=startTime, end=endTime, noBins=int(data["bins"]), format="flat",toList=True,includeIntervalLimits=includeIntervalLimits)
                    if type(result) != type(None):
                        if includeTimeStamps:
                            pass #XXX todo: include the timestamps converted to a certain format
                            #data["nodes"].append("time")
                        response = json.dumps(result,indent = 4)
                        responseCode = 200
                    else:
                        responseData = 400
                except Exception as ex:
                    logger.error("get time series tables failed"+str(ex)+str(sys.exc_info()))
                    responseCode = 404
            else:
                responseCode = 400 # malformed

        elif (str(path) == "_create"):
            logger.debug("create ")
            result = []
            responseCode = 201
            for blob in data:
                #check if new or modification
                id = m.get_id(blob["browsePath"])
                if id:
                    #this is a modification
                    adjust = m.set_properties(blob)
                    result.append(id)
                else:
                    targets = []
                    if "targets" in blob:
                        targets = blob["targets"]
                        del blob["targets"]
                    newNodeId = m.create_node_from_path(blob["browsePath"],blob)
                    if targets:
                        m.add_forward_refs(newNodeId,targets)
                    logger.debug('creating'+blob["browsePath"]+', result:'+str(newNodeId))
                    result.append(newNodeId)
                    if not newNodeId:
                        responseCode = 400
            response = json.dumps(result)
            responseCode = 201

        elif (str(path) == "_push") and str(flask.request.method) in ["POST"]:
            m.push_nodes(data)
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
            m.lock_model()
            m.disable_observers() #avoid intermediate events
            if "deleteExisting" in data and data["deleteExisting"] == True:
                m.remove_forward_refs(data["parent"])
            if "add" in data:
                result = m.add_forward_refs(data["parent"],data["add"])
            if "remove" in data:
                result = m.remove_forward_refs(data["parent"], data["remove"],deleteDuplicates=True)
            m.enable_observers()
            m.release_model()
            m.notify_observers([m.get_id(data["parent"])],"forwardRefs")
            responseCode = 201

        elif (str(path) == "_execute"):
            logger.debug(f"execute function {data} (start the function thread)")
            result =[]
            launch = m.execute_function(data)
            if launch==True:
                responseCode = 200
            elif launch == "busy":
                responseCode = 429
            else:
                responseCode = 404

        elif (str(path) == "_diffUpdate") and str(flask.request.method) in ["GET","POST"]:

            if not data or data["handle"] is None:

                #this is for creating a handle
                curModel = m.get_model_for_web()
                handle = m.create_differential_handle()
                logger.debug("create new differential update, return handle:"+handle)
                res = {"handle":handle,"model":curModel}
                response = json.dumps(res)
                responseCode = 200
            else:
                #we have a handle
                logger.debug("get differential update with handle:"+data["handle"])
                res = m.get_differential_update(data["handle"])
                if res:
                    logger.debug("return diff update from :"+data["handle"]+"=>" + res["handle"]+"data"+json.dumps(res))
                    response = json.dumps(res)
                    responseCode = 200
                else:
                    logger.error("requested handle does not exist"+data["handle"])
                    response ="requested handle does not exist"
                    responseCode = 404

        elif (str(path)=='embedbokeh'):
            # here, we must have the correct html file for rendering including css and html coloring
            # as the index.html is not relevant anymore
            embed = """     
                <!doctype html>
                <body>
                  <link rel="stylesheet" href="templates/styles.css">
                  <script>{% include 'moment.min.js.js' %}</script>
                  <script>{% include 'moment-timezone-with-data.min.js' %} </script>
                  {{ script|safe }}
                </body>
                </html>
            """

            app_url = data['url']#'http://localhost:5006/bokeh_web'
            try:
                if 1==0:
                    #this is the old style pulling the session, both work only for localhost
                    with pull_session(url=app_url) as session:
                        # customize session here
                        #script = server_session(session_id='12345', url=app_url)
                        logger.debug("bokeh pull_session done")
                        script= server_session(session_id=session.id, url=app_url)
                        logger.debug("bokeh server_session() done")
                        #script = server_document('http://localhost:5006/bokeh_web')
                        temp = render_template_string(embed, script=script)
                        response = temp
                        responseCode = 200
                        #return temp
                else:
                    script = server_session(session_id=str(uuid.uuid4().hex), url=app_url)
                    temp = render_template_string(embed, script=script)
                    response = temp
                    responseCode = 200


            except Exception as ex:
                logger.error("pulling session failed"+str(ex)+str(sys.exc_info()[0]))
                responseCode = 404

        elif (str(path)=="dropnodes") and str(flask.request.method) in ["POST"]:
            logger.debug("dropnodes")
            try:
                nodeIds = data["nodes"]
                #check which type of widget we have to work on
                if  m.get_node(data["path"]).get_child("widgetType").get_value() == "timeSeriesWidget":
                    selectNode = m.get_node(data["path"]).get_child("selectedVariables") # pick the referencer from the widget
                    #also check that the dropped nodes are columns
                    if type(data["nodes"]) is not list:
                        data["nodes"]=[data["nodes"]]
                    newNodesIds = []
                    for nodeid in data["nodes"]:
                        if m.get_node_info(nodeid)["type"] not in ["column","timeseries"]:
                            logger.warning("we ignore this node, is not a colum"+str(nodeid))
                        else:
                            newNodesIds.append(m.get_id(nodeid))
                    #the nodes are columns
                    logger.debug("now adding new nodes to the widget"+str(newNodesIds))
                    #first check, if we have this one already, if so, we don't add it again
                    leaves=selectNode.get_leaves_ids()
                    newRefs = [id for id in newNodesIds if id not in leaves]
                    m.add_forward_refs(selectNode.get_id(),newRefs)
                responseCode = 201
            except Exception as ex:
                logger.error("can't add the variables to the widget"+str(ex)+str(sys.exc_info()[0]))
                responseCode = 404

        elif (str(path)=="move") and str(flask.request.method) in ["POST"]:
            logger.debug("move")
            try:
                moveResult = m.move(data["nodes"],data["parent"])
                responseCode = 200
            except Exception as ex:
                logger.error("can't move"+str(ex)+str(sys.exc_info()[0]))
                responseCode = 404

        elif (str(path)=="_getlayout") and str(flask.request.method) in ["POST","GET"]:
            logger.debug("get layout")
            try:
                fileName = m.get_value(data['layoutNode'])
                with open("web/customui/"+fileName) as fp:
                    soup = BeautifulSoup(fp, "lxml")
                    divs = soup.find_all(
                        id=re.compile("^ui-component"))  # find all divs that have a string starting with "ui-component"
                    for div in divs:
                        uiinfo = json.loads(div.attrs['uiinfo'])
                        try:
                            #now find the widget by looking into the model
                            widgetType = m.get_node(uiinfo['component']+'.model').get_leaves()[0].get_child("widgetType").get_value()
                            if widgetType == "timeSeriesWidget":
                                #this is a bokeh time series widget, so we must do some things here
                                port = m.get_node(uiinfo['component']+'.settings').get_value()["port"]
                                #now get the host under which the client sees me:
                                host = flask.request.host.split(':')[0]
                                #script = server_session(session_id=str(uuid.uuid4().hex), url="http://localhost:"+str(port)+"/bokeh_web")
                                script = server_document(url="http://"+host+":"+str(port)+"/bokeh_web", relative_urls=False, resources='default',
                                                arguments=None)
                                #script = script.encode('utf-8') # due to problem with "&"
                                scriptHtml = BeautifulSoup(script, "lxml")
                                scriptTag = scriptHtml.find("script")
                                scriptSource = scriptTag["src"]
                                scriptId = scriptTag["id"]
                                scriptinsert = scriptTag.prettify(formatter=None)

                                scriptTag = soup.new_tag("script",src=scriptSource,id=scriptId)
                                uiinfo["droppath"]=m.get_node(uiinfo['component']+'.model').get_leaves()[0].get_browse_path()
                                div.append(scriptTag)
                                div.attrs['uiinfo']=json.dumps(uiinfo)
                            else:
                                logger.error("unsupported widget type"+str(widgetType))
                            print(uiinfo)
                        except Exception as ex:
                            logger.error("can't get layout component" + str(uiinfo['component']))
                response = str(soup)
                response=response.replace('&amp;','&') # hack: can't get beautifulsoup to suppress the conversion
                logger.debug(response)
                responseCode = 200

            except Exception as ex:
                logger.error("can't get layout" + str(ex) + str(sys.exc_info()[0]))
                responseCode = 404

        elif (str(path)=="_setlen") and str(flask.request.method) in ["POST"]:
            logger.debug("setlen of column")
            result = {}
            for descriptor,newLen in data.items():
                result[descriptor] = m.set_column_len(descriptor,newLen)
            responseCode = 200
            response = json.dumps(result)

        elif ((str(path)=="_upload") and str(flask.request.method) in ["GET"]):
            # Return the files from the upload folder

            try:
                # get the files from the upload folder
                filenames = []
                #listdir(mypath)
                #for r, d, f in os.walk(UPLOAD_FOLDER):
                for filename in os.listdir(UPLOAD_FOLDER):
                    fullPath=os.path.join(UPLOAD_FOLDER, filename)
                    if not os.path.isfile(fullPath):
                        continue
                    #for filename in f:
                    filenames.append({
                        "name": filename,
                        "time": os.path.getmtime(fullPath)
                    })

                responseCode = 200
                response = json.dumps(filenames)

            except Exception as ex:
                logger.error("can't retrieve the files from the upload folder: " + str(ex) + str(sys.exc_info()[0]))
                responseCode = 404

        elif ((str(path) == "_upload") and str(flask.request.method) in ["POST"]):
            # Upload a file to the server

            try:
                # check if the post request has the file part
                if 'file' not in request.files:
                    responseCode = 404
                    logger.error("File part missing in upload request")
                else:
                    file = request.files['file']
                    # if user does not select file, browser also
                    # submit an empty part without filename
                    if file.filename == '':
                        responseCode = 404
                        logger.error("Filename not specified")
                    else:
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(web.config['UPLOAD_FOLDER'], filename))
                        responseCode = 200
                        response = "success"
            except Exception as ex:
                logger.error("Can't save the file to the upload folder: " + str(ex) + str(sys.exc_info()[0]))
                responseCode = 404



        else:
            logger.error("CANNOT HANDLE REQUEST, is unknown"+str(path))
            responseCode = 404

        timeElapsed = (datetime.datetime.now() - requestStartTime).total_seconds()
        logger.info("response on " + str(path) + ": " + str(responseCode) + ", len:" + str( len(response)) + " duration:"+str(timeElapsed))
        return flask.Response(response, mimetype="text/html"), responseCode
    except Exception as ex:
        logger.error("general error " +str(sys.exc_info()[0])+".."+str(ex) + str(traceback.format_exc()))

        return flask.Response("",mimetype="text/html"),501

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--port', help='Port on which the restservice is listening', default=6001, type=int)
    parser.add_argument('--plugin_directory',
                        help='Adds a directory to the list of directories from which plugins are loaded',
                        action='append',
                        default=[])
    parser.add_argument('model', help='Full path to model or name of a model in the models subdirectory', nargs='?', default=None)

    args = parser.parse_args()
    model_path = args.model
    port = args.port
    plugin_directories = args.plugin_directory

    m = model.Model()
    for plugin_directory in plugin_directories:
        print('Importing plugins from directory \"{:}\"'.format(plugin_directory))
        m.import_plugins_from_directory(plugin_directory)
    if model_path is not None:
        if model_path == "occupancy":
            print("starting occupany demo")
            m.create_test(2)
        elif model_path == "dynamictest":
            print("starting the dynamic test")
            m.create_test(3)
        else:
            print("load model from disk: " + model_path)
            m.load(model_path)#,includeData=False)

    web.run(host='0.0.0.0', port=port, debug=False)#, threaded = False)

    #enable this to use wsgi web server instead
    #http_server = WSGIServer(('0.0.0.0', 6001), web)
    #http_server.serve_forever()

