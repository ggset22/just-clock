# -*- coding: utf-8 -*-
"""
Простое приложение "Часы" для Android на Kivy.

Экран 1 (Clock)    — большие цифровые часы на фоне (цвет или картинка).
Экран 2 (Settings) — смена цвета фона, картинки фона, цвета часов,
                      включение/выключение отображения секунд.

Все настройки сохраняются в JSON-файле в папке данных приложения,
поэтому переживают перезапуск.
"""

import os
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.storage.jsonstore import JsonStore
from kivy.uix.screenmanager import Screen, ScreenManager, FadeTransition
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.switch import Switch
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.image import Image as KivyImage
from kivy.properties import ListProperty, StringProperty, BooleanProperty

# Запрашиваем разрешения на Android (чтение картинок из галереи)
try:
    from android.permissions import request_permissions, Permission  # noqa
    request_permissions([
        Permission.READ_EXTERNAL_STORAGE,
        Permission.READ_MEDIA_IMAGES,
    ])
except Exception:
    pass

# Стартовая папка для выбора картинки
try:
    from android.storage import primary_external_storage_path
    START_PATH = primary_external_storage_path()
except Exception:
    START_PATH = os.path.expanduser("~")

DEFAULT_SETTINGS = {
    "bg_color": [0.05, 0.05, 0.08, 1],
    "clock_color": [1, 1, 1, 1],
    "bg_image": "",
    "show_seconds": True,
}


class SettingsManager:
    """Обёртка над JsonStore для хранения настроек."""

    def __init__(self, app_dir):
        path = os.path.join(app_dir, "clock_settings.json")
        self.store = JsonStore(path)
        if not self.store.exists("settings"):
            self.store.put("settings", **DEFAULT_SETTINGS)

    def get(self):
        data = dict(DEFAULT_SETTINGS)
        data.update(self.store.get("settings"))
        return data

    def update(self, **kwargs):
        data = self.get()
        data.update(kwargs)
        self.store.put("settings", **data)


class ClockScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        self.add_widget(self.layout)

        # Фон: либо картинка, либо закрашенный прямоугольник
        self.bg_image_widget = KivyImage(allow_stretch=True, keep_ratio=False,
                                          size_hint=(1, 1), pos=(0, 0))
        self.layout.add_widget(self.bg_image_widget)

        with self.layout.canvas.before:
            self.bg_color_instr = Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)

        self.layout.bind(pos=self._sync_rect, size=self._sync_rect)

        # Циферблат
        self.time_label = Label(
            text="00:00:00",
            font_size="64sp",
            bold=True,
            size_hint=(1, 1),
            halign="center",
            valign="middle",
        )
        self.time_label.bind(size=self._update_text_align)
        self.layout.add_widget(self.time_label)

        # Кнопка настроек (шестерёнка) в углу
        self.settings_btn = Button(
            text="⚙",
            font_size="26sp",
            size_hint=(None, None),
            size=("56dp", "56dp"),
            pos_hint={"right": 0.98, "top": 0.98},
            background_color=(0, 0, 0, 0.35),
        )
        self.settings_btn.bind(on_release=self.open_settings)
        self.layout.add_widget(self.settings_btn)

        self._clock_event = None

    def _update_text_align(self, *_):
        self.time_label.text_size = self.time_label.size

    def _sync_rect(self, *_):
        self.bg_rect.pos = self.layout.pos
        self.bg_rect.size = self.layout.size
        self.bg_image_widget.size = self.layout.size
        self.bg_image_widget.pos = self.layout.pos

    def open_settings(self, *_):
        self.manager.current = "settings"

    def on_enter(self):
        self.refresh_from_settings()
        self._tick(0)
        self._clock_event = Clock.schedule_interval(self._tick, 1)

    def on_leave(self):
        if self._clock_event:
            self._clock_event.cancel()
            self._clock_event = None

    def refresh_from_settings(self):
        app = App.get_running_app()
        data = app.settings_manager.get()

        # Цвет часов
        self.time_label.color = data["clock_color"]

        # Фон: картинка или цвет
        if data["bg_image"] and os.path.isfile(data["bg_image"]):
            self.bg_image_widget.source = data["bg_image"]
            self.bg_image_widget.opacity = 1
            self.bg_color_instr.rgba = (0, 0, 0, 0)
        else:
            self.bg_image_widget.opacity = 0
            self.bg_color_instr.rgba = data["bg_color"]

        self.show_seconds = data["show_seconds"]

    def _tick(self, _dt):
        app = App.get_running_app()
        show_seconds = app.settings_manager.get()["show_seconds"]
        fmt = "%H:%M:%S" if show_seconds else "%H:%M"
        self.time_label.text = datetime.now().strftime(fmt)


