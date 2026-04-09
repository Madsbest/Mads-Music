import os
import jnius
import shutil
import random
import time
import threading
import json
import re

import pygame
from jnius import autoclass, PythonJavaClass, java_method
from kivy.app import App
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image as KivyImage
from kivy.core.window import Window
from kivy.clock import Clock, mainthread
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.utils import platform
from kivy.config import Config
from kivy.metrics import dp, sp

Config.set('graphics', 'resizable', '0')

try:
    from plyer import filechooser
except ImportError:
    filechooser = None

if platform != 'android':
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.mixer.init()

# ── Paden ─────────────────────────────────────────────────────────────────────
APP_BASE_PATH = os.path.dirname(os.path.abspath(__file__))


def get_android_files_dir():
    try:
        from android.storage import app_storage_path
        base_path = app_storage_path()
        if base_path:
            return base_path
    except Exception:
        pass
    try:
        activity = autoclass('org.kivy.android.PythonActivity').mActivity
        context = activity.getApplicationContext()
        return context.getFilesDir().getAbsolutePath()
    except Exception:
        return APP_BASE_PATH


def get_writable_base_path():
    if platform == 'android':
        return get_android_files_dir()
    return APP_BASE_PATH


WRITABLE_BASE_PATH = get_writable_base_path()
BACKGROUND_SERVICE_STATE = os.path.join(WRITABLE_BASE_PATH, "background_service.json")
MEDIA_STATE_PATH = os.path.join(WRITABLE_BASE_PATH, "media_state.json")
MEDIA_COMMAND_PATH = os.path.join(WRITABLE_BASE_PATH, "media_command.json")
APP_STATE_PATH = os.path.join(WRITABLE_BASE_PATH, "app_state.json")
APP_DEBUG_LOG_PATH = os.path.join(WRITABLE_BASE_PATH, "app_debug.log")
SERVICE_HEARTBEAT_PATH = os.path.join(WRITABLE_BASE_PATH, "service_heartbeat.json")


def get_safe_paths():
    music = os.path.join(WRITABLE_BASE_PATH, "music")
    os.makedirs(music, exist_ok=True)
    return music, os.path.join(APP_BASE_PATH, "Buttons")

