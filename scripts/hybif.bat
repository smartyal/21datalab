setlocal
set "HTTP_PROYX="
set "HTTPS_PROXY="
set "http_proxy="
set "https_proxy="
set py=c:\Anaconda3\envs\hybifenv\python.exe

set mypath=C:\Users\al\devel\ARBEIT\zeissGit_neu\hybif_experiments\21datalab
cd %mypath%
set PYTHONPATH=C:\Users\al\devel\ARBEIT\zeissGit_neu\hybif_experiments\21datalab;C:\Users\al\devel\ARBEIT\zeissGit_neu\hybif_experiments\
%py% C:\Users\al\devel\ARBEIT\zeissGit_neu\hybif_experiments\21datalab\restservice.py C:\Users\al\devel\ARBEIT\zeissGit_neu\hybif_experiments\21datalab\models\s4 --plugin_directory ../workbench_plugins
 
endlocal