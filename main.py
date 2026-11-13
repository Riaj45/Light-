from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, RoundedRectangle
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.utils import get_color_from_hex

Window.clearcolor = get_color_from_hex("#0F172A")

# Android hardware is initialized only after CAMERA permission is granted.
ANDROID_PLATFORM = False
try:
    from kivy.utils import platform
    ANDROID_PLATFORM = platform == "android"
except Exception:
    pass

if ANDROID_PLATFORM:
    try:
        from android.permissions import request_permissions, Permission
    except Exception:
        request_permissions = None
        Permission = None


class TorchController:
    """Small wrapper around Android CameraManager torch control."""

    def __init__(self):
        self.manager = None
        self.camera_id = None
        self.available = False
        self.error = None

    def initialize(self):
        if not ANDROID_PLATFORM:
            self.error = "Android hardware is unavailable on this platform."
            return False

        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            CameraCharacteristics = autoclass(
                "android.hardware.camera2.CameraCharacteristics"
            )

            activity = PythonActivity.mActivity
            self.manager = activity.getSystemService(Context.CAMERA_SERVICE)

            ids = self.manager.getCameraIdList()
            for camera_id in ids:
                try:
                    characteristics = self.manager.getCameraCharacteristics(camera_id)
                    has_flash = characteristics.get(
                        CameraCharacteristics.FLASH_INFO_AVAILABLE
                    )
                    if has_flash:
                        self.camera_id = camera_id
                        self.available = True
                        self.error = None
                        return True
                except Exception:
                    continue

            self.error = "No camera with an LED flash was found."
            return False
        except Exception as exc:
            self.error = "Camera initialization failed: {}".format(exc)
            self.available = False
            return False

    def set_torch(self, enabled):
        if not self.available or self.manager is None or self.camera_id is None:
            return False
        try:
            self.manager.setTorchMode(self.camera_id, bool(enabled))
            return True
        except Exception as exc:
            self.error = "Torch error: {}".format(exc)
            return False

    def battery_level(self):
        if not ANDROID_PLATFORM:
            return None
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            BatteryManager = autoclass("android.os.BatteryManager")
            activity = PythonActivity.mActivity
            manager = activity.getSystemService(Context.BATTERY_SERVICE)
            level = int(manager.getIntProperty(
                BatteryManager.BATTERY_PROPERTY_CAPACITY
            ))
            return level if 0 <= level <= 100 else None
        except Exception:
            return None


class GlowFlashButton(Widget):
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.glow_radius = 0
        self.is_on = False

        with self.canvas:
            self.glow_color = Color(1, 0.85, 0.2, 0)
            self.glow_circle = Ellipse()
            self.ring_color = Color(0.2, 0.28, 0.4, 1)
            self.ring_circle = Ellipse()
            self.btn_color = Color(0.12, 0.16, 0.23, 1)
            self.btn_circle = Ellipse()

        self.bind(pos=self.update_canvas, size=self.update_canvas)

    def update_canvas(self, *args):
        cx, cy = self.center_x, self.center_y
        base_r = max(0, min(self.width, self.height) * 0.30)
        glow_r = base_r + self.glow_radius
        ring_r = base_r + 8

        self.glow_circle.pos = (cx - glow_r, cy - glow_r)
        self.glow_circle.size = (glow_r * 2, glow_r * 2)
        self.ring_circle.pos = (cx - ring_r, cy - ring_r)
        self.ring_circle.size = (ring_r * 2, ring_r * 2)
        self.btn_circle.pos = (cx - base_r, cy - base_r)
        self.btn_circle.size = (base_r * 2, base_r * 2)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            cx, cy = self.center_x, self.center_y
            radius = min(self.width, self.height) * 0.30
            distance_sq = (touch.x - cx) ** 2 + (touch.y - cy) ** 2
            if distance_sq <= (radius + 15) ** 2:
                self.callback()
                return True
        return super().on_touch_down(touch)

    def animate_state(self, state, sos_mode=False, animate_glow=True):
        self.is_on = bool(state)
        Animation.cancel_all(self.btn_color)
        Animation.cancel_all(self.ring_color)
        Animation.cancel_all(self.glow_color)

        if state:
            if sos_mode:
                Animation(
                    r=0.94, g=0.27, b=0.27, duration=0.12
                ).start(self.btn_color)
                Animation(
                    r=1, g=0.6, b=0.6, duration=0.12
                ).start(self.ring_color)
                Animation(
                    r=0.94, g=0.27, b=0.27, a=0.45, duration=0.12
                ).start(self.glow_color)
            else:
                Animation(
                    r=1, g=0.82, b=0.15, duration=0.12
                ).start(self.btn_color)
                Animation(
                    r=1, g=0.92, b=0.5, duration=0.12
                ).start(self.ring_color)
                Animation(
                    r=1, g=0.85, b=0.2, a=0.35, duration=0.12
                ).start(self.glow_color)

            if animate_glow:
                Animation.cancel_all(self, "glow_radius")
                pulse = (
                    Animation(glow_radius=24, duration=0.45, t="in_out_quad")
                    + Animation(glow_radius=12, duration=0.45, t="in_out_quad")
                )
                pulse.repeat = True
                pulse.bind(on_progress=lambda *_: self.update_canvas())
                pulse.start(self)
        else:
            Animation.cancel_all(self, "glow_radius")
            Animation(r=0.12, g=0.16, b=0.23, duration=0.12).start(self.btn_color)
            Animation(r=0.2, g=0.28, b=0.4, duration=0.12).start(self.ring_color)
            Animation(a=0, duration=0.12).start(self.glow_color)
            Animation(glow_radius=0, duration=0.12).start(self)
        self.update_canvas()


class FlashlightUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(
            orientation="vertical", padding=20, spacing=12, **kwargs
        )
        self.torch = TorchController()
        self.hardware_ready = False
        self.flash_on = False
        self.sos_active = False
        self.blink_event = None
        self.timer_event = None
        self.blink_speed = 0.0
        self.strobe_state = False
        self.sos_index = 0
        self.remaining_seconds = 0
        self.timer_options = [0, 60, 300, 600]
        self.timer_labels = ["Timer: OFF", "Timer: 1m", "Timer: 5m", "Timer: 10m"]
        self.timer_idx = 0

        self.sos_pattern = [
            (True, 0.2), (False, 0.2), (True, 0.2), (False, 0.2),
            (True, 0.2), (False, 0.5),
            (True, 0.6), (False, 0.2), (True, 0.6), (False, 0.2),
            (True, 0.6), (False, 0.5),
            (True, 0.2), (False, 0.2), (True, 0.2), (False, 0.2),
            (True, 0.2), (False, 1.2),
        ]

        top_bar = BoxLayout(orientation="horizontal", size_hint=(1, 0.08))
        self.title_lbl = Label(
            text="[b]FLASHLIGHT PRO[/b]", markup=True, font_size="20sp",
            halign="left", color=(0.95, 0.96, 0.98, 1)
        )
        self.title_lbl.bind(size=self.title_lbl.setter("text_size"))
        self.battery_lbl = Label(
            text="Battery: --%", font_size="14sp",
            halign="right", color=(0.3, 0.85, 0.5, 1)
        )
        self.battery_lbl.bind(size=self.battery_lbl.setter("text_size"))
        top_bar.add_widget(self.title_lbl)
        top_bar.add_widget(self.battery_lbl)
        self.add_widget(top_bar)

        self.status_lbl = Label(
            text="STATUS: OFF", font_size="15sp",
            size_hint=(1, 0.07), color=(0.58, 0.64, 0.72, 1)
        )
        self.add_widget(self.status_lbl)

        self.flash_btn = GlowFlashButton(
            callback=self.toggle_power, size_hint=(1, 0.42)
        )
        self.add_widget(self.flash_btn)

        button_row = BoxLayout(
            orientation="horizontal", spacing=12, size_hint=(1, 0.12)
        )
        self.sos_btn = Button(
            text="[b]SOS MODE: OFF[/b]", markup=True, font_size="14sp",
            background_normal="", background_color=(0.2, 0.25, 0.35, 1)
        )
        self.sos_btn.bind(on_release=self.toggle_sos)
        self.timer_btn = Button(
            text="[b]Timer: OFF[/b]", markup=True, font_size="14sp",
            background_normal="", background_color=(0.2, 0.25, 0.35, 1)
        )
        self.timer_btn.bind(on_release=self.cycle_timer)
        button_row.add_widget(self.sos_btn)
        button_row.add_widget(self.timer_btn)
        self.add_widget(button_row)

        self.card = BoxLayout(
            orientation="vertical", padding=15, spacing=8, size_hint=(1, 0.24)
        )
        with self.card.canvas.before:
            self.card_bg_color = Color(0.12, 0.16, 0.23, 1)
            self.card_bg = RoundedRectangle(radius=[18])
        self.card.bind(pos=self.update_card_bg, size=self.update_card_bg)

        self.blink_lbl = Label(
            text="Blink Mode: OFF (Steady Light)", font_size="14sp",
            color=(0.9, 0.94, 1, 1)
        )
        self.card.add_widget(self.blink_lbl)
        self.slider = Slider(
            min=0, max=10, value=0, step=0.5, cursor_size=(24, 24)
        )
        self.slider.bind(value=self.on_speed_change)
        self.card.add_widget(self.slider)
        self.add_widget(self.card)

        Clock.schedule_once(self.request_camera_permission, 0.5)
        Clock.schedule_interval(self.update_battery, 10)

    def request_camera_permission(self, *_):
        if not ANDROID_PLATFORM:
            self.status_lbl.text = "PREVIEW MODE: Android device required"
            return
        if request_permissions is None:
            self.status_lbl.text = "ERROR: Android permission API unavailable"
            return
        try:
            request_permissions([Permission.CAMERA], self.permission_callback)
        except Exception as exc:
            self.status_lbl.text = "Permission error: {}".format(exc)

    def permission_callback(self, permissions, grants):
        granted = bool(grants) and all(grants)
        Clock.schedule_once(
            lambda _dt: self.finish_hardware_setup(granted), 0
        )

    def finish_hardware_setup(self, granted):
        if not granted:
            self.status_lbl.text = "CAMERA PERMISSION DENIED"
            return
        self.hardware_ready = self.torch.initialize()
        if self.hardware_ready:
            self.status_lbl.text = "READY: FLASHLIGHT OFF"
        else:
            self.status_lbl.text = "FLASH UNAVAILABLE"
        self.update_battery()

    def update_card_bg(self, *_):
        self.card_bg.pos = self.card.pos
        self.card_bg.size = self.card.size

    def update_battery(self, *_):
        level = self.torch.battery_level()
        self.battery_lbl.text = (
            "Battery: {}%".format(level) if level is not None
            else "Battery: --%"
        )

    def set_hardware_torch(self, state):
        if not ANDROID_PLATFORM:
            return False
        if not self.hardware_ready:
            self.status_lbl.text = "FLASH NOT READY: CHECK PERMISSION"
            return False
        success = self.torch.set_torch(state)
        if not success and self.torch.error:
            self.status_lbl.text = "FLASH ERROR: {}".format(self.torch.error[:55])
        return success

    def toggle_power(self):
        if self.sos_active:
            self.stop_sos()
            return
        if self.flash_on:
            self.turn_everything_off()
            return
        if ANDROID_PLATFORM and not self.hardware_ready:
            self.status_lbl.text = "FLASH NOT READY: GRANT CAMERA PERMISSION"
            return
        self.flash_on = True
        self.start_timer_if_needed()
        self.update_flash_behavior()

    def toggle_sos(self, *_):
        if self.sos_active:
            self.stop_sos()
            return
        if ANDROID_PLATFORM and not self.hardware_ready:
            self.status_lbl.text = "FLASH NOT READY: GRANT CAMERA PERMISSION"
            return
        self.sos_active = True
        self.flash_on = True
        self.sos_btn.text = "[b]SOS MODE: ON[/b]"
        self.sos_btn.background_color = (0.75, 0.18, 0.18, 1)
        self.start_timer_if_needed()
        self.update_flash_behavior()

    def stop_sos(self):
        self.sos_active = False
        self.sos_btn.text = "[b]SOS MODE: OFF[/b]"
        self.sos_btn.background_color = (0.2, 0.25, 0.35, 1)
        self.turn_everything_off()

    def cycle_timer(self, *_):
        self.timer_idx = (self.timer_idx + 1) % len(self.timer_options)
        self.remaining_seconds = self.timer_options[self.timer_idx]
        self.timer_btn.text = "[b]{}[/b]".format(
            self.timer_labels[self.timer_idx]
        )
        if self.remaining_seconds > 0:
            self.timer_btn.background_color = (0.15, 0.45, 0.72, 1)
            if self.flash_on:
                self.start_timer_if_needed()
        else:
            self.cancel_timer()
            self.refresh_status_text()

    def cancel_timer(self):
        if self.timer_event is not None:
            self.timer_event.cancel()
            self.timer_event = None

    def start_timer_if_needed(self):
        self.cancel_timer()
        duration = self.timer_options[self.timer_idx]
        if duration > 0:
            self.remaining_seconds = duration
            self.timer_event = Clock.schedule_interval(self.timer_tick, 1)

    def timer_tick(self, _dt):
        self.remaining_seconds -= 1
        self.refresh_status_text()
        if self.remaining_seconds <= 0:
            if self.sos_active:
                self.stop_sos()
            else:
                self.turn_everything_off()
            return False
        return True

    def turn_everything_off(self):
        self.flash_on = False
        if self.blink_event is not None:
            self.blink_event.cancel()
            self.blink_event = None
        self.cancel_timer()
        self.set_hardware_torch(False)
        self.flash_btn.animate_state(False)
        self.status_lbl.text = "STATUS: OFF"
        self.status_lbl.color = (0.58, 0.64, 0.72, 1)

    def on_speed_change(self, _instance, value):
        self.blink_speed = float(value)
        if value == 0:
            self.blink_lbl.text = "Blink Mode: OFF (Steady Light)"
        else:
            self.blink_lbl.text = "Blink Speed: {:.1f} cycles/sec".format(value)
        if self.flash_on and not self.sos_active:
            self.update_flash_behavior()

    def refresh_status_text(self):
        timer_text = ""
        if self.timer_options[self.timer_idx] > 0 and self.flash_on:
            mins, secs = divmod(max(0, self.remaining_seconds), 60)
            timer_text = " | Auto-Off: {:02d}:{:02d}".format(mins, secs)

        if not self.flash_on:
            self.status_lbl.text = "STATUS: OFF"
            self.status_lbl.color = (0.58, 0.64, 0.72, 1)
        elif self.sos_active:
            self.status_lbl.text = "STATUS: SOS MODE" + timer_text
            self.status_lbl.color = (0.95, 0.3, 0.3, 1)
        elif self.blink_speed == 0:
            self.status_lbl.text = "STATUS: ON" + timer_text
            self.status_lbl.color = (1, 0.85, 0.2, 1)
        else:
            self.status_lbl.text = "STATUS: BLINK ({:.1f}x)".format(
                self.blink_speed
            ) + timer_text
            self.status_lbl.color = (0.22, 0.74, 0.97, 1)

    def update_flash_behavior(self):
        if self.blink_event is not None:
            self.blink_event.cancel()
            self.blink_event = None
        self.refresh_status_text()

        if self.sos_active:
            self.sos_index = 0
            self.run_sos_step()
        elif self.blink_speed == 0:
            if self.set_hardware_torch(True):
                self.flash_btn.animate_state(True, animate_glow=True)
            elif ANDROID_PLATFORM:
                self.turn_everything_off()
        else:
            self.strobe_state = False
            self.set_hardware_torch(False)
            interval = 1.0 / (self.blink_speed * 2.0)
            self.blink_event = Clock.schedule_interval(
                self.blink_tick, interval
            )

    def run_sos_step(self, *_):
        if not self.sos_active or not self.flash_on:
            return False
        state, duration = self.sos_pattern[self.sos_index]
        success = self.set_hardware_torch(state)
        self.flash_btn.animate_state(
            state, sos_mode=True, animate_glow=False
        )
        if not success and ANDROID_PLATFORM:
            self.stop_sos()
            return False
        self.sos_index = (self.sos_index + 1) % len(self.sos_pattern)
        self.blink_event = Clock.schedule_once(self.run_sos_step, duration)
        return False

    def blink_tick(self, _dt):
        if not self.flash_on or self.sos_active:
            return False
        self.strobe_state = not self.strobe_state
        success = self.set_hardware_torch(self.strobe_state)
        self.flash_btn.animate_state(
            self.strobe_state, animate_glow=False
        )
        if not success and ANDROID_PLATFORM:
            self.turn_everything_off()
            return False
        return True

    def stop_all(self):
        if self.blink_event is not None:
            self.blink_event.cancel()
            self.blink_event = None
        self.cancel_timer()
        self.set_hardware_torch(False)
        self.flash_on = False
        self.sos_active = False


class FlashlightApp(App):
    def build(self):
        self.ui = FlashlightUI()
        return self.ui

    def on_pause(self):
        # Stop the torch and reset the visible controls when backgrounded.
        if hasattr(self, "ui"):
            self.ui.stop_all()
            self.ui.sos_btn.text = "[b]SOS MODE: OFF[/b]"
            self.ui.sos_btn.background_color = (0.2, 0.25, 0.35, 1)
            self.ui.flash_btn.animate_state(False)
            self.ui.status_lbl.text = "STATUS: OFF"
        return True

    def on_stop(self):
        if hasattr(self, "ui"):
            self.ui.stop_all()


if __name__ == "__main__":
    FlashlightApp().run()
