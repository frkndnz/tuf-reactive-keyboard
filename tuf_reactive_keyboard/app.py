"""Entry point: wires the key hook, lighting engine, tray icon and window together."""

import collections
import ctypes
import os
import sys

from . import APP_NAME, config
from .backends import connect
from .effects import Engine
from .i18n import Translator


def _resource(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, *parts)


def _single_instance(t):
    from .winapi import ERROR_ALREADY_EXISTS, kernel32, user32
    handle = kernel32.CreateMutexW(None, False, "Local\\TUFReactiveKeyboard")
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        user32.MessageBoxW(None, t("already_running"), APP_NAME, 0x40)
        sys.exit(0)
    return handle  # keep alive for the lifetime of the process


def main():
    settings = config.load()
    t = Translator(settings["language"])
    _mutex = _single_instance(t)  # noqa: F841

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("frkndnz.TUFReactiveKeyboard")
    except Exception:
        pass

    from .keyhook import KeyHook
    from .ui import MainWindow

    events = collections.deque()
    hook = KeyHook(events)
    engine = Engine(settings, events, connect)

    def tray_factory(post):
        from .tray import Tray
        return Tray(t, settings, post)

    win = MainWindow(t, settings, engine, tray_factory=tray_factory,
                     start_hidden="--minimized" in sys.argv)
    ico = _resource("assets", "icon.ico")
    if os.path.exists(ico):
        win.after(250, lambda: win.iconbitmap(ico))  # after CTk sets its default icon

    hook.start()
    engine.start()
    try:
        win.mainloop()
    finally:
        engine.stop_evt.set()
        hook.stop()
        engine.join(timeout=1.5)
        config.save(settings)
        try:
            win.destroy()
        except Exception:
            pass
