"""Settings persistence (%APPDATA%) and 'start with Windows'."""

import json
import os
import sys

from . import APP_ID
from .effects import DEFAULT_SETTINGS

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_ID)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

APP_DEFAULTS = {
    "language": "auto",        # auto | tr | en
    "close_to_tray": True,
}

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "TUFReactiveKeyboard"


def load():
    data = {**DEFAULT_SETTINGS, **APP_DEFAULTS}
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            saved = json.load(f)
        for k, v in saved.items():
            if k in data:
                data[k] = tuple(v) if isinstance(data[k], tuple) else v
    except (OSError, ValueError):
        pass
    data["paused"] = False
    return data


def save(data):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({k: list(v) if isinstance(v, tuple) else v for k, v in data.items()},
                      f, indent=2)
        os.replace(tmp, CONFIG_PATH)
    except OSError:
        pass


def _launch_command():
    if getattr(sys, "frozen", False):           # PyInstaller .exe
        return f'"{sys.executable}" --minimized'
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(pyw):
        exe = pyw
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return f'"{exe}" "{os.path.join(root, "run.pyw")}" --minimized'


def autostart_enabled():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, RUN_VALUE)
        return True
    except OSError:
        return False


def set_autostart(enabled):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if enabled:
            winreg.SetValueEx(k, RUN_VALUE, 0, winreg.REG_SZ, _launch_command())
        else:
            try:
                winreg.DeleteValue(k, RUN_VALUE)
            except OSError:
                pass
