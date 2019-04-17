import sys
sys.path.append('..')

import model
import modeltemplates
import datetime
import pytz
import json


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
    print("unchanged")
    print(json.dumps(m.get_differential_update(diff["handle"])))


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




if __name__ == "__main__":

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
    test_move()




