setlocal
set "HTTP_PROYX="
set "HTTPS_PROXY="
set "http_proxy="
set "https_proxy="

set mypath=%cd%
cd %mypath%\..
start python restservice.py streamdemo_3 --plugin_directory private
start bokeh serve bokeh_web --allow-websocket-origin="*" --port 5006 --args http://127.0.0.1:6001/ root.visualization.workbench
start python streamsourcenew.py 250 6001 5
endlocal