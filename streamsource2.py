import pytz
import json
import copy
import datetime
import numpy
import sys
import time
import requests
import dates
sys.path.append('..')
from model import date2secs

lastTimeStamp = None


valuesPerInsert = 10


def get_data():

    body = {
        "nodes": ["root.occupancyData.variables.Temperature","root.occupancyData.variables.Light"],
        "startTime": None,
        "endTime": None,
        "bins": 30*4*valuesPerInsert,
        "includeIntervalLimits": False
    }
    while 1:
        try:
            response = requests.post("http://127.0.0.1:6001/_getdata", data=json.dumps(body))
            break
        except:
            print("cant get initial data, try again")

    r = json.loads(response.content.decode("utf-8"))

    data = {}

    for entry in r:
        name = entry.split('.')[-1]
        if name.endswith("__time"):
            times = numpy.asarray(r[entry])
        else:
            data[name]= numpy.asarray(r[entry])

    print(f"len of responses  {len(times)}")
    return data,times


def get_events():

    evs = ["busy_start","busy_end","free_start","free_end"]
    times = ["2015-02-12T09:16:00+01:00","2015-02-12T15:46:00+01:00","2015-02-12T19:40:00+01:00","2015-02-13T05:03:00+01:00"]

    return evs,numpy.asarray([dates.date2secs(tim) for tim in times],dtype=numpy.float64)


def make_blob(epoch, includeOutlier=True):
    outlier = 0
    if includeOutlier:
        global lastTimeStamp
        if not lastTimeStamp:
            lastTimeStamp = epoch
        else:
            if epoch > lastTimeStamp + 7:
                lastTimeStamp = epoch
                #every 5 seconds an outlier
                print("outlier!")
                outlier = 1


    blob = {
        "sin": numpy.sin(2*numpy.pi*(1/20)*epoch),
        "cos": numpy.cos(2*numpy.pi*(1/20)*epoch)+outlier,
        "step": round(epoch%20),
        "__time": epoch
    }
    return blob


def write_test(rate,port =6001):

    data,times = get_data()
    duration = times[-1] - times[0]

    events,eventTimes = get_events()


    #we want the whole data to be done in 30 seconds, we we need to put the data in 30/rate packets

    while True:
        #shift the data
        times = times + duration # shift the data
        eventTimes = eventTimes +duration
        print("iterate")
        for idx in range(0,len(times),valuesPerInsert):
            time.sleep(float(rate)/1000)

            #prepare the data
            blob = {var:list(vals[idx:idx+valuesPerInsert]) for var,vals in data.items()}
            blob["__time"]=list(times[idx:idx+valuesPerInsert])
            t=blob["__time"][0]

            # now prepare the events
            evBlob = {"root.events":[], "__time":[]}
            for ev, evt in zip(events, eventTimes):
                if evt >= blob["__time"][0] and evt <= blob["__time"][-1]:
                    evBlob["root.events"].append(ev)
                    evBlob["__time"].append(evt)

            #build the total req
            req = {"node":"root.pipeline","function":"feed","parameter":[{"type":"timeseries","data":blob}]}
            if len(evBlob["__time"]) > 0:
                ##add the events
                req["parameter"].append({"type":"eventseries","data":evBlob})

            #send the data
            print(f"t now {t} {dates.epochToIsoString(t)}")

            try:
                host = "http://127.0.0.1:" + str(port) + "/_execute"
                start = time.time()
                try:
                    r = None
                    r = requests.post(host, data=json.dumps(req),timeout=5)
                finally:
                    end = time.time()-start
                    print(f" result {r.status_code} in {end}")
            except Exception as ex:
                print(f"sent {json.dumps(req)} with exception {ex}")





if __name__ == '__main__':
    # give the rate in ms

    if len(sys.argv) > 1:
        rate = int(sys.argv[1])
    else:
        rate = 1000

    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    else:
        port = 6001


    write_test(rate, port)
