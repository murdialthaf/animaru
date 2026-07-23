import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gio", "2.0")

from gi.repository import Adw, GdkPixbuf, Gio, GLib, Gtk

from anipy_api.provider import LanguageTypeEnum, get_provider

from animaru_app.utils.history import (
    get_progress,
    in_watchlist,
    toggle_watchlist,
)



class EpisodeCard(Gtk.Box):
    def __init__(self, episode: int, anime_id: str, lang, on_play):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.episode = episode
        self.anime_id = anime_id
        self.lang = lang
        self._on_play = on_play

        self.add_css_class("episode-card")
        self.set_margin_bottom(4)

        num_label = Gtk.Label(label=f"{episode}")
        num_label.set_size_request(40, -1)
        num_label.set_halign(Gtk.Align.CENTER)
        num_label.add_css_class("episode-number")
        self.append(num_label)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)
        title = Gtk.Label(label=f"Episode {episode}")
        title.set_halign(Gtk.Align.START)
        title.set_xalign(0)
        title.add_css_class("episode-title")
        info_box.append(title)
        self.append(info_box)

        play_btn = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        play_btn.add_css_class("play-button")
        play_btn.set_valign(Gtk.Align.CENTER)
        play_btn.connect("clicked", self._on_play_clicked)
        self.append(play_btn)

    def _on_play_clicked(self, _btn):
        self._on_play(self.anime_id, self.episode, self.lang)


