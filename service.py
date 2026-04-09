import json
import os
import time

from jnius import autoclass, PythonJavaClass, java_method


APP_BASE_PATH = os.path.dirname(os.path.abspath(__file__))
CHANNEL_ID = "mads_music_playback_v4"
NOTIFICATION_ID = 424242

ACTION_PREV = "madsmusic_prev"
ACTION_PLAY_PAUSE = "madsmusic_play_pause"
ACTION_NEXT = "madsmusic_next"
ACTION_STOP = "madsmusic_stop"


def get_writable_base_path():
    try:
        from android.storage import app_storage_path
        base_path = app_storage_path()
        if base_path:
            return base_path
    except Exception:
        pass
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
SERVICE_HEARTBEAT_PATH = os.path.join(WRITABLE_BASE_PATH, "service_heartbeat.json")


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


def write_heartbeat(alive, enabled=False, extra=None):
    payload = {
        "alive": bool(alive),
        "enabled": bool(enabled),
        "ts": time.time(),
    }
    if extra:
        payload.update(extra)
    write_json(SERVICE_HEARTBEAT_PATH, payload)


class NotificationCommandReceiverCallback(PythonJavaClass):
    __javainterfaces__ = ['org/kivy/android/GenericBroadcastReceiverCallback']
    __javacontext__ = 'app'

    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    @java_method('(Landroid/content/Context;Landroid/content/Intent;)V')
    def onReceive(self, context, intent):
        if self._callback:
            self._callback(context, intent)


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
            "mode_summary": "Standaard afspelen",
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
        self.IntentFilter = autoclass('android.content.IntentFilter')
        self.GenericBroadcastReceiver = autoclass('org.kivy.android.GenericBroadcastReceiver')

        self.notification_manager = self.context.getSystemService(self.Context.NOTIFICATION_SERVICE)
        self.media_session = None
        self.receiver = None
        self.receiver_callback = None
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
            self.receiver_callback = NotificationCommandReceiverCallback(self._on_broadcast)
            self.receiver = self.GenericBroadcastReceiver(self.receiver_callback)
            intent_filter = self.IntentFilter()
            for action in [ACTION_PREV, ACTION_PLAY_PAUSE, ACTION_NEXT, ACTION_STOP]:
                intent_filter.addAction(action)

            tiramisu = getattr(self.VersionCodes, 'TIRAMISU', 33)
            if self.BuildVersion.SDK_INT >= tiramisu:
                self.context.registerReceiver(
                    self.receiver,
                    intent_filter,
                    self.Context.RECEIVER_NOT_EXPORTED
                )
            else:
                self.context.registerReceiver(self.receiver, intent_filter)
            debug_log("Notification receiver registered")
        except Exception as exc:
            debug_log(f"BroadcastReceiver init failed: {exc}")
            self.receiver = None
            self.receiver_callback = None

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
            channel.enableVibration(False)
            channel.setShowBadge(False)
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
        debug_log(f"Notification action received: {action}")
        mapping = {
            ACTION_PREV: "prev",
            ACTION_PLAY_PAUSE: "play_pause",
            ACTION_NEXT: "next",
            ACTION_STOP: "stop",
        }
        command = mapping.get(action)
        if not command:
            return

        write_json(
            MEDIA_COMMAND_PATH,
            {"command": command, "id": time.time()},
        )
        debug_log(f"Media command written: {command}")

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
        builder.addAction(
            self.AndroidDrawables.ic_menu_close_clear_cancel,
            "Stop",
            self._build_action_intent(ACTION_STOP, 4)
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
                self.context.unregisterReceiver(self.receiver)
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
    debug_log(f"Service base path: {WRITABLE_BASE_PATH}")
    try:
        PythonService = autoclass('org.kivy.android.PythonService')
        PythonService.mService.setAutoRestartService(True)
        debug_log("Auto restart enabled on PythonService")
    except Exception as exc:
        debug_log(f"Auto restart setup failed: {exc}")
    wake_lock = acquire_wake_lock()
    controller = MediaNotificationController()
    initial_state = read_media_state()
    controller.show(initial_state)
    last_state_dump = json.dumps(initial_state, sort_keys=True)
    disabled_since = None

    try:
        while True:
            service_state = read_service_state()
            service_enabled = bool(service_state.get("enabled", False))
            write_heartbeat(True, enabled=service_enabled)

            if not service_enabled:
                if disabled_since is None:
                    disabled_since = time.time()
                    debug_log("Service disabled flag detected, entering grace period")
                elif time.time() - disabled_since >= 8.0:
                    debug_log("Service disabled grace period elapsed, stopping")
                    break
            else:
                disabled_since = None

            media_state = read_media_state()
            state_dump = json.dumps(media_state, sort_keys=True)
            if state_dump != last_state_dump:
                debug_log(f"Notification update: {state_dump}")
                controller.show(media_state)
                last_state_dump = state_dump
            time.sleep(0.35)
    finally:
        debug_log("Service stopping")
        write_heartbeat(False, enabled=False)
        controller.stop()
        release_wake_lock(wake_lock)


if __name__ == '__main__':
    run_service()
