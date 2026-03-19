import json
import os
import time

from jnius import autoclass
from android.broadcast import BroadcastReceiver


APP_BASE_PATH = os.path.dirname(os.path.abspath(__file__))
CHANNEL_ID = "mads_music_playback_v2"
NOTIFICATION_ID = 424242

ACTION_PREV = "madsmusic_prev"
ACTION_PLAY_PAUSE = "madsmusic_play_pause"
ACTION_NEXT = "madsmusic_next"


def get_writable_base_path():
    try:
        PythonService = autoclass('org.kivy.android.PythonService')
        service = PythonService.mService
        return service.getFilesDir().getAbsolutePath()
    except Exception:
        return APP_BASE_PATH


WRITABLE_BASE_PATH = get_writable_base_path()
BACKGROUND_SERVICE_STATE = os.path.join(WRITABLE_BASE_PATH, "background_service.json")
MEDIA_STATE_PATH = os.path.join(WRITABLE_BASE_PATH, "media_state.json")
MEDIA_COMMAND_PATH = os.path.join(WRITABLE_BASE_PATH, "media_command.json")
SERVICE_LOG_PATH = os.path.join(WRITABLE_BASE_PATH, "service_debug.log")


def read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def write_json(path, payload):
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
    except Exception:
        pass


def debug_log(message):
    try:
        with open(SERVICE_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except Exception:
        pass


def read_service_state():
    return read_json(BACKGROUND_SERVICE_STATE, {"enabled": False})


def read_media_state():
    return read_json(
        MEDIA_STATE_PATH,
        {
            "enabled": False,
            "playing": False,
            "title": "Mads Music",
            "subtitle": "Mads Music Player",
        },
    )


def acquire_wake_lock():
    try:
        PythonService = autoclass('org.kivy.android.PythonService')
        Context = autoclass('android.content.Context')
        PowerManager = autoclass('android.os.PowerManager')

        service = PythonService.mService
        power_manager = service.getSystemService(Context.POWER_SERVICE)
        wake_lock = power_manager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            'MadsMusic:BackgroundPlayback'
        )
        wake_lock.setReferenceCounted(False)
        wake_lock.acquire()
        return wake_lock
    except Exception:
        return None


def release_wake_lock(wake_lock):
    if not wake_lock:
        return

    try:
        if wake_lock.isHeld():
            wake_lock.release()
    except Exception:
        pass


