@echo off
cd /d "%~dp0"
pythonw.exe "%~dp0monitor_ips.py" gui
if errorlevel 1 (
  echo Nao foi possivel abrir a janela. Confira a instalacao do Python com Tkinter.
  echo Para diagnosticar: python monitor_ips.py gui
  pause
)
