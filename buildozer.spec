[app]

title = Flashlight Pro
package.name = flashlightpro
package.domain = org.riajapps

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,md

version = 1.0.0

requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.permissions = CAMERA
android.api = 35
android.minapi = 23
android.archs = arm64-v8a, armeabi-v7a

# Build on a Linux computer using Buildozer.
# Do not add pyjnius manually; python-for-android provides it for Android builds.

[buildozer]

log_level = 2
warn_on_root = 1
