@echo off
cd /d "%~dp0"
rem Prefer regular Python 3.13 (the free-threaded 3.13t build lacks pywin32 wheels), else any Python 3
set "PYV=-3.13"
py %PYV% -c "import sys" 2>nul || set "PYV=-3"
py %PYV% -c "import customtkinter, pystray, PIL" 2>nul || (
  echo Installing requirements...
  py %PYV% -m pip install -r requirements.txt || ( pause & exit /b 1 )
)
start "" pyw %PYV% run.pyw
