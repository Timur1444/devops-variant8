@echo off
setlocal
cd /d "%~dp0"
echo Creating a local Python environment...
if exist ".venv\Scripts\python.exe" goto dependencies
python -m venv .venv
if errorlevel 1 goto failed
:dependencies
echo Installing project dependencies. Please wait...
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
if errorlevel 1 goto failed
echo.
echo Open http://127.0.0.1:5000 in your browser when the server is ready.
echo Keep this window open. Press Ctrl+C to stop the application.
echo.
".venv\Scripts\python.exe" -m flask --app wsgi run
if errorlevel 1 goto failed
goto finished
:failed
echo.
echo Startup failed. Send the error text or a screenshot to the chat.
pause
:finished
endlocal
