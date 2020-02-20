import sys
sys.path.append('..')
sys.path.append('../plugins')

import model
import modeltemplates
import datetime
import pytz
import json
import templates
import time
from bs4 import BeautifulSoup
import re
import requests
import threading
import sse

"""
 this file contains test functions and helpers to test the model api and functionality
"""

class Timer:
    def __init__(self):
        self.start()
        pass
    def start(self,totalCount = None):
        self.startTime = datetime.datetime.now()
        self.totalCount = totalCount
    def stop(self,text=""):
        now = datetime.datetime.now()
        delta = (now-self.startTime).total_seconds()
        print(text+", elapsed time:",delta)
        self.startTime = datetime.datetime.now()
    def remaining(self, nowCount, totalCount=None):
        if totalCount:
            self.totalCount=totalCount
        if nowCount!= 0:
            now = datetime.datetime.now()
            delta = (now - self.startTime).total_seconds()
            remainingSecs = (float(self.totalCount)/float(nowCount))*delta-delta
            print(str(nowCount)+"/"+str(self.totalCount)+": remaining sec %2.2f"%remainingSecs)




def create_test_model_large(myModel,noVars=100,blobs=10,lines=1000):
    """
        creating a large model. we insert blobs with each containing lines
        !! we totally enter blobs*lines lines to the table
        Args:
            vars: the number of vars to be created
            blobs: the number of blobs to be inserted
            lines: the number of lines to be inserted with EACH blob
        Returns:
            the model
    """
    t = Timer()
    #make a table and put in the variables
    print("make a table with ",noVars," rows and ",(blobs*lines)," rows")
    vars = []
    for var in range(noVars):
        variableName = "myvariable"+str(var)
        vars.append(variableName)
    modeltemplates.create_table(myModel, variableNames=vars)

    #prepare a row as dataBlob
    rowEntry = {}
    for leaf in myModel.get_leaves('root.newTable.columns'):
        rowEntry[leaf["browsePath"]]=[]

    #remove the time field and add the __time
    timeBrowsePath = myModel.get_leaves('root.newTable.timeField')[0]['browsePath']
    rowEntry.pop(timeBrowsePath)
    #rowEntry['__time']=[]
    print(rowEntry)


    #put in some data
    startTime = datetime.datetime.now(tz=pytz.utc)
    deltaseconds = 0
    tt=Timer()
    t.start()
    for blobNo in range(blobs):
        print("blob",blobNo,"of",blobs)
        blob = rowEntry.copy()
        for key in blob:
            blob[key]=list(range(deltaseconds,deltaseconds+lines))
        #for the time it's special
        blob['__time']=[]
        for d in range(lines):
            blob['__time'].append( model.date2secs(startTime+datetime.timedelta(seconds=deltaseconds+d) )        )
        deltaseconds+=lines
        print("deltasec",deltaseconds)
        tt.remaining(blobNo,blobs)
        t.start()
        myModel.ts_table_add_blob(blob)
        t.stop("entered"+str(lines)+"lines")

    return myModel

def create_ts_visu_for_table(model,tablePath="root.newTable",visuPath="root.visu"):
    """
        adds a stardard ts visu for an existing table, makes all the hooks right
    """
    # create another TS-widget
    model.create_node_from_path(visuPath, {"type": "widget"})
    model.create_nodes_from_template(visuPath,modeltemplates.timeseriesWidget)
    #model.create_nodes_from_template('root.visualization.widgets.timeseriesOccupancy.buttons.button1',
    #                                modeltemplates.button)
    model.delete_node(visuPath+'.buttons.button1')
    model.add_forward_refs(visuPath+'.selectedVariables',[tablePath+'.variables.myvariable0'])
    model.add_forward_refs(visuPath+'.selectableVariables',[tablePath+'.variables'])
    model.add_forward_refs(visuPath+'.table', [tablePath])
    model.set_value(visuPath+".hasBackground",False)



