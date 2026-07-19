[app]
title = BetPawa Predictor
package.name = betpawapredictor
package.domain = org.sserunjogidev
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.include_patterns = predictions.json,model_meta.json
version = 1.0.0

# kivy 2.1.0 is the stable release with verified python-for-android recipes
requirements = python3,kivy==2.1.0,pillow

orientation = portrait
fullscreen = 0

android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True

# Single arch for faster build and better compatibility
android.archs = arm64-v8a

android.permissions = INTERNET

[buildozer]
log_level = 2
warn_on_root = 0
