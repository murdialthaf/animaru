import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib

from animaru.windows.main_window import MainWindow


class AnimaruApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.animaru.app",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        GLib.set_application_name("Animaru")
        self.connect("startup", self.on_startup)
        self.connect("activate", self.on_activate)

    def on_startup(self, app):
        style = Adw.StyleManager.get_default()
        style.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

    def on_activate(self, app):
        win = self.props.active_window
        if not win:
            win = MainWindow(application=app)
        win.present()


def main():
    app = AnimaruApp()
    app.run(None)
