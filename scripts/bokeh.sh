#!/bin/bash

export HTTP_PROXY=
export HTTPS_PROXY=
export http_proxy=
export https_proxy=
cd ..
# python restservice.py occupancydemo &
bokeh serve bokeh_web --allow-websocket-origin="*" --port 5006 --args http://127.0.0.1:6001/ root.visualization.workbench
# bokeh serve bokeh_web --allow-websocket-origin="*" --port 5010 --args http://127.0.0.1:6001/ root.visualization.selfservice0 &
