import os
import jnius
import shutil
import random
import time
import threading
import json

import pygame
from jnius import autoclass, PythonJavaClass, java_method
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
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


def get_safe_paths():
    music = os.path.join(WRITABLE_BASE_PATH, "music")
    os.makedirs(music, exist_ok=True)
    return music, os.path.join(APP_BASE_PATH, "Buttons")

MUSIC_PATH, ICON_PATH = get_safe_paths()
CIRCLE_IMG = os.path.join(ICON_PATH, "circle.png")
UPLOAD_IMG = os.path.join(ICON_PATH, "uploadmusic.png")
DELETE_IMG = os.path.join(ICON_PATH, "delete.png")


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
        self.font_size        = sp(16)
        self.background_color = (0, 0, 0, 0)
        with self.canvas.before:
            Color(*(0.12, 0.8, 0.45, 0.3) if is_active else (0.12, 0.12, 0.12, 1))
            self.rect = RoundedRectangle(radius=[dp(10)])
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *a):
        self.rect.pos  = self.pos
        self.rect.size = self.size


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
        if "upload" in src:                      self.display_img.size = (dp(45), dp(45))
        elif "play" in src or "pause" in src:    self.display_img.size = (dp(75), dp(75))
        elif "delete" in src:                    self.display_img.size = (dp(28), dp(28))
        else:                                    self.display_img.size = (dp(42), dp(42))

    def set_active(self, state):
        self.display_img.source = self.img_active_path if state else self.img_normal_path


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────────────────────

