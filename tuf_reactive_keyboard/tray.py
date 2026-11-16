"""System tray icon (pystray). All callbacks are forwarded to the UI thread via a queue."""

from PIL import Image, ImageDraw

from .effects import MODES


def make_icon(color=(0, 160, 255), size=64):
    """A small rounded keyboard glyph."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 64
    d.rounded_rectangle((2 * s, 12 * s, 62 * s, 52 * s), radius=8 * s, fill=(24, 26, 32, 255))
    c = tuple(int(v) for v in color) + (255,)
    for row, (n, y) in enumerate(((7, 18), (7, 27), (6, 36))):
        w = 52 / n
        off = 6 + (row * 2)
        for i in range(n):
            x0 = off + i * w
            d.rounded_rectangle((x0 * s, y * s, (x0 + w - 2) * s, (y + 6) * s), radius=1.5 * s, fill=c)
    d.rounded_rectangle((18 * s, 44 * s, 46 * s, 48 * s), radius=1.5 * s, fill=c)
    return img


class Tray:
    def __init__(self, t, settings, post):
        import pystray
        self.post = post   # function(action, arg) -> queued for the UI thread
        s = settings
        mode_items = [
            pystray.MenuItem(
                t(f"mode_{m}"),
                (lambda m: lambda icon, item: post("mode", m))(m),
                checked=(lambda m: lambda item: s["mode"] == m)(m),
                radio=True,
            )
            for m in MODES
        ]
        menu = pystray.Menu(
            pystray.MenuItem(t("tray_show"), lambda i, it: post("show", None), default=True),
            pystray.MenuItem(
                lambda item: t("resume") if s["paused"] else t("pause"),
                lambda i, it: post("toggle_pause", None),
            ),
            pystray.MenuItem(t("tray_mode"), pystray.Menu(*mode_items)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("tray_quit"), lambda i, it: post("quit", None)),
        )
        self.icon = pystray.Icon("tuf-reactive-keyboard", make_icon(), "TUF Reactive Keyboard", menu)

    def start(self):
        self.icon.run_detached()

    def refresh(self):
        try:
            self.icon.update_menu()
        except Exception:
            pass

    def stop(self):
        try:
            self.icon.stop()
        except Exception:
            pass
