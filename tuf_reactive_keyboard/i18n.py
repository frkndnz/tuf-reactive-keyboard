"""Turkish / English UI strings."""

STRINGS = {
    "en": {
        "subtitle": "Typing-reactive lighting for ASUS TUF keyboards",
        "status_connecting": "Connecting…",
        "status_connected": "Connected",
        "status_preview": "Preview only",
        "status_paused": "Paused",
        "speed_unit": "WPM",
        "keys_per_sec": "{:.1f} keys/s",
        "section_mode": "Effect",
        "mode_combo": "Combo",
        "mode_flash": "Flash",
        "mode_speed": "Speed",
        "mode_keytype": "Key type",
        "desc_combo": "Colour follows your typing speed and flashes on every key.",
        "desc_flash": "The keyboard lights up on every key press and fades out.",
        "desc_speed": "Blue when you type slowly, shifting to red as you speed up.",
        "desc_keytype": "Letters, digits, space, Enter and delete keys flash in different colours.",
        "section_theme": "Theme",
        "theme_ocean": "Ocean",
        "theme_fire": "Fire",
        "theme_neon": "Neon",
        "theme_matrix": "Matrix",
        "theme_ice": "Ice",
        "theme_sunset": "Sunset",
        "theme_custom": "Custom",
        "color_base": "Idle colour",
        "color_flash": "Flash colour",
        "section_tuning": "Fine-tuning",
        "decay": "Fade time",
        "idle": "Idle brightness",
        "section_app": "App",
        "autostart": "Start with Windows",
        "close_to_tray": "Keep running in tray when closed",
        "language": "Language",
        "lang_auto": "Auto",
        "pause": "Pause",
        "resume": "Resume",
        "diagnostics": "Copy diagnostics",
        "copied": "Copied!",
        "tray_show": "Show",
        "tray_quit": "Quit",
        "tray_mode": "Effect",
        "already_running": "TUF Reactive Keyboard is already running (check the system tray).",
        "preview_help": "The keyboard could not be reached. The effect runs in the preview only. "
                        "Try running as administrator, or copy the diagnostics and open an issue on GitHub.",
        "pick_color": "Pick a colour",
        "restart_note": "Language changes apply after restart.",
    },
    "tr": {
        "subtitle": "ASUS TUF klavyeler için yazmaya tepki veren aydınlatma",
        "status_connecting": "Bağlanıyor…",
        "status_connected": "Bağlı",
        "status_preview": "Sadece önizleme",
        "status_paused": "Duraklatıldı",
        "speed_unit": "kelime/dk",
        "keys_per_sec": "{:.1f} tuş/sn",
        "section_mode": "Efekt",
        "mode_combo": "Karma",
        "mode_flash": "Flaş",
        "mode_speed": "Hız",
        "mode_keytype": "Tuş türü",
        "desc_combo": "Renk yazma hızını takip eder, her tuşta flaş yapar.",
        "desc_flash": "Her tuşa basışta klavye parlar ve yavaşça söner.",
        "desc_speed": "Yavaş yazarken mavi, hızlandıkça kırmızıya kayar.",
        "desc_keytype": "Harf, rakam, boşluk, Enter ve silme tuşları farklı renkte flaş yapar.",
        "section_theme": "Tema",
        "theme_ocean": "Okyanus",
        "theme_fire": "Ateş",
        "theme_neon": "Neon",
        "theme_matrix": "Matrix",
        "theme_ice": "Buz",
        "theme_sunset": "Gün batımı",
        "theme_custom": "Özel",
        "color_base": "Bekleme rengi",
        "color_flash": "Flaş rengi",
        "section_tuning": "İnce ayar",
        "decay": "Sönme süresi",
        "idle": "Bekleme parlaklığı",
        "section_app": "Uygulama",
        "autostart": "Windows ile başlat",
        "close_to_tray": "Kapatınca tepside çalışmaya devam et",
        "language": "Dil",
        "lang_auto": "Otomatik",
        "pause": "Duraklat",
        "resume": "Devam et",
        "diagnostics": "Tanılama bilgisini kopyala",
        "copied": "Kopyalandı!",
        "tray_show": "Göster",
        "tray_quit": "Çıkış",
        "tray_mode": "Efekt",
        "already_running": "TUF Reactive Keyboard zaten çalışıyor (sistem tepsisine bak).",
        "preview_help": "Klavyeye ulaşılamadı, efekt sadece önizlemede çalışıyor. "
                        "Yönetici olarak çalıştırmayı dene ya da tanılama bilgisini kopyalayıp GitHub'da bildir.",
        "pick_color": "Renk seç",
        "restart_note": "Dil değişikliği yeniden başlatınca uygulanır.",
    },
}


def system_language():
    try:
        import ctypes
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        if lang_id & 0x3FF == 0x1F:  # LANG_TURKISH
            return "tr"
    except Exception:
        pass
    return "en"


class Translator:
    def __init__(self, setting="auto"):
        self.lang = system_language() if setting == "auto" else setting
        if self.lang not in STRINGS:
            self.lang = "en"

    def __call__(self, key):
        return STRINGS[self.lang].get(key) or STRINGS["en"].get(key, key)
