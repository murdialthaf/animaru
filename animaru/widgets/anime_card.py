import threading
import urllib.request

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")

from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk

from animaru.utils.series import SeriesEntry

COLORS = [
    "#7c3aed", "#ec4899", "#f59e0b", "#10b981",
    "#3b82f6", "#ef4444", "#8b5cf6", "#06b6d4",
    "#f97316", "#84cc16", "#d946ef", "#14b8a6",
]


class AnimeCard(Gtk.Box):
    def __init__(
        self,
        series: SeriesEntry,
        poster_url: str = "",
        progress: float = 0,
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.series = series
        self.poster_url = poster_url
        self._progress = progress

        self.set_size_request(150, 245)
        self.set_halign(Gtk.Align.START)
        self.add_css_class("anime-card")

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_size_request(150, -1)
        outer.add_css_class("anime-card-outer")

        self.poster = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.poster.set_size_request(150, 200)
        self.poster.set_halign(Gtk.Align.FILL)
        self.poster.set_valign(Gtk.Align.FILL)
        self.poster.set_overflow(Gtk.Overflow.HIDDEN)

        color = COLORS[hash(series.primary_id) % len(COLORS)]
        self.poster_css = Gtk.CssProvider()
        css = f".card-bg-{hash(series.primary_id) % 12} {{ background: {color}; }}"
        self.poster_css.load_from_string(css)
        self.poster.get_style_context().add_provider(
            self.poster_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.poster.add_css_class(f"card-bg-{hash(series.primary_id) % 12}")

        initial = series.name[0].upper() if series.name else "?"
        self.init_label = Gtk.Label(label=initial)
        self.init_label.set_halign(Gtk.Align.CENTER)
        self.init_label.set_valign(Gtk.Align.CENTER)
        self.init_label.set_vexpand(True)
        self.init_label.add_css_class("card-initial")
        init_provider = Gtk.CssProvider()
        init_provider.load_from_string(
            ".card-initial { font-size: 48px; font-weight: 700; color: rgba(255,255,255,0.3); }"
        )
        self.init_label.get_style_context().add_provider(
            init_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.poster.append(self.init_label)

        self.image_widget = None

        outer.append(self.poster)

        self.progress_bar = Gtk.Box()
        self.progress_bar.set_size_request(-1, 3)
        self.progress_fill = Gtk.Box()
        self.progress_fill.set_size_request(int(160 * progress), 3)
        self.progress_fill.add_css_class("card-progress-fill")
        self.progress_bar.append(self.progress_fill)
        outer.append(self.progress_bar)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        title_box.set_margin_start(6)
        title_box.set_margin_end(6)
        title_box.set_margin_top(6)
        title_box.set_margin_bottom(6)

        title_label = Gtk.Label(label=series.name)
        title_label.set_wrap(True)
        title_label.set_max_width_chars(14)
        title_label.set_width_chars(14)
        title_label.set_halign(Gtk.Align.FILL)
        title_label.set_xalign(0)
        title_label.set_lines(2)
        title_label.set_ellipsize(True)
        title_label.add_css_class("card-title")
        title_box.append(title_label)

        if len(series.seasons) > 1:
            badge = Gtk.Label(label=f"{len(series.seasons)} Seasons")
            badge.set_halign(Gtk.Align.START)
            badge.add_css_class("card-ep-label")
            title_box.append(badge)

        if progress > 0:
            prog_text = Gtk.Label(label=f"{int(progress * 100)}% watched")
            prog_text.set_halign(Gtk.Align.START)
            prog_text.add_css_class("card-progress-text")
            title_box.append(prog_text)

        outer.append(title_box)
        self.append(outer)

        if poster_url:
            self._load_image(poster_url)

    def _load_image(self, url: str):
        def _fetch():
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
                    },
                )
                resp = urllib.request.urlopen(req, timeout=10)
                data = resp.read()
                bytes_data = GLib.Bytes.new(data)
                stream = Gio.MemoryInputStream.new_from_bytes(bytes_data)
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                    stream, 320, 400, True
                )
                GLib.idle_add(self._set_image, pixbuf)
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    def _set_image(self, pixbuf):
        if self.image_widget:
            return
        self.image_widget = Gtk.Picture.new_for_pixbuf(pixbuf)
        self.image_widget.set_content_fit(Gtk.ContentFit.COVER)
        self.image_widget.set_halign(Gtk.Align.FILL)
        self.image_widget.set_valign(Gtk.Align.FILL)
        self.image_widget.set_hexpand(True)
        self.image_widget.set_vexpand(True)
        self.image_widget.set_size_request(-1, 200)
        self.image_widget.add_css_class("card-image")
        self.poster.remove(self.init_label)
        self.poster.append(self.image_widget)


class ContinueWatchingCard(AnimeCard):
    def __init__(self, entry: dict):
        from animaru.utils.series import SeriesEntry

        all_seasons = entry.get("all_seasons", [(entry["anime_id"], f"Season {entry.get('season', 1)}")])
        series = SeriesEntry(
            name=entry["anime_title"],
            seasons=all_seasons,
            primary_id=entry["anime_id"],
        )
        super().__init__(
            series,
            poster_url=entry.get("poster_url", ""),
            progress=entry.get("progress", 0),
        )
        self.entry = entry
        self.episode = entry.get("episode", 1)
        self.season = entry.get("season", 1)

        ep_label = Gtk.Label(
            label=f"S{self.season} · Ep {self.episode} / {entry.get('total_episodes', '?')}"
        )
        ep_label.set_halign(Gtk.Align.START)
        ep_label.add_css_class("card-ep-label")
        outer = self.get_first_child()
        if outer:
            title_box = outer.get_last_child()
            if title_box:
                title_box.append(ep_label)
