import sys
from widgets import *

from bokeh.models.widgets import Panel,Tabs
from bokeh.plotting import figure
from bokeh.themes import Theme

#import themes

try:
    print("arguments:", sys.argv)
    modelUrl = sys.argv[1]
    modelPath = sys.argv[2]
except:
    pass

print("modelurl and path",modelUrl,modelPath,type(modelUrl),type('http://localhost:6001/'))

#ts_server = TimeSeriesWidgetDataServer('http://localhost:6001/',"root.visualization.widgets.timeseriesOne")
ts_server = TimeSeriesWidgetDataServer(str(modelUrl),str(modelPath))
t = TimeSeriesWidget(ts_server)
#print("before curdoc")
#curdoc().title = 'self service analytics!'
#print("after")
#curdoc().add_root(t.get_layout())


#try some panel
tab1 = Panel(child = t.get_layout(),title="Annotations") # first tab
p2 = figure()
p2.line([1,2,3,4,5],[11,12,13,14,15])

tab2=Panel(child=p2,title="Step 2")                     #second tab
tabs = Tabs(tabs=[tab1,tab2],css_classes=['tabs_21'])   #put them together
curdoc().add_root(tabs)
curdoc().add_periodic_callback(t.periodic_cb, 500)
#curdoc().theme = Theme(json=themes.defaultTheme)
curdoc().theme = Theme(json=themes.whiteTheme)

