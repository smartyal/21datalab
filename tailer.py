import time
import threading
import os
import numpy as np
import glob
import signal
import argparse
import logging
#from logging.handlers import RotatingFileHandler
import queue
import requests
import datetime

def str_lim(obj,lim):
    stri = str(obj)
    stri=stri.replace('\n','')
    if len(stri)>lim:
        half = round(lim/2)
        return stri[:half]+"..."+stri[-half:]
    else:
        return stri



class DirWatcher():
    """
        this class can watch a directory and calls back when a new file matches the pattern
        usage:
        d = DirWatcher(..)
        d.start()
        d.stop()
    """
    def __init__(self,dir,timeout=1,lastModified=None,callback=None,logger=None):
        """
            Args
                dir [string]: the full path including wildcards like c:\temp\logs\2020_applog*.log
                timeout [float] : the period in seconds to check for new files on the directory, use the possible maximum to reduce load
                lastModified [float]: this is a filter: give a time in seconds. All files that have been last modified before this time diff will not be considered at all
                callback [fkt(filename)] the callback that will be called if a new file is to be watched
                logger [logging.logger] a logger to be used
        """
        self.dir = dir
        self.running = True
        self.timeout = timeout
        self.callback = callback
        self.lastModified = lastModified
        self.logger = logger
        self.files = []

    def get_files(self):
        # returns the list of files matching the match filter sorted by last changed first

        start = time.time()
        files = glob.glob(self.dir)

        #now filter by last modified time
        now = time.time()
        filteredNames = []
        changeTimes = []

        if self.files != [] and not self.lastModified:
            if set(self.files)==set(files):
                totalTime = time.time() - start
                if self.logger: self.logger.debug(f"DirWatcher.get_files shortcut in {totalTime} {len(files)}files")
                return self.files
        for name in files:
            changeTime = now-os.path.getmtime(name)

            if (self.lastModified and changeTime<self.lastModified) or (not self.lastModified):
                filteredNames.append(name)
                changeTimes.append(changeTime)

        indices = np.argsort(changeTimes)

        sortedNames = []
        for index in indices:
            sortedNames.append(filteredNames[index])

        totalTime = time.time()-start
        if self.logger: self.logger.debug(f"DirWatcher.get_files processed in {totalTime} {len(sortedNames)} files")

        return sortedNames

    def start(self):
        self.files = self.get_files()
        if self.files:
            self.callback(self.files[0])
        #now start the thread
        self.running = True
        self.thread = threading.Thread(target=self.follow)
        self.thread.start()

    def follow(self):
        if self.logger : self.logger.info(f"DirWatcher.start thread")
        while self.running:
            newList = self.get_files()
            if newList:
                if not self.files or newList[0]!=self.files[0]:
                    #the file name that has changed last has changed, this is a new log file:
                    self.callback(newList[0])
                self.files = newList
            time.sleep(self.timeout)
        if self.logger: self.logger.info("DirWatcher. thread finished")

    def stop(self):
        if self.logger: self.logger.info("DirWatcher.stop")
        self.running = False


class FileTailer():

    def __init__(self,fileName,timeout =1,callback=None,logger=None):
        self.fileName = fileName
        self.running = True
        self.cb = callback
        self.timeout = timeout
        self.file = open(self.fileName, "r")
        self.logger = logger
        if self.logger:self.logger.info(f"FileTailer.init {self.fileName}")

    def start(self):
        self.thread = threading.Thread(target = self.follow)
        self.thread.start()

    def flush(self):
        while True:
            newLine = self.file.readline()
            if not newLine:
                break

    def follow(self):
        buffer = ""
        if self.logger: self.logger.info(f"FileTailer.follow {self.fileName}")
        while self.running:
            newLine = self.file.readline()
            if not newLine:
                time.sleep(self.timeout)
            else:
                buffer += newLine
                if buffer.endswith('\n'):
                    if self.cb:
                        self.cb(buffer)
                    buffer = ""#reset buffer
                else:
                    if self.logger: self.logger.info(f"FileTailer.follow. line not complete")
        self.file.close()
        if self.logger: self.logger.info(f"FileTailer.follow.threadFinish {self.fileName}")

    def stop(self):
        self.running = False

    def get_file_name(self):
        return self.fileName

