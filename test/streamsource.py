import pytz
import json
import copy
import datetime
import numpy
import sys
import time
import requests
sys.path.append('..')
from model import date2secs

lastTimeStamp = None


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
        "root.folder.sin": numpy.sin(2*numpy.pi*(1/20)*epoch),
        "root.folder.cos": numpy.cos(2*numpy.pi*(1/20)*epoch)+outlier,
        "root.folder.step": round(epoch%20),
        "root.folder.time": epoch
    }
    return blob



def write_test(rate,port =6001):

    while True:
        time.sleep(float(rate)/1000)
        now = datetime.datetime.now(pytz.timezone("Europe/Berlin"))
        epoch = date2secs(now)
        blob = make_blob(epoch)
        body = [blob]
        try:
            startTime = datetime.datetime.now()
            host = "http://127.0.0.1:"+str(port)+"/_appendRow"
            r = requests.post(host, data=json.dumps(body),timeout=5)
            diff = (datetime.datetime.now()-startTime).total_seconds()
            print(f"sent {json.dumps(body)} with result {r.status_code} difftime{diff}")
        except Exception as ex:
            print(f"sent {json.dumps(body)} with exception {ex}")


if __name__ == '__main__':
    # give the rate in ms
    
    
    if len(sys.argv)>1:
        rate = int(sys.argv[1])
    else:
        rate = 1000
     
    
    if len(sys.argv)>2:
        port = int(sys.argv[2])
    else:
        port = 6001
    
    write_test(rate,port)    