class ImageChooserPopup(Popup):
    def __init__(self, on_choose, **kwargs):
        super().__init__(**kwargs)
        self.title = "Выберите картинку"
        self.size_hint = (0.9, 0.9)
        self.on_choose = on_choose

        root = BoxLayout(orientation="vertical", spacing="6dp", padding="6dp")
        self.chooser = FileChooserIconView(
            path=START_PATH if os.path.isdir(START_PATH) else os.path.expanduser("~"),
            filters=["*.png", "*.jpg", "*.jpeg", "*.bmp", "*.PNG", "*.JPG", "*.JPEG"],
        )
        root.add_widget(self.chooser)

        buttons = BoxLayout(size_hint=(1, None), height="48dp", spacing="6dp")
        choose_btn = Button(text="Выбрать")
        cancel_btn = Button(text="Отмена")
        choose_btn.bind(on_release=self._choose)
        cancel_btn.bind(on_release=self.dismiss)
        buttons.add_widget(choose_btn)
        buttons.add_widget(cancel_btn)
        root.add_widget(buttons)

        self.content = root

    def _choose(self, *_):
        if self.chooser.selection:
            self.on_choose(self.chooser.selection[0])
        self.dismiss()


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        outer = BoxLayout(orientation="vertical")

        scroll = ScrollView(size_hint=(1, 1))
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing="12dp",
                             padding="12dp")
        content.bind(minimum_height=content.setter("height"))

        # --- Цвет фона ---
        content.add_widget(Label(text="Цвет фона", size_hint_y=None, height="30dp",
                                  bold=True))
        self.bg_picker = ColorPicker(size_hint_y=None, height="380dp")
        self.bg_picker.bind(color=self._on_bg_color)
        content.add_widget(self.bg_picker)

        img_row = BoxLayout(size_hint_y=None, height="48dp", spacing="8dp")
        pick_img_btn = Button(text="Выбрать картинку фона")
        pick_img_btn.bind(on_release=self.choose_image)
        clear_img_btn = Button(text="Убрать картинку")
        clear_img_btn.bind(on_release=self.clear_image)
        img_row.add_widget(pick_img_btn)
        img_row.add_widget(clear_img_btn)
        content.add_widget(img_row)

        self.image_status = Label(text="Картинка фона не выбрана", size_hint_y=None,
                                   height="24dp", font_size="12sp")
        content.add_widget(self.image_status)

        # --- Цвет часов ---
        content.add_widget(Label(text="Цвет часов", size_hint_y=None, height="30dp",
                                  bold=True))
        self.clock_picker = ColorPicker(size_hint_y=None, height="380dp")
        self.clock_picker.bind(color=self._on_clock_color)
        content.add_widget(self.clock_picker)

        # --- Показывать секунды ---
        sec_row = BoxLayout(size_hint_y=None, height="48dp", spacing="8dp")
        sec_row.add_widget(Label(text="Показывать секунды"))
        self.seconds_switch = Switch(active=True)
        self.seconds_switch.bind(active=self._on_seconds_switch)
        sec_row.add_widget(self.seconds_switch)
        content.add_widget(sec_row)

        scroll.add_widget(content)
        outer.add_widget(scroll)

        back_btn = Button(text="Назад", size_hint=(1, None), height="52dp")
        back_btn.bind(on_release=self.go_back)
        outer.add_widget(back_btn)

        self.add_widget(outer)

    def on_enter(self):
        app = App.get_running_app()
        data = app.settings_manager.get()
        self.bg_picker.color = data["bg_color"]
        self.clock_picker.color = data["clock_color"]
        self.seconds_switch.active = data["show_seconds"]
        if data["bg_image"]:
            self.image_status.text = "Картинка: " + os.path.basename(data["bg_image"])
        else:
            self.image_status.text = "Картинка фона не выбрана (используется цвет)"

    def _on_bg_color(self, _instance, value):
        App.get_running_app().settings_manager.update(bg_color=list(value))

    def _on_clock_color(self, _instance, value):
        App.get_running_app().settings_manager.update(clock_color=list(value))

    def _on_seconds_switch(self, _instance, value):
        App.get_running_app().settings_manager.update(show_seconds=bool(value))

    def choose_image(self, *_):
        popup = ImageChooserPopup(on_choose=self._image_chosen)
        popup.open()

    def _image_chosen(self, path):
        App.get_running_app().settings_manager.update(bg_image=path)
        self.image_status.text = "Картинка: " + os.path.basename(path)

    def clear_image(self, *_):
        App.get_running_app().settings_manager.update(bg_image="")
        self.image_status.text = "Картинка фона не выбрана (используется цвет)"

    def go_back(self, *_):
        clock_screen = self.manager.get_screen("clock")
        clock_screen.refresh_from_settings()
        self.manager.current = "clock"


class ClockApp(App):
    def build(self):
        Window.softinput_mode = "below_target"
        self.settings_manager = SettingsManager(self.user_data_dir)

        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(ClockScreen(name="clock"))
        sm.add_widget(SettingsScreen(name="settings"))
        return sm


if __name__ == "__main__":
    ClockApp().run()
