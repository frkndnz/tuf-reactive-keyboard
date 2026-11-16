"""Main window (CustomTkinter)."""

import queue
import tkinter as tk
from tkinter import colorchooser

import customtkinter as ctk

from . import APP_NAME, __version__, config, diagnostics
from .effects import MODES, THEMES, from_hex, lerp, to_hex

# Palette
BG = "#0e1014"
CARD = "#161920"
CARD_BORDER = "#242833"
KEY = "#1c1f27"
TEXT = "#e8eaf0"
MUTED = "#8b91a3"
ACCENT = "#3b82f6"
ACCENT_HOVER = "#2f6fd6"
STATUS_COLORS = {
    "connecting": "#4b5263",
    "connected": "#15803d",
    "preview": "#b45309",
    "paused": "#475569",
}

# Simple laptop keyboard: key widths per row, in key units (15 units per row)
KB_ROWS = [
    [1] * 13 + [2],
    [1.5] + [1] * 12 + [1.5],
    [1.75] + [1] * 11 + [2.25],
    [2.25] + [1] * 10 + [2.75],
    [1.25, 1.25, 1.25, 6.25, 1.25, 1.25, 1.25, 1.25],
]


def _round_rect(canvas, x0, y0, x1, y1, r, **kw):
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return canvas.create_polygon(pts, smooth=True, **kw)


class Card(ctk.CTkFrame):
    def __init__(self, master, title=None, **kw):
        super().__init__(master, fg_color=CARD, corner_radius=14,
                         border_width=1, border_color=CARD_BORDER, **kw)
        self.grid_columnconfigure(0, weight=1)
        if title:
            ctk.CTkLabel(self, text=title.upper(), text_color=MUTED,
                         font=ctk.CTkFont("Segoe UI", 11, "bold")).grid(
                row=0, column=0, sticky="w", padx=16, pady=(12, 4))


