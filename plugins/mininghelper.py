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
       

def prominent_points(y,times=None):
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
    
    minMax = find_zeros(d1)

    mini = minMax & (d2>0)
    maxi = minMax & (d2<0)
    
    turn   = find_zeros(d2)
    turnL  = turn & (d3>0)
    turnR  = turn & (d3<0)
    
    
    rising = d1>0

    result=[]
    
    
    for index in np.where(minMax)[0]:
        if d2[index]>0:
            entry={"type":"min","index":index,"time":times[index],"d2":d2[index],"value":y[index]}
            result.append(entry)
        elif d2[index]<0:
            entry = {"type": "max", "index": index, "time": times[index],"d2":d2[index],"value":y[index]}
            result.append(entry)
        else:
            print("undecides for min/max")

    totalResult = {"pps":result,"max":maxi,"min":mini,"rising":rising,"turnL":turnL,"turnR":turnR}

    return totalResult

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