MUSIC_PATH, ICON_PATH = get_safe_paths()
CIRCLE_IMG = os.path.join(ICON_PATH, "circle.png")
UPLOAD_IMG = os.path.join(ICON_PATH, "uploadmusic.png")
DELETE_IMG = os.path.join(ICON_PATH, "delete.png")
LIKE_ON_IMG = os.path.join(ICON_PATH, "likebuttonon.png")
LIKE_OFF_IMG = os.path.join(ICON_PATH, "likebuttonoff.png")
SETTINGS_IMG = os.path.join(ICON_PATH, "settings.png")
SERVICE_NOTIFICATION_CHANNEL_ID = "mads_music_playback_v4"
NOTIFICATION_CHANNEL_ID = "mads_music_in_app_v2"
NOTIFICATION_ID = 424242
ACTION_PREV = "org.madsmusic.action.PREV"
ACTION_PLAY_PAUSE = "org.madsmusic.action.PLAY_PAUSE"
ACTION_NEXT = "org.madsmusic.action.NEXT"
ACTION_STOP = "org.madsmusic.action.STOP"
NOTIFICATION_ACTION_EXTRA = "mads_notification_action"
DEFAULT_LANGUAGE = "nl"
DEFAULT_THEME = "graphite"
DEFAULT_PLAYBACK_SPEED = 1.0
MIN_PLAYBACK_SPEED = 0.75
MAX_PLAYBACK_SPEED = 2.0
PLAYBACK_SPEED_OPTIONS = [0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
DEFAULT_SEEK_STEP = 10
SEEK_STEP_OPTIONS = [5, 10, 15, 30]
DEFAULT_PLAYLIST_DENSITY = "balanced"
PLAYLIST_DENSITY_OPTIONS = ["compact", "balanced", "comfortable"]
THEMES = {
    "graphite": {
        "bg": (0.05, 0.05, 0.05, 1),
        "panel": (0.12, 0.12, 0.12, 1),
        "panel_alt": (0.15, 0.15, 0.15, 1),
        "accent": (0.12, 0.8, 0.45, 1),
        "accent_soft": (0.12, 0.8, 0.45, 0.24),
        "accent_row": (0.12, 0.8, 0.45, 0.3),
        "text": (0.95, 0.95, 0.95, 1),
        "muted": (0.65, 0.65, 0.65, 1),
        "popup_overlay": (0, 0, 0, 0.82),
    },
    "midnight": {
        "bg": (0.03, 0.05, 0.09, 1),
        "panel": (0.07, 0.11, 0.17, 1),
        "panel_alt": (0.1, 0.15, 0.22, 1),
        "accent": (0.24, 0.64, 1.0, 1),
        "accent_soft": (0.24, 0.64, 1.0, 0.22),
        "accent_row": (0.24, 0.64, 1.0, 0.28),
        "text": (0.93, 0.96, 1, 1),
        "muted": (0.63, 0.72, 0.82, 1),
        "popup_overlay": (0, 0.02, 0.06, 0.84),
    },
    "sunset": {
        "bg": (0.11, 0.08, 0.07, 1),
        "panel": (0.18, 0.12, 0.1, 1),
        "panel_alt": (0.22, 0.15, 0.12, 1),
        "accent": (1.0, 0.47, 0.22, 1),
        "accent_soft": (1.0, 0.47, 0.22, 0.22),
        "accent_row": (1.0, 0.47, 0.22, 0.28),
        "text": (0.98, 0.95, 0.92, 1),
        "muted": (0.79, 0.69, 0.62, 1),
        "popup_overlay": (0.06, 0.02, 0.01, 0.84),
    },
    "forest": {
        "bg": (0.05, 0.08, 0.06, 1),
        "panel": (0.09, 0.14, 0.11, 1),
        "panel_alt": (0.12, 0.18, 0.14, 1),
        "accent": (0.34, 0.87, 0.54, 1),
        "accent_soft": (0.34, 0.87, 0.54, 0.22),
        "accent_row": (0.34, 0.87, 0.54, 0.28),
        "text": (0.93, 0.98, 0.95, 1),
        "muted": (0.66, 0.79, 0.72, 1),
        "popup_overlay": (0.01, 0.05, 0.03, 0.84),
    },
}
TRANSLATIONS = {
    "nl": {
        "search_hint": "Zoek nummer...",
        "clear": "Wis",
        "scope_all": "Alle tracks",
        "scope_favorites": "Favorieten",
        "scope_recent": "Recent gespeeld",
        "sort_title": "Sortering: A-Z",
        "sort_recent": "Sortering: Nieuw",
        "sort_reverse": "Sortering: Z-A",
        "library_stats": "{visible} zichtbaar | {total} tracks | {favorites} favorieten | {recent} recent",
        "choose_track": "Kies een track",
        "tagline": "Mads Music Player",
        "track_counter": "Track {index} van {total}",
        "up_next_empty": "Up next: voeg tracks toe om een queue te zien",
        "up_next_single": "Up next: geen andere tracks in je library",
        "up_next_shuffle": "Up next: shuffle kiest live uit je library",
        "up_next_prefix": "Up next: {tracks}",
        "settings_title": "Instellingen",
        "settings_language": "Taal",
        "settings_theme": "Thema",
        "settings_library": "Library-weergave",
        "settings_sorting": "Sortering",
        "settings_density": "Playlist-grootte",
        "settings_speed": "Afspeelsnelheid",
        "settings_seek_step": "Sprongknoppen",
        "settings_delete_behavior": "Verwijderen",
        "settings_actions": "Acties",
        "settings_about": "Over deze app",
        "settings_subtitle": "Pas je player aan zoals jij hem wilt.",
        "settings_reset": "Herstel standaard",
        "settings_clear_recent": "Wis recent",
        "settings_close": "Sluiten",
        "settings_delete_confirm_on": "Vraag eerst",
        "settings_delete_confirm_off": "Direct",
        "density_compact": "Compact",
        "density_balanced": "Normaal",
        "density_comfortable": "Ruim",
        "about_tracks": "Tracks",
        "about_library": "Library-map",
        "about_mode": "Huidige modus",
        "lang_nl": "Nederlands",
        "lang_en": "Engels",
        "theme_graphite": "Graphite",
        "theme_midnight": "Midnight",
        "theme_sunset": "Sunset",
        "theme_forest": "Forest",
        "delete_badge": "VERWIJDER TRACK",
        "delete_subtitle": "Dit nummer wordt uit je library verwijderd. Favorietstatus gaat ook weg.",
        "delete_keep": "Toch houden",
        "delete_confirm": "Ja, verwijderen",
        "imported": "Geimporteerd: {filename}",
        "version_label": "Versie {version}",
        "load_failed": "Laden mislukt",
        "track_info_button": "Track info",
        "track_info_duration": "Lengte",
        "track_info_file": "Bestand",
        "track_info_favorite": "Favoriet",
        "track_info_modes": "Modus",
        "track_info_speed": "Snelheid",
        "track_info_close": "Sluiten",
        "track_info_yes": "Ja",
        "track_info_no": "Nee",
        "mode_standard": "Standaard afspelen",
        "mode_shuffle": "Shuffle",
        "mode_repeat": "Repeat",
    },
    "en": {
        "search_hint": "Search track...",
        "clear": "Clear",
        "scope_all": "All tracks",
        "scope_favorites": "Favorites",
        "scope_recent": "Recently played",
        "sort_title": "Sort: A-Z",
        "sort_recent": "Sort: Newest",
        "sort_reverse": "Sort: Z-A",
        "library_stats": "{visible} visible | {total} tracks | {favorites} favorites | {recent} recent",
        "choose_track": "Choose a track",
        "tagline": "Mads Music Player",
        "track_counter": "Track {index} of {total}",
        "up_next_empty": "Up next: add tracks to see a queue",
        "up_next_single": "Up next: no other tracks in your library",
        "up_next_shuffle": "Up next: shuffle chooses live from your library",
        "up_next_prefix": "Up next: {tracks}",
        "settings_title": "Settings",
        "settings_language": "Language",
        "settings_theme": "Theme",
        "settings_library": "Library view",
        "settings_sorting": "Sorting",
        "settings_density": "Playlist size",
        "settings_speed": "Playback speed",
        "settings_seek_step": "Jump buttons",
        "settings_delete_behavior": "Delete flow",
        "settings_actions": "Actions",
        "settings_about": "About this app",
        "settings_subtitle": "Tune the player so it feels exactly right.",
        "settings_reset": "Reset defaults",
        "settings_clear_recent": "Clear recent",
        "settings_close": "Close",
        "settings_delete_confirm_on": "Ask first",
        "settings_delete_confirm_off": "Instant",
        "density_compact": "Compact",
        "density_balanced": "Balanced",
        "density_comfortable": "Comfort",
        "about_tracks": "Tracks",
        "about_library": "Library folder",
        "about_mode": "Current mode",
        "lang_nl": "Dutch",
        "lang_en": "English",
        "theme_graphite": "Graphite",
        "theme_midnight": "Midnight",
        "theme_sunset": "Sunset",
        "theme_forest": "Forest",
        "delete_badge": "DELETE TRACK",
        "delete_subtitle": "This song will be removed from your library. Favorite status will also be cleared.",
        "delete_keep": "Keep it",
        "delete_confirm": "Yes, delete",
        "imported": "Imported: {filename}",
        "version_label": "Version {version}",
        "load_failed": "Loading failed",
        "track_info_button": "Track info",
        "track_info_duration": "Duration",
        "track_info_file": "File",
        "track_info_favorite": "Favorite",
        "track_info_modes": "Mode",
        "track_info_speed": "Speed",
        "track_info_close": "Close",
        "track_info_yes": "Yes",
        "track_info_no": "No",
        "mode_standard": "Standard playback",
        "mode_shuffle": "Shuffle",
        "mode_repeat": "Repeat",
    },
}


def current_palette():
    app = App.get_running_app()
    theme_name = getattr(app, 'theme_name', DEFAULT_THEME) if app else DEFAULT_THEME
    return THEMES.get(theme_name, THEMES[DEFAULT_THEME])


def format_speed_value(speed):
    text = f"{float(speed):.2f}".rstrip("0").rstrip(".")
    if "." not in text:
        text += ".0"
    return f"{text}x"


def read_project_version():
    try:
        spec_path = os.path.join(APP_BASE_PATH, "buildozer.spec")
        with open(spec_path, "r", encoding="utf-8") as fh:
            content = fh.read()
        match = re.search(r"(?m)^version\s*=\s*(.+?)\s*$", content)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return "dev"


def get_runtime_app_version():
    if platform == 'android':
        try:
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            context = activity.getApplicationContext()
            package_manager = context.getPackageManager()
            package_name = context.getPackageName()
            build_version = autoclass('android.os.Build$VERSION')
            version_codes = autoclass('android.os.Build$VERSION_CODES')
            if build_version.SDK_INT >= 33:
                package_info_flags = autoclass('android.content.pm.PackageManager$PackageInfoFlags')
                package_info = package_manager.getPackageInfo(package_name, package_info_flags.of(0))
            else:
                package_info = package_manager.getPackageInfo(package_name, 0)
            version_name = str(package_info.versionName or "").strip()
            if version_name:
                return version_name
        except Exception:
            pass
    return read_project_version()


def app_debug_log(message):
    try:
        with open(APP_DEBUG_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except Exception:
        pass


def read_shared_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def format_time(seconds):
    if not seconds or seconds < 0:
        return "0:00"
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"


def get_length(path):
    try:
        from mutagen import File as MFile
        f = MFile(path)
        if f and hasattr(f, 'info') and hasattr(f.info, 'length'):
            return float(f.info.length)
    except Exception:
        pass
    try:
        snd = pygame.mixer.Sound(path)
        l = snd.get_length()
        del snd
        return l
    except Exception:
        pass
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# AUDIO ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class PygameAudioEngine:

    def __init__(self, on_track_complete=None):
        self._path       = None
        self._length     = 0.0
        self._pos_offset = 0.0
        self._clk        = 0.0
        self.playing     = False
        self.loaded      = False
        self._volume     = 0.7
        self._speed      = DEFAULT_PLAYBACK_SPEED
        self._preload_path = None  # pad van vooraf geladen nummer
        self._on_track_complete = on_track_complete

    @property
    def loaded_path(self):
        return self._path

    @property
    def length(self):
        return self._length

    def load_and_play(self, path, on_length=None):
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self._volume)
            pygame.mixer.music.play()
        except Exception:
            self.loaded  = False
            self.playing = False
            return False

        self._path       = path
        self._length     = 0.0
        self._pos_offset = 0.0
        self._clk        = time.perf_counter()
        self.playing     = True
        self.loaded      = True

        if on_length:
            def _worker():
                l = get_length(path)
                Clock.schedule_once(lambda dt: on_length(l), 0)
            threading.Thread(target=_worker, daemon=True).start()

        return True

    def pause(self):
        if not self.playing:
            return
        self._pos_offset = self.get_pos()
        pygame.mixer.music.pause()
        self.playing = False

    def resume(self):
        if self.playing or not self.loaded:
            return
        pygame.mixer.music.unpause()
        self._clk    = time.perf_counter()
        self.playing = True

    def seek(self, pos):
        if not self.loaded:
            return
        pos = max(0.0, float(pos))
        was_playing = self.playing
        try:
            if was_playing:
                pygame.mixer.music.set_pos(pos)
                self._pos_offset = pos
                self._clk        = time.perf_counter()
            else:
                pygame.mixer.music.play(start=pos)
                pygame.mixer.music.pause()
                self._pos_offset = pos
                self.playing     = False
        except Exception:
            pass

    def stop(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self._path       = None
        self._length     = 0.0
        self._pos_offset = 0.0
        self.playing     = False
        self.loaded      = False

    def preload(self, path):
        """Laad het volgende nummer alvast in een achtergrond-thread."""
        if path == self._preload_path or path == self._path:
            return
        self._preload_path = path

        def _worker():
            try:
                # Haal lengte alvast op zodat die direct beschikbaar is
                get_length(path)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def set_volume(self, v):
        self._volume = max(0.0, min(1.0, float(v)))
        try:
            pygame.mixer.music.set_volume(self._volume)
        except Exception:
            pass

    def set_speed(self, speed):
        self._speed = max(MIN_PLAYBACK_SPEED, min(MAX_PLAYBACK_SPEED, float(speed)))

    def get_pos(self):
        if not self.playing:
            return self._pos_offset
        elapsed = time.perf_counter() - self._clk
        raw     = self._pos_offset + elapsed
        return min(raw, self._length) if self._length > 0 else raw

    def is_finished(self):
        if not self.playing:
            return False
        if self._length > 0 and self.get_pos() >= self._length - 0.4:
            return True
        if not pygame.mixer.music.get_busy():
            return True
        return False


class AndroidCompletionListener(PythonJavaClass):
    __javainterfaces__ = ['android/media/MediaPlayer$OnCompletionListener']
    __javacontext__ = 'app'

    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    @java_method('(Landroid/media/MediaPlayer;)V')
    def onCompletion(self, media_player):
        if self._callback:
            self._callback()


class AndroidAudioEngine:

    def __init__(self, on_track_complete=None):
        self._path = None
        self._length = 0.0
        self._volume = 0.7
        self._speed = DEFAULT_PLAYBACK_SPEED
        self.playing = False
        self.loaded = False
        self._player = None
        self._preload_path = None
        self._on_track_complete = on_track_complete

        self._activity = autoclass('org.kivy.android.PythonActivity').mActivity
        self._context = self._activity.getApplicationContext()
        self._media_player_cls = autoclass('android.media.MediaPlayer')
        self._audio_manager_cls = autoclass('android.media.AudioManager')
        self._context_cls = autoclass('android.content.Context')
        self._power_manager_cls = autoclass('android.os.PowerManager')
        self._build_version = autoclass('android.os.Build$VERSION')
        self._version_codes = autoclass('android.os.Build$VERSION_CODES')
        self._audio_manager = self._context.getSystemService(self._context_cls.AUDIO_SERVICE)
        self._completion_listener = AndroidCompletionListener(self._handle_completion)

    @property
    def loaded_path(self):
        return self._path

    @property
    def length(self):
        return self._length

    def _request_audio_focus(self):
        try:
            self._audio_manager.requestAudioFocus(
                None,
                self._audio_manager_cls.STREAM_MUSIC,
                self._audio_manager_cls.AUDIOFOCUS_GAIN
            )
        except Exception:
            pass

    def _abandon_audio_focus(self):
        try:
            self._audio_manager.abandonAudioFocus(None)
        except Exception:
            pass

    def _release_player(self):
        if not self._player:
            return
        try:
            self._player.setOnCompletionListener(None)
        except Exception:
            pass
        try:
            self._player.reset()
        except Exception:
            pass
        try:
            self._player.release()
        except Exception:
            pass
        self._player = None

    def _handle_completion(self):
        self.playing = False
        if self._on_track_complete:
            self._on_track_complete()

    def load_and_play(self, path, on_length=None):
        player = self._media_player_cls()

        try:
            self._release_player()
            self._request_audio_focus()
            try:
                player.setWakeMode(self._context, self._power_manager_cls.PARTIAL_WAKE_LOCK)
            except Exception:
                pass
            player.setAudioStreamType(self._audio_manager_cls.STREAM_MUSIC)
            player.setDataSource(path)
            player.setOnCompletionListener(self._completion_listener)
            player.prepare()
            player.setVolume(self._volume, self._volume)
            player.start()
            self._apply_speed(player)
        except Exception:
            try:
                player.release()
            except Exception:
                pass
            self.loaded = False
            self.playing = False
            self._path = None
            self._length = 0.0
            return False

        self._player = player
        self._path = path
        self._length = max(0.0, player.getDuration() / 1000.0)
        self.playing = True
        self.loaded = True

        if on_length:
            Clock.schedule_once(lambda dt: on_length(self._length), 0)

        return True

    def pause(self):
        if not self.playing or not self._player:
            return
        try:
            self._player.pause()
            self.playing = False
        except Exception:
            pass

    def resume(self):
        if self.playing or not self.loaded or not self._player:
            return
        try:
            self._request_audio_focus()
            self._player.start()
            self.playing = True
        except Exception:
            pass

    def seek(self, pos):
        if not self.loaded or not self._player:
            return
        try:
            self._player.seekTo(int(max(0.0, float(pos)) * 1000))
        except Exception:
            pass

    def stop(self):
        if self._player:
            try:
                self._player.stop()
            except Exception:
                pass
        self._release_player()
        self._abandon_audio_focus()
        self._path = None
        self._length = 0.0
        self.playing = False
        self.loaded = False

    def preload(self, path):
        self._preload_path = path

    def set_volume(self, v):
        self._volume = max(0.0, min(1.0, float(v)))
        if not self._player:
            return
        try:
            self._player.setVolume(self._volume, self._volume)
        except Exception:
            pass

    def _apply_speed(self, player=None):
        target_player = player or self._player
        if not target_player:
            return
        try:
            if self._build_version.SDK_INT < self._version_codes.M:
                return
            params = target_player.getPlaybackParams()
            params.setSpeed(float(self._speed))
            target_player.setPlaybackParams(params)
        except Exception:
            pass

    def set_speed(self, speed):
        self._speed = max(MIN_PLAYBACK_SPEED, min(MAX_PLAYBACK_SPEED, float(speed)))
        self._apply_speed()

    def get_pos(self):
        if not self._player or not self.loaded:
            return 0.0
        try:
            return max(0.0, self._player.getCurrentPosition() / 1000.0)
        except Exception:
            return 0.0

    def is_finished(self):
        return False


def create_audio_engine(on_track_complete=None):
    if platform == 'android':
        return AndroidAudioEngine(on_track_complete=on_track_complete)
    return PygameAudioEngine(on_track_complete=on_track_complete)


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM WIDGETS
# ─────────────────────────────────────────────────────────────────────────────

class RoundedSongButton(Button):
    def __init__(self, title, is_active=False, **kwargs):
        super().__init__(**kwargs)
        self.text             = title
        self._base_font_size  = sp(15)
        self._min_font_size   = sp(11.5)
        self.font_size        = self._base_font_size
        self.background_color = (0, 0, 0, 0)
        self.color            = current_palette()["text"]
        self.is_active        = bool(is_active)
        self.halign           = 'left'
        self.valign           = 'middle'
        self.shorten          = False
        self.shorten_from     = 'right'
        self.max_lines        = 1
        self.padding          = [dp(16), dp(0)]
        with self.canvas.before:
            self._bg_color = Color(*current_palette()["panel"])
            self.rect = RoundedRectangle(radius=[dp(10)])
        self.bind(pos=self._upd, size=self._upd, text=self._upd)
        self.set_active(is_active)

    def _upd(self, *a):
        self.rect.pos  = self.pos
        self.rect.size = self.size
        self._fit_text()

    def _fit_text(self):
        available_width = max(0, self.width - dp(26))
        available_height = max(0, self.height - dp(10))
        self.text_size = (None, None)
        self.shorten = False
        size = self._base_font_size
        while size >= self._min_font_size:
            self.font_size = size
            self.texture_update()
            if self.texture_size[0] <= available_width and self.texture_size[1] <= available_height:
                break
            size -= 0.5
        else:
            self.font_size = self._min_font_size
            self.shorten = True
        self.text_size = (available_width, self.height)

    def set_active(self, is_active):
        self.is_active = bool(is_active)
        palette = current_palette()
        self._bg_color.rgba = palette["accent_row"] if self.is_active else palette["panel"]
        self.color = palette["text"]


class SpotifySlider(Slider):
    def __init__(self, **kwargs):
        kwargs.setdefault('value_track', True)
        kwargs.setdefault('value_track_color', [0.12, 0.8, 0.45, 1])
        super().__init__(**kwargs)
        try:
            if os.path.exists(CIRCLE_IMG):
                self.cursor_image = CIRCLE_IMG
        except Exception:
            pass
        try:
            self.cursor_size       = (dp(20), dp(20))
            self.padding           = dp(10)
            self.background_width  = dp(4)
            self.value_track_width = dp(4)
            self.background_color  = [0.3, 0.3, 0.3, 1]
        except Exception:
            pass
        self._grabbed      = False
        self.cb_drag_start = None
        self.cb_drag_move  = None
        self.cb_drag_end   = None

    def _touch_to_value(self, tx):
        frac = (tx - self.x) / max(1.0, self.width)
        return self.min + max(0.0, min(1.0, frac)) * (self.max - self.min)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._grabbed = True
            self.value    = self._touch_to_value(touch.x)
            if self.cb_drag_start: self.cb_drag_start()
            if self.cb_drag_move:  self.cb_drag_move(self.value)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self.value = self._touch_to_value(touch.x)
            if self.cb_drag_move: self.cb_drag_move(self.value)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self._grabbed = False
            self.value    = self._touch_to_value(touch.x)
            if self.cb_drag_end: self.cb_drag_end(self.value)
            return True
        return super().on_touch_up(touch)


class ImageButton(Button):
    def __init__(self, img_normal, img_active=None, **kwargs):
        self.icon_size = kwargs.pop("icon_size", None)
        super().__init__(**kwargs)
        self.img_normal_path   = img_normal
        self.img_active_path   = img_active if img_active else img_normal
        self.background_normal = ''
        self.background_color  = (0, 0, 0, 0)
        self.display_img = KivyImage(source=img_normal, center=self.center)
        self.add_widget(self.display_img)
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *a):
        self.display_img.center = self.center
        src = self.display_img.source
        if self.icon_size is not None:
            size = self.icon_size
            self.display_img.size = (dp(size), dp(size))
        elif "upload" in src:                    self.display_img.size = (dp(45), dp(45))
        elif "play" in src or "pause" in src:    self.display_img.size = (dp(75), dp(75))
        elif "settings" in src:                  self.display_img.size = (dp(34), dp(34))
        elif "delete" in src:                    self.display_img.size = (dp(28), dp(28))
        elif "likebutton" in src:                self.display_img.size = (dp(28), dp(28))
        else:                                    self.display_img.size = (dp(42), dp(42))

    def set_active(self, state):
        self.display_img.source = self.img_active_path if state else self.img_normal_path


class PillButton(Button):
    def __init__(self, title, active=False, **kwargs):
        self._allow_shorten = kwargs.pop("allow_shorten", False)
        self._min_font_size = kwargs.pop("min_font_size", sp(10.5))
        self._base_font_size = kwargs.pop("base_font_size", sp(12.5))
        super().__init__(**kwargs)
        self.text = title
        self.font_size = self._base_font_size
        self.bold = True
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.color = (0.95, 0.95, 0.95, 1)
        self.active = active
        self.padding = [dp(14), dp(10)]
        self.halign = 'center'
        self.valign = 'middle'
        self.shorten = False
        self.shorten_from = 'right'
        self.max_lines = 1
        with self.canvas.before:
            self._bg_color = Color(*current_palette()["panel"])
            self._bg_rect = RoundedRectangle(radius=[dp(16)])
        self.bind(pos=self._update_canvas, size=self._update_canvas, text=self._update_canvas)
        self.set_active(active)

    def _update_canvas(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._fit_text()

    def _fit_text(self):
        available_width = max(0, self.width - dp(18))
        available_height = max(0, self.height - dp(10))
        self.text_size = (None, None)
        self.shorten = False
        size = self._base_font_size
        while size >= self._min_font_size:
            self.font_size = size
            self.texture_update()
            if self.texture_size[0] <= available_width and self.texture_size[1] <= available_height:
                break
            size -= 0.5
        else:
            self.font_size = self._min_font_size
            self.shorten = self._allow_shorten
        self.text_size = (available_width, self.height)

    def set_active(self, active):
        self.active = bool(active)
        palette = current_palette()
        if self.active:
            self._bg_color.rgba = palette["accent_soft"]
            self.color = palette["accent"]
        else:
            self._bg_color.rgba = palette["panel"]
            self.color = palette["text"]


class AndroidNotificationController:
    def __init__(self, action_callback):
        self._action_callback = action_callback
        self._active = False
        self.receiver = None

        self.activity = autoclass('org.kivy.android.PythonActivity').mActivity
        self.context = self.activity.getApplicationContext()

        self.Intent = autoclass('android.content.Intent')
        self.PendingIntent = autoclass('android.app.PendingIntent')
        self.Notification = autoclass('android.app.Notification')
        self.NotificationBuilder = autoclass('android.app.Notification$Builder')
        self.NotificationMediaStyle = autoclass('android.app.Notification$MediaStyle')
        self.NotificationChannel = autoclass('android.app.NotificationChannel')
        self.NotificationManager = autoclass('android.app.NotificationManager')
        self.BuildVersion = autoclass('android.os.Build$VERSION')
        self.VersionCodes = autoclass('android.os.Build$VERSION_CODES')
        self.MediaSession = autoclass('android.media.session.MediaSession')
        self.PlaybackState = autoclass('android.media.session.PlaybackState')
        self.PlaybackStateBuilder = autoclass('android.media.session.PlaybackState$Builder')
        self.MediaMetadata = autoclass('android.media.MediaMetadata')
        self.MediaMetadataBuilder = autoclass('android.media.MediaMetadata$Builder')
        self.AndroidDrawables = autoclass('android.R$drawable')

        self.notification_manager = self.context.getSystemService(self.context.NOTIFICATION_SERVICE)
        self.media_session = None

        self._create_channel()
        self._init_media_session()

    def _create_channel(self):
        if self.BuildVersion.SDK_INT < self.VersionCodes.O:
            return

        channel = self.NotificationChannel(
            NOTIFICATION_CHANNEL_ID,
            "Mads Music",
            self.NotificationManager.IMPORTANCE_LOW
        )
        channel.setDescription("Muziekbediening voor Mads Music")
        try:
            channel.setLockscreenVisibility(self.Notification.VISIBILITY_PUBLIC)
        except Exception:
            pass
        self.notification_manager.createNotificationChannel(channel)

    def _init_media_session(self):
        try:
            self.media_session = self.MediaSession(self.context, "MadsMusicInAppSession")
            self.media_session.setActive(True)
        except Exception as exc:
            app_debug_log(f"MediaSession init failed: {exc}")
            self.media_session = None

    def _pending_flags(self):
        flags = self.PendingIntent.FLAG_UPDATE_CURRENT
        if self.BuildVersion.SDK_INT >= self.VersionCodes.M:
            flags |= self.PendingIntent.FLAG_IMMUTABLE
        return flags

    def _build_content_intent(self, action=None, request_code=100):
        launch_intent = self.context.getPackageManager().getLaunchIntentForPackage(
            self.context.getPackageName()
        )
        if not launch_intent:
            return None

        if action:
            launch_intent.setAction(action)
            launch_intent.putExtra(NOTIFICATION_ACTION_EXTRA, action)

        launch_intent.setFlags(
            self.Intent.FLAG_ACTIVITY_NEW_TASK
            | self.Intent.FLAG_ACTIVITY_SINGLE_TOP
            | self.Intent.FLAG_ACTIVITY_CLEAR_TOP
        )
        return self.PendingIntent.getActivity(
            self.context,
            request_code,
            launch_intent,
            self._pending_flags()
        )

    def _update_media_session(self, state):
        if not self.media_session:
            return

        actions = (
            self.PlaybackState.ACTION_PLAY
            | self.PlaybackState.ACTION_PAUSE
            | self.PlaybackState.ACTION_PLAY_PAUSE
            | self.PlaybackState.ACTION_SKIP_TO_PREVIOUS
            | self.PlaybackState.ACTION_SKIP_TO_NEXT
            | self.PlaybackState.ACTION_STOP
        )
        if state.get("enabled"):
            playback_state = self.PlaybackState.STATE_PLAYING if state.get("playing") else self.PlaybackState.STATE_PAUSED
        else:
            playback_state = self.PlaybackState.STATE_STOPPED
        speed = 1.0 if state.get("playing") else 0.0

        try:
            state_builder = self.PlaybackStateBuilder()
            state_builder.setActions(actions)
            state_builder.setState(playback_state, 0, speed)
            self.media_session.setPlaybackState(state_builder.build())

            metadata_builder = self.MediaMetadataBuilder()
            metadata_builder.putString(
                self.MediaMetadata.METADATA_KEY_TITLE,
                state.get("title", "Mads Music")
            )
            metadata_builder.putString(
                self.MediaMetadata.METADATA_KEY_ARTIST,
                state.get("subtitle", "Mads Music Player")
            )
            self.media_session.setMetadata(metadata_builder.build())
            self.media_session.setActive(bool(state.get("enabled")))
        except Exception as exc:
            app_debug_log(f"MediaSession update failed: {exc}")

    def _build_notification(self, state):
        if self.BuildVersion.SDK_INT >= self.VersionCodes.O:
            builder = self.NotificationBuilder(self.context, NOTIFICATION_CHANNEL_ID)
        else:
            builder = self.NotificationBuilder(self.context)

        content_intent = self._build_content_intent()
        if content_intent:
            builder.setContentIntent(content_intent)

        builder.setContentTitle(state.get("title", "Mads Music"))
        builder.setContentText(state.get("subtitle", "Mads Music Player"))
        mode_summary = state.get("mode_summary", "")
        if mode_summary:
            try:
                builder.setSubText(mode_summary)
            except Exception:
                pass
        builder.setSmallIcon(self.context.getApplicationInfo().icon)
        builder.setVisibility(self.Notification.VISIBILITY_PUBLIC)
        builder.setCategory(self.Notification.CATEGORY_TRANSPORT)
        builder.setOnlyAlertOnce(True)
        builder.setShowWhen(False)
        builder.setOngoing(bool(state.get("enabled")))
        try:
            builder.setPriority(self.Notification.PRIORITY_LOW)
        except Exception:
            pass

        builder.addAction(
            self.AndroidDrawables.ic_media_previous,
            "Vorige",
            self._build_content_intent(ACTION_PREV, 1)
        )
        builder.addAction(
            self.AndroidDrawables.ic_media_pause if state.get("playing") else self.AndroidDrawables.ic_media_play,
            "Pauze" if state.get("playing") else "Afspelen",
            self._build_content_intent(ACTION_PLAY_PAUSE, 2)
        )
        builder.addAction(
            self.AndroidDrawables.ic_media_next,
            "Volgende",
            self._build_content_intent(ACTION_NEXT, 3)
        )
        builder.addAction(
            self.AndroidDrawables.ic_menu_close_clear_cancel,
            "Stop",
            self._build_content_intent(ACTION_STOP, 4)
        )

        if self.media_session:
            try:
                style = self.NotificationMediaStyle()
                style.setMediaSession(self.media_session.getSessionToken())
                try:
                    style.setShowActionsInCompactView(0, 1, 2)
                except Exception:
                    pass
                builder.setStyle(style)
            except Exception as exc:
                app_debug_log(f"MediaStyle setup failed: {exc}")

        return builder.build()

    def show(self, state):
        try:
            self._update_media_session(state)
            self.notification_manager.notify(NOTIFICATION_ID, self._build_notification(state))
            self._active = True
        except Exception as exc:
            app_debug_log(f"Notification show failed: {exc}")

    def stop(self):
        try:
            self.notification_manager.cancel(NOTIFICATION_ID)
        except Exception:
            pass
        self._active = False

    def shutdown(self):
        try:
            if self.receiver:
                self.context.unregisterReceiver(self.receiver)
        except Exception:
            pass
        self.stop()
        try:
            if self.media_session:
                self.media_session.release()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────────────────────

class MadsMusicSpotify(App):

    def build(self):
        app_debug_log(f"App build start, base path: {WRITABLE_BASE_PATH}")
        self.all_songs_data = []
        self.current_index  = 0
        self.audio          = create_audio_engine(on_track_complete=self._handle_track_complete)
        self.current_volume = 0.7
        self.is_dragging    = False
        self.is_shuffle     = False
        self.is_repeat      = False
        self._service_enabled = False
        self._last_media_command_id = None
        self._player_lock = threading.RLock()
        self._stop_background_worker = threading.Event()
        self._pending_track_complete = threading.Event()
        self._banner_event = None
        self._delete_popup = None
        self._settings_popup = None
        self._track_info_popup = None
        self.show_favorites_only = False
        self.library_scope = "all"
        self.sort_mode = "title"
        self.favorites = set()
        self.recently_played = []
        self.language = DEFAULT_LANGUAGE
        self.theme_name = DEFAULT_THEME
        self.playback_speed = DEFAULT_PLAYBACK_SPEED
        self.seek_step = DEFAULT_SEEK_STEP
        self.playlist_density = DEFAULT_PLAYLIST_DENSITY
        self.confirm_delete_enabled = True
        self.notification_controller = None
        self._notification_fallback_enabled = False
        self._android_service_class = None
        self._android_service_running = False
        self._last_service_start_request = 0.0
        self._last_notification_settings_open = 0.0
        self.app_version = get_runtime_app_version()
        self._app_state = self._load_app_state()
        self._apply_saved_state()

        main = BoxLayout(
            orientation='vertical',
            padding=[dp(18), dp(18), dp(18), dp(16)],
            spacing=dp(10)
        )
        with main.canvas.before:
            self.bg_color = Color(*current_palette()["bg"])
            self.bg_rect = Rectangle(pos=main.pos, size=Window.size)
        main.bind(pos=self._update_bg, size=self._update_bg)

        # ── top bar ──
        top_bar = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        self.title_label = Label(
            text="MADS MUSIC", font_size=sp(24), bold=True,
            color=current_palette()["accent"], size_hint_x=0.66
        )
        top_bar.add_widget(self.title_label)
        self.btn_upload = ImageButton(UPLOAD_IMG, size_hint_x=0.17)
        self.btn_upload.bind(on_release=self.upload_track)
        top_bar.add_widget(self.btn_upload)
        self.btn_settings = ImageButton(SETTINGS_IMG, size_hint_x=0.17)
        self.btn_settings.bind(on_release=self.open_settings)
        top_bar.add_widget(self.btn_settings)
        main.add_widget(top_bar)

        # ── zoekbalk ──
        search_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        sc = BoxLayout(padding=[dp(2), dp(2), dp(2), dp(2)])
        with sc.canvas.before:
            self._search_color = Color(*current_palette()["panel_alt"])
            self._search_bg = RoundedRectangle(radius=[dp(12)])
        sc.bind(
            pos =lambda i, v: setattr(self._search_bg, 'pos',  v),
            size=lambda i, v: setattr(self._search_bg, 'size', v)
        )
        self.search_bar = TextInput(
            hint_text=self.tr('search_hint'), multiline=False,
            background_color=(0, 0, 0, 0), foreground_color=current_palette()["text"],
            padding=[dp(14), dp(10)], font_size=sp(15),
            cursor_color=current_palette()["accent"]
        )
        self.search_bar.bind(text=self.filter_playlist)
        sc.add_widget(self.search_bar)
        self.btn_clear_search = PillButton(self.tr("clear"), active=False, size_hint_x=None, width=dp(62))
        self.btn_clear_search.bind(on_release=self.clear_search)
        search_row.add_widget(sc)
        search_row.add_widget(self.btn_clear_search)
        main.add_widget(search_row)
        toolbar = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        self.btn_scope = PillButton(self._scope_button_text(), active=self.library_scope != "all")
        self.btn_scope.bind(on_release=self.cycle_library_scope)
        self.btn_sort = PillButton(self._sort_button_text(), active=False)
        self.btn_sort.bind(on_release=self.cycle_sort_mode)
        toolbar.add_widget(self.btn_scope)
        toolbar.add_widget(self.btn_sort)
        main.add_widget(toolbar)
        self.library_stats = Label(
            text="0 tracks in je library",
            size_hint_y=None,
            height=dp(18),
            font_size=sp(12),
            color=(0.65, 0.65, 0.65, 1),
            halign='left',
            valign='middle'
        )
        self.library_stats.bind(size=lambda inst, value: setattr(inst, 'text_size', value))
        main.add_widget(self.library_stats)

        # ── playlist ──
        scroll = ScrollView(size_hint_y=0.52, do_scroll_x=False)
        self.playlist_layout = GridLayout(cols=1, spacing=dp(10), size_hint_y=None)
        self.playlist_layout.bind(minimum_height=self.playlist_layout.setter('height'))
        scroll.add_widget(self.playlist_layout)
        main.add_widget(scroll)

        # ── song info ──
        info_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(74), spacing=dp(2))
        self.song_label   = Label(text=self.tr("choose_track"), font_size=sp(20), bold=True, color=current_palette()["text"])
        self.artist_label = Label(text=self.tr("tagline"), font_size=sp(14),
                                  color=current_palette()["muted"])
        self.up_next_label = Label(
            text=self.tr("up_next_empty"),
            font_size=sp(11),
            color=current_palette()["muted"]
        )
        info_box.add_widget(self.song_label)
        info_box.add_widget(self.artist_label)
        info_box.add_widget(self.up_next_label)
        main.add_widget(info_box)

        utility_row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
        self.btn_seek_back = PillButton(f"-{self.seek_step}s", active=False, size_hint_x=None, width=dp(72))
        self.btn_track_info = PillButton(self.tr("track_info_button"), active=False, size_hint_x=None, width=dp(102))
        self.btn_seek_forward = PillButton(f"+{self.seek_step}s", active=False, size_hint_x=None, width=dp(72))
        self.btn_seek_back.bind(on_release=lambda inst: self.seek_relative(-self.seek_step))
        self.btn_track_info.bind(on_release=self.open_track_info)
        self.btn_seek_forward.bind(on_release=lambda inst: self.seek_relative(self.seek_step))
        utility_row.add_widget(self.btn_seek_back)
        utility_row.add_widget(Label())
        utility_row.add_widget(self.btn_track_info)
        utility_row.add_widget(Label())
        utility_row.add_widget(self.btn_seek_forward)
        main.add_widget(utility_row)

        # ── progress slider ──
        prog_box = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(10))
        self.time_current = Label(text="0:00", font_size=sp(11), size_hint_x=0.15)
        self.slider = SpotifySlider(min=0, max=100, value=0)
        self.slider.cb_drag_start = self._on_drag_start
        self.slider.cb_drag_move  = self._on_drag_move
        self.slider.cb_drag_end   = self._on_drag_end
        self.time_total = Label(text="0:00", font_size=sp(11), size_hint_x=0.15)
        prog_box.add_widget(self.time_current)
        prog_box.add_widget(self.slider)
        prog_box.add_widget(self.time_total)
        main.add_widget(prog_box)

        # ── controls ──
        controls = BoxLayout(size_hint_y=None, height=dp(96), spacing=dp(8))
        self.btn_shuffle = ImageButton(
            os.path.join(ICON_PATH, "shufflebuttonwhite.png"),
            os.path.join(ICON_PATH, "shufflebuttongreen.png"),
            size_hint_x=0.16,
            icon_size=44)
        btn_prev         = ImageButton(os.path.join(ICON_PATH, "lastsong.png"), size_hint_x=0.18, icon_size=54)
        self.btn_play    = ImageButton(os.path.join(ICON_PATH, "playbutton.png"), size_hint_x=0.32, icon_size=92)
        btn_next         = ImageButton(os.path.join(ICON_PATH, "nextsong.png"), size_hint_x=0.18, icon_size=54)
        self.btn_repeat  = ImageButton(
            os.path.join(ICON_PATH, "repeatbuttonoff.png"),
            os.path.join(ICON_PATH, "repeatbuttonon.png"),
            size_hint_x=0.16,
            icon_size=44)

        self.btn_shuffle.bind(on_release=self.toggle_shuffle)
        btn_prev.bind(on_release=self.prev_song)
        self.btn_play.bind(on_release=self.toggle_music)
        btn_next.bind(on_release=self.next_song)
        self.btn_repeat.bind(on_release=self.toggle_repeat)
        self.btn_shuffle.set_active(self.is_shuffle)
        self.btn_repeat.set_active(self.is_repeat)

        for c in [self.btn_shuffle, btn_prev, self.btn_play, btn_next, self.btn_repeat]:
            controls.add_widget(c)
        main.add_widget(controls)

        # ── volume ──
        vol_box = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(10))
        self.volume_label = Label(text="VOL", font_size=sp(11), size_hint_x=0.14,
                                  color=current_palette()["accent"])
        self.volume_slider = SpotifySlider(min=0, max=1, value=self.current_volume)
        self.volume_slider.cb_drag_end = lambda v: self.set_volume(None, v)
        self.volume_slider.bind(value=self.set_volume)
        self.btn_speed = PillButton(self._speed_button_text(), active=self.playback_speed != DEFAULT_PLAYBACK_SPEED, size_hint_x=None, width=dp(84))
        self.btn_speed.bind(on_release=self.cycle_playback_speed)
        vol_box.add_widget(self.volume_label)
        vol_box.add_widget(self.volume_slider)
        vol_box.add_widget(self.btn_speed)
        main.add_widget(vol_box)
        self.banner_box = BoxLayout(
            size_hint_y=None,
            height=dp(44),
            padding=[dp(16), dp(10)],
            opacity=0
        )
        with self.banner_box.canvas.before:
            self.banner_color = Color(*current_palette()["panel_alt"])
            self.banner_bg = RoundedRectangle(radius=[dp(18)])
        self.banner_box.bind(pos=self._update_banner_bg, size=self._update_banner_bg)
        self.banner = Label(
            text="",
            font_size=sp(12),
            bold=True,
            color=current_palette()["text"],
            halign='center',
            valign='middle'
        )
        self.banner.bind(size=lambda inst, value: setattr(inst, 'text_size', value))
        self.banner_box.add_widget(self.banner)
        main.add_widget(self.banner_box)

        self.load_songs()
        self.audio.set_speed(self.playback_speed)
        self._apply_theme()
        Clock.schedule_interval(self.update_progress, 0.25)
        self._start_background_worker()
        return main

    def _bind_android_activity_callbacks(self):
        if platform != 'android':
            return
        try:
            from android import activity
            activity.bind(on_new_intent=self._on_new_intent)
            app_debug_log("Bound Android on_new_intent callback")
            try:
                self._process_android_intent(
                    autoclass('org.kivy.android.PythonActivity').mActivity.getIntent()
                )
            except Exception as exc:
                app_debug_log(f"Initial intent processing skipped: {exc}")
        except Exception as exc:
            app_debug_log(f"Activity callback bind failed: {exc}")

    def _on_new_intent(self, *args):
        intent = args[-1] if args else None
        self._process_android_intent(intent)

    def _process_android_intent(self, intent):
        if platform != 'android' or not intent:
            return False

        try:
            action_value = str(intent.getStringExtra(NOTIFICATION_ACTION_EXTRA) or "")
        except Exception:
            action_value = ""

        if not action_value:
            try:
                action_value = str(intent.getAction() or "")
            except Exception:
                action_value = ""

        action_map = {
            ACTION_PREV: "prev",
            ACTION_PLAY_PAUSE: "play_pause",
            ACTION_NEXT: "next",
            ACTION_STOP: "stop",
        }
        mapped_action = action_map.get(action_value)
        if not mapped_action:
            return False

        app_debug_log(f"Intent notification action received: {action_value}")
        Clock.schedule_once(lambda dt: self._handle_notification_action(mapped_action), 0)
        return True

    def _ensure_notification_fallback(self):
        if platform != 'android':
            return
        if self.notification_controller:
            return
        try:
            self.notification_controller = AndroidNotificationController(self._handle_notification_action)
            app_debug_log("Notification fallback controller initialised")
        except Exception as exc:
            app_debug_log(f"Notification fallback init failed: {exc}")

    def _ensure_android_service_channel(self):
        if platform != 'android':
            return
        try:
            BuildVersion = autoclass('android.os.Build$VERSION')
            VersionCodes = autoclass('android.os.Build$VERSION_CODES')
            if BuildVersion.SDK_INT < VersionCodes.O:
                return

            Notification = autoclass('android.app.Notification')
            NotificationChannel = autoclass('android.app.NotificationChannel')
            NotificationManager = autoclass('android.app.NotificationManager')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            context = activity.getApplicationContext()
            manager = context.getSystemService(context.NOTIFICATION_SERVICE)
            channel = NotificationChannel(
                SERVICE_NOTIFICATION_CHANNEL_ID,
                "Mads Music",
                NotificationManager.IMPORTANCE_DEFAULT
            )
            channel.setDescription("Muziekbediening voor Mads Music")
            try:
                channel.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC)
                channel.enableVibration(False)
                channel.setShowBadge(False)
            except Exception:
                pass
            manager.createNotificationChannel(channel)
            app_debug_log("Service notification channel ensured")
        except Exception as exc:
            app_debug_log(f"Service notification channel setup failed: {exc}")

    def _android_notifications_enabled(self, channel_id=SERVICE_NOTIFICATION_CHANNEL_ID):
        if platform != 'android':
            return True
        try:
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            context = activity.getApplicationContext()
            NotificationManagerCompat = autoclass('androidx.core.app.NotificationManagerCompat')
            manager_compat = getattr(NotificationManagerCompat, 'from')(context)
            app_enabled = bool(manager_compat.areNotificationsEnabled())
            channel_enabled = True

            BuildVersion = autoclass('android.os.Build$VERSION')
            VersionCodes = autoclass('android.os.Build$VERSION_CODES')
            if channel_id and BuildVersion.SDK_INT >= VersionCodes.O:
                NotificationManager = autoclass('android.app.NotificationManager')
                manager = context.getSystemService(context.NOTIFICATION_SERVICE)
                channel = manager.getNotificationChannel(channel_id)
                if channel is not None:
                    channel_enabled = channel.getImportance() != NotificationManager.IMPORTANCE_NONE

            enabled = bool(app_enabled and channel_enabled)
            app_debug_log(
                f"Notification status checked: app_enabled={app_enabled} "
                f"channel_enabled={channel_enabled} channel_id={channel_id}"
            )
            return enabled
        except Exception as exc:
            app_debug_log(f"Notification status check failed: {exc}")
            return True

    def _open_android_notification_settings(self, channel_id=SERVICE_NOTIFICATION_CHANNEL_ID):
        if platform != 'android':
            return
        if time.time() - self._last_notification_settings_open < 20.0:
            return
        self._last_notification_settings_open = time.time()
        try:
            from android.runnable import run_on_ui_thread
            Intent = autoclass('android.content.Intent')
            Settings = autoclass('android.provider.Settings')
            BuildVersion = autoclass('android.os.Build$VERSION')
            VersionCodes = autoclass('android.os.Build$VERSION_CODES')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            package_name = activity.getApplicationContext().getPackageName()

            @run_on_ui_thread
            def _open_settings():
                if BuildVersion.SDK_INT >= VersionCodes.O and channel_id:
                    intent = Intent(Settings.ACTION_CHANNEL_NOTIFICATION_SETTINGS)
                    intent.putExtra(Settings.EXTRA_APP_PACKAGE, package_name)
                    intent.putExtra(Settings.EXTRA_CHANNEL_ID, channel_id)
                else:
                    intent = Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                    intent.putExtra("app_package", package_name)
                    intent.putExtra("app_uid", activity.getApplicationInfo().uid)
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                activity.startActivity(intent)

            _open_settings()
            app_debug_log(f"Opened Android notification settings for channel: {channel_id}")
        except Exception as exc:
            app_debug_log(f"Open notification settings failed: {exc}")

    def _ensure_android_notifications_ready(self, interactive=False):
        if platform != 'android':
            return True
        notifications_enabled = self._android_notifications_enabled()
        if notifications_enabled:
            return True
        app_debug_log(f"Notifications disabled, interactive={interactive}")
        if interactive:
            self._request_android_runtime_permissions(force=True)
            Clock.schedule_once(lambda dt: self._open_android_notification_settings(), 0.8)
        return False

    def _resolve_android_service_class(self):
        if platform != 'android':
            return None
        if self._android_service_class is not None:
            return self._android_service_class

        activity = autoclass('org.kivy.android.PythonActivity').mActivity
        package_name = activity.getApplicationContext().getPackageName()
        class_name = f"{package_name}.ServiceMadsmusic"
        self._android_service_class = autoclass(class_name)
        app_debug_log(f"Resolved Android service class: {class_name}")
        return self._android_service_class

    def _start_android_service(self):
        if platform != 'android':
            return False
        try:
            service_class = self._resolve_android_service_class()
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            self._last_service_start_request = time.time()
            service_class.start(activity, "")
            self._android_service_running = True
            app_debug_log("Android service start requested")
            return True
        except Exception as exc:
            self._android_service_running = False
            app_debug_log(f"Android service start failed: {exc}")
            return False

    def _stop_android_service(self):
        if platform != 'android':
            return
        try:
            service_class = self._resolve_android_service_class()
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            service_class.stop(activity)
            app_debug_log("Android service stop requested")
        except Exception as exc:
            app_debug_log(f"Android service stop failed: {exc}")
        self._android_service_running = False

    def _load_app_state(self):
        try:
            with open(APP_STATE_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}

    def _apply_saved_state(self):
        state = self._app_state or {}
        self.language = state.get("language", DEFAULT_LANGUAGE)
        if self.language not in TRANSLATIONS:
            self.language = DEFAULT_LANGUAGE
        self.theme_name = state.get("theme", DEFAULT_THEME)
        if self.theme_name not in THEMES:
            self.theme_name = DEFAULT_THEME
        self.playback_speed = max(MIN_PLAYBACK_SPEED, min(MAX_PLAYBACK_SPEED, float(state.get("playback_speed", DEFAULT_PLAYBACK_SPEED))))
        self.current_volume = max(0.0, min(1.0, float(state.get("volume", self.current_volume))))
        self.is_shuffle = bool(state.get("shuffle", False))
        self.is_repeat = bool(state.get("repeat", False))
        if self.is_shuffle and self.is_repeat:
            self.is_repeat = False
        saved_scope = state.get("library_scope")
        if saved_scope not in {"all", "favorites", "recent"}:
            saved_scope = "favorites" if state.get("favorites_only", False) else "all"
        self.library_scope = saved_scope
        self.show_favorites_only = self.library_scope == "favorites"
        self.sort_mode = state.get("sort_mode", "title")
        if self.sort_mode not in {"title", "recent", "reverse"}:
            self.sort_mode = "title"
        self.seek_step = int(state.get("seek_step", DEFAULT_SEEK_STEP))
        if self.seek_step not in SEEK_STEP_OPTIONS:
            self.seek_step = DEFAULT_SEEK_STEP
        self.playlist_density = state.get("playlist_density", DEFAULT_PLAYLIST_DENSITY)
        if self.playlist_density not in PLAYLIST_DENSITY_OPTIONS:
            self.playlist_density = DEFAULT_PLAYLIST_DENSITY
        self.confirm_delete_enabled = bool(state.get("confirm_delete", True))
        self.current_index = max(0, int(state.get("last_index", 0)))
        self.favorites = set(state.get("favorites", []))
        self.recently_played = list(state.get("recently_played", []))

    def _save_app_state(self):
        payload = {
            "language": self.language,
            "theme": self.theme_name,
            "playback_speed": self.playback_speed,
            "seek_step": self.seek_step,
            "playlist_density": self.playlist_density,
            "confirm_delete": self.confirm_delete_enabled,
            "volume": self.current_volume,
            "shuffle": self.is_shuffle,
            "repeat": self.is_repeat,
            "favorites_only": self.library_scope == "favorites",
            "library_scope": self.library_scope,
            "sort_mode": self.sort_mode,
            "last_index": self.current_index,
            "favorites": sorted(self.favorites),
            "recently_played": self.recently_played[:20],
            "updated_at": time.time(),
        }
        try:
            with open(APP_STATE_PATH, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
        except Exception:
            pass

    def _read_service_heartbeat(self):
        return read_shared_json(SERVICE_HEARTBEAT_PATH, {})

    def _service_recently_alive(self, max_age=4.0):
        heartbeat = self._read_service_heartbeat()
        ts = heartbeat.get("ts", 0)
        alive = bool(heartbeat.get("alive"))
        return alive and (time.time() - float(ts)) <= max_age

    def _ensure_background_service(self, dt):
        return

    def _sort_button_text(self):
        mapping = {
            "title": self.tr("sort_title"),
            "recent": self.tr("sort_recent"),
            "reverse": self.tr("sort_reverse"),
        }
        return mapping.get(self.sort_mode, self.tr("sort_title"))

    def tr(self, key, **kwargs):
        language_map = TRANSLATIONS.get(self.language, TRANSLATIONS[DEFAULT_LANGUAGE])
        text = language_map.get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

    def _scope_button_text(self):
        mapping = {
            "all": self.tr("scope_all"),
            "favorites": self.tr("scope_favorites"),
            "recent": self.tr("scope_recent"),
        }
        return mapping.get(self.library_scope, self.tr("scope_all"))

    def _theme_display_name(self, theme_name):
        return self.tr(f"theme_{theme_name}")

    def _speed_button_text(self):
        return format_speed_value(self.playback_speed)

    def _seek_button_text(self, direction):
        prefix = "+" if direction > 0 else "-"
        return f"{prefix}{int(self.seek_step)}s"

    def _density_button_text(self, density):
        return self.tr(f"density_{density}")

    def _playlist_row_height(self):
        mapping = {
            "compact": dp(40),
            "balanced": dp(46),
            "comfortable": dp(54),
        }
        return mapping.get(self.playlist_density, dp(46))

    def _update_player_action_buttons(self):
        loaded = bool(self.audio.loaded and self.all_songs_data)
        if hasattr(self, 'btn_speed'):
            self.btn_speed.text = self._speed_button_text()
            self.btn_speed.set_active(abs(self.playback_speed - DEFAULT_PLAYBACK_SPEED) > 0.01)
        if hasattr(self, 'btn_seek_back'):
            self.btn_seek_back.text = self._seek_button_text(-self.seek_step)
            self.btn_seek_back.disabled = not loaded
            self.btn_seek_back.opacity = 1 if loaded else 0.68
            self.btn_seek_back.set_active(loaded)
        if hasattr(self, 'btn_seek_forward'):
            self.btn_seek_forward.text = self._seek_button_text(self.seek_step)
            self.btn_seek_forward.disabled = not loaded
            self.btn_seek_forward.opacity = 1 if loaded else 0.68
            self.btn_seek_forward.set_active(loaded)
        if hasattr(self, 'btn_track_info'):
            self.btn_track_info.text = self.tr("track_info_button")
            self.btn_track_info.disabled = not loaded
            self.btn_track_info.opacity = 1 if loaded else 0.68
            self.btn_track_info.set_active(loaded)

    def _refresh_static_texts(self):
        if hasattr(self, 'search_bar'):
            self.search_bar.hint_text = self.tr("search_hint")
        if hasattr(self, 'btn_clear_search'):
            self.btn_clear_search.text = self.tr("clear")
        self._update_player_action_buttons()
        if not self.audio.loaded:
            self._reset_player_ui()
        else:
            self._update_now_playing_meta()
        self._refresh_playlist_view()

    def _apply_theme(self):
        palette = current_palette()
        if hasattr(self, 'bg_color'):
            self.bg_color.rgba = palette["bg"]
        if hasattr(self, '_search_color'):
            self._search_color.rgba = palette["panel_alt"]
        if hasattr(self, 'banner_color'):
            self.banner_color.rgba = palette["panel_alt"]
        if hasattr(self, 'title_label'):
            self.title_label.color = palette["accent"]
        if hasattr(self, 'song_label'):
            self.song_label.color = palette["text"]
        if hasattr(self, 'artist_label'):
            self.artist_label.color = palette["muted"]
        if hasattr(self, 'up_next_label'):
            self.up_next_label.color = palette["muted"]
        if hasattr(self, 'library_stats'):
            self.library_stats.color = palette["muted"]
        if hasattr(self, 'volume_label'):
            self.volume_label.color = palette["accent"]
        if hasattr(self, 'banner'):
            self.banner.color = palette["text"]
        if hasattr(self, 'time_current'):
            self.time_current.color = palette["muted"]
        if hasattr(self, 'time_total'):
            self.time_total.color = palette["muted"]
        if hasattr(self, 'search_bar'):
            self.search_bar.foreground_color = palette["text"]
            self.search_bar.cursor_color = palette["accent"]
            self.search_bar.hint_text_color = palette["muted"]
        for name in ["btn_clear_search", "btn_scope", "btn_sort", "btn_speed", "btn_seek_back", "btn_seek_forward", "btn_track_info"]:
            widget = getattr(self, name, None)
            if widget:
                widget.set_active(widget.active)
        if hasattr(self, 'btn_shuffle'):
            self.btn_shuffle.set_active(self.is_shuffle)
        if hasattr(self, 'btn_repeat'):
            self.btn_repeat.set_active(self.is_repeat)
        if hasattr(self, 'slider'):
            self.slider.value_track_color = palette["accent"]
        if hasattr(self, 'volume_slider'):
            self.volume_slider.value_track_color = palette["accent"]
        self._refresh_static_texts()

    def _mode_summary(self):
        labels = []
        if self.is_shuffle:
            labels.append(self.tr("mode_shuffle"))
        if self.is_repeat:
            labels.append(self.tr("mode_repeat"))
        if self.library_scope == "favorites":
            labels.append(self.tr("scope_favorites"))
        elif self.library_scope == "recent":
            labels.append(self.tr("scope_recent"))
        return " | ".join(labels) if labels else self.tr("mode_standard")

    def _update_banner_bg(self, instance, value):
        self.banner_bg.pos = instance.pos
        self.banner_bg.size = instance.size

    def show_banner_message(self, message, duration=2.4):
        Clock.schedule_once(lambda dt: self._show_banner_ui(message, duration), 0)
        self._show_android_toast(message)

    def _show_banner_ui(self, message, duration):
        if not hasattr(self, 'banner'):
            return
        self.banner.text = message
        self.banner_box.opacity = 1
        if self._banner_event is not None:
            self._banner_event.cancel()
        self._banner_event = Clock.schedule_once(self._hide_banner, duration)

    def _show_android_toast(self, message):
        if platform != 'android':
            return
        try:
            from android.runnable import run_on_ui_thread
            Toast = autoclass('android.widget.Toast')
            String = autoclass('java.lang.String')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity

            @run_on_ui_thread
            def _toast():
                Toast.makeText(
                    activity.getApplicationContext(),
                    String(message),
                    Toast.LENGTH_SHORT
                ).show()

            _toast()
        except Exception:
            pass

    def _hide_banner(self, dt):
        if hasattr(self, 'banner_box'):
            self.banner_box.opacity = 0
        self._banner_event = None

    def _remember_recent_song(self, song_path):
        if not song_path:
            return
        self.recently_played = [path for path in self.recently_played if path != song_path]
        self.recently_played.insert(0, song_path)
        self.recently_played = self.recently_played[:20]

    def _up_next_text(self):
        if not self.all_songs_data:
            return self.tr("up_next_empty")
        if len(self.all_songs_data) == 1:
            return self.tr("up_next_single")
        if self.is_shuffle:
            return self.tr("up_next_shuffle")

        titles = []
        for offset in range(1, min(3, len(self.all_songs_data))):
            next_song = self.all_songs_data[(self.current_index + offset) % len(self.all_songs_data)]
            titles.append(next_song['title'])
        return self.tr("up_next_prefix", tracks=" | ".join(titles))

    def _update_now_playing_meta(self):
        if not self.audio.loaded or not self.all_songs_data:
            self._reset_player_ui()
            return

        song = self.all_songs_data[self.current_index]
        self.song_label.text = song['title']
        self.artist_label.text = self.tr("track_counter", index=self.current_index + 1, total=len(self.all_songs_data))
        self.up_next_label.text = self._up_next_text()
        self._update_player_action_buttons()

    def _unique_music_destination(self, filename):
        safe_name = os.path.basename(filename or "Mads_Track.mp3")
        stem, ext = os.path.splitext(safe_name)
        if not stem:
            stem = "Mads_Track"
        if not ext:
            ext = ".mp3"

        candidate = os.path.join(MUSIC_PATH, f"{stem}{ext}")
        counter = 2
        while os.path.exists(candidate):
            candidate = os.path.join(MUSIC_PATH, f"{stem} ({counter}){ext}")
            counter += 1
        return candidate

    def _reset_player_ui(self):
        self.song_label.text = self.tr("choose_track")
        self.artist_label.text = self.tr("tagline")
        self.up_next_label.text = self.tr("up_next_empty")
        self.slider.max = 100
        self.slider.value = 0
        self.time_current.text = "0:00"
        self.time_total.text = "0:00"
        self.btn_play.display_img.source = os.path.join(ICON_PATH, "playbutton.png")
        self._update_player_action_buttons()

    def _get_visible_songs(self):
        query_text = self.search_bar.text.lower().strip() if hasattr(self, 'search_bar') else ""
        songs = list(self.all_songs_data)
        if self.library_scope == "favorites":
            songs = [song for song in songs if song['path'] in self.favorites]
        elif self.library_scope == "recent":
            recent_index = {path: idx for idx, path in enumerate(self.recently_played)}
            songs = [song for song in songs if song['path'] in recent_index]
            songs.sort(key=lambda song: recent_index[song['path']])
        if query_text:
            songs = [song for song in songs if query_text in song['title'].lower()]

        if self.library_scope == "recent":
            return songs
        if self.sort_mode == "reverse":
            songs.sort(key=lambda song: song['title'].lower(), reverse=True)
        elif self.sort_mode == "recent":
            songs.sort(
                key=lambda song: os.path.getmtime(song['path']) if os.path.exists(song['path']) else 0,
                reverse=True
            )
        else:
            songs.sort(key=lambda song: song['title'].lower())
        return songs

    def _refresh_playlist_view(self):
        visible_songs = self._get_visible_songs()
        self.build_playlist(visible_songs)
        total = len(self.all_songs_data)
        favorites = len([song for song in self.all_songs_data if song['path'] in self.favorites])
        self.library_stats.text = self.tr(
            "library_stats",
            visible=len(visible_songs),
            total=total,
            favorites=favorites,
            recent=len(self.recently_played),
        )
        if hasattr(self, 'btn_scope'):
            self.btn_scope.text = self._scope_button_text()
            self.btn_scope.set_active(self.library_scope != "all")
        if hasattr(self, 'btn_sort'):
            self.btn_sort.text = self._sort_button_text()
        if hasattr(self, 'btn_clear_search'):
            has_query = bool(self.search_bar.text.strip())
            self.btn_clear_search.set_active(has_query)
            self.btn_clear_search.opacity = 1 if has_query else 0.72

    def _request_android_runtime_permissions(self, force=False):
        return

    def _update_bg(self, instance, value):
        self.bg_rect.pos  = instance.pos
        self.bg_rect.size = instance.size

    def _build_media_state_payload(self, force_enabled=None):
        enabled = bool(force_enabled) if force_enabled is not None else bool(
            self._service_enabled and self.audio.loaded and self.all_songs_data
        )

        if not enabled:
            return {
                "enabled": False,
                "playing": False,
                "title": "Mads Music",
                "subtitle": self.tr("tagline"),
                "mode_summary": self._mode_summary(),
                "updated_at": time.time(),
            }

        song = self.all_songs_data[self.current_index]
        return {
            "enabled": True,
            "playing": bool(self.audio.playing),
            "title": song['title'],
            "subtitle": self.tr("track_counter", index=self.current_index + 1, total=len(self.all_songs_data)),
            "mode_summary": self._mode_summary(),
            "updated_at": time.time(),
        }

    def _write_service_state(self, enabled):
        return

    def _write_media_state(self):
        return self._build_media_state_payload()

    def _update_android_notification(self, payload=None):
        return

    def _clear_media_command(self):
        try:
            if os.path.exists(MEDIA_COMMAND_PATH):
                os.remove(MEDIA_COMMAND_PATH)
        except Exception:
            pass

    def _read_media_command(self):
        try:
            with open(MEDIA_COMMAND_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return None

    def _consume_external_command(self):
        command = self._read_media_command()
        if not command:
            return None

        command_id = command.get("id")
        if not command_id or command_id == self._last_media_command_id:
            return None

        self._last_media_command_id = command_id
        self._clear_media_command()

        action = command.get("command")
        if action not in {"play_pause", "next", "prev", "stop"}:
            return None
        return action

    def _execute_background_action(self, action):
        app_debug_log(f"Background action requested: {action}")

        def _run_action():
            with self._player_lock:
                if action == "track_complete":
                    self._handle_track_complete_internal()
                elif action == "play_pause":
                    self._toggle_music_internal(update_ui=False)
                elif action == "next":
                    self._next_song_internal(update_ui=False)
                elif action == "prev":
                    self._prev_song_internal(update_ui=False)
                elif action == "stop":
                    self._stop_music_internal(update_ui=False)
                else:
                    return False
            return True

        if platform == 'android':
            try:
                from android.runnable import run_on_ui_thread
                result = {"handled": False}
                done = threading.Event()

                @run_on_ui_thread
                def _run_on_android_ui():
                    try:
                        result["handled"] = _run_action()
                    except Exception as exc:
                        app_debug_log(f"Background action failed on UI thread: {action} :: {exc}")
                    finally:
                        done.set()

                _run_on_android_ui()
                done.wait(1.5)
                return bool(result["handled"])
            except Exception as exc:
                app_debug_log(f"UI thread dispatch failed, fallback direct: {action} :: {exc}")

        try:
            return bool(_run_action())
        except Exception as exc:
            app_debug_log(f"Background action failed: {action} :: {exc}")
            return False

    def _handle_notification_action(self, action):
        app_debug_log(f"Direct notification action: {action}")
        with self._player_lock:
            if action == "play_pause":
                self._toggle_music_internal(update_ui=False)
            elif action == "next":
                self._next_song_internal(update_ui=False)
            elif action == "prev":
                self._prev_song_internal(update_ui=False)
            elif action == "stop":
                self._stop_music_internal(update_ui=False)
        self._schedule_ui_refresh()

    def _start_background_worker(self):
        if platform != 'android':
            return

        worker = threading.Thread(target=self._background_worker_loop, daemon=True)
        worker.start()
        self._background_worker = worker

    def _background_worker_loop(self):
        while not self._stop_background_worker.is_set():
            handled = False

            if self._pending_track_complete.is_set():
                self._pending_track_complete.clear()
                handled = self._execute_background_action("track_complete") or handled

            action = self._consume_external_command()
            if action:
                handled = self._execute_background_action(action) or handled

            if handled:
                self._schedule_ui_refresh()

            time.sleep(0.2)

    def _schedule_ui_refresh(self):
        try:
            Clock.schedule_once(lambda dt: self._refresh_ui_from_state(), 0)
        except Exception:
            pass

    def _refresh_ui_from_state(self):
        if not hasattr(self, 'btn_play'):
            return

        if not self.audio.loaded or not self.all_songs_data:
            self._reset_player_ui()
            self._refresh_playlist_view()
            return

        self._update_now_playing_meta()
        self.btn_play.display_img.source = os.path.join(
            ICON_PATH,
            "pausebutton.png" if self.audio.playing else "playbutton.png"
        )

        if self.audio.length > 0:
            self.slider.max = self.audio.length
            self.time_total.text = format_time(self.audio.length)
        else:
            self.slider.max = 100
            self.time_total.text = "..."

        if not self.is_dragging:
            pos = self.audio.get_pos()
            self.slider.value = min(pos, self.slider.max)
            self.time_current.text = format_time(pos)

        self._refresh_playlist_view()

    def _set_background_service(self, enabled):
        self._service_enabled = False
        return

    def _handle_track_complete(self, *args):
        self._pending_track_complete.set()

    def _handle_track_complete_internal(self):
        if self.is_repeat:
            self._play_current_song(update_ui=False)
        else:
            self._next_song_internal(update_ui=False)

    def _old_on_pause(self):
        # True = app blijft leven als scherm uitgaat
        # pygame audio (SDL2 thread) speelt gewoon door
        return True

    def _old_on_resume(self):
        # Niets te doen — audio speelt al door
        pass

    # ── slider callbacks ───────────────────────────────────────────────────────

    def _legacy_on_pause(self):
        self._write_service_state(self.audio.playing)
        return True

    def _legacy_on_resume(self):
        self._write_service_state(self.audio.playing)

    def on_stop(self):
        app_debug_log(f"on_stop called: loaded={self.audio.loaded} playing={self.audio.playing}")
        if not self.audio.loaded:
            self._stop_background_worker.set()
            self._set_background_service(False)
        else:
            self._set_background_service(True)
        self._save_app_state()
        self._write_media_state()

    def on_pause(self):
        app_debug_log(f"on_pause called: loaded={self.audio.loaded} playing={self.audio.playing}")
        self._set_background_service(self.audio.loaded)
        self._save_app_state()
        self._write_media_state()
        return True

    def on_resume(self):
        app_debug_log(f"on_resume called: loaded={self.audio.loaded} playing={self.audio.playing}")
        self._set_background_service(self.audio.loaded)
        self._write_media_state()
        if platform == 'android':
            try:
                self._process_android_intent(
                    autoclass('org.kivy.android.PythonActivity').mActivity.getIntent()
                )
            except Exception as exc:
                app_debug_log(f"Resume intent processing failed: {exc}")
        self._refresh_ui_from_state()

    def _on_drag_start(self):
        self.is_dragging = True

    def _on_drag_move(self, value):
        self.time_current.text = format_time(value)

    def _on_drag_end(self, value):
        self.is_dragging = False
        self.audio.seek(value)

    # ── playback ───────────────────────────────────────────────────────────────

    def play_music(self):
        with self._player_lock:
            self._play_current_song(update_ui=True)

    def toggle_music(self, instance=None):
        with self._player_lock:
            self._toggle_music_internal(update_ui=True)

    def stop_music(self, instance=None):
        with self._player_lock:
            self._stop_music_internal(update_ui=True)

    def _play_current_song(self, update_ui=True):
        if not self.all_songs_data:
            return False

        song = self.all_songs_data[self.current_index]
        self._save_app_state()

        if update_ui:
            self.slider.value = 0
            self.time_current.text = "0:00"
            self.time_total.text = "..."
            self._update_now_playing_meta()

        self.audio.set_volume(self.current_volume)

        def on_length(l):
            if self.audio.loaded_path == song['path']:
                self.audio._length = l
                if update_ui:
                    self.slider.max = l if l > 0 else 100
                    self.time_total.text = format_time(l) if l > 0 else "..."

        ok = self.audio.load_and_play(song['path'], on_length=on_length)

        if ok:
            self._remember_recent_song(song['path'])
            self._save_app_state()
            self._write_media_state()
            self._set_background_service(True)
            if update_ui:
                self.slider.max = 100
                self.btn_play.display_img.source = os.path.join(ICON_PATH, "pausebutton.png")
                self._update_now_playing_meta()
            Clock.schedule_once(lambda dt: self._preload_next(), 1.0)
        else:
            self._set_background_service(False)
            self._write_media_state()
            if update_ui:
                self.song_label.text = self.tr("load_failed")
                self.btn_play.display_img.source = os.path.join(ICON_PATH, "playbutton.png")

        if update_ui:
            self._refresh_playlist_view()

        return ok

    def _toggle_music_internal(self, update_ui=True):
        if not self.audio.loaded:
            if self.all_songs_data:
                return self._play_current_song(update_ui=update_ui)
            return False

        if self.audio.playing:
            self.audio.pause()
        else:
            self.audio.resume()

        self._write_media_state()
        self._set_background_service(self.audio.loaded)
        self._save_app_state()

        if update_ui:
            self.btn_play.display_img.source = os.path.join(
                ICON_PATH,
                "pausebutton.png" if self.audio.playing else "playbutton.png"
            )
            self._refresh_playlist_view()

        return True

    def _stop_music_internal(self, update_ui=True):
        self.audio.stop()
        self._set_background_service(False)
        self._write_media_state()
        self._save_app_state()

        if update_ui:
            self._reset_player_ui()
            self._refresh_playlist_view()

        return True

    # ── progress update ────────────────────────────────────────────────────────

    def update_progress(self, dt):
        if self.is_dragging or not self.audio.loaded:
            return

        if self.audio.is_finished():
            if self.is_repeat:
                self.play_music()
            else:
                self.next_song()
            return

        if not self.audio.playing:
            return

        pos = self.audio.get_pos()
        if self.slider.max > 0:
            self.slider.value = min(pos, self.slider.max)
        self.time_current.text = format_time(pos)

        if self.audio.length > 0 and self.slider.max != self.audio.length:
            self.slider.max      = self.audio.length
            self.time_total.text = format_time(self.audio.length)

    # ── song management ────────────────────────────────────────────────────────

    def _preload_next(self):
        """Haal de lengte van het volgende nummer alvast op in de achtergrond."""
        if not self.all_songs_data or self.is_shuffle:
            return
        next_idx  = (self.current_index + 1) % len(self.all_songs_data)
        next_path = self.all_songs_data[next_idx]['path']
        self.audio.preload(next_path)

    def load_songs(self):
        if not os.path.exists(MUSIC_PATH):
            return
        files = [f for f in sorted(os.listdir(MUSIC_PATH))
                 if f.lower().endswith((".mp3", ".wav", ".ogg", ".m4a"))]
        self.all_songs_data = [
            {'index': i, 'path': os.path.join(MUSIC_PATH, f),
             'title': f.rsplit('.', 1)[0]}
            for i, f in enumerate(files)
        ]
        self.favorites = {path for path in self.favorites if os.path.exists(path)}
        self.recently_played = [path for path in self.recently_played if os.path.exists(path)]
        if self.all_songs_data:
            self.current_index = min(self.current_index, len(self.all_songs_data) - 1)
        else:
            self.current_index = 0
            self._set_background_service(False)
            self._write_media_state()
        self._refresh_playlist_view()
        self._save_app_state()
        self._write_media_state()

    def build_playlist(self, song_list):
        self.playlist_layout.clear_widgets()
        row_height = self._playlist_row_height()
        for song in song_list:
            is_current = (song['index'] == self.current_index and self.audio.loaded)
            is_favorite = song['path'] in self.favorites
            row    = BoxLayout(size_hint_y=None, height=row_height, spacing=dp(8))
            fav_btn = ImageButton(LIKE_OFF_IMG, LIKE_ON_IMG, size_hint_x=0.11)
            fav_btn.set_active(is_favorite)
            fav_btn.bind(on_release=lambda x, p=song['path']: self.toggle_favorite(p))
            btn    = RoundedSongButton(title=song['title'], is_active=is_current,
                                       size_hint_x=0.76)
            btn.bind(on_release=lambda x, i=song['index']: self.play_specific(i))
            del_btn = ImageButton(DELETE_IMG, size_hint_x=0.13)
            del_btn.bind(on_release=lambda x, p=song['path']: self.request_delete_song(p))
            row.add_widget(fav_btn)
            row.add_widget(btn)
            row.add_widget(del_btn)
            self.playlist_layout.add_widget(row)

    def toggle_favorite(self, song_path):
        if song_path in self.favorites:
            self.favorites.remove(song_path)
        else:
            self.favorites.add(song_path)
        self._save_app_state()
        self._refresh_playlist_view()
        self._write_media_state()

    def toggle_favorites_filter(self, instance=None):
        target_scope = "all" if self.library_scope == "favorites" else "favorites"
        self.set_library_scope(target_scope)

    def clear_search(self, instance=None):
        if hasattr(self, 'search_bar'):
            self.search_bar.text = ""
        self._refresh_playlist_view()

    def seek_relative(self, delta_seconds):
        if not self.audio.loaded:
            return
        with self._player_lock:
            target = self.audio.get_pos() + float(delta_seconds)
            if self.audio.length > 0:
                target = min(self.audio.length, target)
            target = max(0.0, target)
            self.audio.seek(target)
        if not self.is_dragging:
            self.slider.value = min(target, self.slider.max)
            self.time_current.text = format_time(target)

    def _build_info_row(self, title, value):
        palette = current_palette()
        row = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(54), spacing=dp(2))
        label = Label(
            text=title,
            size_hint_y=None,
            height=dp(16),
            font_size=sp(11),
            color=palette["muted"],
            halign='left',
            valign='middle'
        )
        label.bind(size=lambda inst, size: setattr(inst, 'text_size', size))
        value_label = Label(
            text=value,
            size_hint_y=None,
            height=dp(32),
            font_size=sp(15),
            color=palette["text"],
            halign='left',
            valign='middle'
        )
        value_label.bind(size=lambda inst, size: setattr(inst, 'text_size', size))
        row.add_widget(label)
        row.add_widget(value_label)
        return row

    def open_track_info(self, instance=None):
        if not self.audio.loaded or not self.all_songs_data:
            return
        if self._track_info_popup:
            try:
                self._track_info_popup.dismiss()
            except Exception:
                pass

        song = self.all_songs_data[self.current_index]
        duration = self.audio.length if self.audio.loaded_path == song['path'] and self.audio.length > 0 else get_length(song['path'])
        palette = current_palette()

        card = BoxLayout(orientation='vertical', spacing=dp(14), padding=[dp(22), dp(22), dp(22), dp(18)])
        with card.canvas.before:
            Color(*palette["panel"])
            card_bg = RoundedRectangle(radius=[dp(26)])
        card.bind(
            pos=lambda inst, value: setattr(card_bg, 'pos', value),
            size=lambda inst, value: setattr(card_bg, 'size', value)
        )

        header = Label(
            text=song['title'],
            size_hint_y=None,
            height=dp(34),
            font_size=sp(22),
            bold=True,
            color=palette["text"]
        )
        subtitle = Label(
            text=self.tr("track_counter", index=self.current_index + 1, total=len(self.all_songs_data)),
            size_hint_y=None,
            height=dp(18),
            font_size=sp(11),
            color=palette["muted"]
        )

        details = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None)
        details.bind(minimum_height=details.setter('height'))
        details.add_widget(self._build_info_row(self.tr("track_info_duration"), format_time(duration)))
        details.add_widget(self._build_info_row(self.tr("track_info_file"), os.path.basename(song['path'])))
        details.add_widget(self._build_info_row(
            self.tr("track_info_favorite"),
            self.tr("track_info_yes") if song['path'] in self.favorites else self.tr("track_info_no")
        ))
        details.add_widget(self._build_info_row(self.tr("track_info_modes"), self._mode_summary()))
        details.add_widget(self._build_info_row(self.tr("track_info_speed"), format_speed_value(self.playback_speed)))

        scroll = ScrollView(do_scroll_x=False, size_hint=(1, 1))
        scroll.add_widget(details)

        footer = BoxLayout(size_hint_y=None, height=dp(46))
        close_btn = PillButton(self.tr("track_info_close"), active=True)
        close_btn.bind(on_release=lambda inst: self._track_info_popup.dismiss())
        footer.add_widget(close_btn)

        card.add_widget(header)
        card.add_widget(subtitle)
        card.add_widget(scroll)
        card.add_widget(footer)

        content = AnchorLayout(anchor_x='center', anchor_y='center', padding=[dp(18), dp(18), dp(18), dp(18)])
        card.size_hint = (1, None)
        card.height = min(Window.height - dp(36), dp(470))
        content.add_widget(card)

        popup = Popup(
            title="",
            content=content,
            size_hint=(1, 1),
            auto_dismiss=True,
            separator_height=0,
            background='',
            background_color=(0, 0, 0, 0)
        )
        if hasattr(popup, 'overlay_color'):
            popup.overlay_color = palette["popup_overlay"]
        self._track_info_popup = popup
        popup.bind(on_dismiss=lambda *_: setattr(self, '_track_info_popup', None))
        popup.open()

    def _refresh_settings_popup(self, popup):
        if popup:
            popup.dismiss()
        Clock.schedule_once(lambda dt: self.open_settings(), 0.05)

    def set_language(self, language_code, popup=None):
        if language_code not in TRANSLATIONS:
            return
        self.language = language_code
        self._save_app_state()
        self._apply_theme()
        if popup:
            self._refresh_settings_popup(popup)

    def set_theme(self, theme_name, popup=None):
        if theme_name not in THEMES:
            return
        self.theme_name = theme_name
        self._save_app_state()
        self._apply_theme()
        if popup:
            self._refresh_settings_popup(popup)

    def set_library_scope(self, scope, popup=None):
        if scope not in {"all", "favorites", "recent"}:
            return
        self.library_scope = scope
        self.show_favorites_only = self.library_scope == "favorites"
        self._save_app_state()
        self._refresh_playlist_view()
        self._write_media_state()
        if popup:
            self._refresh_settings_popup(popup)

    def set_sort_mode(self, sort_mode, popup=None):
        if sort_mode not in {"title", "recent", "reverse"}:
            return
        self.sort_mode = sort_mode
        self._save_app_state()
        self._refresh_playlist_view()
        self._write_media_state()
        if popup:
            self._refresh_settings_popup(popup)

    def set_playlist_density(self, density, popup=None):
        if density not in PLAYLIST_DENSITY_OPTIONS:
            return
        self.playlist_density = density
        self._save_app_state()
        self._refresh_playlist_view()
        if popup:
            self._refresh_settings_popup(popup)

    def set_playback_speed(self, speed, popup=None):
        self.playback_speed = max(MIN_PLAYBACK_SPEED, min(MAX_PLAYBACK_SPEED, float(speed)))
        self.audio.set_speed(self.playback_speed)
        self._update_player_action_buttons()
        self._save_app_state()
        if popup:
            self._refresh_settings_popup(popup)

    def set_seek_step(self, step, popup=None):
        if int(step) not in SEEK_STEP_OPTIONS:
            return
        self.seek_step = int(step)
        self._update_player_action_buttons()
        self._save_app_state()
        if popup:
            self._refresh_settings_popup(popup)

    def set_delete_confirmation(self, enabled, popup=None):
        self.confirm_delete_enabled = bool(enabled)
        self._save_app_state()
        if popup:
            self._refresh_settings_popup(popup)

    def clear_recently_played(self, popup=None):
        self.recently_played = []
        self._save_app_state()
        self._refresh_playlist_view()
        self._write_media_state()
        if popup:
            self._refresh_settings_popup(popup)

    def cycle_playback_speed(self, instance=None):
        current = round(float(self.playback_speed), 2)
        options = [round(value, 2) for value in PLAYBACK_SPEED_OPTIONS]
        try:
            index = options.index(current)
        except ValueError:
            index = options.index(round(DEFAULT_PLAYBACK_SPEED, 2))
        next_speed = PLAYBACK_SPEED_OPTIONS[(index + 1) % len(PLAYBACK_SPEED_OPTIONS)]
        self.set_playback_speed(next_speed)

    def reset_preferences(self, popup=None):
        self.language = DEFAULT_LANGUAGE
        self.theme_name = DEFAULT_THEME
        self.playback_speed = DEFAULT_PLAYBACK_SPEED
        self.seek_step = DEFAULT_SEEK_STEP
        self.playlist_density = DEFAULT_PLAYLIST_DENSITY
        self.confirm_delete_enabled = True
        self.library_scope = "all"
        self.sort_mode = "title"
        self.is_shuffle = False
        self.is_repeat = False
        self.show_favorites_only = False
        self.audio.set_speed(self.playback_speed)
        if hasattr(self, 'btn_shuffle'):
            self.btn_shuffle.set_active(False)
        if hasattr(self, 'btn_repeat'):
            self.btn_repeat.set_active(False)
        self._update_player_action_buttons()
        self._save_app_state()
        self._refresh_playlist_view()
        self._write_media_state()
        self._apply_theme()
        if popup:
            self._refresh_settings_popup(popup)

    def _build_settings_section(self, title, buttons):
        palette = current_palette()
        button_height = dp(46)
        grid_height = (button_height * len(buttons)) + (dp(8) * max(0, len(buttons) - 1))
        section = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(28) + grid_height + dp(22),
            spacing=dp(10),
            padding=[dp(14), dp(14), dp(14), dp(14)]
        )
        with section.canvas.before:
            Color(*palette["panel_alt"])
            section_bg = RoundedRectangle(radius=[dp(20)])
        section.bind(
            pos=lambda inst, value: setattr(section_bg, 'pos', value),
            size=lambda inst, value: setattr(section_bg, 'size', value)
        )
        section_label = Label(
            text=title,
            size_hint_y=None,
            height=dp(18),
            font_size=sp(12),
            bold=True,
            color=current_palette()["muted"],
            halign='left',
            valign='middle'
        )
        section_label.bind(size=lambda inst, value: setattr(inst, 'text_size', value))
        row = BoxLayout(orientation='vertical', size_hint_y=None, height=grid_height, spacing=dp(8))
        for button in buttons:
            button.size_hint_y = None
            button.height = button_height
            row.add_widget(button)
        section.add_widget(section_label)
        section.add_widget(row)
        return section

    def _build_settings_info_section(self, title, items):
        palette = current_palette()
        section = BoxLayout(
            orientation='vertical',
            spacing=dp(10),
            padding=[dp(14), dp(14), dp(14), dp(14)],
            size_hint_y=None
        )
        with section.canvas.before:
            Color(*palette["panel_alt"])
            section_bg = RoundedRectangle(radius=[dp(20)])
        section.bind(
            pos=lambda inst, value: setattr(section_bg, 'pos', value),
            size=lambda inst, value: setattr(section_bg, 'size', value)
        )

        header = Label(
            text=title,
            size_hint_y=None,
            height=dp(18),
            font_size=sp(12),
            bold=True,
            color=palette["muted"],
            halign='left',
            valign='middle'
        )
        header.bind(size=lambda inst, value: setattr(inst, 'text_size', value))
        section.add_widget(header)

        for label_text, value_text in items:
            row = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(52), spacing=dp(2))
            key_label = Label(
                text=label_text,
                size_hint_y=None,
                height=dp(16),
                font_size=sp(11),
                color=palette["muted"],
                halign='left',
                valign='middle'
            )
            key_label.bind(size=lambda inst, value: setattr(inst, 'text_size', value))
            value_label = Label(
                text=value_text,
                size_hint_y=None,
                height=dp(32),
                font_size=sp(14),
                color=palette["text"],
                halign='left',
                valign='middle',
                shorten=True,
                shorten_from='right'
            )
            value_label.bind(size=lambda inst, value: setattr(inst, 'text_size', value))
            row.add_widget(key_label)
            row.add_widget(value_label)
            section.add_widget(row)

        section.height = dp(28) + (len(items) * dp(52)) + (max(0, len(items) - 1) * dp(10)) + dp(28)
        return section

    def open_settings(self, instance=None):
        if self._settings_popup:
            try:
                self._settings_popup.dismiss()
            except Exception:
                pass

        palette = current_palette()
        card = BoxLayout(orientation='vertical', spacing=dp(14), padding=[dp(22), dp(22), dp(22), dp(18)])
        with card.canvas.before:
            Color(*palette["panel"])
            card_bg = RoundedRectangle(radius=[dp(26)])
        card.bind(
            pos=lambda inst, value: setattr(card_bg, 'pos', value),
            size=lambda inst, value: setattr(card_bg, 'size', value)
        )

        header = Label(
            text=self.tr("settings_title"),
            size_hint_y=None,
            height=dp(34),
            font_size=sp(24),
            bold=True,
            color=palette["text"]
        )
        subtitle = Label(
            text=self.tr("settings_subtitle"),
            size_hint_y=None,
            height=dp(18),
            font_size=sp(11),
            color=palette["muted"]
        )
        version_chip = PillButton(self.tr("version_label", version=self.app_version), active=True, size_hint_y=None, height=dp(38))
        version_chip.opacity = 1
        version_chip.color = palette["accent"]

        lang_buttons = []
        for code in ["nl", "en"]:
            button = PillButton(self.tr(f"lang_{code}"), active=self.language == code)
            button.bind(on_release=lambda inst, value=code: self.set_language(value, self._settings_popup))
            lang_buttons.append(button)

        theme_buttons = []
        for theme_name in ["graphite", "midnight", "sunset", "forest"]:
            button = PillButton(self._theme_display_name(theme_name), active=self.theme_name == theme_name)
            button.bind(on_release=lambda inst, value=theme_name: self.set_theme(value, self._settings_popup))
            theme_buttons.append(button)

        library_buttons = []
        for scope in ["all", "favorites", "recent"]:
            button = PillButton(self.tr(f"scope_{scope}"), active=self.library_scope == scope)
            button.bind(on_release=lambda inst, value=scope: self.set_library_scope(value, self._settings_popup))
            library_buttons.append(button)

        density_buttons = []
        for density in PLAYLIST_DENSITY_OPTIONS:
            button = PillButton(self._density_button_text(density), active=self.playlist_density == density)
            button.bind(on_release=lambda inst, value=density: self.set_playlist_density(value, self._settings_popup))
            density_buttons.append(button)

        sort_buttons = []
        for mode in ["title", "recent", "reverse"]:
            button = PillButton(self._sort_button_text() if self.sort_mode == mode else {
                "title": self.tr("sort_title"),
                "recent": self.tr("sort_recent"),
                "reverse": self.tr("sort_reverse"),
            }[mode], active=self.sort_mode == mode)
            button.bind(on_release=lambda inst, value=mode: self.set_sort_mode(value, self._settings_popup))
            sort_buttons.append(button)

        speed_buttons = []
        for speed in PLAYBACK_SPEED_OPTIONS:
            button = PillButton(format_speed_value(speed), active=abs(self.playback_speed - speed) < 0.01)
            button.bind(on_release=lambda inst, value=speed: self.set_playback_speed(value, self._settings_popup))
            speed_buttons.append(button)

        seek_buttons = []
        for step in SEEK_STEP_OPTIONS:
            button = PillButton(f"{step}s", active=self.seek_step == step)
            button.bind(on_release=lambda inst, value=step: self.set_seek_step(value, self._settings_popup))
            seek_buttons.append(button)

        delete_buttons = []
        for enabled, label in [(True, self.tr("settings_delete_confirm_on")), (False, self.tr("settings_delete_confirm_off"))]:
            button = PillButton(label, active=self.confirm_delete_enabled == enabled)
            button.bind(on_release=lambda inst, value=enabled: self.set_delete_confirmation(value, self._settings_popup))
            delete_buttons.append(button)

        action_buttons = []
        clear_recent_btn = PillButton(self.tr("settings_clear_recent"), active=False)
        clear_recent_btn.bind(on_release=lambda inst: self.clear_recently_played(self._settings_popup))
        action_buttons.append(clear_recent_btn)

        footer = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        reset_btn = PillButton(self.tr("settings_reset"), active=False)
        reset_btn.bind(on_release=lambda inst: self.reset_preferences(self._settings_popup))
        close_btn = PillButton(self.tr("settings_close"), active=True)
        close_btn.bind(on_release=lambda inst: self._settings_popup.dismiss())
        footer.add_widget(reset_btn)
        footer.add_widget(close_btn)

        about_items = [
            (self.tr("about_tracks"), str(len(self.all_songs_data))),
            (self.tr("about_library"), MUSIC_PATH),
            (self.tr("about_mode"), self._mode_summary()),
        ]

        sections = BoxLayout(orientation='vertical', spacing=dp(14), size_hint_y=None)
        sections.bind(minimum_height=sections.setter('height'))
        sections.add_widget(version_chip)
        sections.add_widget(self._build_settings_section(self.tr("settings_language"), lang_buttons))
        sections.add_widget(self._build_settings_section(self.tr("settings_theme"), theme_buttons))
        sections.add_widget(self._build_settings_section(self.tr("settings_library"), library_buttons))
        sections.add_widget(self._build_settings_section(self.tr("settings_density"), density_buttons))
        sections.add_widget(self._build_settings_section(self.tr("settings_sorting"), sort_buttons))
        sections.add_widget(self._build_settings_section(self.tr("settings_speed"), speed_buttons))
        sections.add_widget(self._build_settings_section(self.tr("settings_seek_step"), seek_buttons))
        sections.add_widget(self._build_settings_section(self.tr("settings_delete_behavior"), delete_buttons))
        sections.add_widget(self._build_settings_section(self.tr("settings_actions"), action_buttons))
        sections.add_widget(self._build_settings_info_section(self.tr("settings_about"), about_items))

        scroll = ScrollView(do_scroll_x=False, size_hint=(1, 1))
        scroll.add_widget(sections)

        card.add_widget(header)
        card.add_widget(subtitle)
        card.add_widget(scroll)
        card.add_widget(footer)

        content = AnchorLayout(
            anchor_x='center',
            anchor_y='center',
            padding=[dp(18), dp(18), dp(18), dp(18)]
        )
        card.size_hint = (1, None)
        card.height = min(Window.height - dp(36), dp(620))
        content.add_widget(card)

        popup = Popup(
            title="",
            content=content,
            size_hint=(1, 1),
            auto_dismiss=True,
            separator_height=0,
            background='',
            background_color=(0, 0, 0, 0)
        )
        if hasattr(popup, 'overlay_color'):
            popup.overlay_color = palette["popup_overlay"]
        self._settings_popup = popup
        popup.bind(on_dismiss=lambda *_: setattr(self, '_settings_popup', None))
        popup.open()

    def cycle_library_scope(self, instance=None):
        order = ["all", "favorites", "recent"]
        current_position = order.index(self.library_scope) if self.library_scope in order else 0
        self.set_library_scope(order[(current_position + 1) % len(order)])

    def cycle_sort_mode(self, instance=None):
        order = ["title", "recent", "reverse"]
        current_position = order.index(self.sort_mode) if self.sort_mode in order else 0
        self.set_sort_mode(order[(current_position + 1) % len(order)])

    def request_delete_song(self, song_path):
        if not self.confirm_delete_enabled:
            self.delete_song(song_path)
            return
        song_name = os.path.basename(song_path).rsplit('.', 1)[0]
        palette = current_palette()
        card = BoxLayout(orientation='vertical', spacing=dp(16), padding=[dp(22), dp(22), dp(22), dp(18)])
        with card.canvas.before:
            Color(*palette["panel"])
            card_bg = RoundedRectangle(radius=[dp(26)])
        card.bind(
            pos=lambda inst, value: setattr(card_bg, 'pos', value),
            size=lambda inst, value: setattr(card_bg, 'size', value)
        )

        badge = Label(
            text=self.tr("delete_badge"),
            size_hint_y=None,
            height=dp(22),
            font_size=sp(11),
            bold=True,
            color=palette["accent"]
        )
        title = Label(
            text=song_name,
            size_hint_y=None,
            height=dp(42),
            font_size=sp(22),
            bold=True,
            color=palette["text"]
        )
        subtitle = Label(
            text=self.tr("delete_subtitle"),
            font_size=sp(13),
            color=palette["muted"]
        )
        subtitle.bind(size=lambda inst, value: setattr(inst, 'text_size', (value[0], None)))

        actions = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(12))
        cancel_btn = PillButton(self.tr("delete_keep"), active=False)
        delete_btn = PillButton(self.tr("delete_confirm"), active=True)
        cancel_btn._bg_color.rgba = palette["panel_alt"]
        cancel_btn.color = palette["text"]
        delete_btn._bg_color.rgba = (0.78, 0.2, 0.28, 1)
        delete_btn.color = (1, 1, 1, 1)

        actions.add_widget(cancel_btn)
        actions.add_widget(delete_btn)
        card.add_widget(badge)
        card.add_widget(title)
        card.add_widget(subtitle)
        card.add_widget(actions)

        content = AnchorLayout(
            anchor_x='center',
            anchor_y='center',
            padding=[dp(18), dp(18), dp(18), dp(18)]
        )
        card.size_hint = (1, None)
        card.height = dp(280)
        content.add_widget(card)

        popup = Popup(
            title="",
            content=content,
            size_hint=(1, 1),
            auto_dismiss=True,
            separator_height=0,
            background='',
            background_color=(0, 0, 0, 0)
        )
        if hasattr(popup, 'overlay_color'):
            popup.overlay_color = palette["popup_overlay"]
        cancel_btn.bind(on_release=popup.dismiss)
        delete_btn.bind(on_release=lambda *_: self._confirm_delete_song(popup, song_path))
        self._delete_popup = popup
        popup.open()

    def _confirm_delete_song(self, popup, song_path):
        popup.dismiss()
        self.delete_song(song_path)

    def play_specific(self, index):
        with self._player_lock:
            self.current_index = index
            self._play_current_song(update_ui=True)

    def next_song(self, *args):
        with self._player_lock:
            self._next_song_internal(update_ui=True)

    def prev_song(self, *args):
        with self._player_lock:
            self._prev_song_internal(update_ui=True)

    def _next_song_internal(self, update_ui=True):
        if not self.all_songs_data:
            return False
        if self.is_shuffle:
            self.current_index = random.randint(0, len(self.all_songs_data) - 1)
        else:
            self.current_index = (self.current_index + 1) % len(self.all_songs_data)
        return self._play_current_song(update_ui=update_ui)

    def _prev_song_internal(self, update_ui=True):
        if not self.all_songs_data:
            return False
        if self.audio.get_pos() > 3.0:
            return self._play_current_song(update_ui=update_ui)
        self.current_index = (self.current_index - 1) % len(self.all_songs_data)
        return self._play_current_song(update_ui=update_ui)

    def delete_song(self, song_path):
        deleted_index = next((song['index'] for song in self.all_songs_data if song['path'] == song_path), None)
        was_current = self.audio.loaded_path == song_path
        was_playing = bool(self.audio.playing)

        if self._track_info_popup and was_current:
            try:
                self._track_info_popup.dismiss()
            except Exception:
                pass

        if was_current:
            self.audio.stop()
            self._set_background_service(False)
            self._reset_player_ui()
        try:
            os.remove(song_path)
            self.favorites.discard(song_path)
            self.recently_played = [path for path in self.recently_played if path != song_path]
            if deleted_index is not None:
                if deleted_index >= len(self.all_songs_data) - 1:
                    self.current_index = max(0, deleted_index - 1)
                else:
                    self.current_index = deleted_index
            self.load_songs()
            if was_current and self.all_songs_data and was_playing:
                self.current_index = min(self.current_index, len(self.all_songs_data) - 1)
                self._play_current_song(update_ui=True)
            self._write_media_state()
            self._save_app_state()
        except Exception:
            pass

    def filter_playlist(self, instance, text):
        self._refresh_playlist_view()

    # ── controls ───────────────────────────────────────────────────────────────

    def set_volume(self, instance, value):
        self.current_volume = value
        self.audio.set_volume(value)
        self._save_app_state()

    def toggle_shuffle(self, instance):
        self.is_shuffle = not self.is_shuffle
        if self.is_shuffle and self.is_repeat:
            self.is_repeat = False
            self.btn_repeat.set_active(False)
        self.btn_shuffle.set_active(self.is_shuffle)
        self._update_now_playing_meta()
        self._save_app_state()
        self._write_media_state()

    def toggle_repeat(self, instance):
        self.is_repeat = not self.is_repeat
        if self.is_repeat and self.is_shuffle:
            self.is_shuffle = False
            self.btn_shuffle.set_active(False)
        self.btn_repeat.set_active(self.is_repeat)
        self._update_now_playing_meta()
        self._save_app_state()
        self._write_media_state()

    # ── Android upload ─────────────────────────────────────────────────────────

    def upload_track(self, instance):
        if platform == 'android':
            try:
                from jnius import autoclass
                from android import activity, mActivity
                Intent = autoclass('android.content.Intent')
                intent = Intent(Intent.ACTION_GET_CONTENT)
                intent.setType("audio/*")
                activity.bind(on_activity_result=self.on_activity_result)
                mActivity.startActivityForResult(intent, 999)
            except Exception:
                pass
        else:
            if filechooser:
                filechooser.open_file(on_selection=self._on_file_selection)

    def on_activity_result(self, request_code, result_code, intent):
        if platform == 'android':
            from android import activity
            activity.unbind(on_activity_result=self.on_activity_result)
            if request_code == 999:
                from jnius import autoclass
                Activity = autoclass('android.app.Activity')
                if result_code == Activity.RESULT_OK and intent:
                    uri = intent.getData()
                    if uri:
                        self.process_android_uri(uri)

    def process_android_uri(self, uri):
        try:
            from jnius import autoclass
            from android import mActivity
            resolver = mActivity.getApplicationContext().getContentResolver()
            filename = "Mads_Track.mp3"
            cursor   = resolver.query(uri, None, None, None, None)
            if cursor and cursor.moveToFirst():
                OpenableColumns = autoclass('android.provider.OpenableColumns')
                idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if idx != -1:
                    filename = cursor.getString(idx)
                cursor.close()
            dest_path = self._unique_music_destination(filename)
            pfd = resolver.openFileDescriptor(uri, "r")
            with os.fdopen(os.dup(pfd.getFd()), 'rb') as f_in:
                with open(dest_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            pfd.close()
            Clock.schedule_once(lambda dt: self.load_songs(), 0.5)
            self.show_banner_message(self.tr("imported", filename=os.path.basename(dest_path)))
        except Exception:
            pass

    def _on_file_selection(self, selection):
        if selection:
            dest = self._unique_music_destination(os.path.basename(selection[0]))
            shutil.copy(selection[0], dest)
            Clock.schedule_once(lambda dt: self.load_songs(), 0.5)
            self.show_banner_message(self.tr("imported", filename=os.path.basename(dest)))
    
    def start_background_music(self):
        if platform == 'android':
            self._set_background_service(True)
            
if __name__ == "__main__":
    MadsMusicSpotify().run()
