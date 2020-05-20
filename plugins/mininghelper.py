# -*- coding: utf-8 -*-

import numpy as np
from sklearn.metrics import mean_squared_error
from scipy.signal import find_peaks
from scipy.spatial.distance import euclidean
from scipy.ndimage import gaussian_filter
import time
#import fastdtw
#from dtaidistance import dtw


# %%  some normalization functions
def normalized_rms(y, y_hat):
    v_y = np.var(y)
    if v_y == 0:
        v_y = 1
    norm_res = np.sqrt(mean_squared_error(y, y_hat) / v_y)
    return norm_res


def center(x: np.ndarray):
    y = x - np.mean(x)
    return y


def center_scale(x: np.ndarray):
    xc = center(x)
    x_std = np.std(xc, ddof=1)
    if x_std == 0 or np.isnan(x_std):
        x_std = 1

    x_cs = xc / x_std
    return x_cs


def normalize_range(x: np.ndarray, new_min: float = 0.0, new_max: float = 1.0):
    x_min = np.min(x)
    x_max = np.max(x)
    d = x_max - x_min

    if d == 0:
        d = 1

    xn = new_min + (x-x_min)/d * (new_max-new_min)

    return xn


# %% similarity measures
def pearson_correlation_coefficient(x: np.ndarray, y: np.ndarray):
    x_cs = center_scale(x)
    y_cs = center_scale(y)
    c = np.dot(x_cs, y_cs) / len(x_cs)

    return c


def pearson_center(x: np.ndarray, y: np.ndarray):
    x_cs = center(x)
    y_cs = center(y)
    c = np.dot(x_cs, y_cs) / len(x_cs)

    return c



def normalized_euclidean_distance(x, y):
    d = np.linalg.norm(x - y)
    xn = np.linalg.norm(x)
    yn = np.linalg.norm(y)
    md = np.maximum(xn, yn)

    if md == 0.0:
        md = 1
    d /= md

    return d


def distance_by_dynamic_time_warping(x, y):
    distance, path = fastdtw.fastdtw(x, y, dist=euclidean)

    return distance, path


def distance_by_dynamic_time_warping2(x, y):
    distance = dtw.distance_fast(x, y)
    return distance


# %%
def subtract_polynomial_model(y: np.ndarray, degree: int = 1):
    """
        example:
        M = 100
        mu, sigma = 1, 0.3
        x = np.linspace(0, 1, M)
        y = np.random.normal(mu, sigma, M)
        degree = 2
        y_hat = subtract_polynomial_model(y, degree=degree)
        plt.scatter(x, y, color='navy', s=30, marker='o', label="data points")
        plt.plot(x, y_hat, color='red', linewidth=2, label="degree %d" % degree)
        plt.grid()
        plt.show()
    """
    m = len(y)
    x = np.linspace(-1.0, 1.0, m)
    c = np.polyfit(x, y, degree)
    p1 = np.poly1d(c)
    y_hat = p1(x)
    r = y - y_hat
    return r, y_hat


# %%
def template_matching_1d(template: np.ndarray, y: np.ndarray, sim_method: str = 'pearson',
                         preprocesssing_method: str = 'no', normalize: bool = True):
    m = len(template)
    n = len(y)
    c = np.zeros((n,))
    for i in np.arange(0, n):
        x1 = i
        x2 = np.minimum(i + m, n)
        yi = y[x1:x2]
        t = template[:(x2-x1)]

        if len(t) > 5:
            if preprocesssing_method == 'subtract_quad':
                t, _ = subtract_polynomial_model(t, degree=2)
                yi, _ = subtract_polynomial_model(yi, degree=2)

            if preprocesssing_method == 'subtract_gradient':
                t, _ = subtract_polynomial_model(t, degree=1)
                yi, _ = subtract_polynomial_model(yi, degree=1)

            if preprocesssing_method == 'subtract_kub':
                t, _ = subtract_polynomial_model(t, degree=3)
                yi, _ = subtract_polynomial_model(yi, degree=3)


        if sim_method == 'pearson':
            pc = pearson_correlation_coefficient(t, yi)
            c[i] = pc

        if sim_method == 'conv':
            c[i] = np.abs(np.dot(t, yi))

        if sim_method == 'euclidean':
            nd = 1.0 - normalized_euclidean_distance(t, yi)
            c[i] = nd  # np.maximum(np.minimum(1.0, nd), 0.0)

        if sim_method == 'dtw':
            d, _ = distance_by_dynamic_time_warping(t, yi)
            c[i] = 1.0 - d

        if sim_method == 'dtw2':
            d = distance_by_dynamic_time_warping2(t, yi)
            c[i] = 1.0 - d

    if normalize:
        c = normalize_range(c)

    return c