class MadsMusicSpotify(App):

    def build(self):
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
        self._write_service_state(False)
        self._clear_media_command()
        self._write_media_state()
        self._request_android_runtime_permissions()

        main = BoxLayout(
            orientation='vertical',
            padding=[dp(20), dp(25), dp(20), dp(25)],
            spacing=dp(15)
        )
        with main.canvas.before:
            Color(0.05, 0.05, 0.05, 1)
            self.bg_rect = Rectangle(pos=main.pos, size=Window.size)
        main.bind(pos=self._update_bg, size=self._update_bg)

        # ── top bar ──
        top_bar = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10))
        top_bar.add_widget(Label(
            text="MADS MUSIC", font_size=sp(24), bold=True,
            color=(0.12, 0.8, 0.45, 1), size_hint_x=0.7
        ))
        self.btn_upload = ImageButton(UPLOAD_IMG, size_hint_x=0.3)
        self.btn_upload.bind(on_release=self.upload_track)
        top_bar.add_widget(self.btn_upload)
        main.add_widget(top_bar)

        # ── zoekbalk ──
        sc = BoxLayout(size_hint_y=None, height=dp(45),
                       padding=[dp(2), dp(2), dp(2), dp(2)])
        with sc.canvas.before:
            Color(0.15, 0.15, 0.15, 1)
            self._search_bg = RoundedRectangle(radius=[dp(12)])
        sc.bind(
            pos =lambda i, v: setattr(self._search_bg, 'pos',  v),
            size=lambda i, v: setattr(self._search_bg, 'size', v)
        )
        self.search_bar = TextInput(
            hint_text='Zoek nummer...', multiline=False,
            background_color=(0, 0, 0, 0), foreground_color=(1, 1, 1, 1),
            padding=[dp(14), dp(10)], font_size=sp(15),
            cursor_color=(0.12, 0.8, 0.45, 1)
        )
        self.search_bar.bind(text=self.filter_playlist)
        sc.add_widget(self.search_bar)
        main.add_widget(sc)

        # ── playlist ──
        scroll = ScrollView(size_hint_y=0.4, do_scroll_x=False)
        self.playlist_layout = GridLayout(cols=1, spacing=dp(10), size_hint_y=None)
        self.playlist_layout.bind(minimum_height=self.playlist_layout.setter('height'))
        scroll.add_widget(self.playlist_layout)
        main.add_widget(scroll)

        # ── song info ──
        info_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(80))
        self.song_label   = Label(text="Kies een track", font_size=sp(20), bold=True)
        self.artist_label = Label(text="Mads Music Player", font_size=sp(14),
                                  color=(0.5, 0.5, 0.5, 1))
        info_box.add_widget(self.song_label)
        info_box.add_widget(self.artist_label)
        main.add_widget(info_box)

        # ── progress slider ──
        prog_box = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(10))
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
        controls = BoxLayout(size_hint_y=None, height=dp(100), spacing=dp(5))
        self.btn_shuffle = ImageButton(
            os.path.join(ICON_PATH, "shufflebuttonwhite.png"),
            os.path.join(ICON_PATH, "shufflebuttongreen.png"))
        btn_prev         = ImageButton(os.path.join(ICON_PATH, "lastsong.png"))
        self.btn_play    = ImageButton(os.path.join(ICON_PATH, "playbutton.png"))
        btn_next         = ImageButton(os.path.join(ICON_PATH, "nextsong.png"))
        self.btn_repeat  = ImageButton(
            os.path.join(ICON_PATH, "repeatbuttonoff.png"),
            os.path.join(ICON_PATH, "repeatbuttonon.png"))

        self.btn_shuffle.bind(on_release=self.toggle_shuffle)
        btn_prev.bind(on_release=self.prev_song)
        self.btn_play.bind(on_release=self.toggle_music)
        btn_next.bind(on_release=self.next_song)
        self.btn_repeat.bind(on_release=self.toggle_repeat)

        for c in [self.btn_shuffle, btn_prev, self.btn_play, btn_next, self.btn_repeat]:
            controls.add_widget(c)
        main.add_widget(controls)

        # ── volume ──
        vol_box = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        vol_box.add_widget(Label(text="VOL", font_size=sp(11), size_hint_x=0.15,
                                 color=(0.12, 0.8, 0.45, 1)))
        self.volume_slider = SpotifySlider(min=0, max=1, value=self.current_volume)
        self.volume_slider.cb_drag_end = lambda v: self.set_volume(None, v)
        self.volume_slider.bind(value=self.set_volume)
        vol_box.add_widget(self.volume_slider)
        main.add_widget(vol_box)

        self.load_songs()
        Clock.schedule_interval(self.update_progress, 0.25)
        self._start_background_worker()
        return main

    def _request_android_runtime_permissions(self):
        if platform != 'android':
            return

        try:
            from android.permissions import request_permissions, Permission

            permissions = []
            post_notifications = getattr(Permission, 'POST_NOTIFICATIONS', None)
            if post_notifications:
                permissions.append(post_notifications)

            if permissions:
                request_permissions(permissions)
        except Exception:
            pass

    def _update_bg(self, instance, value):
        self.bg_rect.pos  = instance.pos
        self.bg_rect.size = instance.size

    def _write_service_state(self, enabled):
        try:
            with open(BACKGROUND_SERVICE_STATE, "w", encoding="utf-8") as fh:
                json.dump({"enabled": bool(enabled), "ts": time.time()}, fh)
        except Exception:
            pass

    def _write_media_state(self):
        if not self.audio.loaded or not self.all_songs_data:
            payload = {
                "enabled": False,
                "playing": False,
                "title": "Mads Music",
                "subtitle": "Mads Music Player",
                "updated_at": time.time(),
            }
        else:
            song = self.all_songs_data[self.current_index]
            payload = {
                "enabled": True,
                "playing": bool(self.audio.playing),
                "title": song['title'],
                "subtitle": f"Track {self.current_index + 1} van {len(self.all_songs_data)}",
                "updated_at": time.time(),
            }

        try:
            with open(MEDIA_STATE_PATH, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
        except Exception:
            pass

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
            return False

        command_id = command.get("id")
        if not command_id or command_id == self._last_media_command_id:
            return False

        self._last_media_command_id = command_id
        self._clear_media_command()

        action = command.get("command")
        if action == "play_pause":
            self._toggle_music_internal(update_ui=False)
        elif action == "next":
            self._next_song_internal(update_ui=False)
        elif action == "prev":
            self._prev_song_internal(update_ui=False)
        else:
            return False

        self._schedule_ui_refresh()
        return True

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
                with self._player_lock:
                    self._handle_track_complete_internal()
                handled = True

            with self._player_lock:
                if self._consume_external_command():
                    handled = True

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
            self.song_label.text = "Kies een track"
            self.artist_label.text = "Mads Music Player"
            self.time_current.text = "0:00"
            self.time_total.text = "0:00"
            self.slider.max = 100
            self.slider.value = 0
            self.btn_play.display_img.source = os.path.join(ICON_PATH, "playbutton.png")
            self.build_playlist(self.all_songs_data)
            return

        song = self.all_songs_data[self.current_index]
        self.song_label.text = song['title']
        self.artist_label.text = f"Track {self.current_index + 1} van {len(self.all_songs_data)}"
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

        self.build_playlist(self.all_songs_data)

    def _set_background_service(self, enabled):
        if platform != 'android':
            return

        enabled = bool(enabled)
        self._write_service_state(enabled)

        if not enabled:
            self._service_enabled = False
            return

        if self._service_enabled:
            return

        try:
            ServiceClass = autoclass('org.madsmusic.madsmusic.ServiceMadsmusic')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            ServiceClass.start(activity, '')
            self._service_enabled = True
        except Exception as e:
            print(f"Service start fout: {e}")

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
        self._stop_background_worker.set()
        self._set_background_service(False)
        self._write_media_state()

    def on_pause(self):
        self._set_background_service(self.audio.loaded)
        self._write_media_state()
        return True

    def on_resume(self):
        self._set_background_service(self.audio.loaded)
        self._write_media_state()
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

    def _play_current_song(self, update_ui=True):
        if not self.all_songs_data:
            return False

        song = self.all_songs_data[self.current_index]

        if update_ui:
            self.slider.value = 0
            self.time_current.text = "0:00"
            self.time_total.text = "..."
            self.song_label.text = song['title']
            self.artist_label.text = f"Track {self.current_index + 1} van {len(self.all_songs_data)}"

        self.audio.set_volume(self.current_volume)

        def on_length(l):
            if self.audio.loaded_path == song['path']:
                self.audio._length = l
                if update_ui:
                    self.slider.max = l if l > 0 else 100
                    self.time_total.text = format_time(l) if l > 0 else "..."

        ok = self.audio.load_and_play(song['path'], on_length=on_length)

        if ok:
            self._write_media_state()
            self._set_background_service(True)
            if update_ui:
                self.slider.max = 100
                self.btn_play.display_img.source = os.path.join(ICON_PATH, "pausebutton.png")
            Clock.schedule_once(lambda dt: self._preload_next(), 1.0)
        else:
            self._set_background_service(False)
            self._write_media_state()
            if update_ui:
                self.song_label.text = "Laden mislukt"
                self.btn_play.display_img.source = os.path.join(ICON_PATH, "playbutton.png")

        if update_ui:
            self.build_playlist(self.all_songs_data)

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

        if update_ui:
            self.btn_play.display_img.source = os.path.join(
                ICON_PATH,
                "pausebutton.png" if self.audio.playing else "playbutton.png"
            )
            self.build_playlist(self.all_songs_data)

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
        if self.all_songs_data:
            self.current_index = min(self.current_index, len(self.all_songs_data) - 1)
        else:
            self.current_index = 0
            self._set_background_service(False)
            self._write_media_state()
        self.build_playlist(self.all_songs_data)
        self._write_media_state()

    def build_playlist(self, song_list):
        self.playlist_layout.clear_widgets()
        for song in song_list:
            is_current = (song['index'] == self.current_index and self.audio.loaded)
            row    = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(10))
            btn    = RoundedSongButton(title=song['title'], is_active=is_current,
                                       size_hint_x=0.85)
            btn.bind(on_release=lambda x, i=song['index']: self.play_specific(i))
            del_btn = ImageButton(DELETE_IMG, size_hint_x=0.15)
            del_btn.bind(on_release=lambda x, p=song['path']: self.delete_song(p))
            row.add_widget(btn)
            row.add_widget(del_btn)
            self.playlist_layout.add_widget(row)

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
        if self.audio.loaded_path == song_path:
            self.audio.stop()
            self._set_background_service(False)
            self.song_label.text   = "Kies een track"
            self.artist_label.text = "Mads Music Player"
            self.slider.value      = 0
            self.time_current.text = "0:00"
            self.time_total.text   = "0:00"
            self.btn_play.display_img.source = os.path.join(ICON_PATH, "playbutton.png")
        try:
            os.remove(song_path)
            self.load_songs()
            self._write_media_state()
        except Exception:
            pass

    def filter_playlist(self, instance, text):
        query    = text.lower()
        filtered = [s for s in self.all_songs_data if query in s['title'].lower()]
        self.build_playlist(filtered)

    # ── controls ───────────────────────────────────────────────────────────────

    def set_volume(self, instance, value):
        self.current_volume = value
        self.audio.set_volume(value)

    def toggle_shuffle(self, instance):
        self.is_shuffle = not self.is_shuffle
        self.btn_shuffle.set_active(self.is_shuffle)

    def toggle_repeat(self, instance):
        self.is_repeat = not self.is_repeat
        self.btn_repeat.set_active(self.is_repeat)

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
            dest_path = os.path.join(MUSIC_PATH, filename)
            pfd = resolver.openFileDescriptor(uri, "r")
            with os.fdopen(os.dup(pfd.getFd()), 'rb') as f_in:
                with open(dest_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            pfd.close()
            Clock.schedule_once(lambda dt: self.load_songs(), 0.5)
        except Exception:
            pass

    def _on_file_selection(self, selection):
        if selection:
            dest = os.path.join(MUSIC_PATH, os.path.basename(selection[0]))
            shutil.copy(selection[0], dest)
            Clock.schedule_once(lambda dt: self.load_songs(), 0.5)
    
    def start_background_music(self):
        if platform == 'android':
            self._set_background_service(True)
            
if __name__ == "__main__":
    MadsMusicSpotify().run()
