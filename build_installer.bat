@echo off
setlocal

set "ISCC=%ProgramFiles%\Inno Setup 7\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%LocalAppData%\Programs\Inno Setup 7\ISCC.exe"

if not exist "dist\imgconv.exe" (
  echo Error: dist\imgconv.exe was not found. Run build.bat first.
  exit /b 1
)

if not exist "%ISCC%" (
  echo Error: Inno Setup 7 was not found.
  echo Install it from https://jrsoftware.org/isdl.php, then run this script again.
  exit /b 1
)

"%ISCC%" installer.iss
if errorlevel 1 exit /b %errorlevel%

echo Installer created in InstallerOutput.