# %%

def detect_peaks(y: np.ndarray, min_level: float = 0.8, max_level: float = 1.01, min_dist: int = 10):
    #peaks, _ = find_peaks(y, height=(min_level, max_level), distance=min_dist)

    peaks, _ = find_peaks(y, height=min_level, distance=min_dist)
    #print("detect peaks",_)
    return peaks
    
def find_zeros(data):
    result = np.full(len(data),False)
    for index in range(len(data)-1):
        y1 = data[index]
        y2 = data[index+1]
        if y1==0 and y2!=0:
            result[index+1] = True
            #print(f"y1==0 and y2!=0 @ {index}")
        elif y1>0 and y2<0:
            result[index+1] = True
            #print(f"y1>0 and y2<0 @ {index}")
        elif y2>0 and y1<0:
            result[index+1] = True
            #print(f"y2>0 and y1<0: @ {index}")
    return result

def dif(vector,appendEnd=True):
    #return the derivate (diff) of the vector with same length like the input (appending the end)
    d= np.diff(vector)
    #print(f"diff of {vector} => {d}")
    #return np.append(d[0],d)
    if appendEnd:
        return np.append( d,d[-1])
    else: 
        return np.append(d[0],d)
       

def prominent_points(y,times=None,includeTurningPoints = False, edges = None, d2Lim=0, d3Lim=0, d4Lim=0):
    """
        generate an ordered list of dict with prominent points entries
        each entry carries several infos
        {
            type:min,max, ...
            index: the index
            x: the x[index]
        }
    """

    d1=dif(y)
    d2=dif(d1,appendEnd=False)
    d3=dif(d2,appendEnd=False)
    d4=dif(d3,appendEnd=False)
    
    minMax = find_zeros(d1)

    mini = minMax & (d2 > d2Lim)
    maxi = minMax & (d2 < -d2Lim)
    
    turn   = find_zeros(d2)
    turnL  = turn & (d3 > d3Lim)
    turnR  = turn & (d3 < -d3Lim)

    edge = find_zeros(d3)
    edgeL = edge & (d4 > d4Lim)
    edgeR = edge & (d4 < -d4Lim)
    
    rising = d1>0

    result=[]
    

    if includeTurningPoints:
        all = minMax|turn
    else:
        all = minMax
    for index in np.where(all)[0]:
        if minMax[index]:
            if d2[index]>0:
                entry={"type":"min","index":index,"time":times[index],"d2":d2[index],"value":y[index]}
                result.append(entry)
            elif d2[index]<0:
                entry = {"type": "max", "index": index, "time": times[index],"d2":d2[index],"value":y[index]}
                result.append(entry)
            else:
                print(f"undecides for min/max {d2[index]}")
        else:
            if d3[index]>0:
                entry = {"type": "turnL", "index": index, "time": times[index], "d3": d3[index], "value": y[index]}
                result.append(entry)
            elif d3[index]<0:
                entry = {"type": "turnR", "index": index, "time": times[index], "d3": d3[index], "value": y[index]}
                result.append(entry)
            else:
                print(f"undecide for turnl/r ")

    totalResult = {"pps":result,"max":maxi,"min":mini,"rising":rising,"turnL":turnL,"turnR":turnR,"y":y}

    if edges:
        #edgeL,edgeR = pps_edge(y,edges["slidingLen"],edges["sigma"])
        totalResult["edgeL"]=edgeL
        totalResult["edgeR"]=edgeR

    return totalResult


