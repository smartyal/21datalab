import requests
import json
import copy
import datetime
from model import date2secs
import pytz



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


if __name__ == '__main__':
    get_forwards()