class MediaNotificationController:

    def __init__(self):
        PythonService = autoclass('org.kivy.android.PythonService')
        self.service = PythonService.mService
        self.context = self.service.getApplicationContext()

        self.Context = autoclass('android.content.Context')
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

        self.notification_manager = self.context.getSystemService(self.Context.NOTIFICATION_SERVICE)
        self.media_session = None
        self.receiver = None
        self._is_foreground = False

        self._create_channel()
        self._init_media_session()
        self._init_receiver()

    def _init_media_session(self):
        try:
            self.media_session = self.MediaSession(self.context, "MadsMusicLockscreen")
            self.media_session.setActive(True)
        except Exception as exc:
            debug_log(f"MediaSession init failed: {exc}")
            self.media_session = None

    def _init_receiver(self):
        try:
            self.receiver = BroadcastReceiver(
                self._on_broadcast,
                actions=[ACTION_PREV, ACTION_PLAY_PAUSE, ACTION_NEXT]
            )
            self.receiver.start()
        except Exception as exc:
            debug_log(f"BroadcastReceiver init failed: {exc}")
            self.receiver = None

    def _create_channel(self):
        if self.BuildVersion.SDK_INT < self.VersionCodes.O:
            return

        channel = self.NotificationChannel(
            CHANNEL_ID,
            "Mads Music",
            self.NotificationManager.IMPORTANCE_DEFAULT
        )
        channel.setDescription("Lockscreen bediening voor Mads Music")
        try:
            channel.setLockscreenVisibility(self.Notification.VISIBILITY_PUBLIC)
        except Exception:
            pass
        self.notification_manager.createNotificationChannel(channel)

    def _pending_flags(self):
        flags = self.PendingIntent.FLAG_UPDATE_CURRENT
        if self.BuildVersion.SDK_INT >= self.VersionCodes.M:
            flags |= self.PendingIntent.FLAG_IMMUTABLE
        return flags

    def _build_action_intent(self, action, request_code):
        intent = self.Intent()
        intent.setAction(action)
        intent.setPackage(self.context.getPackageName())
        return self.PendingIntent.getBroadcast(
            self.context,
            request_code,
            intent,
            self._pending_flags()
        )

    def _build_content_intent(self):
        launch_intent = self.context.getPackageManager().getLaunchIntentForPackage(
            self.context.getPackageName()
        )
        if not launch_intent:
            return None

        launch_intent.setFlags(
            self.Intent.FLAG_ACTIVITY_NEW_TASK
            | self.Intent.FLAG_ACTIVITY_SINGLE_TOP
            | self.Intent.FLAG_ACTIVITY_CLEAR_TOP
        )
        return self.PendingIntent.getActivity(
            self.context,
            100,
            launch_intent,
            self._pending_flags()
        )

    def _on_broadcast(self, context, intent):
        action = str(intent.getAction() or "")
        mapping = {
            ACTION_PREV: "prev",
            ACTION_PLAY_PAUSE: "play_pause",
            ACTION_NEXT: "next",
        }
        command = mapping.get(action)
        if not command:
            return

        write_json(
            MEDIA_COMMAND_PATH,
            {"command": command, "id": time.time()},
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
        )
        playback_state = self.PlaybackState.STATE_PLAYING if state.get("playing") else self.PlaybackState.STATE_PAUSED
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
            debug_log(f"MediaSession update failed: {exc}")

    def _build_notification(self, state):
        if self.BuildVersion.SDK_INT >= self.VersionCodes.O:
            builder = self.NotificationBuilder(self.context, CHANNEL_ID)
        else:
            builder = self.NotificationBuilder(self.context)

        content_intent = self._build_content_intent()
        if content_intent:
            builder.setContentIntent(content_intent)

        builder.setContentTitle(state.get("title", "Mads Music"))
        builder.setContentText(state.get("subtitle", "Mads Music Player"))
        builder.setSmallIcon(self.context.getApplicationInfo().icon)
        builder.setVisibility(self.Notification.VISIBILITY_PUBLIC)
        builder.setCategory(self.Notification.CATEGORY_TRANSPORT)
        builder.setOnlyAlertOnce(True)
        builder.setShowWhen(False)
        builder.setOngoing(bool(state.get("enabled")))
        try:
            builder.setPriority(self.Notification.PRIORITY_HIGH)
        except Exception:
            pass
        try:
            if self.BuildVersion.SDK_INT >= self.VersionCodes.S:
                builder.setForegroundServiceBehavior(self.Notification.FOREGROUND_SERVICE_IMMEDIATE)
        except Exception as exc:
            debug_log(f"Foreground behavior setup failed: {exc}")

        builder.addAction(
            self.AndroidDrawables.ic_media_previous,
            "Vorige",
            self._build_action_intent(ACTION_PREV, 1)
        )
        builder.addAction(
            self.AndroidDrawables.ic_media_pause if state.get("playing") else self.AndroidDrawables.ic_media_play,
            "Pauze" if state.get("playing") else "Afspelen",
            self._build_action_intent(ACTION_PLAY_PAUSE, 2)
        )
        builder.addAction(
            self.AndroidDrawables.ic_media_next,
            "Volgende",
            self._build_action_intent(ACTION_NEXT, 3)
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
                debug_log(f"MediaStyle setup failed: {exc}")

        return builder.build()

    def show(self, state):
        self._update_media_session(state)
        notification = self._build_notification(state)

        if not self._is_foreground:
            try:
                self.service.startForeground(NOTIFICATION_ID, notification)
                self._is_foreground = True
            except Exception as exc:
                debug_log(f"startForeground failed: {exc}")
        try:
            self.notification_manager.notify(NOTIFICATION_ID, notification)
        except Exception as exc:
            debug_log(f"notify failed: {exc}")

    def stop(self):
        try:
            if self.receiver:
                self.receiver.stop()
        except Exception:
            pass

        try:
            self.notification_manager.cancel(NOTIFICATION_ID)
        except Exception:
            pass

        try:
            self.service.stopForeground(True)
        except Exception:
            pass

        try:
            if self.media_session:
                self.media_session.release()
        except Exception:
            pass


def run_service():
    debug_log("Service started")
    wake_lock = acquire_wake_lock()
    controller = MediaNotificationController()
    last_state_dump = None

    try:
        while read_service_state().get("enabled", False):
            media_state = read_media_state()
            state_dump = json.dumps(media_state, sort_keys=True)
            if state_dump != last_state_dump:
                debug_log(f"Notification update: {state_dump}")
                controller.show(media_state)
                last_state_dump = state_dump
            time.sleep(0.35)
    finally:
        debug_log("Service stopping")
        controller.stop()
        release_wake_lock(wake_lock)


if __name__ == '__main__':
    run_service()
