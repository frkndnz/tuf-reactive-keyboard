"""Colour maths, effect modes, themes and the lighting engine thread."""

import collections
import math
import threading
import time

# ---------------------------------------------------------------- colours

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(c1, c2, t):
    t = clamp(t)
    return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(3))


def scale(c, k):
    return tuple(v * clamp(k) for v in c)


def to_hex(c):
    return "#%02x%02x%02x" % tuple(int(clamp(v, 0, 255)) for v in c)


def from_hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def gradient(stops, x):
    if x <= stops[0][0]:
        return stops[0][1]
    for (x0, c0), (x1, c1) in zip(stops, stops[1:]):
        if x <= x1:
            return lerp(c0, c1, (x - x0) / (x1 - x0))
    return stops[-1][1]


# Typing speed (keys per second) -> colour
SPEED_STOPS = [
    (0.0, (0, 90, 255)),
    (3.0, (140, 0, 255)),
    (6.0, (255, 0, 120)),
    (9.0, (255, 30, 0)),
]

# ---------------------------------------------------------------- modes

MODES = ["combo", "flash", "speed", "keytype"]

KEYTYPE_COLORS = {
    "letter": (0, 160, 255),
    "digit": (0, 255, 120),
    "space": (255, 200, 0),
    "enter": (0, 255, 0),
    "delete": (255, 0, 0),
    "other": (200, 0, 255),
}

# Turkish letters (ğ ü ş ı ö ç) and other layout letters live on OEM keys
_OEM_LETTERS = {0xBA, 0xBF, 0xC0, 0xDB, 0xDC, 0xDD, 0xDE, 0xE2}


def key_type(vk):
    if 0x41 <= vk <= 0x5A or vk in _OEM_LETTERS:
        return "letter"
    if 0x30 <= vk <= 0x39 or 0x60 <= vk <= 0x69:
        return "digit"
    if vk == 0x20:
        return "space"
    if vk == 0x0D:
        return "enter"
    if vk in (0x08, 0x2E):
        return "delete"
    return "other"


# ---------------------------------------------------------------- themes
# theme id -> (idle/base colour, flash colour)
THEMES = {
    "ocean": ((0, 60, 255), (0, 255, 255)),
    "fire": ((255, 40, 0), (255, 200, 0)),
    "neon": ((255, 0, 170), (0, 255, 255)),
    "matrix": ((0, 90, 0), (140, 255, 140)),
    "ice": ((90, 160, 255), (255, 255, 255)),
    "sunset": ((255, 70, 0), (255, 0, 140)),
}

DEFAULT_SETTINGS = {
    "mode": "combo",
    "theme": "ocean",
    "base": THEMES["ocean"][0],
    "flash": THEMES["ocean"][1],
    "decay": 0.35,      # flash fade time constant, seconds
    "idle": 0.15,       # idle brightness 0..1
    "paused": False,
}

# ---------------------------------------------------------------- engine

SPEED_WINDOW = 1.5      # seconds of history used to measure typing speed
MAX_APPLY_FPS = 20      # max colour updates per second sent to the keyboard


def compute_color(s, speed, flash, flash_color):
    """Pure function: settings + state -> RGB tuple (floats)."""
    if s["paused"]:
        return tuple(float(v) for v in s["base"])
    mode = s["mode"]
    idle = s["idle"]
    speed_color = gradient(SPEED_STOPS, speed)
    activity = clamp(speed / 3.0)

    if mode in ("flash", "keytype"):
        return lerp(scale(s["base"], idle), flash_color, flash)
    if mode == "speed":
        level = idle + (1 - idle) * (max(activity, 0.35) if speed > 0.2 else 0)
        return scale(speed_color, level)
    # combo
    base = scale(speed_color, idle + (1 - idle) * 0.4 * activity)
    peak = lerp(speed_color, (255, 255, 255), 0.2)
    return lerp(base, peak, flash)


class Engine(threading.Thread):
    """Consumes key events, computes the colour and pushes it to the backend."""

    def __init__(self, settings, events, connect_fn):
        super().__init__(daemon=True, name="Engine")
        self.s = settings
        self.events = events
        self.connect_fn = connect_fn
        self.stop_evt = threading.Event()
        self.color = (0.0, 0.0, 0.0)
        self.speed = 0.0
        self.last_key = None          # (time, vk) for the on-screen preview
        self.state = "connecting"     # connecting | connected | preview
        self.backend_name = ""
        self.attempts = []
        self.error = ""

    def run(self):
        backend, self.attempts = self.connect_fn(self.s["base"])
        if backend:
            self.state, self.backend_name = "connected", backend.name
        else:
            self.state = "preview"

        held = set()
        presses = collections.deque()
        flash = 0.0
        flash_color = self.s["flash"]
        last = time.perf_counter()
        last_apply = 0.0
        last_sent = None

        while not self.stop_evt.is_set():
            now = time.perf_counter()
            dt, last = now - last, now

            while self.events:
                t, vk, down = self.events.popleft()
                if not down:
                    held.discard(vk)
                    continue
                if vk in held:          # ignore auto-repeat while a key is held
                    continue
                held.add(vk)
                if self.s["paused"]:
                    continue
                presses.append(t)
                flash = 1.0
                self.last_key = (t, vk)
                flash_color = (KEYTYPE_COLORS[key_type(vk)]
                               if self.s["mode"] == "keytype" else self.s["flash"])

            while presses and now - presses[0] > SPEED_WINDOW:
                presses.popleft()
            kps = len(presses) / SPEED_WINDOW
            self.speed += (kps - self.speed) * clamp(dt * 4)
            flash *= math.exp(-dt / max(0.05, self.s["decay"]))

            self.color = compute_color(self.s, self.speed, flash, flash_color)

            if backend and now - last_apply >= 1.0 / MAX_APPLY_FPS:
                val = tuple(int(round(clamp(v, 0, 255))) for v in self.color)
                if val != last_sent:
                    try:
                        backend.apply(val)
                        last_sent, last_apply = val, now
                    except Exception as e:
                        self.error = str(e)
                        self.state = "preview"
                        backend.close()
                        backend = None

            time.sleep(1 / 60)

        if backend:
            try:
                backend.apply(self.s["base"])  # leave the keyboard on the base colour
            except Exception:
                pass
            backend.close()
