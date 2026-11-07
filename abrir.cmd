@echo off
setlocal
set "ELECTRON_RUN_AS_NODE="
cd /d "%~dp0"
if not exist "%~dp0node_modules\electron\dist\electron.exe" (
  echo Preparando a interface Electron pela primeira vez...
  call npm.cmd ci
  if errorlevel 1 (
    echo Falha na instalacao. Confira Node.js e a conexao com a internet.
    pause
    exit /b 1
  )
  call npm.cmd run prepare:desktop
  if errorlevel 1 (
    echo Nao foi possivel preparar o Electron. Confira a conexao e tente novamente.
    pause
    exit /b 1
  )
)
start "" "%~dp0node_modules\electron\dist\electron.exe" "%~dp0." %*
