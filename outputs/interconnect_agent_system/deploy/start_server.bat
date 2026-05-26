@echo off
chcp 65001 >nul
setlocal EnableExtensions

set "ROOT=%~dp0"
cd /d "%ROOT%"

if "%INTERCONNECT_HOST%"=="" set "INTERCONNECT_HOST=0.0.0.0"
if "%INTERCONNECT_PORT%"=="" set "INTERCONNECT_PORT=8765"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -Namespace Win32 -Name Console -MemberDefinition '[DllImport(\"kernel32.dll\", SetLastError=true)] public static extern IntPtr GetStdHandle(int nStdHandle); [DllImport(\"kernel32.dll\", SetLastError=true)] public static extern bool GetConsoleMode(IntPtr hConsoleHandle, out int lpMode); [DllImport(\"kernel32.dll\", SetLastError=true)] public static extern bool SetConsoleMode(IntPtr hConsoleHandle, int dwMode);'; $h=[Win32.Console]::GetStdHandle(-10); $mode=0; if([Win32.Console]::GetConsoleMode($h,[ref]$mode)){ $mode = ($mode -band (-bnot 0x40)) -band (-bnot 0x20); [Win32.Console]::SetConsoleMode($h,$mode) | Out-Null }" >nul 2>nul

for %%F in (".env" ".env.local") do (
  if exist "%ROOT%%%~F" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%ROOT%%%~F") do (
      if not "%%~A"=="" set "%%~A=%%~B"
    )
  )
)

set "PYTHON_CMD="
set "PORTABLE_PYTHON=0"
if exist "%ROOT%runtime\python\python.exe" (
  set "PYTHON_CMD=%ROOT%runtime\python\python.exe"
  set "PORTABLE_PYTHON=1"
)

if "%PYTHON_CMD%"=="" (
  py -3 -c "import sys; print(sys.executable)" > "%TEMP%\interconnect_python_path.txt" 2>nul
  if exist "%TEMP%\interconnect_python_path.txt" set /p PYTHON_CMD=<"%TEMP%\interconnect_python_path.txt"
)

if "%PYTHON_CMD%"=="" (
  for /f "delims=" %%P in ('where python 2^>nul') do (
    if "%PYTHON_CMD%"=="" set "PYTHON_CMD=%%P"
  )
)

if "%PYTHON_CMD%"=="" (
  echo Python 3.10+ was not found.
  echo Install Python from https://www.python.org/downloads/windows/ or rebuild this package with embedded Python.
  if not "%INTERCONNECT_NO_PAUSE%"=="1" pause
  exit /b 1
)

if not "%PORTABLE_PYTHON%"=="1" if not "%INTERCONNECT_SKIP_SETUP%"=="1" (
  if not exist "%ROOT%.venv\Scripts\python.exe" (
    echo Creating local Python virtual environment...
    "%PYTHON_CMD%" -m venv "%ROOT%.venv"
    if errorlevel 1 goto setup_failed
  )
  set "PYTHON_CMD=%ROOT%.venv\Scripts\python.exe"
  "%PYTHON_CMD%" -m pip --version >nul 2>nul
  if errorlevel 1 "%PYTHON_CMD%" -m ensurepip --upgrade
  if errorlevel 1 goto setup_failed
  if exist "%ROOT%requirements-server.txt" (
    if exist "%ROOT%wheelhouse" (
      "%PYTHON_CMD%" -m pip install --no-index --find-links "%ROOT%wheelhouse" -r "%ROOT%requirements-server.txt"
      if errorlevel 1 "%PYTHON_CMD%" -m pip install -r "%ROOT%requirements-server.txt"
    ) else (
      "%PYTHON_CMD%" -m pip install -r "%ROOT%requirements-server.txt"
    )
    if errorlevel 1 goto setup_failed
  )
)

if not exist "%ROOT%exports" mkdir "%ROOT%exports"
if not exist "%ROOT%logs" mkdir "%ROOT%logs"

echo.
echo Interconnect Agent server is starting...
echo Local URL:  http://127.0.0.1:%INTERCONNECT_PORT%/
echo Remote URL: http://SERVER-IP:%INTERCONNECT_PORT%/
echo Host: %INTERCONNECT_HOST%
echo Press Ctrl+C to stop.
echo.

if not "%INTERCONNECT_SKIP_BROWSER%"=="1" start "" "http://127.0.0.1:%INTERCONNECT_PORT%/"

"%PYTHON_CMD%" "%ROOT%backend\server.py" --host "%INTERCONNECT_HOST%" --port "%INTERCONNECT_PORT%"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%INTERCONNECT_NO_PAUSE%"=="1" pause
exit /b %EXIT_CODE%

:setup_failed
echo Failed to prepare Python dependencies.
if not "%INTERCONNECT_NO_PAUSE%"=="1" pause
exit /b 1
