import sys
sys.path.append('..')

import model
import modeltemplates
import datetime
import pytz


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

if __name__ == "__main__":
    t = Timer()
    m=model.Model()
    create_test_model_large(m,lines=10000)
    create_ts_visu_for_table(m)
    m.show()
    #now check the times
    timeBrowsePath = m.get_leaves('root.newTable.timeField')[0]['browsePath']
    val = m.get_value(timeBrowsePath)
    print("vals",val[0],val[-1],model.secs2dateString(val[0]),model.secs2dateString(val[-1]))



    m.save("newtest")

    #t.start()
    #m.save("savetest")
    #t.stop("saving ")
    #n=model.Model()
    #t.start()
    #n.load("savetest")
    #t.stop("loading")
    #n.show()






