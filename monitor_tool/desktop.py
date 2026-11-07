"""Launcher Electron. O CLI continua independente de Node/Electron."""
from pathlib import Path
import os
import subprocess
import sys
from .models import MonitorError


def launch(demo=False, backups=None):
    root = Path(__file__).resolve().parents[1]
    executable = root / "node_modules" / "electron" / "dist" / ("electron.exe" if sys.platform == "win32" else "electron")
    if not executable.is_file():
        raise MonitorError("Electron não está instalado. Execute npm ci e npm run prepare:desktop, ou use abrir.cmd.")
    args = [str(executable), str(root)]
    if demo:
        args.append("--demo")
    if backups:
        args.extend(["--backup-dir", str(Path(backups).resolve())])
    env = os.environ.copy()
    env.pop("ELECTRON_RUN_AS_NODE", None)
    return subprocess.call(args, cwd=root, shell=False, env=env)
