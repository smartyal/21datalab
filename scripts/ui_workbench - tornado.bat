setlocal
set "HTTP_PROYX="
set "HTTPS_PROXY="
set "http_proxy="
set "https_proxy="

set mypath=%cd%
cd %mypath%\..\bokeh_web
start python start.py http://127.0.0.1:6001/ root.visualization.workbench 5006

endlocal
