"""Start OptiQuake alerts automatically when the user signs in to Windows, keep
the computer awake while monitoring, and keep a bounded log file.
Copyright (c) 2026 Lic. Juan Esteban Ramírez
SPDX-License-Identifier: AGPL-3.0-only

Uses the per-user Startup folder (no administrator rights). A small runner
script restarts the program if it ever stops, and exits once the Startup
entry is removed.
"""
import os, pathlib, platform, subprocess, sys

LAUNCHER_NAME = "OptiQuake-Alertas.cmd"
LOG_MAX_BYTES = 5 * 1024 * 1024

def startup_dir():
    appdata = os.environ.get("APPDATA") or str(pathlib.Path.home())
    return pathlib.Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

def _quote(arg):
    return subprocess.list2cmdline([str(arg)])

def runner_script(python, script, args, log_path, launcher_path):
    cmdline = " ".join(_quote(x) for x in [python, script, *args, "--log", log_path])
    return "\r\n".join([
        "@echo off",
        "chcp 65001 >nul",  # paths with accents (C:\Users\José) are written as UTF-8
        "title OptiQuake Local - alertas de sismo",
        f'cd /d {_quote(pathlib.Path(script).parent)}',
        ":loop",
        f"if not exist {_quote(launcher_path)} exit /b 0",
        cmdline,
        "timeout /t 10 /nobreak >nul",
        "goto loop",
        "",
    ])

def launcher_script(runner_path):
    return "\r\n".join([
        "@echo off",
        "chcp 65001 >nul",
        f'start "OptiQuake" /min cmd /c {_quote(runner_path)}',
        "",
    ])

def install(args, home, script=None, python=None, startup=None):
    """Create the runner and the Startup entry. Returns (runner, launcher)."""
    home = pathlib.Path(home)
    home.mkdir(parents=True, exist_ok=True)
    startup = pathlib.Path(startup or startup_dir())
    startup.mkdir(parents=True, exist_ok=True)
    script = pathlib.Path(script or pathlib.Path(__file__).with_name("optiquake.py")).resolve()
    python = python or sys.executable
    launcher = startup / LAUNCHER_NAME
    runner = home / "run-alerts.cmd"
    runner.write_text(runner_script(python, script, args, home / "optiquake.log", launcher),
                      encoding="utf-8", newline="")
    launcher.write_text(launcher_script(runner), encoding="utf-8", newline="")
    return runner, launcher

def uninstall(startup=None):
    launcher = pathlib.Path(startup or startup_dir()) / LAUNCHER_NAME
    if launcher.exists():
        launcher.unlink()
        return True
    return False

def open_log(path):
    """Append to path, rotating to path.1 when it grows past LOG_MAX_BYTES."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > LOG_MAX_BYTES:
        old = path.with_name(path.name + ".1")
        if old.exists():
            old.unlink()
        path.rename(old)
    return open(path, "a", encoding="utf-8", errors="replace", buffering=1)

def keep_awake():
    """Prevent Windows from sleeping while this process runs (screen may still turn off)."""
    if platform.system() != "Windows":
        return False
    import ctypes
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
    return bool(ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED))
