#!/usr/bin/env sh 
: "${PATH_BASE:="$(git rev-parse --show-toplevel)"}"

export HTTP_PROXY=
export HTTPS_PROXY=
export http_proxy=
export https_proxy=
# python restservice.py occupancydemo &
cd "${PATH_BASE}" 
bokeh serve bokeh_web --allow-websocket-origin="*" --port 5006 --args http://127.0.0.1:6001/ root.visualization.workbench
# bokeh serve bokeh_web --allow-websocket-origin="*" --port 5010 --args http://127.0.0.1:6001/ root.visualization.selfservice0 &
