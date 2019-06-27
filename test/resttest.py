import requests
import json
import copy
import datetime
#from model import date2secs
import pytz
import aiohttp
import sys
sys.path.append('..')
import model



def test_data():
    body = {
    "nodes" :["root.variables.f0","root.variables.f1"],
    #"startTime" : "2018-01-01T02:10:08.445+02:00",
    #"endTime" :   "2018-01-01T03:10:08.445+02:00",
    "bins" : 300,
    "includeTimeStamps":"02:00"
    }
    r=requests.post("http://localhost:6001/_getdata",data=json.dumps(body))
    print(json.dumps(r.json(),indent=4))


def write_test():
    now = datetime.datetime.now(pytz.timezone("CET"))
    epoch = date2secs(now)
    blob ={
        "root.folder.var1":1,
        "root.folder.var2": 2,
        "root.folder.var3": 3,
        "root.folder.time": epoch
    }

    body = []
    for i in range(10):
        blob["root.folder.time"]=epoch+i
        body.append(copy.deepcopy(blob))

    r = requests.post("http://localhost:6001/_appendRow", data=json.dumps(body))

    #now make a query

    body = {
        "nodes" :["root.folder.var1","root.folder.var2"],
        "startTime" : epoch+10,
        "endTime" : epoch+25,
        "bins" : 300,
        "includeTimeStamps":"02:00"
    }
    r=requests.post("http://localhost:6001/_getdata",data=json.dumps(body))
    print(json.dumps(r.json(),indent=4))


def get_children():
    body = ["root.folder2"]
    r = requests.post("http://localhost:6001/_get", data=json.dumps(body))
    print(json.dumps(r.json(), indent=4))

def get_forwards():
    body = "root.visualization.widgets.timeseriesOne.selectedVariables"
    r = requests.post("http://localhost:6001/_getleaves", data=json.dumps(body))
    print(json.dumps(r.json(), indent=4))


def remote_test():
    pass


def __web_call(self, method, path, reqData):
    """
        this functions makes a call to the backend model serer to get data
        Args:
            method(string) one of ["GET","POST"]
            path: the nodepath to the time series widtet
            reqData: a dictionary with request data for te query like the list of variables, time limits etc.
        Returns (dict):
            the data from the backend as dict
    """
    self.logger.info("__web_call %s %s", method, path)
    try:
        if method.upper() == "GET":
            response = requests.get(self.url + path, timeout=0.01)
        elif method.upper() == "POST":
            import datetime
            now = datetime.datetime.now()
            for timeout in [0.001,0.1,1,10]:
                try:
                    response = requests.post(self.url + path, data=json.dumps(reqData), timeout=timeout)
                    break
                except:
                    continue


            after = datetime.datetime.now()
            diff = (after - now).total_seconds()
            self.logger.debug("response " + str(response) + " took " + str(diff))
        rData = json.loads(response.content.decode("utf-8"))
        return rData
    except BaseException as ex:
        self.logger.error("Error calling web " + str(ex))
        return None




def speed_test():
    #testing the sequential speed of requests
    def post(path,reqData,asynch = False):
        response = None
        host = "http://localhost:6001/"
        import datetime
        now = datetime.datetime.now()
        for timeout in [0.001, 0.1, 1, 10]:
            try:
                response = requests.post(host+ path, data=json.dumps(reqData), timeout=timeout)
                print(timeout)
                break
            except:
                continue
        after = datetime.datetime.now()
        diff = (after-now).total_seconds()
        print("response "+str(response)+" took "+ str(diff))
        if not response:
            print("no res")
            return None
        else:
            rData = json.loads(response.content.decode("utf-8"))
            return rData


    host = "localhost:6001"
    path = "root.visualization.widgets.timeseriesOccupancy"

    request = path + ".selectedVariables"
    nodes = post("_getleaves", request)

    # get the selectable
    nodes = post("_getleaves", path + '.selectableVariables')

    # also remeber the timefield as path
    request = path + ".table"
    nodes = post("_getleaves", request)


def get_branch():
    r = requests.post("http://localhost:6001/_getbranch", "root.visualization.workbench")
    print(json.dumps(r.json(), indent=4))
    m=model.Model()
    m.load(r.json(),False)
    m.show()


if __name__ == '__main__':
    #get_forwards()
    #speed_test()
    #get_branch()