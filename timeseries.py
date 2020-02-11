import numpy


class TimeSeries:
    def __init__(self,allocSize = 10000):
        self.allocSize = allocSize
        self.times = numpy.asarray([],dtype=numpy.float64)
        self.values = numpy.asarray([],dtype=numpy.float64)

    def __realloc(self,size=0):
        alloc = numpy.full(self.allocSize+size, numpy.nan, dtype=numpy.float64)
        self.values=numpy.append(self.values,alloc)
        self.times =numpy.append(self.times,alloc)

    def insert(self,values=None,times=None):

        if len(values)!= len(times):
            return False

        remainingSpace = numpy.count_nonzero(numpy.isnan(self.times))
        newLen = len(values)
        if remainingSpace < newLen:
            self.__realloc(newLen)
        start=numpy.min(numpy.argwhere(~numpy.isfinite(self.times)))
        self.values[start:start+newLen]=values
        self.times[start:start + newLen] = times

        resortIndices = numpy.argsort(self.times)
        self.values= self.values[resortIndices]
        self.times = self.times[resortIndices]

        return True

    def set_masked(self, values, mask):
        #only with indices
        if len(values) == len(self.values):
            return False
        self.values[mask]=values[mask]
        return True

    def set(self,values=None,times=None):
        if type(values) != type(None):
            self.values = numpy.copy(numpy.asarray(values))
        if type(times) != type(None):
            self.times = numpy.copy(numpy.asarray(times))
        return True

    def get(self, start=None, end=None, copy=False, resampleTimes = None, noBins = None, includeIntervalLimits = False):
        """
            returns raw data dict with { {"values":[..],"__time":[...], "name2":{"values":[..], "__time":[..]

        """
        haveData = True

        remainingSpace = numpy.count_nonzero(numpy.isnan(self.times))
        lastValidIndex = len(self.times)-remainingSpace-1


        if start:
            startIndex = numpy.searchsorted(self.times, start)
        else:
            startIndex = 0

        if end:
            endIndex = numpy.searchsorted(self.times, end)
        else:
            endIndex = lastValidIndex

        if startIndex == endIndex:
            haveData = False
        else:
            #assure limits
            if startIndex> lastValidIndex:
                #this means, all the data is left from the query, we should no provide data
                haveData = False
            if endIndex >= lastValidIndex:
                endIndex = lastValidIndex


        if haveData:
            if not resampleTimes:

                if includeIntervalLimits:
                    if startIndex != 0:
                        startIndex = startIndex -1
                    if endIndex <= lastValidIndex -1 :
                        endIndex = endIndex +1
                if noBins:
                    #we pick samples only if we have more than requested
                    if (endIndex-startIndex)>noBins:
                        takeIndices = numpy.linspace(startIndex, endIndex, noBins, endpoint=True, dtype=int)
                    else:
                        takeIndices = numpy.arange(startIndex, endIndex+1) #arange excludes the last
                else:
                    takeIndices = numpy.arange(startIndex,endIndex+1) #arange exludes the last

                times = self.times[takeIndices]
                values = self.values[takeIndices]
            else:
                oldTimes = self.times[startIndex:endIndex]
                oldValues = self.values[startIndex:endIndex]
                newValues = self.__resample(resampleTimes,oldTimes,oldValues)
                times = resampleTimes
                values = newValues
        else:
            times=[]
            values=[]


        if copy:
            result = {"__time": numpy.copy(times), "values":numpy.copy(values)}
        else:
            result = {"__time": times, "values": values}

        return result

    def __resample(self,newTimes, oldTimes, values, method="ffill"):
        """
            resample the values along a new time axis
            up/down samping is possible, and distances are possible
            if upsamping
            Args:
                newTimes: a numpy.array of time values (typically epoch seconds in UTC
                oldTimes: the old time stamps of the values, must have same length as values
                values: a numpy array of values to be up/down sampled
                method: the method used when up/down sampling. we currently only support the
                            "ffill":
                                @downsampling: sample values (we take the last value in time (sample and hold)
                                @upsampling: we also take the last old value in time (forward fill, sample and hold)
            Returns:
                numpy array of type values of the length of newTimes with the up/down-sampled values

        """

        newValues = numpy.full(len(newTimes), numpy.nan)

        # if the searchsorted gives index 0, we must put the new value in front of the old and use nan for the value
        # as we don't have any valid previous value, the fastest way to do this is to put a value infront and use
        # the searchsorted as a vector process with the "right", e.g. right	a[i-1] <= v < a[i],
        # so we get the found index i as one bigger than out timestamp (which is then <= the searched time)
        # we should actually take the result index -1 to have the right index, but the values have been shifted by one to the right, so
        # we are fine
        # example:
        #   oldTimes = 11,12,13
        #   old values = 11,12,13
        #   newTimes 10,10.5,11,11.5
        #       preprocessing values preold= nan,11,12,13
        #       searchsorted (10,10.5,11,11.5 "right" gives: 0,0,1,1)
        #       result is preold[0,0,1,1] =[nan,nan,11,11]
        myvals = numpy.insert(values, 0, numpy.nan)
        found = numpy.searchsorted(oldTimes, newTimes, "right")
        newValues = myvals[found]

        return newValues