class MainWindow(ctk.CTk):
    def __init__(self, t, settings, engine, tray_factory=None, start_hidden=False):
        ctk.set_appearance_mode("dark")
        super().__init__(fg_color=BG)
        self.t = t
        self.s = settings
        self.engine = engine
        self.q = queue.Queue()
        self._save_job = None
        self._last_hex = None
        self._last_status = None

        self.title(APP_NAME)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.font_h1 = ctk.CTkFont("Segoe UI", 20, "bold")
        self.font_body = ctk.CTkFont("Segoe UI", 13)
        self.font_small = ctk.CTkFont("Segoe UI", 12)
        self.font_big = ctk.CTkFont("Segoe UI", 34, "bold")

        self._build()

        self.tray = None
        if tray_factory:
            try:
                self.tray = tray_factory(lambda action, arg: self.q.put((action, arg)))
                self.tray.start()
            except Exception:
                self.tray = None

        if start_hidden and self.tray:
            self.withdraw()
        self.after(33, self._tick)

    # ------------------------------------------------------------ layout
    def _build(self):
        t = self.t
        root = ctk.CTkFrame(self, fg_color="transparent")
        root.pack(padx=18, pady=16)

        # Header
        header = ctk.CTkFrame(root, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=APP_NAME, font=self.font_h1, text_color=TEXT).grid(
            row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text=t("subtitle"), font=self.font_small, text_color=MUTED).grid(
            row=1, column=0, sticky="w")
        self.status_pill = ctk.CTkLabel(header, text=t("status_connecting"), corner_radius=12,
                                        fg_color=STATUS_COLORS["connecting"], text_color="white",
                                        font=ctk.CTkFont("Segoe UI", 12, "bold"), height=26)
        self.status_pill.grid(row=0, column=1, rowspan=2, sticky="e", ipadx=10)

        left = ctk.CTkFrame(root, fg_color="transparent")
        left.grid(row=1, column=0, sticky="ns", padx=(0, 12))
        left.grid_rowconfigure(1, weight=1)
        right = ctk.CTkFrame(root, fg_color="transparent")
        right.grid(row=1, column=1, sticky="ns")

        self._build_preview(left)
        self._build_mode(left)
        self._build_theme(right)
        self._build_tuning(right)
        self._build_app(right)

        ctk.CTkLabel(root, text=f"v{__version__}  ·  github.com/frkndnz/tuf-reactive-keyboard",
                     font=self.font_small, text_color="#5b6172").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _build_preview(self, parent):
        card = Card(parent)
        card.grid(row=0, column=0, sticky="ew")
        self.cw, self.ch = 420, 200
        self.canvas = tk.Canvas(card, width=self.cw, height=self.ch, bg=CARD,
                                highlightthickness=0, bd=0)
        self.canvas.grid(row=0, column=0, padx=16, pady=(16, 6))

        pad = 18
        self.glow = _round_rect(self.canvas, pad - 8, 10, self.cw - pad + 8, self.ch - 10, 18,
                                fill=CARD, outline="")
        unit = (self.cw - 2 * pad) / 15
        kh = (self.ch - 2 * 22) / 5
        self.keys = []
        y = 22
        for row in KB_ROWS:
            x = pad
            for w in row:
                k = _round_rect(self.canvas, x + 2, y + 2, x + w * unit - 2, y + kh - 2, 5,
                                fill=KEY, outline="#000000", width=1.6)
                self.keys.append(k)
                x += w * unit
            y += kh

        stats = ctk.CTkFrame(card, fg_color="transparent")
        stats.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 6))
        self.wpm_lbl = ctk.CTkLabel(stats, text="0", font=self.font_big, text_color=TEXT)
        self.wpm_lbl.grid(row=0, column=0, rowspan=2, sticky="w")
        ctk.CTkLabel(stats, text=self.t("speed_unit"), font=self.font_small,
                     text_color=MUTED).grid(row=0, column=1, sticky="sw", padx=(8, 0), pady=(10, 0))
        self.kps_lbl = ctk.CTkLabel(stats, text=self.t("keys_per_sec").format(0),
                                    font=self.font_small, text_color=MUTED)
        self.kps_lbl.grid(row=1, column=1, sticky="nw", padx=(8, 0))
        self.pause_btn = ctk.CTkButton(stats, text=self.t("pause"), width=110, height=32,
                                       fg_color=CARD_BORDER, hover_color="#30364a",
                                       command=self.toggle_pause, font=self.font_body)
        self.pause_btn.grid(row=0, column=2, rowspan=2, sticky="e")
        stats.grid_columnconfigure(2, weight=1)

        self.help_lbl = ctk.CTkLabel(card, text="", font=self.font_small, text_color="#f59e0b",
                                     wraplength=420, justify="left")
        self.help_lbl.grid(row=2, column=0, sticky="w", padx=18, pady=(0, 12))

    def _build_mode(self, parent):
        t = self.t
        card = Card(parent, t("section_mode"))
        card.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        self.mode_labels = {m: t(f"mode_{m}") for m in MODES}
        self.mode_by_label = {v: k for k, v in self.mode_labels.items()}
        self.mode_seg = ctk.CTkSegmentedButton(
            card, values=list(self.mode_labels.values()), command=self._on_mode,
            font=self.font_body, height=34, selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER, unselected_color=KEY,
            unselected_hover_color="#262a35", fg_color=KEY)
        self.mode_seg.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 8))
        self.mode_seg.set(self.mode_labels[self.s["mode"]])
        self.mode_desc = ctk.CTkLabel(card, text=t(f"desc_{self.s['mode']}"), font=self.font_small,
                                      text_color=MUTED, wraplength=420, justify="left", height=36,
                                      anchor="w")
        self.mode_desc.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 12))

    def _build_theme(self, parent):
        t = self.t
        card = Card(parent, t("section_theme"))
        card.grid(row=0, column=0, sticky="ew")
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.grid(row=1, column=0, sticky="w", padx=14, pady=(4, 6))
        self.theme_btns = {}
        for i, (tid, (base, flash)) in enumerate(THEMES.items()):
            b = ctk.CTkButton(grid, text=t(f"theme_{tid}"), width=96, height=34, corner_radius=10,
                              fg_color=to_hex(lerp(base, (0, 0, 0), 0.25)),
                              hover_color=to_hex(base), border_color=to_hex(flash),
                              text_color="white", font=self.font_small,
                              command=lambda tid=tid: self._on_theme(tid))
            b.grid(row=i // 3, column=i % 3, padx=3, pady=3)
            self.theme_btns[tid] = b

        colors = ctk.CTkFrame(card, fg_color="transparent")
        colors.grid(row=2, column=0, sticky="ew", padx=14, pady=(2, 14))
        self.base_btn = self._color_button(colors, "base", t("color_base"))
        self.base_btn.grid(row=0, column=0, padx=3)
        self.flash_btn = self._color_button(colors, "flash", t("color_flash"))
        self.flash_btn.grid(row=0, column=1, padx=3)
        self._refresh_theme_ui()

    def _color_button(self, parent, key, label):
        return ctk.CTkButton(parent, text=label, width=147, height=34, corner_radius=10,
                             border_width=2, font=self.font_small,
                             command=lambda: self._pick_color(key))

    def _build_tuning(self, parent):
        t = self.t
        card = Card(parent, t("section_tuning"))
        card.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.decay_val = self._slider_row(card, 1, t("decay"), 0.1, 1.5, 28, self.s["decay"],
                                          self._on_decay, lambda v: f"{v:.2f} s")
        self.idle_val = self._slider_row(card, 2, t("idle"), 0, 1, 20, self.s["idle"],
                                         self._on_idle, lambda v: f"{v * 100:.0f}%")

    def _slider_row(self, card, row, label, lo, hi, steps, value, cmd, fmt):
        f = ctk.CTkFrame(card, fg_color="transparent")
        f.grid(row=row, column=0, sticky="ew", padx=16, pady=(2, 10 if row == 2 else 2))
        f.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(f, text=label, font=self.font_body, text_color=TEXT, width=130,
                     anchor="w").grid(row=0, column=0, sticky="w")
        val = ctk.CTkLabel(f, text=fmt(value), font=self.font_small, text_color=MUTED, width=56,
                           anchor="e")
        val.grid(row=0, column=2, sticky="e")
        sl = ctk.CTkSlider(f, from_=lo, to=hi, number_of_steps=steps, width=150,
                           button_color=ACCENT, button_hover_color=ACCENT_HOVER,
                           progress_color=ACCENT,
                           command=lambda v: (cmd(v), val.configure(text=fmt(v))))
        sl.set(value)
        sl.grid(row=0, column=1, sticky="ew", padx=8)
        return val

    def _build_app(self, parent):
        t = self.t
        card = Card(parent, t("section_app"))
        card.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.autostart_sw = ctk.CTkSwitch(card, text=t("autostart"), font=self.font_body,
                                          progress_color=ACCENT, command=self._on_autostart)
        self.autostart_sw.grid(row=1, column=0, sticky="w", padx=16, pady=4)
        try:
            if config.autostart_enabled():
                self.autostart_sw.select()
        except Exception:
            pass
        self.tray_sw = ctk.CTkSwitch(card, text=t("close_to_tray"), font=self.font_body,
                                     progress_color=ACCENT, command=self._on_close_to_tray)
        self.tray_sw.grid(row=2, column=0, sticky="w", padx=16, pady=4)
        if self.s["close_to_tray"]:
            self.tray_sw.select()

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=3, column=0, sticky="ew", padx=16, pady=(6, 16))
        ctk.CTkLabel(row, text=t("language"), font=self.font_body, text_color=TEXT).grid(
            row=0, column=0, sticky="w")
        self.lang_map = {t("lang_auto"): "auto", "Türkçe": "tr", "English": "en"}
        lang_label = {v: k for k, v in self.lang_map.items()}[self.s["language"]]
        self.lang_menu = ctk.CTkOptionMenu(row, values=list(self.lang_map), width=110, height=30,
                                           fg_color=KEY, button_color=CARD_BORDER,
                                           button_hover_color="#30364a", font=self.font_small,
                                           command=self._on_language)
        self.lang_menu.set(lang_label)
        self.lang_menu.grid(row=0, column=1, padx=(10, 0))
        self.diag_btn = ctk.CTkButton(row, text=t("diagnostics"), height=30, fg_color=CARD_BORDER,
                                      hover_color="#30364a", font=self.font_small,
                                      command=self._copy_diagnostics)
        self.diag_btn.grid(row=0, column=2, padx=(10, 0))
        self.note_lbl = ctk.CTkLabel(card, text="", font=self.font_small, text_color=MUTED)
        self.note_lbl.grid(row=4, column=0, sticky="w", padx=16, pady=(0, 10))
        self.note_lbl.grid_remove()

    # ------------------------------------------------------------ actions
    def _schedule_save(self):
        if self._save_job:
            self.after_cancel(self._save_job)
        self._save_job = self.after(600, lambda: config.save(self.s))

    def _on_mode(self, label):
        self.set_mode(self.mode_by_label[label])

    def set_mode(self, mode):
        self.s["mode"] = mode
        self.mode_seg.set(self.mode_labels[mode])
        self.mode_desc.configure(text=self.t(f"desc_{mode}"))
        if self.tray:
            self.tray.refresh()
        self._schedule_save()

    def _on_theme(self, tid):
        self.s["theme"] = tid
        self.s["base"], self.s["flash"] = THEMES[tid]
        self._refresh_theme_ui()
        self._schedule_save()

    def _pick_color(self, key):
        res = colorchooser.askcolor(color=to_hex(self.s[key]), title=self.t("pick_color"),
                                    parent=self)
        if res and res[1]:
            self.s[key] = from_hex(res[1])
            self.s["theme"] = "custom"
            self._refresh_theme_ui()
            self._schedule_save()

    def _refresh_theme_ui(self):
        for tid, b in self.theme_btns.items():
            b.configure(border_width=3 if self.s["theme"] == tid else 0)
        for btn, key in ((self.base_btn, "base"), (self.flash_btn, "flash")):
            c = self.s[key]
            btn.configure(fg_color=to_hex(lerp(c, (0, 0, 0), 0.3)), hover_color=to_hex(c),
                          border_color=to_hex(c),
                          text_color="black" if sum(c) > 500 else "white")

    def _on_decay(self, v):
        self.s["decay"] = round(float(v), 2)
        self._schedule_save()

    def _on_idle(self, v):
        self.s["idle"] = round(float(v), 2)
        self._schedule_save()

    def toggle_pause(self):
        self.s["paused"] = not self.s["paused"]
        self.pause_btn.configure(text=self.t("resume") if self.s["paused"] else self.t("pause"))
        if self.tray:
            self.tray.refresh()

    def _on_autostart(self):
        try:
            config.set_autostart(bool(self.autostart_sw.get()))
        except Exception as e:
            self.note_lbl.configure(text=str(e))
            self.note_lbl.grid()

    def _on_close_to_tray(self):
        self.s["close_to_tray"] = bool(self.tray_sw.get())
        self._schedule_save()

    def _on_language(self, label):
        self.s["language"] = self.lang_map[label]
        self.note_lbl.configure(text=self.t("restart_note"))
        self.note_lbl.grid()
        self._schedule_save()

    def _copy_diagnostics(self):
        self.clipboard_clear()
        self.clipboard_append(diagnostics.report(self.engine))
        self.diag_btn.configure(text=self.t("copied"))
        self.after(1500, lambda: self.diag_btn.configure(text=self.t("diagnostics")))

    def show(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def on_close(self):
        if self.s["close_to_tray"] and self.tray:
            self.withdraw()
        else:
            self.quit_app()

    def quit_app(self):
        config.save(self.s)
        if self.tray:
            self.tray.stop()
        self.quit()

    # ------------------------------------------------------------ loop
    def _tick(self):
        while not self.q.empty():
            action, arg = self.q.get_nowait()
            if action == "show":
                self.show()
            elif action == "quit":
                self.quit_app()
                return
            elif action == "toggle_pause":
                self.toggle_pause()
            elif action == "mode":
                self.set_mode(arg)

        e = self.engine
        status = "paused" if self.s["paused"] and e.state == "connected" else e.state
        if status != self._last_status:
            self._last_status = status
            text = self.t(f"status_{status}")
            self.status_pill.configure(text=f"  {text}  ", fg_color=STATUS_COLORS[status])
            self.help_lbl.configure(text=self.t("preview_help") if status == "preview" else "")
            if not self.help_lbl.cget("text"):
                self.help_lbl.grid_remove()
            else:
                self.help_lbl.grid()

        if self.state() != "withdrawn":
            c = e.color
            h = to_hex(c)
            if h != self._last_hex:
                self._last_hex = h
                for k in self.keys:
                    self.canvas.itemconfigure(k, outline=h)
                self.canvas.itemconfigure(self.glow, fill=to_hex(lerp(from_hex(CARD), c, 0.16)))
            self.wpm_lbl.configure(text=f"{e.speed * 12:.0f}")
            self.kps_lbl.configure(text=self.t("keys_per_sec").format(e.speed))

        self.after(33, self._tick)