class LogFileFollower():
    def __init__(self,dir,dirUpdatePeriod = 10,fileUpdatePeriod=1,callback = None,flushFirstFile = True,logger=None):
        self.dir = dir
        self.dirUpdatePeriod = dirUpdatePeriod
        self.fileUpdatePeriod = fileUpdatePeriod
        self.dataCb = callback
        self.currentLogFile = None
        self.flushFirstFile = flushFirstFile
        self.fileWatcher = None
        self.dirWatcher =None
        self.logger = logger

    def start(self):
        if self.logger:self.logger.info("LogFileFollower.start ")
        self.dirWatcher = DirWatcher(self.dir,timeout=self.dirUpdatePeriod,callback=self.on_log_file_changed,logger=self.logger)
        self.dirWatcher.start()

    def on_new_log_line(self,line):
        if self.logger: self.logger.debug(f"LogFileFollower.on_new_log_line {str_lim(line,100)} ")
        if self.dataCb:
            self.dataCb(line)

    def on_log_file_changed(self,name):
        if self.logger: self.logger.debug(f"LogFileFollower.on_log_file_changed to {name}")

        if self.fileWatcher:
            self.fileWatcher.stop()
            self.fileWatcher = FileTailer(name,timeout = self.fileUpdatePeriod,callback=self.on_new_log_line,logger=self.logger)
        else:
            #this is the first
            self.fileWatcher = FileTailer(name,timeout = self.fileUpdatePeriod,callback=self.on_new_log_line,logger=self.logger)
            if self.flushFirstFile:
                self.fileWatcher.flush() #pull all previous lines
        self.fileWatcher.start()


    def stop(self):
        self.dirWatcher.stop()
        if self.fileWatcher:
            self.fileWatcher.stop()

class HTTPOut():
    def __init__(self,url,logger=None,retryPeriod = 1,httpTimeout=20,maxRetries=None):
        """
            Args.
                url: the target url
                retryPeriod: the timeout for http post retries
                httpTimeout: the timeout for one http post call
                maxRetries: the max retries for one packet until discard, set to -1 to retry forever
        :param url:
        :param logger:
        :param retryPeriod:
        :param httpTimeout:
        :param maxRetries:
        """
        self.url = url
        self.logger = logger
        self.q = queue.Queue()
        self.retryPeriod = retryPeriod
        self.httpTimeout = httpTimeout
        self.maxRetries = maxRetries

    def start(self):
        self.thread = threading.Thread(target = self.run)
        self.thread.start()

    def __call(self,msg):
        start = time.time()
        try:
            res = requests.post(self.url, data=msg, timeout=self.httpTimeout)
            duration = time.time() - start
            if res.status_code < 400:
                if self.logger:self.logger.debug(f"successfully called out to {self.url} in {duration} s, responseCode {res.status_code}")
                return True
        except Exception as ex:
            duration = time.time() - start
            if self.logger: self.logger.warning(f"error http post {self.url} in {duration} s, {ex}")
            pass
        return False

    def send(self,msg):
        self.q.put(msg)
        if self.logger: self.logger.debug(f"HTTPOut.send for enqueue, quque size {self.q.qsize()}, msg: {str_lim(msg,100)}")


    def run(self):
        if self.logger:self.logger.info(f"HTTPOut.thread start")
        self.running = True
        while self.running:
            try:
                msg = self.q.get(timeout=1)
            except:
                continue
            try:
                result = self.__call(msg)
                if not result:
                    retries = self.maxRetries
                    if not retries:
                        if self.logger: self.logger.warning(f"HTTPOut retries exhausted, discard this packet, queue size {self.q.qsize()}")
                    while retries!=0 and not result and self.running:
                        if retries>0:
                            retries=retries-1
                        if retries==0:
                            if self.logger: self.logger.warning( f"HTTPOut retry {retries}/{self.maxRetries} exhausted, discard this packet, queue size {self.q.qsize()}")
                        else:
                            if self.logger: self.logger.warning(f"HTTPOut retry {retries}/{self.maxRetries}, queue size {self.q.qsize()}")
                            result = self.__call(msg) #retry

            except Exception as ex:
                if self.logger: self.logger.error(f"HTTPOut.run {ex}")

        if self.logger: self.logger.info("HTTPOut.thread finish")

    def stop(self):
        if self.logger: self.logger.info(f"HTTPOut.stop()")
        self.running = False

if __name__ == "__main__":


    #make a logger
    logger = logging.getLogger("Tailer")
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    """
    logfile = RotatingFileHandler("./log/model.log", maxBytes=1000 * 1000 * 100, backupCount=10)  # 10x100MB = 1GB max
    logfile.setFormatter(formatter)
    self.logger.addHandler(logfile)
    """
    logger.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument('--dirtimeout', help='time in seconds how often we check for new files', default=10, type=float)
    parser.add_argument('--filetimeout',help='timeout to check for new line in the currently watched file',default = 1, type =float)
    parser.add_argument('dir', help='filepath with match pattern or direct path to file', nargs='?', default=None)
    args = parser.parse_args()


    def on_log(data):
        print(f"on log {data}")

    print(f"start sniffing of {args.dir} with dirtimeout {args.dirtimeout} {args.filetimeout}")
    l = LogFileFollower(args.dir,fileUpdatePeriod=args.filetimeout,dirUpdatePeriod=args.dirtimeout,callback=on_log,logger=logger)
    l.start()


    running = True
    def handler(signum, frame):
        global running
        print('gracefully exit..')
        l.stop()
        running = False
    signal.signal(signal.SIGINT, handler)

    while running:
        #hang here until ctrl break via sighandler
        time.sleep(1)


