setlocal
set "HTTP_PROYX="
set "HTTPS_PROXY="
set "http_proxy="
set "https_proxy="

set mypath=%cd%
cd %mypath%\..
start python restservice.py streamdemo_messe --port 6002 --plugin_directory private
start bokeh serve bokeh_web --allow-websocket-origin="*" --port 5016 --args http://127.0.0.1:6002/ root.visualization.workbench
start python streamsource.py 250 6002
endlocal