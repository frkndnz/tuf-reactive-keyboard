"""Collects a short, privacy-safe report users can paste into a GitHub issue."""

import platform
import sys

from . import __version__


def _bios_info():
    info = {}
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\BIOS") as k:
            for name in ("SystemManufacturer", "SystemProductName", "BIOSVersion"):
                try:
                    info[name] = winreg.QueryValueEx(k, name)[0]
                except OSError:
                    pass
    except OSError:
        pass
    return info


def report(engine):
    bios = _bios_info()
    lines = [
        f"TUF Reactive Keyboard {__version__}",
        f"Model: {bios.get('SystemManufacturer', '?')} {bios.get('SystemProductName', '?')}",
        f"BIOS: {bios.get('BIOSVersion', '?')}",
        f"Windows: {platform.version()} ({platform.machine()})",
        f"Python: {sys.version.split()[0]}{' (frozen)' if getattr(sys, 'frozen', False) else ''}",
        f"State: {engine.state}" + (f" via {engine.backend_name}" if engine.backend_name else ""),
    ]
    for key, result in engine.attempts:
        lines.append(f"  {key}: {result}")
    if engine.error:
        lines.append(f"Runtime error: {engine.error}")
    return "\n".join(lines)
