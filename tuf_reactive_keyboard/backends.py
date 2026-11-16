"""Ways of sending a colour to the keyboard.

AtkAcpiBackend  – ASUS ATKACPI driver, used by TUF laptops (same method as
                  G-Helper and the Linux asus-wmi driver). Tried first.
AuraBackend     – ASUS Aura SDK COM object (needs pywin32). Fallback.

Both only *apply* colours; nothing is saved to the BIOS / firmware.
"""

import ctypes
import ctypes.wintypes as wt
import struct


def _to_byte(v):
    return max(0, min(255, int(round(v))))


class BackendError(Exception):
    pass


class AtkAcpiBackend:
    key = "atkacpi"
    name = "ASUS ATKACPI"

    CONTROL_CODE = 0x0022240C
    DEVS = 0x53564544            # "DEVS" ACPI method
    TUF_KB = 0x00100056
    TUF_KB2 = 0x0010005A
    KB_BRIGHTNESS = 0x00050021
    CMD_APPLY = 0xB3             # apply only. 0xB4 would save to BIOS – never used here.
    MODE_STATIC = 0x00
    SPEED = 0xE1

    def __init__(self):
        from .winapi import INVALID_HANDLE_VALUE, kernel32
        self._k = kernel32
        h = kernel32.CreateFileW(r"\\.\ATKACPI", 0xC0000000, 0x3, None, 3, 0x80, None)
        if not h or h == INVALID_HANDLE_VALUE:
            raise BackendError(f"cannot open \\\\.\\ATKACPI (error {ctypes.get_last_error()})")
        self.h = h
        self.dev_id = None

    def _devs(self, dev_id, params):
        args = struct.pack("<I", dev_id) + params
        buf = struct.pack("<II", self.DEVS, len(args)) + args
        inb = ctypes.create_string_buffer(buf, len(buf))
        outb = ctypes.create_string_buffer(16)
        ret = wt.DWORD()
        ok = self._k.DeviceIoControl(self.h, self.CONTROL_CODE, inb, len(buf),
                                     outb, 16, ctypes.byref(ret), None)
        if not ok:
            raise BackendError(f"DeviceIoControl error {ctypes.get_last_error()}")
        return struct.unpack_from("<i", outb.raw, 0)[0]

    def set_brightness(self, level):
        """Backlight level 0..3."""
        self._devs(self.KB_BRIGHTNESS, struct.pack("<I", 0x80 | max(0, min(3, level))))

    def probe(self, rgb):
        """Try both known device ids; return True if the keyboard accepted the colour."""
        try:
            self.set_brightness(3)
        except BackendError:
            pass
        params = self._params(rgb)
        for dev in (self.TUF_KB, self.TUF_KB2):
            if self._devs(dev, params) == 1:
                self.dev_id = dev
                return True
        return False

    def _params(self, rgb):
        r, g, b = (_to_byte(v) for v in rgb)
        return bytes([self.CMD_APPLY, self.MODE_STATIC, r, g, b, self.SPEED])

    def apply(self, rgb):
        self._devs(self.dev_id, self._params(rgb))

    def close(self):
        try:
            self._k.CloseHandle(self.h)
        except Exception:
            pass


class AuraBackend:
    key = "aura"

    def __init__(self):
        try:
            import pythoncom
            import win32com.client
        except ImportError as e:
            raise BackendError("pywin32 not installed") from e
        pythoncom.CoInitialize()
        try:
            self.sdk = win32com.client.Dispatch("aura.sdk.1")
            self.sdk.SwitchMode()
        except Exception as e:
            raise BackendError(f"Aura SDK unavailable ({e})") from e
        self.devices = []
        names = []
        for dev in self._items(self.sdk.Enumerate(0)):
            lights = self._items(dev.Lights)
            if lights:
                self.devices.append((dev, lights))
                try:
                    names.append(str(dev.Name))
                except Exception:
                    names.append("device")
        if not self.devices:
            self.close()
            raise BackendError("Aura SDK found no lighting devices")
        self.name = "Aura SDK: " + ", ".join(names)

    @staticmethod
    def _items(coll):
        try:
            return list(coll)
        except TypeError:
            return [coll.Item(i) for i in range(coll.Count)]

    def probe(self, rgb):
        self.apply(rgb)
        return True

    def apply(self, rgb):
        r, g, b = (_to_byte(v) for v in rgb)
        val = r | (g << 8) | (b << 16)  # 0x00BBGGRR
        for dev, lights in self.devices:
            for light in lights:
                light.Color = val
            dev.Apply()

    def close(self):
        try:
            self.sdk.ReleaseControl(0)
        except Exception:
            pass


def connect(initial_rgb):
    """Return (backend or None, list of (backend_key, error) attempts)."""
    attempts = []
    for cls in (AtkAcpiBackend, AuraBackend):
        try:
            be = cls()
        except Exception as e:
            attempts.append((cls.key, str(e)))
            continue
        try:
            if be.probe(initial_rgb):
                attempts.append((cls.key, "ok"))
                return be, attempts
            attempts.append((cls.key, "keyboard did not accept the command"))
        except Exception as e:
            attempts.append((cls.key, str(e)))
        be.close()
    return None, attempts
