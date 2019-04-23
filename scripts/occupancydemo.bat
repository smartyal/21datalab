set mypath=%cd%
cd %mypath%\..
start python restservice.py occupancydemo
start bokeh serve bokeh_web --allow-websocket-origin=localhost:6001 --allow-websocket-origin=localhost:5006 --args http://localhost:6001/ root.visualization.workbench 