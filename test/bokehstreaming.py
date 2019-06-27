import numpy as np

from bokeh.io import curdoc
from bokeh.layouts import row
from bokeh.palettes import Viridis3
from bokeh.plotting import figure
from bokeh.models import CheckboxGroup, Legend, LegendItem
from bokeh.models import ColumnDataSource
from bokeh.models import Range1d,DataRange1d,CustomJS
from bokeh.models.widgets import Button
from bokeh.layouts import row
import time

mysource = ColumnDataSource({"time":list(range(20)),"y":list(range(20))})
counter = 20
streamingOn = False

p = figure()#x_range=(0,1))
#p.x_range=DataRange1d(start=0,end=end)#,follow="start")

def update():
    if streamingOn:

        global counter
        global mysource
        global p
        print(".")
        updatedic={"time":[counter],"y":[counter%10]}
        counter=counter+1
        if 0:
            mysource.stream(updatedic,20)
            #currentData = mysource.data.data
        else:
            newdic={}
            for var in updatedic:
                dat = mysource.data[var][1:]
                dat.extend(updatedic[var])
                newdic[var]=dat
            mysource.data=newdic

        start = mysource.data["time"][0]
        end = mysource.data["time"][-1]
        p.x_range.start = start
        p.x_range.end = end
        print(f"start{start} and end{end}")


def button_cb():
    global streamingOn
    if streamingOn:
        streamingOn=False
    else:
        streamingOn =True

def button2_cb():
    global p
    global mysource
    start = mysource.data["time"][0]
    end = mysource.data["time"][-1]
    p.x_range=DataRange1d(start,end)
def button3_cb():
    print("button3 blick")

p.line(x="time",y="y",source = mysource)
#p.line([1,2,3,4],[1,2,3,4])

button = Button(label="stream")
button.on_click(button_cb)

button2 = Button(label="set something")
button.on_click(button2_cb)

button3 = Button(label="reset")

button3.js_on_click(CustomJS(args=dict(p=p), code="""
    p.reset.emit()
"""))
button3.on_click(button3_cb)
curdoc().add_root(row([p,button,button2,button3]))
curdoc().add_periodic_callback(update, 1000)