class TimeSeriesTable:
    """
        the TSTable is an API class for the access of tabled data
        for any alternative implementation, the api should be implemented such as create, insert etc.

    """
    def __init__(self,allocSize = 10000):
        self.store = {}
        self.allocSize = allocSize

    def create(self,name):
        self.store[name]=TimeSeries(allocSize=self.allocSize)
        return True

    def delete(self,name):
        del self.store[name]
        return True

    def clear(self):
        self.store={}

    def insert(self,name,values=None,times=None):
        return self.store[name].write(values,times)

    def set(self,name,values = None,times = None):
        return self.store[name].set(values,times)

    def get_table(self, names, start=None, end=None, copy=False, resampleTimes=None, noBins = None, includeIntervalLimits=False):
        """
            returns raw data dict with {name:{"values":[..],"__time":[...], "name2":{"values":[..], "__time":[..]
        """
        if not type(names) is list:
            names = [names]
        result = {}
        for name in names:
            if name in self.store:
                result[name]=self.store[name].get(start=start,end=end,copy=copy,resampleTimes=resampleTimes,noBins=noBins,includeIntervalLimits=includeIntervalLimits)
        return result

    def get_info(self,name = None):
        if not name:
            s=""
            for k,v in self.store.items():
                s=s+f"{k}: {v.get()}"+"\n"
            return s
        else:
            if not name in self.store:
                return f"time series data not found"
            else:
                dat = self.store[name].get()['values']

                return f"time series len {len(dat)}, data:{dat[0:min(len(dat),10)]}"


    def insert_blobs(self,blobs):
        """ blob is a dict or list of dicts of key and values containing one time base like
        {
            "root.vars.a": [1.5,1.6,1.7]m
            "root.vars.b": [2,3,4]
            "__time" :[100001,100002,100003]
        }
        """
        if not type(blobs) is list:
            blobs = [blobs]

        return [self.__insert_blob(b) for b in blobs]

    def __insert_blob(self,blob):
        if not "__time" in blob:
            return False

        lens = [len(v) for k,v in blob.items()]
        if len(set(lens)) != 1:
            #the lengths differ, we can't process
            return False

        for k,v in blob.items():
            if k=="__time":
                continue
            if k not in self.store:
                self.create(k)
            self.store[k].insert(values=v,times=blob["__time"])




    def save(self,name):
        saveDict = {}
        for k,v in self.store.items():
            ts = v.get()
            saveDict[k] = ts["values"]
            saveDict[k+"__time"] = ts["__time"]

        numpy.savez(name, **saveDict)

    def load(self,name):
        get = numpy.load(name+".npz")
        for entry in get.files:
            if entry.endswith("__time"):
                id = entry[:-6]
            else:
                id = entry
            if not id in self.store:
                self.create(id)
            if entry.endswith("__time"):
                self.store[id].set(times=get[entry])
            else:
                self.store[id].set(values=get[entry])
        return True