def prominent_points_new(x,y, features=["min","max","turnL","turnR","edgeL","edgeR","samples"], d2Lim=0, d3Lim=0, d4Lim=0):
    """
        generate an ordered list of dict with prominent points entries
        each entry carries several infos
        {
            type:min,max, ...
            index: the index
            x: the x[index]
        }
    """

    d1 = dif(y)
    d2 = dif(d1, appendEnd=False)
    d3 = dif(d2, appendEnd=False)
    d4 = dif(d3, appendEnd=False)

    minMax = find_zeros(d1)

    mini = minMax & (d2 > d2Lim)
    maxi = minMax & (d2 < -d2Lim)

    turn = find_zeros(d2)
    turnL = turn & (d3 > d3Lim)
    turnR = turn & (d3 < -d3Lim)

    edge = find_zeros(d3)
    edgeL = edge & (d4 > d4Lim)
    edgeR = edge & (d4 < -d4Lim)

    rising = d1 > 0

    result = []

    #now
    all = np.full(len(x),False)

    if "turnL" in features or "turnR" in features:
        all = all | turn
    if "min" in features or "max" in features:
        all = all | minMax

    if "edgeL" in features or "edgeR" in features:
        all = all | edge

    #now go over all zeros and find min, max etc
    for index in np.where(all)[0]:
        if minMax[index]:
            if d2[index] > 0:
                if "min" in features:
                    entry = {"type": "min", "index": index, "time": x[index], "d2": d2[index], "value": y[index]}
                    result.append(entry)
            elif d2[index] < 0:
                if "max" in features:
                    entry = {"type": "max", "index": index, "time": x[index], "d2": d2[index], "value": y[index]}
                    result.append(entry)
            else:
                print(f"undecides for min/max {d2[index]}")

        if turn[index]:
            if d3[index] > 0:
                if "turnL" in features:
                    entry = {"type": "turnL", "index": index, "time": x[index], "d3": d3[index], "value": y[index]}
                    result.append(entry)
            elif d3[index] < 0:
                if "turnR" in features:
                    entry = {"type": "turnR", "index": index, "time": x[index], "d3": d3[index], "value": y[index]}
                    result.append(entry)
            else:
                print(f"undecide for turnl/r ")

        if edge[index]:
            if d4[index] > 0:
                if "edgeL" in features:
                    entry =  {"type": "edgeL", "index": index, "time": x[index], "d3": d3[index], "value": y[index]}
                    result.append(entry)
                if "edgeR" in features:
                    entry = {"type": "edgeR", "index": index, "time": x[index], "d3": d3[index], "value": y[index]}
                    result.append(entry)

    #also include the arrays for easy printing
    totalResult = {"pps": result,"y":y}
    if "max" in features:
        totalResult["max"] = maxi
    if "min" in features:
        totalResult["min"] =  mini
    if "turnL" in features:
        totalResult["turnL"] = turnL
    if "turnR" in features:
        totalResult["turnR"] = turnR
    if "edgeL" in features:
        totalResult["edgeL"] = edgeL
    if "edgeR" in features:
        totalResult["edgeR"] = edgeR


    return totalResult


def prominent_points_downsampling(y,times,factor=10):
    totalLen = len(y)
    points = []
    samples = np.full(totalLen,False)
    for index in range(0,totalLen,factor):
        samples[index]=True
        points.append({"type": "sample", "index": index, "time": times[index], "value": y[index]})
    totalResult = {"pps":points,"samples":samples,"y":y}
    return totalResult


def pps_edge(y,slidingLen=20,sigmaLevel=4):

    totalLen = len(y)
    edgeL = np.full(totalLen,False)
    edgeR = np.full(totalLen, False)
    index = 0
    while index<totalLen-slidingLen-1:
        index += 1

        window = y[index:index+slidingLen]
        mu = np.mean(window)
        sigma = np.std(window)
        left = np.abs((y[index-1]-mu)/sigma)
        right = np.abs((y[index+slidingLen]-mu)/sigma)
        if left>sigmaLevel:
            edgeL[index-1]=True
            index+=slidingLen

        if right>sigmaLevel:
            edgeR[index+slidingLen]=True
            index += slidingLen

    return edgeL,edgeR

def pps_prep(y,filter=None,poly=None, diff = False,postFilter = None):
    if filter!=None:
        y=gaussian_filter(y, sigma=filter)
    if poly != None:
        y=subtract_polynomial_model(y,poly)
    if diff:
        y=dif(y)
    if postFilter!= None:
        y=gaussian_filter(y,sigma=postFilter)
    return y


