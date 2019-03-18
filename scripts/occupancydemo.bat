set mypath=%cd%
cd %mypath%\..
start python restservice.py occupancy
start bokeh serve bokeh_web --args http://localhost:6001/ root.visualization.widgets.timeseriesOccupancy 