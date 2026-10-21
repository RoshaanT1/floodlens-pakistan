@echo off
rem Builds the dashboard and assembles a ready-to-push Space folder OUTSIDE the repo.
rem Run from anywhere:  space\prepare.bat
setlocal
set REPO=%~dp0..
set OUT=%~dp0..\..\floodlens-space-out

echo Building the frontend...
pushd "%REPO%\frontend"
call npm run build
if errorlevel 1 (
  echo BUILD FAILED. Nothing was prepared.
  popd
  exit /b 1
)
popd

if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%"
copy /y "%~dp0Dockerfile" "%OUT%\" >nul
copy /y "%~dp0README.md" "%OUT%\" >nul
copy /y "%~dp0serve.py" "%OUT%\" >nul
xcopy /e /i /y "%REPO%\frontend\dist" "%OUT%\dist" >nul

echo.
echo Ready: %OUT%
echo Test it first:  cd frontend  then  npm run preview
endlocal
