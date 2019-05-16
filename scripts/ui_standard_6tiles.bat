setlocal
set "HTTP_PROYX="
set "HTTPS_PROXY="
set "http_proxy="
set "https_proxy="

set mypath=%cd%
cd %mypath%\..
start bokeh serve bokeh_web --allow-websocket-origin=localhost:6001 --allow-websocket-origin=localhost:5006 --port 5006 --args http://localhost:6001/ root.visualization.workbench
start bokeh serve bokeh_web --allow-websocket-origin=localhost:6001 --allow-websocket-origin=localhost:5010 --port 5010 --args http://localhost:6001/ root.visualization.selfservice0
start bokeh serve bokeh_web --allow-websocket-origin=localhost:6001 --allow-websocket-origin=localhost:5011 --port 5011 --args http://localhost:6001/ root.visualization.selfservice1  
start bokeh serve bokeh_web --allow-websocket-origin=localhost:6001 --allow-websocket-origin=localhost:5012 --port 5012 --args http://localhost:6001/ root.visualization.selfservice2  
start bokeh serve bokeh_web --allow-websocket-origin=localhost:6001 --allow-websocket-origin=localhost:5013 --port 5013 --args http://localhost:6001/ root.visualization.selfservice3  
start bokeh serve bokeh_web --allow-websocket-origin=localhost:6001 --allow-websocket-origin=localhost:5014 --port 5014 --args http://localhost:6001/ root.visualization.selfservice4  
start bokeh serve bokeh_web --allow-websocket-origin=localhost:6001 --allow-websocket-origin=localhost:5015 --port 5015 --args http://localhost:6001/ root.visualization.selfservice5  

endlocal

