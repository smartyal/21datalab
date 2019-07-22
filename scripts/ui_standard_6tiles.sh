#!/bin/bash

export HTTP_PROXY=
export HTTPS_PROXY=
export http_proxy=
export https_proxy=
cd ..

bokeh servebokeh_web --allow-websocket-origin="*" --port 5006 --args http://localhost:6001/ root.visualization.workbench
bokeh servebokeh_web --allow-websocket-origin="*" --port 5010 --args http://localhost:6001/ root.visualization.selfservice0
bokeh servebokeh_web --allow-websocket-origin="*" --port 5011 --args http://localhost:6001/ root.visualization.selfservice1  
bokeh servebokeh_web --allow-websocket-origin="*" --port 5012 --args http://localhost:6001/ root.visualization.selfservice2  
bokeh servebokeh_web --allow-websocket-origin="*" --port 5013 --args http://localhost:6001/ root.visualization.selfservice3  
bokeh servebokeh_web --allow-websocket-origin="*" --port 5014 --args http://localhost:6001/ root.visualization.selfservice4  
bokeh servebokeh_web --allow-websocket-origin="*" --port 5015 --args http://localhost:6001/ root.visualization.selfservice5  
