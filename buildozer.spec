[app]
title = BetPawa Predictor
package.name = betpawapredictor
package.domain = org.sserunjogivdev
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,pkl,json,csv
version = 1.0.0

requirements = python3,kivy==2.2.0,numpy,xgboost,scikit-learn,requests,beautifulsoup4,Pillow

orientation = portrait
fullscreen = 0
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a

android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# App icon (place icon.png in root)
# icon.filename = %(source.dir)s/assets/icon.png
# presplash.filename = %(source.dir)s/assets/splash.png

[buildozer]
log_level = 2
warn_on_root = 1
