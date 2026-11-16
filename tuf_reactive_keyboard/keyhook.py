"""System-wide low-level keyboard hook.

Privacy: only the virtual-key code and up/down state are passed on, to an
in-memory queue. Nothing is written to disk or sent anywhere.
"""

import ctypes
import ctypes.wintypes as wt
import threading
import time

from .winapi import (
    HOOKPROC, KBDLLHOOKSTRUCT, WH_KEYBOARD_LL, WM_KEYDOWN, WM_KEYUP,
    WM_QUIT, WM_SYSKEYDOWN, WM_SYSKEYUP, kernel32, user32,
)


class KeyHook(threading.Thread):
    def __init__(self, events):
        super().__init__(daemon=True, name="KeyHook")
        self.events = events  # collections.deque of (time, vk, is_down)
        self.tid = None
        self._proc = None

    def run(self):
        self.tid = kernel32.GetCurrentThreadId()

        def proc(n_code, w_param, l_param):
            if n_code == 0:
                kb = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                    self.events.append((time.perf_counter(), kb.vkCode, True))
                elif w_param in (WM_KEYUP, WM_SYSKEYUP):
                    self.events.append((time.perf_counter(), kb.vkCode, False))
            return user32.CallNextHookEx(None, n_code, w_param, l_param)

        self._proc = HOOKPROC(proc)  # keep a reference so it isn't garbage-collected
        hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._proc, kernel32.GetModuleHandleW(None), 0
        )
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        if hook:
            user32.UnhookWindowsHookEx(hook)

    def stop(self):
        if self.tid:
            user32.PostThreadMessageW(self.tid, WM_QUIT, 0, 0)
