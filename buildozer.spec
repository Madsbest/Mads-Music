[app]
title = Mads Music
package.name = madsmusic
package.domain = org.madsmusic

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,mp3,wav,ogg,m4a,json
source.include_patterns = Buttons/*,music/*
source.exclude_dirs = __pycache__,bin,.git,.venv,venv

version = 1.1
icon.filename = Buttons/app_icon.png

# pyjnius is de juiste recipe-naam voor Buildozer/p4a.
requirements = python3,kivy==2.3.0,pygame==2.5.2,plyer,android,pyjnius,mutagen,cython==0.29.33

# Geen background service of notificatie meer nodig.

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_AUDIO,WAKE_LOCK

# API 33 avoids Android 14 foreground-service-type enforcement that
# current python-for-android service packaging does not reliably expose.
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a

android.enable_androidx = True
android.gradle_dependencies = androidx.core:core:1.9.0
android.release_artifact = apk

log_level = 2
warn_on_root = 1

[buildozer]
bin_dir = ./bin
