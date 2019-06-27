setlocal
set "HTTP_PROYX="
set "HTTPS_PROXY="
set "http_proxy="
set "https_proxy="

set mypath=%cd%
cd %mypath%\..
start python restservice.py streamdemo
start bokeh serve bokeh_web --allow-websocket-origin=localhost:6001 --allow-websocket-origin=localhost:5006 --port 5006 --args http://localhost:6001/ root.visualization.workbench
cd test
start python streamsource.py 250
endlocal