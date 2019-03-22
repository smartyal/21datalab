

def read_occupancy(fileName="datatest2.txt"):
    import datetime
    from dateutil.parser import parse

    def round_time(dt=None, round_to=60):
        if dt == None:
            dt = datetime.datetime.now()
        seconds = (dt - dt.min).seconds
        rounding = (seconds + round_to / 2) // round_to * round_to
        return dt + datetime.timedelta(0, rounding - seconds, -dt.microsecond)

    f = open(fileName, "r")
    data = f.readlines()
    f.close()
    #for line in data:
    #    print(line)

    #the first is the labels
    labels = data[0].split(',')
    newData={}
    newLabels=[]
    for key in labels:
        newKey=key.replace('"','').replace('\n','')
        newData[newKey]=[]
        newLabels.append(newKey)

    for line in data[1:]:
        items = line.split(',')
        items=items[1:] # omit the first
        #convert the time
        my_time = parse(items[0])
        epoch = round_time(my_time).timestamp()#*1000
        #print(epoch)
        items[0]=epoch # write it back to the items
        for key,item in zip(newLabels,items):
            value = float(item)
            newData[key].append(value)
    return newData




if __name__ == '__main__':
    read_occupancy("datatest2.txt")