def pps_mining(motif, series, timeRanges={1: 0.7, 7: 0.5}, valueRanges={1: 0.8}, typeFilter=[], motifStartIndex=None,
               motifEndIndex=None, debug=None):
    """
        Prominent PointS mining
        Args
            motif: a list of prominent points to mine for, typically the result of prominent_points()["pps"]
            series: a list of proment points to mine in
            timeRanges: a dictionary giving the degree of freedom of consecutive time points, the key gives the distance between points
                        as index, the freedom gives the range to be fulfilled, example:
                        {1:0.5}: all following time points of a motif in the series must have the distance of the original motif +-50%
                        lets say the motif has the time points 13,15,17
                        then the series is allowed to have 10, 12 +- 1 (original: (15-13)*0.5 = 1 )
            valueRanges: same freedom calculation as the timeRanges for values
                        example: {1:0.2}, original values: 40,50
                        values in the series: 35, 45 +- 2, also 35,43 would be ok
                        typeFilter []: list of types select only some types out of the pps, like ["min", "max"]

    """
    startTime = time.time()
    found = []
    # print([pp for pp in motif])
    motif = [pp for pp in motif if pp["type"] in typeFilter]
    if not motifStartIndex:
        motifStartIndex = 0
    if not motifEndIndex:
        motifEndIndex = len(motif)
    motif = motif[motifStartIndex:motifEndIndex]
    series = [pp for pp in series if pp["type"] in typeFilter]
    print(f"motif prominent points {len(motif)}")

    index = -1
    motifIndex = 0  # the next motif index to match to
    last = len(series) - 1
    while index < last:
        index = index + 1
        if debug:
            print(f":@{index}/{last}:", end="")

        if series[index]["type"] == motif[motifIndex]["type"]:
            if motifIndex == 0:
                if debug:
                    print("<", end="")
            if motifIndex > 0:

                # check the timings
                for k, v in timeRanges.items():
                    if motifIndex >= k:
                        # check this
                        motifDiff = motif[motifIndex]["time"] - motif[motifIndex - k]["time"]
                        seriesDiff = series[index]["time"] - series[index - k]["time"]
                        motifDiffMin = max(0, motifDiff - v * motifDiff)
                        motifDiffMax = motifDiff + v * motifDiff

                        ok = seriesDiff > motifDiffMin and seriesDiff < motifDiffMax
                        if debug:
                            print(
                                f"check diff ({k}: {motifDiffMin} < {seriesDiff}< {motifDiffMax}) motif:{motifDiff}: {ok}")
                        if not ok:
                            # go back
                            if debug:
                                print(f"go back, time bad, motifIndex {motifIndex}")
                            index = index - motifIndex + 1
                            motifIndex = 0
                            break
            if motifIndex > 0:
                for k, v in valueRanges.items():
                    if motifIndex > k:
                        # check this
                        motifDiff = abs(motif[motifIndex]["value"] - motif[motifIndex - k]["value"])
                        seriesDiff = abs(series[index]["value"] - series[index - k]["value"])
                        motifDiffMin = max(0, motifDiff - v * motifDiff)
                        motifDiffMax = motifDiff + v * motifDiff
                        ok = seriesDiff > motifDiffMin and seriesDiff < motifDiffMax
                        if debug:
                            print(
                                f"check value diff ({k}: {motifDiffMin} < {seriesDiff}< {motifDiffMax}) motif:{motifDiff}: {ok}")
                        if not ok:
                            if debug:
                                print(f"go back, value bad motifIndex {motifIndex}")
                            index = index - motifIndex + 1
                            motifIndex = 0
                            break
            if motifIndex == len(motif) - 1:
                if debug:
                    print("*>\n")
                found.append({"index": index, "time": series[index]["time"]})
                motifIndex = 0

            motifIndex = motifIndex + 1

            if debug:
                print(motifIndex, end="")
        else:
            if debug:
                if motifIndex > 0:
                    print(">")
                else:
                    print("~", end="")
            motifIndex = 0

    if debug:
        print(f"pps mining took {time.time()-startTime} sec")
    return found


