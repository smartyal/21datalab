import numpy
import threading



def merge_times(time1,time2):
    """
        merge two time vectors and remove duplicates
    """
    times = numpy.append(time1,time2)
    resortIndices = numpy.argsort(times)
    times = times[resortIndices]
    diff = numpy.diff(times)
    diff = numpy.append([1],diff)# the diff has one less, so we add one more
    indices = diff != 0
    times = times[indices] # take only those indices which are different from the previous value
    return times

class TimeSeries:
    def __init__(self,values=[],times=[],allocSize = 10000):
        self.allocSize = allocSize
        self.times = numpy.asarray(times,dtype=numpy.float64)
        self.values = numpy.asarray(values,dtype=numpy.float64)
        self.lastValidIndex = self.times.size-1
        self.lock = threading.RLock()

    def __realloc(self,size=0):

        alloc = numpy.full(self.allocSize+size, numpy.nan, dtype=numpy.float64)
        with self.lock:
            self.values=numpy.append(self.values,alloc)
            self.times =numpy.append(self.times,alloc)

    def insert(self, values=None, times=None, profiling =None, allowDuplicates=False):

        #convert to numpy
        if type(times) is not numpy.ndarray:
            times = numpy.asarray(times)
        if type(values) is not numpy.ndarray:
            values = numpy.asarray(values)

        #incoming vector must make sense
        if values.size != times.size:
            return False

        if values.size == 0:
            return True

        with self.lock:
            lastOldValueIndex = self.lastValidIndex #remember for later


            if not allowDuplicates:
                # sort the new values before inserting and remove duplicates of the times
                times,indices = numpy.unique(times, return_index=True)
                values = values[indices]
            else:
                #keep the duplicates but sort
                sortedIndices = numpy.argsort(times)
                times = times[sortedIndices]
                values = values[sortedIndices]


            remainingSpace = (self.times.size-1)-self.lastValidIndex

            newLen = values.size
            if remainingSpace < newLen:
                self.__realloc(newLen)
                if profiling: profiling.lap("alloc")


            if lastOldValueIndex==-1 or times[0]>self.times[lastOldValueIndex]:
                #simply append the data
                start = self.lastValidIndex + 1
                self.values[start:start + newLen] = values
                self.times[start:start + newLen] = times
                self.lastValidIndex += newLen
                if profiling: profiling.lap(f"put in array")
            else:
                #must insert and avoid producing dublicates
                insertIndicesLeft = numpy.searchsorted(self.get_times(),times,side="right")
                if profiling: profiling.lap(f"searchsorted")

                inserted = 0 # the number of elements already inserted, for each already inserted element, we need to add 1 on the insert index for the remaining elements to insert
                for idx,newTime,newValue in zip(insertIndicesLeft,times,values):
                    index = idx + inserted
                    if not allowDuplicates and self.times[index-1] == newTime:
                        #this is just a replacement of existing data
                        self.values[index-1] = newValue
                    else:
                        #this is a real new one, we must insert at position index
                        #make room
                        self.times[index+1:]=self.times[index:-1]
                        self.values[index + 1:] = self.values[index:-1]
                        #put in
                        self.times[index]=newTime
                        self.values[index] = newValue
                        self.lastValidIndex += 1
                        inserted = inserted+1
                if profiling: profiling.lap(f"inserted in array with shift and duplicates")


        return True

    def delete_area(self,start=None,end=None):
        #delete all data where start<=times<=end
        if type(start) == type(None):
            left = 0
        else:
            left = numpy.searchsorted(self.get_times(), start)

        if type(end) == type(None):
            # this is a tail delete that is easy:
            print("adjust last valid in des  {self.lastValidIndex} -> {left -1}")
            self.lastValidIndex = left -1

        else:
            right = numpy.searchsorted(self.get_times(), end, side="right")
            siz = right-left+1
            self.times[left:self.lastValidIndex-siz] = self.times[right+1:self.lastValidIndex]
            self.values[left:self.lastValidIndex - siz] = self.values[right+1:self.lastValidIndex]
            self.lastValidIndex = self.lastValidIndex - siz

        return True


    def set_masked(self, values, mask):
        with self.lock:
            #only with indices
            if len(values) == len(self.values):
                return False
            self.values[mask]=values[mask]
            return True

    def set(self,values=None,times=None,withAllocSpace=False):
        """
            Args:
                withAllocSpace: if set true, we also make space for additional values
        """
        with self.lock:
            if type(values) != type(None):
                if withAllocSpace:
                    alloc = numpy.full(self.allocSize, numpy.nan, dtype=numpy.float64)
                    self.values = numpy.append(numpy.asarray(values), alloc)
                else:
                    self.values = numpy.copy(numpy.asarray(values))
                self.lastValidIndex = len(values) -1
            if type(times) != type(None):
                if withAllocSpace:
                    alloc = numpy.full(self.allocSize, numpy.nan, dtype=numpy.float64)
                    self.times =numpy.append(numpy.asarray(times), alloc)
                else:
                    self.times = numpy.copy(numpy.asarray(times))
                self.lastValidIndex = len(times) - 1
            return True

    def get_values(self):
        return self.values[0:self.lastValidIndex+1]

    def get_times(self):
        return self.times[0:self.lastValidIndex+1]

    def get(self, start=None, end=None, copy=False, resampleTimes = None, noBins = None, includeIntervalLimits = False, resampleMethod = None):
        """

            request data and resample it
            typical use cases:
                1) give a start and end time and the number of bins: this returns a vector of noBins elements including start and end time
                    if the data does not have enough points between start and end, we do NOT deliver more
                    if the data does have more points than noBins between start and end , we downsample by picking values
                2) use the resampleTimes option:
                    give a vector resampleTimes containing time points at which we want to get results, if necessary, the data will be resampled using
                    the resampleMethod

            Args
                start [float]: the start time of the data query in epoch seconds
                end [float] : the end time of the data query in epoch seconds
                copy [bool]: if False, we only get the pointer to the numpy array, not a copy. This saves time, but the data should only be read!
                                 if True we get a full copy of the requested data
                resampleTimes [numpy.array float]: the time points to return in the result
                noBins : if start and end time is given, we can query a certain number of data points, the dat will be up/down sampled with sample and hold
                includeIntervalLimits: if set to true, we will include one more data point each left and right of the requested time
                resampleMethod [enum]: how to resample if we need to; options are:
                    "samplehold" sample and hold
                    "linear": linear interpolation
                    "linearfill": linear interpolation and also interpolate "nan" or "inf" values in the original data


            Return [dict]
                 {"values":[..],"__time":[...]}

        """
        with self.lock:
            haveData = True

            #remainingSpace = numpy.count_nonzero(numpy.isnan(self.times)) #the times will not have any intermediate nan, only at the end
            #lastValidIndex = len(self.times)-remainingSpace-1
            lastValidIndex = self.lastValidIndex




            if start:
                if start < 0:
                    # we support the -start time, endtime = None, typically used for streaming
                    # to query interval from the end
                    # get the last time and subtract the query time
                    lastTime = self.times[lastValidIndex]
                    start = lastTime + start  # look back from the end, note that start is negative
                    if start < 0:
                        start = 0
                startIndex = numpy.searchsorted(self.get_times(), start,"right")-1 #the first index to take
            else:
                startIndex = 0

            if end:
                endIndex = numpy.searchsorted(self.get_times(), end, side="right") # this endIndex is one more than the last that we take
            else:
                endIndex = lastValidIndex +1

            startIndex = max(startIndex,0) # make sure, startIndex is not negative


            if startIndex == endIndex:
                haveData = False
            else:
                #assure limits
                if startIndex > lastValidIndex:
                    #this means, all the data is left from the query, we should no provide data
                    haveData = False
                if endIndex > lastValidIndex+1:
                    endIndex = lastValidIndex+1


            if haveData:
                if type(resampleTimes) == type(None):
                    #print(f"startIdex:{startIndex}:{self.times[startIndex]}, endIndex:{endIndex-1}:{self.times[endIndex-1]}, diff:{self.times[endIndex-1]-self.times[startIndex]}")
                    #print(f"lastvalid {lastValidIndex}:{self.times[lastValidIndex]} ")
                    if includeIntervalLimits:
                        if startIndex != 0:
                            startIndex = startIndex -1
                        if endIndex < lastValidIndex +1: #we can go one above, as the linspace and arange do not include the right
                            endIndex = endIndex +1
                    if noBins:
                        #we pick samples only if we have more than requested
                        if (endIndex-startIndex)>noBins:
                            takeIndices = numpy.linspace(startIndex, endIndex-1, noBins, endpoint=True, dtype=int)
                        else:
                            takeIndices = numpy.arange(startIndex, endIndex) #arange excludes the last

                        times = self.times[takeIndices]
                        values = self.values[takeIndices]

                    else:
                        #takeIndices = numpy.arange(startIndex,endIndex) #arange exludes the last
                        times = self.times[startIndex:endIndex]
                        values = self.values[startIndex:endIndex]
                else:
                    #must resample the data
                    #oldTimes = self.times[startIndex:endIndex]
                    #oldValues = self.values[startIndex:endIndex]

                    if resampleMethod == "linear":
                        values = numpy.interp(resampleTimes,self.get_times(),self.get_values())
                    elif resampleMethod == "linearfill":
                        #fill the nans with data
                        indices = numpy.isfinite(self.get_values())
                        values = numpy.interp(resampleTimes, self.get_times()[indices], self.get_values()[indices])
                    else:
                        #the default is ffill
                        values = self.__resample_ffill(resampleTimes, self.get_times(), self.get_values())
                    times = resampleTimes


            else:
                times=numpy.asarray([])
                values=numpy.asarray([])


            if copy:
                result = {"__time": numpy.copy(times), "values":numpy.copy(values)}
            else:
                result = {"__time": times, "values": values}

            return result

    def __resample_ffill(self,newTimes, oldTimes, values):
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

    def merge(self,timeseries):
        """
            merge another time series into this times series:
            the times will be all time points existing
            double times will be removed
            the new values will get priority on dublicate times
        """
        with self.lock:
            mergeTimes = merge_times(self.get_times(),timeseries.get_times())
            oldValues = self.get(resampleTimes=mergeTimes)["values"]
            if len(oldValues) == 0:
                #the oldValues is empty, so we create a NaN array
                oldValues = numpy.full(len(mergeTimes),numpy.nan,dtype=numpy.float64)
            newValues = timeseries.get(resampleTimes=mergeTimes)["values"]
            indices=numpy.isfinite(newValues)
            oldValues[indices]=newValues[indices]
            self.set(oldValues,mergeTimes)

