@echo off
uglifyjs src\context-menu.js --compress --mangle --comments /^!/ --output dist\context-menu.min.js