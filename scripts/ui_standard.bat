setlocal
set "HTTP_PROYX="
set "HTTPS_PROXY="
set "http_proxy="
set "https_proxy="

set mypath=%cd%
cd %mypath%\..
start bokeh serve bokeh_web --allow-websocket-origin=localhost:6001 --allow-websocket-origin=localhost:5006 --port 5006 --args http://localhost:6001/ root.visualization.workbench    
start bokeh serve bokeh_web --allow-websocket-origin=localhost:6001 --allow-websocket-origin=localhost:5007 --port 5007 --args http://localhost:6001/ root.visualization.self-service

endlocal