class TimeSeriesTable:
    """
        the TSTable is an API class for the access of tabled data
        for any alternative implementation, the api should be implemented such as create, insert etc.

    """
    def __init__(self,allocSize = 10000):
        self.store = {}
        self.allocSize = allocSize

    def get_items(self):
        """
            Returns:
                a list of keys which are the ids of the timeseries stored here

        """
        return list(self.store.keys()) # this makes a copy

    def create(self,name):
        self.store[name]=TimeSeries(allocSize=self.allocSize)
        return True

    def delete(self,name):
        if name in self.store:
            del self.store[name]
        return True

    def clear(self):
        self.store={}

    def insert(self,name,values=None,times=None,allowDuplicates = False):
        if name not in self.store:
            self.create(name)
        return self.store[name].insert(values,times,allowDuplicates = allowDuplicates)

    def append(self, name, values=None, times=None):
        if name not in self.store:
            self.create(name)
        return self.store[name].insert(values,times)


    def set(self,name,values = None,times = None):
        return self.store[name].set(values,times)

    def get_table(self, names, start=None, end=None, copy=False, resampleTimes=None, noBins = None, includeIntervalLimits=False,resampleMethod = None):
        """
            returns raw data dict with {name:{"values":[..],"__time":[...], "name2":{"values":[..], "__time":[..]
        """
        if not type(names) is list:
            names = [names]
        result = {}
        for name in names:
            if name in self.store:
                result[name]=self.store[name].get(start=start,end=end,copy=copy,resampleTimes=resampleTimes,noBins=noBins,includeIntervalLimits=includeIntervalLimits,resampleMethod=resampleMethod)
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

    def delete_area(self,name,start=None,end=None):
        if name not in self.store:
            return False
        return self.store[name].delete_area(start,end)

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


        for k,v in blob.items():
            if numpy.isscalar(v):
                blob[k]=numpy.asarray([v])


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

    def merge(self,name,values,times):
        """
            merge the additional into the origin see merge function to
        """
        if name not in self.store:
            return False
        ts = TimeSeries(values = values, times= times)
        return self.store[name].merge(ts)



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
                self.store[id].set(times=get[entry],withAllocSpace=True)
            else:
                self.store[id].set(values=get[entry],withAllocSpace=True)
        return True