class TrainMiner:
    """
    # train: a flexible length list of points which all are in the constaints of min, max and freedom,
    # this area ends with error break of minTime/minPoints maxPoint/Times freedom are not fulfilled
    # this area ends when a point is out of freedom to force start the next area or
    # after minTime/minPoints the next area is started
        {
        "area": "train",
        "details":{
            "points": # these are to be fulfilled
            {
                "type":"any" # this is the last point in the area
                "minPoints":0
                "maxPoints":inf,
                "minTime": 1000,
                "maxTime":2000
            }
            "freedom":{
                "min":0
                "max: 0.2
            }
        }
    }

    returns of the feed:
    """

    def __init__(self, config,name=None):
        self.minPoints = config["points"]["minPoints"]
        self.maxPoints = config["points"]["maxPoints"]
        self.minTime = config["points"]["minTime"]
        self.maxTime = config["points"]["maxTime"]
        self.pointType = config["points"]["type"]
        self.valMin = config["freedom"]["min"]
        self.valMax = config["freedom"]["max"]
        self.name  = name

        self.reset()

    def reset(self):
        self.noPoints = 0
        self.status = "init"
        self.points = []

    def __check_type(self, point):
        if self.pointType == "any" or point["type"] in self.pointType:
            return True
        else:
            return False

    def __check_freedom(self, point):
        if point["value"] >= self.valMin and point["value"] <= self.valMax:
            return True
        else:
            return False

    def __accept(self, point):
        self.points.append(point)

    def __check_fulfilled(self):
        # check if the current list of points fulfills the expectation
        diffTime = self.points[-1]["time"] - self.points[0]["time"]
        if self.minPoints <= len(self.points) <= self.maxPoints and \
                self.minTime <= diffTime <= self.maxTime:
            return True
        else:
            return False

    def feed(self, point):
        """
            Returns false for not accepted, true for accepted
        """

        result = False

        if not (self.__check_type(point) and self.__check_freedom(point)):
            # point does not match general requirements, reset all
            self.reset()
        else:
            #take this point
            self.__accept(point)
            if self.__check_fulfilled():
                self.status = "fulfilled"
                result = True
            else:
                # check if it was fulfilled before f
                if self.status == "fulfilled":
                    # if was fulfilled before, se we are beyond the limits
                    self.reset()
                else:
                    #was not yet fulfilled, so we are still searching
                    result = True

        return result

    def started(self):
        return len(self.points)>0

    def found(self):
        return self.status == "fulfilled"



class ComplexMiner:
    def __init__(self,config):
        self.miners = []
        for entry in config:
            if entry["area"] == "train":
                self.miners.append(TrainMiner(entry["details"],entry["name"]))
        self.activeIndex = 0
        self.activeFound = False

    def reset(self):
        print("full reset")
        for miner in self.miners:
            miner.reset()
        self.activeIndex = 0
        self.activeFound = False
        self.lastFound = False

    def feed(self,point):

        miner = self.miners[self.activeIndex]
        if self.activeIndex < len(self.miners)-1:
            nextMiner = self.miners[self.activeIndex+1]
        else:
            nextMiner = None
        print(f"feeding x {point['time']} y {point['value']} to miner# {self.activeIndex}")
        if miner.feed(point):
            print("point accepted")
            #the point was accepted, so it fits to the current motif
            if miner.found():
                print("miner.found")
                #the motif was found, this is the TRANSITION PHASE
                if not nextMiner: return True # we are complete!

                result = nextMiner.feed(point)
                if result:
                    print("next result true")
                    if nextMiner.found():
                        #switch to the next if possible
                        if self.activeIndex<len(self.miners):
                            #switch over
                            print("switch over")
                            self.activeIndex+=1
                        else:
                            return True
        else:
            print("point reject")
            #try to switch to the next miner by force
            if nextMiner:
                nextMiner.feed(point)
                if nextMiner.started():
                    print("switch over")
                    self.activeIndex += 1
            else:
                self.reset()



        return False


def plot_pps(plot,x,y,pps,features=["min","max","turnL","turnR","edgeL","edgeR","samples"]):
    """
        plot pps data into a plot
    """
    plot.plot(x,y,"gray")
    plot.plot(x,pps["y"],"blue")




    yPlot = pps["y"]

    if "min" in pps and "min" in features:
        mini = pps["min"]
        plot.plot(x[mini], yPlot[mini], marker="o", linestyle="", color="red")

    if "max" in pps and "max" in features:
        maxi = pps["max"]
        plot.plot(x[maxi],yPlot[maxi],marker="o",linestyle="",color="green")

    if "turnL" in pps:
        turnL= pps["turnL"]
        plot.plot(x[turnL],yPlot[turnL],marker="o",linestyle="",color="orange")

    if "turnR" in pps:
        turnR =  pps["turnR"]
        plot.plot(x[turnR], yPlot[turnR], marker="o", linestyle="", color="yellow")

    if "edgeL" in pps:
        edgeL =pps["edgeL"]
        plot.plot(x[edgeL], yPlot[edgeL], marker="o", linestyle="", color="brown")


    if "edgeR" in pps:
        edgeR = pps["edgeR"]
        plot.plot(x[edgeR], yPlot[edgeR], marker="o", linestyle="", color="pink")

    if "samples" in pps:
        samples = pps["samples"]
        plot.plot(x[samples],yPlot[samples],marker="x",linestyle="",color="gray")