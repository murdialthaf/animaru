import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from animaru.utils.config import load_config
from animaru.utils.history import mark_episode_watched
from animaru.utils.player import play_in_mpv
from animaru.utils.series import group_search_results, search_with_images
from animaru.windows.detail_view import DetailView
from animaru.windows.homepage import Homepage

CARD_CSS = """
    .animaru-window { background: #0a0a14; }
    .animaru-header { background: #12102a; border: none; box-shadow: none; }
    .animaru-header-title { color: #c8b8ff; font-weight: 700; font-size: 1.1em; letter-spacing: 1px; }

    .category-title {
        color: #e0d8ff;
        font-size: 1.3em;
        font-weight: 700;
        letter-spacing: -0.3px;
    }
    .category-scroll {
        border: none;
        background: transparent;
    }
    .category-scroll scrollbar { background: transparent; }
    .category-scroll scrollbar slider { background: #2a2860; border-radius: 4px; min-height: 4px; }

    .anime-card { background: transparent; border-radius: 12px; }
    .anime-card-outer {
        background: #16142e;
        border-radius: 12px;
        transition: all 200ms ease;
    }
    .anime-card-outer:hover {
        background: #1e1c42;
        box-shadow: 0 8px 24px alpha(#7c3aed, 0.2);
    }
    .card-title {
        color: #d0c8f0;
        font-weight: 600;
        font-size: 0.85em;
    }
    .card-initial { font-size: 48px; font-weight: 700; color: rgba(255,255,255,0.15); }
    .card-image { border-radius: 8px 8px 0 0; background: transparent; }
    .card-progress-fill { background: #7c3aed; min-height: 3px; }
    .card-progress-text { color: #7c3aed; font-size: 0.7em; font-weight: 600; }
    .card-ep-label { color: #6a68a0; font-size: 0.7em; }

    .detail-hero {
        background: #12102a;
        border-bottom: 1px solid #1e1c40;
    }
    .hero-title {
        color: #f0e8ff;
        font-size: 2em;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    .hero-meta { color: #7a78b0; font-size: 0.9em; }
    .hero-poster { border-radius: 12px; }
    .hero-gradient { background: linear-gradient(180deg, transparent, #0a0a14); }

    .synopsis-text { color: #a098c8; font-size: 0.9em; line-height: 1.5; }
    .section-header {
        color: #e0d8ff;
        font-size: 1.2em;
        font-weight: 700;
    }

    .episode-card {
        background: #12102a;
        border-radius: 10px;
        padding: 8px 12px;
        transition: all 150ms ease;
    }
    .episode-card:hover { background: #1a1840; }
    .episode-card-current { border: 1px solid #3a3890; }
    .episode-number {
        color: #7c3aed;
        font-weight: 700;
        font-size: 1.1em;
        min-width: 36px;
    }
    .episode-title { color: #c8c0e8; font-size: 0.9em; }
    .play-button {
        background: #7c3aed;
        color: white;
        border-radius: 20px;
        padding: 4px 12px;
        min-width: 0;
    }
    .play-button:hover { background: #6d28d9; }

    .pill-button {
        background: #1a1838;
        color: #c8b8ff;
        border: 1px solid #2a2860;
        border-radius: 20px;
        padding: 4px 16px;
        font-weight: 600;
    }
    .pill-button:hover { background: #242250; border-color: #3a3890; }

    .genre-tag {
        background: alpha(#7c3aed, 0.1);
        color: #7c3aed;
        border: none;
        border-radius: 12px;
        padding: 2px 12px;
        font-size: 0.75em;
        font-weight: 600;
    }

    .back-button {
        background: transparent;
        color: #c8b8ff;
        border: none;
        border-radius: 8px;
        padding: 4px 8px;
    }
    .back-button:hover { background: alpha(currentColor, 0.1); }

    .search-button {
        background: transparent;
        color: #c8b8ff;
        border: none;
        border-radius: 8px;
        padding: 4px 8px;
    }
    .search-button:hover { background: alpha(currentColor, 0.1); }

    .homepage-scroll { background: #0a0a14; }
    .homepage-scroll scrollbar { background: transparent; }
    .homepage-scroll scrollbar slider { background: #2a2860; border-radius: 4px; min-width: 6px; }

    .search-overlay {
        background: alpha(#0a0a14, 0.97);
        padding: 80px 32px;
    }
    .search-overlay-entry {
        background: #1a1838;
        color: #e0d8ff;
        border: 2px solid #2a2860;
        border-radius: 16px;
        font-size: 1.5em;
        padding: 16px 24px;
        min-height: 60px;
    }
    .search-overlay-entry:focus { border-color: #7c3aed; }
    .search-overlay-results { margin-top: 20px; }

    .settings-dialog { background: #0a0a14; }
    .settings-row { margin: 8px 24px; }
    .settings-label { color: #c8c0e8; font-size: 0.95em; }
    .settings-switch { margin-left: 12px; }
"""


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_default_size(1100, 720)
        self.set_title("Animaru")
        self.add_css_class("animaru-window")

        self._provider = None
        self._search_overlay = None
        self._mauth_server = None
        self._init_provider()
        self._load_css()
        self._prepare_actions()
        self._build_ui()
        self._setup_shortcuts()

    def _get_icon_path(self):
        import os
        for path in (
            "/usr/share/icons/hicolor/scalable/apps/animaru.svg",
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "data", "icons", "animaru.svg",
            ),
        ):
            if os.path.exists(path):
                return path
        return ""

    def _load_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(CARD_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _init_provider(self):
        try:
            from anipy_api.provider import get_provider
            self._provider = get_provider("allanime")
        except Exception as e:
            print(f"[App] Provider init failed: {e}")

    def _build_ui(self):
        toolbar_view = Adw.ToolbarView()
        self._header = Adw.HeaderBar()
        self._header.add_css_class("animaru-header")
        self._header.set_decoration_layout(":close")

        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_box.set_halign(Gtk.Align.CENTER)

        self._back_btn = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        self._back_btn.add_css_class("back-button")
        self._back_btn.set_visible(False)
        self._back_btn.connect("clicked", self._on_back)
        self._header.pack_start(self._back_btn)

        icon_path = self._get_icon_path()
        if icon_path:
            title_icon = Gtk.Image.new_from_file(icon_path)
        else:
            title_icon = Gtk.Image.new_from_icon_name("animaru-symbolic")
        title_icon.set_pixel_size(22)
        title_box.append(title_icon)

        title_label = Gtk.Label(label="Animaru")
        title_label.add_css_class("animaru-header-title")
        title_box.append(title_label)
        self._header.set_title_widget(title_box)

        self._search_btn = Gtk.Button.new_from_icon_name("system-search-symbolic")
        self._search_btn.add_css_class("search-button")
        self._search_btn.connect("clicked", self._toggle_search)
        self._header.pack_end(self._search_btn)

        menu_model = Gio.Menu()
        menu_model.append("MyAnimeList Sync", "app.mal-sync")
        menu_model.append("Settings", "app.settings")
        menu_model.append("About Animaru", "app.about")

        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_btn.set_menu_model(menu_model)
        self._header.pack_end(menu_btn)

        toolbar_view.add_top_bar(self._header)

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self._stack.set_transition_duration(200)

        self._homepage = Homepage(
            on_navigate_to_detail=self._show_detail,
            on_navigate_to_search=self._open_search,
        )
        self._stack.add_named(self._homepage, "homepage")

        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_child(self._stack)
        toolbar_view.set_content(self._toast_overlay)
        self.set_child(toolbar_view)

    def _prepare_actions(self):
        app = self.get_application()

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        app.add_action(about_action)

        search_action = Gio.SimpleAction.new("search", None)
        search_action.connect("activate", lambda *_: self._toggle_search())
        app.add_action(search_action)

        back_action = Gio.SimpleAction.new("back", None)
        back_action.connect("activate", lambda *_: self._on_back())
        app.add_action(back_action)

        mal_action = Gio.SimpleAction.new("mal-sync", None)
        mal_action.connect("activate", self._on_mal_sync)
        app.add_action(mal_action)

        settings_action = Gio.SimpleAction.new("settings", None)
        settings_action.connect("activate", self._on_settings)
        app.add_action(settings_action)

    def _on_mal_sync(self, *_):
        from animaru.utils.mal_client import is_authenticated, logout, get_auth_url, \
            start_auth_server, exchange_code, get_pkce_verifier

        if is_authenticated():
            logout()
            self._show_toast("Logged out of MyAnimeList")
            return

        from animaru.utils.mal_client import _CallbackHandler
        import http.server

        server = http.server.HTTPServer(("127.0.0.1", 8543), _CallbackHandler)
        server.code = None

        def _serve():
            server.timeout = 120
            while server.code is None:
                server.handle_request()

        thread = threading.Thread(target=_serve, daemon=True)
        thread.start()

        import webbrowser
        webbrowser.open(get_auth_url())

        self._show_toast("Waiting for MAL authorization...")

        def _check():
            import time
            time.sleep(0.5)
            if server.code:
                verifier = get_pkce_verifier()
                if verifier:
                    token = exchange_code(server.code, verifier)
                    GLib.idle_add(
                        lambda: self._show_toast(
                            "MyAnimeList synced!" if token else "MAL authorization failed"
                        )
                    )
                return
            _check()

        threading.Thread(target=_check, daemon=True).start()

    def _on_settings(self, *_):
        dialog = Adw.PreferencesWindow()
        dialog.set_transient_for(self)
        dialog.set_default_size(500, 400)

        page = Adw.PreferencesPage()
        page.set_title("Settings")
        page.set_name("settings")

        group = Adw.PreferencesGroup()
        group.set_title("Playback")

        skip_row = Adw.ActionRow()
        skip_row.set_title("Skip Intro/Outro")
        skip_row.set_subtitle("Auto-detect and skip opening and ending sequences")
        skip_sw = Gtk.Switch()
        skip_sw.set_valign(Gtk.Align.CENTER)
        skip_sw.set_active(load_config().get("skip_intro", True))
        skip_sw.connect("notify::active", self._on_setting_toggle, "skip_intro")
        skip_row.add_suffix(skip_sw)
        skip_row.set_activatable_widget(skip_sw)
        group.add(skip_row)

        mal_group = Adw.PreferencesGroup()
        mal_group.set_title("MyAnimeList")

        from animaru.utils.mal_client import is_authenticated
        mal_row = Adw.ActionRow()
        mal_row.set_title("Sync Progress")
        mal_row.set_subtitle("Automatically sync watched episodes to MAL")
        mal_sw = Gtk.Switch()
        mal_sw.set_valign(Gtk.Align.CENTER)
        mal_sw.set_active(load_config().get("mal_sync", True) and is_authenticated())
        mal_sw.set_sensitive(is_authenticated())
        mal_sw.connect("notify::active", self._on_setting_toggle, "mal_sync")
        mal_row.add_suffix(mal_sw)
        mal_row.set_activatable_widget(mal_sw)
        mal_group.add(mal_row)

        page.add(group)
        page.add(mal_group)
        dialog.add(page)
        dialog.present()

    def _on_setting_toggle(self, switch, _pspec, key):
        cfg = load_config()
        cfg[key] = switch.get_active()
        from animaru.utils.config import save_config
        save_config(cfg)

    def _setup_shortcuts(self):
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

    def _on_key_pressed(self, _ctrl, keyval, _keycode, state):
        ctrl = state & Gdk.ModifierType.CONTROL_MASK
        if ctrl and keyval == Gdk.KEY_f:
            self._toggle_search()
            return True
        if keyval == Gdk.KEY_Escape:
            if self._search_overlay \
                    and self._stack.get_visible_child_name() == "search":
                self._close_search()
                return True
            elif self._stack.get_visible_child_name() != "homepage":
                self._go_home()
                return True
        return False

    def _show_detail(self, series):
        detail = DetailView(
            series=series,
            on_play=self._play_episode,
            on_back=self._go_home,
        )
        page_name = f"detail_{series.primary_id}"

        existing = self._stack.get_child_by_name(page_name)
        if existing:
            existing.refresh()
            self._stack.set_visible_child_name(page_name)
        else:
            self._stack.add_named(detail, page_name)
            self._stack.set_visible_child_name(page_name)

        self._back_btn.set_visible(True)
        self._search_btn.set_visible(False)

    def _go_home(self):
        self._stack.set_visible_child_name("homepage")
        self._back_btn.set_visible(False)
        self._search_btn.set_visible(True)

    def _on_back(self, *_):
        self._go_home()

    def _play_episode(self, anime_id: str, episode: int, lang):
        if not self._provider:
            return

        skip_intro_enabled = load_config().get("skip_intro", True)

        def _do_play():
            try:
                streams = self._provider.get_video(anime_id, episode, lang)
                if not streams:
                    return
                stream = streams[0]
                url = stream.url
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
                }
                if hasattr(stream, "referrer") and stream.referrer:
                    headers["Referer"] = stream.referrer

                info = None
                try:
                    info = self._provider.get_info(anime_id)
                except Exception:
                    pass

                title = info.name if info and hasattr(info, "name") else anime_id
                poster = info.image if info and hasattr(info, "image") else ""
                total = 0
                try:
                    eps = self._provider.get_episodes(anime_id, lang)
                    total = len(eps) if eps else 0
                except Exception:
                    pass

                chapters = None
                start_time = None
                if skip_intro_enabled:
                    chapters, start_time = self._fetch_skip_data(title, episode)

                play_in_mpv(
                    url=url,
                    headers=headers if headers else None,
                    title=f"{title} - Ep {episode}",
                    chapters=chapters,
                    start_time=start_time,
                )

                GLib.idle_add(
                    mark_episode_watched,
                    anime_id,
                    title,
                    1,
                    episode,
                    total,
                    poster,
                )

                if load_config().get("mal_sync", True):
                    self._sync_to_mal(title, episode)

                has_next = episode < total
                if has_next:
                    GLib.idle_add(
                        self._show_next_toast, title, anime_id, episode + 1, lang
                    )

            except Exception as e:
                print(f"[Playback] Error: {e}")

        threading.Thread(target=_do_play, daemon=True).start()

    def _fetch_skip_data(self, title: str, episode: int):
        from animaru.utils.skip_detector import (
            search_mal_id,
            fetch_skip_times,
            generate_chapters_file,
        )

        try:
            mal_id = search_mal_id(title)
            if not mal_id:
                return None, None

            skip_results = fetch_skip_times(mal_id, episode)
            if not skip_results:
                return None, None

            chapters = generate_chapters_file(skip_results)

            start_time = None
            for r in skip_results:
                if r.get("type") == "op":
                    interval = r.get("interval", {})
                    start_time = interval.get("endTime")
                    break

            GLib.idle_add(
                self._show_toast,
                f"⏭ Skip detected for Episode {episode}",
            )
            return chapters, start_time
        except Exception:
            return None, None

    def _sync_to_mal(self, title: str, episode: int):
        from animaru.utils.mal_client import is_authenticated, update_anime_progress
        from animaru.utils.skip_detector import search_mal_id

        if not is_authenticated():
            return

        try:
            mal_id = search_mal_id(title)
            if not mal_id:
                return
            ok = update_anime_progress(mal_id, episode)
            if ok:
                GLib.idle_add(
                    self._show_toast, f"MAL synced: Ep {episode} of {title}"
                )
        except Exception as e:
            print(f"[MAL Sync] Error: {e}")

    def _show_next_toast(self, title, anime_id, next_ep, lang):
        toast = Adw.Toast.new(f"Up next: Ep {next_ep} of {title}")
        toast.set_timeout(6)
        toast.set_button_label("▶ Play")
        toast.connect(
            "button-clicked", lambda *_: self._play_episode(anime_id, next_ep, lang)
        )
        self._toast_overlay.add_toast(toast)

    def _show_toast(self, msg: str):
        toast = Adw.Toast.new(msg)
        toast.set_timeout(4)
        self._toast_overlay.add_toast(toast)

    def _toggle_search(self, *_):
        if self._search_overlay and self._search_overlay.get_visible():
            self._close_search()
        else:
            self._open_search()

    def _open_search(self):
        if not self._search_overlay:
            self._search_overlay = self._build_search_overlay()
            self._stack.add_named(self._search_overlay, "search")
        self._stack.set_visible_child_name("search")

    def _close_search(self):
        self._stack.set_visible_child_name("homepage")

    def _build_search_overlay(self):
        overlay = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        overlay.add_css_class("search-overlay")

        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_tightening_threshold(600)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)

        entry = Gtk.SearchEntry()
        entry.set_hexpand(True)
        entry.add_css_class("search-overlay-entry")
        entry.set_placeholder_text("Search anime...")
        entry.connect("activate", self._on_search)
        inner.append(entry)

        self._search_entry = entry
        self._search_results_box = Gtk.FlowBox()
        self._search_results_box.set_max_children_per_line(6)
        self._search_results_box.set_min_children_per_line(2)
        self._search_results_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._search_results_box.set_homogeneous(True)
        self._search_results_box.set_column_spacing(12)
        self._search_results_box.set_row_spacing(12)
        self._search_results_box.add_css_class("search-overlay-results")
        self._search_results_box.connect(
            "child-activated", self._on_search_result
        )
        inner.append(self._search_results_box)

        clamp.set_child(inner)
        overlay.append(clamp)
        return overlay

    def _on_search(self, entry):
        query = entry.get_text().strip()
        if len(query) < 2:
            return

        def _search():
            try:
                results = search_with_images(query)
                GLib.idle_add(self._display_search_results, results)
            except Exception as e:
                GLib.idle_add(self._show_search_error, str(e))

        threading.Thread(target=_search, daemon=True).start()

    def _display_search_results(self, results):
        child = self._search_results_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._search_results_box.remove(child)
            child = nxt

        from animaru.widgets.anime_card import AnimeCard

        for entry in results[:30]:
            card = AnimeCard(entry, poster_url=entry.image)
            self._search_results_box.append(card)

        return False

    def _show_search_error(self, msg):
        child = self._search_results_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._search_results_box.remove(child)
            child = nxt
        label = Gtk.Label(label=f"Search failed:\n{msg}")
        label.add_css_class("dim-label")
        label.set_margin_top(40)
        self._search_results_box.append(label)
        return False

    def _on_search_result(self, _flowbox, child):
        card = child.get_child() if hasattr(child, "get_child") else child
        if hasattr(card, "series"):
            self._show_detail(card.series)

    def _on_about(self, *_):
        dialog = Adw.AboutDialog(
            application_name="Animaru",
            version="0.1.0",
            developer_name="Murdi",
            license_type=Gtk.License.GPL_3_0,
            comments="A custom-themed GTK4 GUI for watching and downloading anime.\n"
                      "Powered by anipy-api.",
            website="https://github.com/murdi/animaru",
            issue_url="https://github.com/murdi/animaru/issues",
        )
        dialog.present(self)
