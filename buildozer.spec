[app]
title = BetPawa Predictor
package.name = betpawapredictor
package.domain = org.sserunjogivdev
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.include_patterns = predictions.json,model_meta.json
version = 1.0.0

# kivy 2.1.0 has verified python-for-android recipes; 2.2.0 has config.pxi issues
requirements = python3,kivy==2.1.0

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
warn_on_root = 1
