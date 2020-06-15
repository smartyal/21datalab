setlocal
cd /d %~dp0
cd ..\private
bokeh serve --show bokeh_mining.py