def diff_test():
    """
        a test for the differential update thing
    """
    m=model.Model()

    #make some nodes
    for id in range(10):
        m.create_node("root",name="node"+str(id),type="const",value=id)
    m.show()
    handle = m.create_differential_handle() # get a status snap

    #make some new ones
    for id in range(2):
        m.create_node("root",name="node"+str(id+10),type="const")
    #delete one
    m.delete_node('2')
    #modify
    m.set_value('1',100)
    m.add_property('3',"newPropt","something")
    diff = m.get_differential_update(handle)
    m.show()
    print(json.dumps(diff,indent =4))
    print("unchanged:?")
    print(json.dumps(m.get_differential_update(diff["handle"])))


    #now make more complex queries and watch the history
    m=model.Model()

    #make some nodes
    for id in range(10):
        m.create_node("root",name="node"+str(id),type="const",value=id)
    a = m.create_differential_handle()
    result=[]

    handle = a
    for i in range(20):
        res = m.get_differential_update(handle)
        result.append(res)
        time.sleep(1)
        handle = res["handle"]

    #
    b = m.get_differential_update(a)['handle']
    c = m.get_differential_update(b)['handle']
    d = m.get_differential_update(c)['handle']
    e = m.get_differential_update(c)['handle']
    f = m.get_differential_update(c)['handle']
    g = m.get_differential_update(f)['handle']
    h = m.get_differential_update(g)['handle']
    i = m.get_differential_update(c)['handle']


def template_test():
    m=model.Model()

    template={
        "name": "table",
        "type": "table",
        "value": "this is a great table",
        "children":[
            {
                "name":"var1",
                "type":"variable"
            },
            {
                "name": "columns",
                "type": "referencer",
            },
            {
                "name": "timeField",
                "type": "referencer",
                "references":["table.var1","table.variables.leveltwo"]
            },
            {
                "name": "variables",
                "type": "folder",
                "children":[
                    {
                        "name":"leveltwo",
                        "type":"const"
                    },
                    {
                        "name":"leveltwo2",
                        "type":"const"
                    }
                ]
            }
        ]
    }
    m.create_template_from_path("root.myfolder.myfolder2.mynewNameofTemplate",template)
    m.create_template_from_path("root.myts",templates.timeseriesWidget)
    m.show()


def test_global_id_counter():
    #when the model is saved and loaded, the id counter is not corrected, let's test this here
    m=model.Model()
    m.create_template_from_path("root.something",m.get_templates()["templates.timeseriesWidget"])
    m.create_node_from_path("root.new1")
    m.show()
    m.save("savetest")
    n=model.Model()
    n.load("savetest")
    print("--- after load")
    n.show()
    n.create_node_from_path("root.new2")
    print("--- after create ")
    n.show()


def test_list_dir():
    m=model.Model()
    print(m.get_models())

def test_move():
    m=model.Model()
    m.create_test(1)
    m.show()
    print("----------------------")
    m.create_node_from_path("root.movehere")
    m.create_node_from_path("root.movehereref",{"type":"referencer"})
    m.move("root.variables","root.movehere")
    m.move("root.folder2", "root.movehereref")
    m.show()

def adjust():
    m=model.Model()
    m.load("hybif3",includeData = False)
    m.create_node_from_path("root.visualization")
    m.move(["root.self-service","root.workbench"],"root.visualization")
    m.save("hybif3",includeData = False)
    m.show()


def test_move2():
    m=model.Model()
    m.load("occupancydemo1")
    #m.show()
    print("----------------------")
    m.move("root.visualization.widgets.timeseriesOccupancy","root.visualization")
    m.delete_node("root.visualization.widgets")
    m.set_properties({"name":"workbench"},nodeDesc="root.visualization.timeseriesOccupancy")
    m.show()
    m.save("occupancydemo2")

def test_observer():
    m=model.Model()
    m.create_node_from_path("root.const",{"type":"const","value":0})
    m.create_template_from_path("root.observer",m.get_templates()["system.observer"])
    m.set_value("root.observer.control.executionType","sync")
    m.add_forward_refs("root.observer.subject",["root.const"])
    m.set_value("root.observer.properties",["value"])
    print("before")
    m.show()
    m.execute_function("root.observer")
    print("first execution")
    m.show()
    m.execute_function("root.observer")
    print("second execution")
    m.show()

    m.set_value("root.const",1)
    m.execute_function("root.observer")
    print("somethings changed")
    m.show()

    print("REFERENCER TEST")
    m.create_node_from_path("root.ref",{"type":"referencer"})
    m.create_node_from_path("root.const2")
    #reset the observer
    m.set_value("root.observer.lastStatus",None)
    m.remove_forward_refs("root.observer.subject")
    m.add_forward_refs("root.observer.subject",["root.ref"])
    m.add_forward_refs("root.ref",["root.const"])
    m.set_value("root.observer.properties",["leaves"])
    m.execute_function("root.observer")

    m.show()
    m.add_forward_refs("root.ref",["root.const2"])
    print("changed the ref")
    m.execute_function("root.observer")
    m.show()
    print("did nothing")
    m.execute_function("root.observer")
    m.show()

