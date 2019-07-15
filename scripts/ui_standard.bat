setlocal
set "HTTP_PROYX="
set "HTTPS_PROXY="
set "http_proxy="
set "https_proxy="

set mypath=%cd%
cd %mypath%\..
start bokeh serve bokeh_web --allow-websocket-origin=localhost:6001 --allow-websocket-origin="*" --port 5006 --args http://localhost:6001/ root.visualization.workbench    
start bokeh serve bokeh_web --allow-websocket-origin=localhost:6001 --allow-websocket-origin="*" --port 5010 --args http://localhost:6001/ root.visualization.selfservice0

endlocal