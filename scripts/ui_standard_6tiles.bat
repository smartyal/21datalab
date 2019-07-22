setlocal
set "HTTP_PROYX="
set "HTTPS_PROXY="
set "http_proxy="
set "https_proxy="

set mypath=%cd%
cd %mypath%\..
start bokeh serve bokeh_web --allow-websocket-origin="*" --port 5006 --args http://127.0.0.1:6001/ root.visualization.workbench
start bokeh serve bokeh_web --allow-websocket-origin="*" --port 5010 --args http://127.0.0.1:6001/ root.visualization.selfservice0
start bokeh serve bokeh_web --allow-websocket-origin="*" --port 5011 --args http://127.0.0.1:6001/ root.visualization.selfservice1  
start bokeh serve bokeh_web --allow-websocket-origin="*" --port 5012 --args http://127.0.0.1:6001/ root.visualization.selfservice2  
start bokeh serve bokeh_web --allow-websocket-origin="*" --port 5013 --args http://127.0.0.1:6001/ root.visualization.selfservice3  
start bokeh serve bokeh_web --allow-websocket-origin="*" --port 5014 --args http://127.0.0.1:6001/ root.visualization.selfservice4  
start bokeh serve bokeh_web --allow-websocket-origin="*" --port 5015 --args http://127.0.0.1:6001/ root.visualization.selfservice5  

endlocal

