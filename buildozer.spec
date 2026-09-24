[app]

title = Мои часы
package.name = myclock
package.domain = org.example

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas

version = 1.0

requirements = python3,kivy==2.3.0,pillow

orientation = portrait
fullscreen = 0

# Если положите свою иконку 512x512 в файл icon.png — раскомментируйте строку ниже
# icon.filename = %(source.dir)s/icon.png

android.permissions = READ_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

android.api = 33
android.minapi = 21
android.ndk_api = 21
android.archs = arm64-v8a,armeabi-v7a

[buildozer]

log_level = 2
warn_on_root = 1
