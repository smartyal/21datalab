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

    def set(self,values,times):
        if len(values)!= len(times):
            return False
        self.values = numpy.copy(numpy.asarray(values))
        self.times = numpy.copy(numpy.asarray(times))
        return True

    def get(self, start=None, end=None, copy=False, resampleTimes = None):
        """
            returns raw data dict with { {"values":[..],"__time":[...], "name2":{"values":[..], "__time":[..]

        """



        if start:
            startIndex = numpy.searchsorted(self.times, start)
        else:
            startIndex = 0
        if end:
            endIndex = numpy.searchsorted(self.times, end)
        else:
            endIndex =numpy.min(numpy.argwhere(~numpy.isfinite(self.times)))

        result = {"__time": None, "values": None}
        if not resampleTimes:
            if copy:
                result["__time"] = numpy.copy(self.times[startIndex:endIndex])
                result["values"] = numpy.copy(self.values[startIndex:endIndex])
            else:
                result["__time"] = self.times[startIndex:endIndex]
                result["values"] = self.values[startIndex:endIndex]
        else:
            oldTimes = self.times[startIndex:endIndex]
            oldValues = self.values[startIndex:endIndex]
            newValues = self.__resample(resampleTimes,oldTimes,oldValues)
            result["__time"] = resampleTimes
            result["values"] = newValues

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
                method: the method used when up/down sampling. we currently only support
                            downsampling: sample values (we take the last value in time (sample and hold)
                            upsampling: we also take the last old value in time (forward fill, sample and hold)
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

    def insert(self,name,values=None,times=None):
        return self.store[name].write(values,times)

    def set(self,name,values = None,times = None):
        return self.store[name].set(values,times)

    def get_table(self, names, start=None, end=None, copy=False, resampleTimes=None):
        """
            returns raw data dict with {name:{"values":[..],"__time":[...], "name2":{"values":[..], "__time":[..]
        """
        if not type(names) is list:
            names = [names]
        result = {}
        for name in names:
            if name in self.store:
                result[name]=self.store[name].get(start,end,copy,resampleTimes)
        return result

    def get_info(self,name = None):
        if not name:
            s=""
            for k,v in self.store.items():
                s=s+f"{k}: {v.get()}"+"\n"
            return s
        else:
            return f"time series len { len(self.store[name].get()['__time'])}"


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