def test_get_branch():
    m=model.Model()

    for i in range(3):
        m.create_template_from_path("root.level1.level2.myfolder"+str(i),m.get_templates()["system.counter"])
    m.create_node_from_path("root.level1.level2.myfolder2.ref",{"type":"referencer"})
    m.create_node_from_path("root.const.const")
    m.add_forward_refs("root.level1.level2.myfolder2.ref",["root.const.const"])
    m.show()
    before = json.dumps(m.model)
    branch = m.get_branch("root.level1.level2.myfolder2")
    print(json.dumps(branch,indent = 4))

    n=model.Model()
    n.load(branch,False)
    n.show()
    print("------------")
    m.show()
    if json.dumps(m.model) == before:
        print("model untouched")


def copy_paste_test():
    m=model.Model()
    m.load("occupancydemo")

    #now make 6 identical widgets plus their functions
    for i in range(6):
        widgetPath = "root.visualization.self-service.ui_"+str(i)
        functionPath = "root.ui_function.logisticRegression_"+str(i)
        m.create_template_from_path(widgetPath, m.get_templates()["templates.timeseriesWidget"])
        m.create_template_from_path(widgetPath + ".buttons.button1", m.get_templates()["templates.button"])

        m.create_node_from_path("root.annotations", {"type": "referencer"}) # make a global annotations collector

        m.create_template_from_path(functionPath,m.get_templates()["logisticregression.logisticRegressionTemplate"])



        #copy the referencer settings for the widget which are the same
        referencers=[".selectableVariables",".selectedVariables",".table",".background"]
        for referencer in referencers:
            nodeinfo = m.get_node_info("root.visualization.workbench"+referencer)
            m.add_forward_refs(widgetPath+referencer,nodeinfo["forwardRefs"])

        # copy the referencer settings for the functions which are the same
        referencers = [".input", ".output"]
        for referencer in referencers:
            nodeinfo = m.get_node_info("root.logisticRegression" + referencer)
            m.add_forward_refs(functionPath + referencer, nodeinfo["forwardRefs"])

        #copy values for the widget
        nodes = [".hasAnnotation.tags",".buttons.button1.caption"]
        for node in nodes:
            value = m.get_value("root.visualization.workbench"+node)
            m.set_value(widgetPath+node,value)

        #copy values for the functions
        nodes = [".categoryMap"]
        for node in nodes:
            value = m.get_value("root.logisticRegression"+node)
            m.set_value(functionPath+node,value)




        #now adjust the equal but individual settings for the widget to the functions
        referencers  = {".buttons.button1.onClick":"",".observerBackground":".control.executionCounter"}
        for referencer,target in referencers.items():
            m.add_forward_refs(widgetPath+referencer,[functionPath+target])

        #now adjust the equal but individual settings for the functios to the widgets
        referencers  = {".annotations":".hasAnnotation.newAnnotations"}
        for referencer,target in referencers.items():
            m.add_forward_refs(functionPath+referencer,[widgetPath+target])



    m.save("al6_1")


    #also adjust some values


def html_test():
    with open(r"../web/customui/selfservice6.html") as fp:
        soup = BeautifulSoup(fp,"lxml")
        divs= soup.find_all(id=re.compile("^ui-component")) # find all divs that have a string starting with "ui-component"
        for div in divs:
            uiinfo = json.loads(div.attrs['uiinfo'])
            print(uiinfo)
        print("out:\n"+str(soup))

    with open(r"../web/customui/selfservice6.html") as fp:
        soup = BeautifulSoup(fp,"lxml")
        print("DIV",soup.find('div'))

def more_components():
    m = model.Model()
    m.load("al6_2")
    m.delete_node("root.deployment.ui.components")


    for i in range(6):
        path = "root.deployment.ui.components.selfservice"+str(i)
        template = {
            "name": "selfservice",
            "type": "folder",
            "children":
            [
                {"name":"enabled","type":"const","value":True},
                {"name":"model","type":"referencer"},
                {"name":"settings","type":"const","value":{"port":5010+i}}
            ]
        }
        m.create_template_from_path(path,template)
        m.add_forward_refs(path+".model",["root.visualization.self-service.ui_"+str(i)])
    m.save("al6_3")


