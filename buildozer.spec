[app]
title = BetPawa Predictor
package.name = betpawapredictor
package.domain = org.sserunjogidev
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.include_patterns = predictions.json,model_meta.json
version = 1.0.0

# python3 and hostpython3 MUST be identical versions.
# We pin to 3.9.25 which is what actions/setup-python installs on the runner.
# Python 3.9 has the 'cgi' module required by Cython 0.29.x (Tempita).
requirements = python3==3.9.25,hostpython3==3.9.25,kivy==2.1.0,pillow

orientation = portrait
fullscreen = 0

android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True

# Single arch — faster build, works on all modern Android phones
android.archs = arm64-v8a

android.permissions = INTERNET

[buildozer]
log_level = 2
warn_on_root = 0