class DetailView(Gtk.Box):
    def __init__(
        self, series, on_play: callable, on_back: callable
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._series = series
        self._on_play = on_play
        self._on_back = on_back
        self._provider = None
        self._info = None
        self._episodes = []
        self._lang = LanguageTypeEnum.SUB

        self._season_idx = 0

        self._init_provider()
        self._build_ui()
        self._load_data()

    def _init_provider(self):
        try:
            self._provider = get_provider("allanime")
        except Exception as e:
            print(f"[Detail] Provider init failed: {e}")

    def _build_ui(self):
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_vexpand(True)

        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.scroll.set_child(self.content)

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(48, 48)
        self.spinner.set_halign(Gtk.Align.CENTER)
        self.spinner.set_valign(Gtk.Align.CENTER)
        self.spinner.set_margin_top(80)
        self.spinner.start()
        self.content.append(self.spinner)

        self.ep_spinner = None

        self.append(self.scroll)

    @property
    def _current_season_id(self) -> str:
        return self._series.seasons[self._season_idx][0]

    def _load_data(self):
        if not self._provider:
            return
        thread = threading.Thread(target=self._fetch_info, daemon=True)
        thread.start()

    def _fetch_info(self):
        try:
            info = self._provider.get_info(self._series.primary_id)
            GLib.idle_add(self._display_info, info)
        except Exception as e:
            GLib.idle_add(self._show_error, str(e))

    def _load_episodes(self):
        if not self._provider:
            return
        thread = threading.Thread(target=self._fetch_episodes, daemon=True)
        thread.start()

    def _fetch_episodes(self):
        try:
            eps = self._provider.get_episodes(
                self._current_season_id, self._lang
            )
            GLib.idle_add(self._display_episodes, eps)
        except Exception:
            pass

    def _display_info(self, info):
        if self._info is not None:
            return False
        self._info = info
        self.content.remove(self.spinner)

        self._build_hero(info)
        self._build_actions(info)
        self._build_synopsis(info)
        self._build_season_selector()
        self._build_episodes_section()
        self._load_episodes()

        return False

    def _display_episodes(self, episodes):
        self._episodes = episodes
        self._rebuild_episodes()
        return False

    def _build_hero(self, info):
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        hero.add_css_class("detail-hero")
        hero.set_size_request(-1, 280)

        hero_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        hero_content.set_margin_start(32)
        hero_content.set_margin_end(32)
        hero_content.set_margin_top(60)
        hero_content.set_margin_bottom(20)
        hero_content.set_valign(Gtk.Align.END)
        hero_content.set_hexpand(True)

        poster_box = Gtk.Box()
        poster_box.set_size_request(140, 200)

        initial = info.name[0].upper() if info.name else "?"
        poster_label = Gtk.Label(label=initial)
        poster_label.set_halign(Gtk.Align.CENTER)
        poster_label.set_valign(Gtk.Align.CENTER)
        poster_label.set_vexpand(True)
        poster_label.add_css_class("hero-poster-placeholder")
        poster_box.append(poster_label)

        poster_prov = Gtk.CssProvider()
        poster_prov.load_from_string(
            ".hero-poster-placeholder { font-size: 56px; font-weight: 700; color: rgba(255,255,255,0.2); background: #1a1838; border-radius: 12px; }"
        )
        poster_label.get_style_context().add_provider(
            poster_prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        if hasattr(info, "image") and info.image:
            self._load_hero_image(info.image, poster_box, poster_label)

        hero_content.append(poster_box)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        text_box.set_hexpand(True)
        text_box.set_valign(Gtk.Align.END)

        title = Gtk.Label(label=self._series.name)
        title.set_halign(Gtk.Align.START)
        title.set_xalign(0)
        title.add_css_class("hero-title")
        text_box.append(title)

        meta = []
        if hasattr(info, "release_year") and info.release_year:
            meta.append(str(info.release_year))
        if hasattr(info, "status"):
            meta.append(str(info.status).split(".")[-1].title())
        if len(self._series.seasons) > 1:
            meta.append(f"{len(self._series.seasons)} Seasons")

        if meta:
            meta_label = Gtk.Label(label=" · ".join(meta))
            meta_label.set_halign(Gtk.Align.START)
            meta_label.set_xalign(0)
            meta_label.add_css_class("hero-meta")
            text_box.append(meta_label)

        hero_content.append(text_box)
        hero.append(hero_content)

        gradient = Gtk.Box()
        gradient.set_size_request(-1, 60)
        gradient.set_vexpand(True)
        gradient.add_css_class("hero-gradient")
        hero.append(gradient)

        self.content.append(hero)

    def _load_hero_image(self, url, container, placeholder):
        import urllib.request

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
                    stream, 280, 400, True
                )
                GLib.idle_add(self._set_hero_poster, pixbuf, container, placeholder)
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    def _set_hero_poster(self, pixbuf, container, placeholder):
        img = Gtk.Picture.new_for_pixbuf(pixbuf)
        img.set_size_request(140, 200)
        img.add_css_class("hero-poster")
        container.remove(placeholder)
        container.append(img)

    def _build_actions(self, info):
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_margin_start(32)
        actions.set_margin_end(32)
        actions.set_margin_top(12)
        actions.set_margin_bottom(8)

        wl_btn = Gtk.Button(label="☆ Watchlist")
        wl_btn.add_css_class("pill-button")
        if in_watchlist(self._series.primary_id):
            wl_btn.set_label("★ In Watchlist")
        wl_btn.connect("clicked", self._toggle_wl, wl_btn)
        actions.append(wl_btn)

        if hasattr(info, "genres") and info.genres:
            for g in info.genres[:4]:
                tag = Gtk.Button(label=g)
                tag.add_css_class("genre-tag")
                tag.set_sensitive(False)
                actions.append(tag)

        actions.append(Gtk.Label())
        self.content.append(actions)

    def _toggle_wl(self, _btn, btn):
        result = toggle_watchlist(self._series.primary_id)
        btn.set_label("★ In Watchlist" if result else "☆ Watchlist")

    def _build_synopsis(self, info):
        if not hasattr(info, "synopsis") or not info.synopsis:
            return
        import re

        clean = re.sub(r"<[^>]+>", "", info.synopsis).strip()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_margin_start(32)
        box.set_margin_end(32)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        label = Gtk.Label(label=clean)
        label.set_wrap(True)
        label.set_xalign(0)
        label.set_lines(5)
        label.add_css_class("synopsis-text")
        box.append(label)

        more_btn = Gtk.Button(label="Show more")
        more_btn.add_css_class("text-button")
        more_btn.set_halign(Gtk.Align.START)
        more_btn.connect("clicked", lambda *_: label.set_lines(0))
        box.append(more_btn)
        self.content.append(box)

    def _build_season_selector(self):
        if len(self._series.seasons) <= 1:
            return

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(32)
        box.set_margin_top(16)
        box.set_margin_bottom(8)

        label = Gtk.Label(label="Season:")
        label.add_css_class("section-header")
        box.append(label)

        labels = Gtk.StringList.new([l for _, l in self._series.seasons])
        self._season_dropdown = Gtk.DropDown(model=labels)
        self._season_dropdown.set_selected(0)

        self._season_dropdown.connect("notify::selected", self._on_season_change)
        box.append(self._season_dropdown)

        self.content.append(box)

    def _on_season_change(self, *_):
        self._season_idx = self._season_dropdown.get_selected()

        child = self._ep_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._ep_box.remove(child)
            child = nxt

        self.ep_spinner = Gtk.Spinner()
        self.ep_spinner.set_size_request(24, 24)
        self.ep_spinner.set_halign(Gtk.Align.CENTER)
        self.ep_spinner.set_margin_top(12)
        self.ep_spinner.set_margin_bottom(12)
        self.ep_spinner.start()
        self._episodes_section.append(self.ep_spinner)

        self._load_episodes()

    def _build_episodes_section(self):
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        section.set_margin_start(32)
        section.set_margin_end(32)
        section.set_margin_top(16)
        section.set_margin_bottom(32)

        header = Gtk.Label(label="Episodes")
        header.set_halign(Gtk.Align.START)
        header.set_xalign(0)
        header.add_css_class("section-header")
        header.set_margin_bottom(12)
        section.append(header)

        self._ep_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        section.append(self._ep_box)
        self._episodes_section = section
        self.content.append(section)

    def _rebuild_episodes(self):
        child = self._ep_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._ep_box.remove(child)
            child = nxt

        if self.ep_spinner and self.ep_spinner.get_parent():
            self.ep_spinner.get_parent().remove(self.ep_spinner)
            self.ep_spinner = None

        progress = None
        for sid, _ in self._series.seasons:
            p = get_progress(sid)
            if p:
                progress = p
                break
        last_watched = progress.get("episode", 0) if progress else 0

        for ep in self._episodes:
            card = EpisodeCard(
                ep, self._current_season_id, self._lang, self._on_play
            )
            if ep == last_watched:
                card.add_css_class("episode-card-current")
            self._ep_box.append(card)

    def refresh(self):
        self._load_data()

    def _show_error(self, msg: str):
        self.content.remove(self.spinner)
        label = Gtk.Label(label=f"Failed to load:\n{msg}")
        label.set_halign(Gtk.Align.CENTER)
        label.set_valign(Gtk.Align.CENTER)
        label.set_margin_top(80)
        label.add_css_class("dim-label")
        self.content.append(label)
        return False