def width_6():
    #modify the model for width and height
    m = model.Model()
    m.load("kna6_4")
    for i in range(6):
        path = "root.visualization.self-service.ui_"+str(i)
        m.create_node_from_path(path + ".width",{"type":"const","value":600})
        m.create_node_from_path(path + ".height", {"type": "const", "value": 400})
        m.create_node_from_path(path + ".controlPosition", {"type": "const", "value": "right"})
        m.set_value(path + ".hasHover", "mouse")
        m.set_value(path + ".hasReloadButton",False)
    m.save('kna6_6')


def dates():
    s = "2018-1-1T08:15:00+02:00"
    s2 = "2018-1-1T06:15:00+00:00"
    print(model.date2secs(s),model.date2secs(s2))


def update_widgets(fileName):

    m=model.Model()
    temp = m.get_templates()
    m.load(fileName)
    #now go throught the widget and update all according the template
    #now find all type widget
    newNodes ={}
    for id,props in m.model.items():
        if props["type"] == "widget":
            widget = m.get_node(id)
            print("found widget ",widget.get_browse_path())
            #now go through all first level properties and bring them in if they are missing
            for entry in m.get_templates()['templates.timeseriesWidget']["children"]:
                name = entry["name"]
                if not widget.get_child(name):
                    print("missing " +name + " in "+widget.get_browse_path())
                    newNodes[widget.get_browse_path()+"."+name]=entry

    for k,v in newNodes.items():
        m.create_node_from_path(k, properties=v)
    m.show()
    m.save(fileName+"_update")



def import_annotations():

    files= {""}


def new_observer():
    m = model.Model()
    m.load("occupancydemo")
    m.create_node_from_path("root.var")
    handle = m.create_differential_handle()
    diff = m.get_differential_update(handle)
    m.logger.debug(diff)
    diff = m.get_differential_update(diff["handle"])
    m.logger.debug(diff)


    m.set_value("root.var",5)
    diff = m.get_differential_update(diff["handle"])
    m.logger.debug(diff)
    diff = m.get_differential_update(diff["handle"])
    m.logger.debug(diff)

def test_referencer_lookback():

    m = model.Model()
    m.load("stream_kna")
    res = m.get_referencers('root.folder.cos')
    for r in res:
        print(m.get_browse_path(r))
   # m.show()
    print(f"refs of rootfoldervar {m.get_referencers('root.folder.cos')}")


def req_test():

    while True:
        time.sleep(1)
        now = datetime.datetime.now(pytz.timezone("Europe/Berlin"))
        try:
            startTime = datetime.datetime.now()
            r = requests.get("http://www.google.com",timeout=1.7)
            diff = (datetime.datetime.now()-startTime).total_seconds()
            print(f" result {r.status_code} difftime{diff}")
        except Exception as ex:
            print(f"sent {json.dumps(body)} with exception {ex}")









def sse_test_2():
    def cb(event):
        print(f"callback event:{event}")

    sser = sse.SSEReceiver('http://127.0.0.1:6001/event/stream',cb)
    #t=threading.Timer(20,sser.stop)
    #t.start()
    sser.start()


def branch_test():
    m=model.Model()
    m.load("occupancydemo")
    br = m.get_branch("root.visualization",includeRoot=False,includeForwardRefs=False)
    for k,v in br.items():
        print(f"{k}, {v['browsePath']}")



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", help="port for the restservice")
    args = parser.parse_args()
    print(args.port)


    #t = Timer()
    #m=model.Model()
    #create_test_model_large(m,lines=10000)
    #create_ts_visu_for_table(m)
    #m.show()
    #now check the times
    #timeBrowsePath = m.get_leaves('root.newTable.timeField')[0]['browsePath']
    #val = m.get_value(timeBrowsePath)
    #print("vals",val[0],val[-1],model.secs2dateString(val[0]),model.secs2dateString(val[-1]))



    #m.save("newtest")

    #t.start()
    #m.save("savetest")
    #t.stop("saving ")
    #n=model.Model()
    #t.start()
    #n.load("savetest")
    #t.stop("loading")
    #n.show()

    #diff_test()
    #template_test()
    #test_global_id_counter()
    #test_list_dir()
    #test_move()
    #adjust()
    #test_move2()
    #test_observer()
    #test_get_branch()
    #copy_paste_test()
    #html_test()
    #more_components()
    #width_6()
    #dates()
    #update_widgets('hybif6_2')
    #import_annotations()
    #new_observer()
    #test_referencer_lookback()
    #req_test()
    #sse_client_test()
    #sse_test_2()
    #branch_test()






