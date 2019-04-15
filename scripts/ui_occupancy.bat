set mypath=%cd%
cd %mypath%\..
bokeh serve bokeh_web --allow-websocket-origin=localhost:6001 --allow-websocket-origin=localhost:5006 --args http://localhost:6001/ root.visualization.widgets.timeseriesOccupancy  