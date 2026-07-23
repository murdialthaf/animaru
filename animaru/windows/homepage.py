import threading
import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk

from anipy_api.provider import get_provider

from animaru.utils.history import get_continue_watching
from animaru.utils.series import group_history_entries, group_search_results, search_with_images
from animaru.widgets.anime_card import AnimeCard, ContinueWatchingCard
from animaru.widgets.category_row import CategoryRow

SEED_QUERIES = [
    ("Trending Now", "frieren"),
    ("Top Rated", "shingeki"),
    ("Popular", "spy x family"),
    ("Recently Added", "demon slayer"),
]

GENRE_QUERIES = [
    ("Action", "shonen"),
    ("Romance", "shoujo"),
    ("Comedy", "comedy"),
    ("Fantasy", "fantasy"),
    ("Sci-Fi", "mecha"),
    ("Horror", "horror"),
    ("Adventure", "adventure"),
    ("Classics", "bleach"),
]

INITIAL_BATCH = 20
LOAD_MORE_BATCH = 15


class Homepage(Gtk.Box):
    def __init__(self, on_navigate_to_detail, on_navigate_to_search):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.on_navigate = on_navigate_to_detail
        self.on_navigate_search = on_navigate_to_search
        self._provider = None
        self._loaded = False
        self._row_map: dict[str, CategoryRow] = {}

        self._init_provider()

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_vexpand(True)
        self.scroll.add_css_class("homepage-scroll")

        self.rows_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.scroll.set_child(self.rows_box)
        self.append(self.scroll)

        self._build_continue_watching()
        self._build_categories()

    def _init_provider(self):
        try:
            self._provider = get_provider("allanime")
        except Exception as e:
            print(f"[Homepage] Provider init failed: {e}")

    def _build_continue_watching(self):
        cw = get_continue_watching()
        if not cw:
            return
        row = CategoryRow("Continue Watching")
        row._has_more = False
        grouped = group_history_entries(cw)
        for entry in grouped:
            card = ContinueWatchingCard(entry)
            row.add_card(card)
        row.connect("card-activated", self._on_card)
        self.rows_box.append(row)

    def _build_categories(self):
        if not self._provider:
            return

        self._build_genre_banner()

        for title, query in SEED_QUERIES:
            self._make_category_row(title, query)

        thread = threading.Thread(
            target=self._load_all_sequential, daemon=True
        )
        thread.start()

    def _make_category_row(self, title, query):
        row = CategoryRow(title)
        row._query = query
        row._offset = 0
        row._all_results = None
        row._has_more = True

        spinner = Gtk.Spinner()
        spinner.set_size_request(24, 24)
        spinner.set_margin_top(12)
        spinner.set_margin_bottom(12)
        spinner.set_halign(Gtk.Align.CENTER)
        spinner.start()

        spinner_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        spinner_box.set_halign(Gtk.Align.CENTER)
        spinner_box.append(spinner)
        row.card_box.append(spinner_box)
        self.rows_box.append(row)

        row.connect("card-activated", self._on_card)
        row.connect("load-more", self._on_load_more)
        self._row_map[title] = row
        return row

    def _build_genre_banner(self):
        banner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        banner.set_margin_start(24)
        banner.set_margin_end(24)
        banner.set_margin_top(24)

        label = Gtk.Label(label="Browse by Genre")
        label.set_halign(Gtk.Align.START)
        label.set_xalign(0)
        label.add_css_class("category-title")
        label.set_margin_bottom(8)
        banner.append(label)

        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(8)
        flow.set_min_children_per_line(4)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_column_spacing(8)
        flow.set_row_spacing(8)
        flow.set_halign(Gtk.Align.START)

        for genre_name, _ in GENRE_QUERIES:
            btn = Gtk.Button(label=genre_name)
            btn.add_css_class("pill-button")
            btn.connect("clicked", self._on_genre_click, genre_name)
            flow.append(btn)

        banner.append(flow)
        self.rows_box.append(banner)

    def _on_genre_click(self, _btn, genre_name):
        query = next(
            (q for g, q in GENRE_QUERIES if g == genre_name), genre_name.lower()
        )
        title = genre_name
        row = self._make_category_row(title, query)

        thread = threading.Thread(
            target=self._fetch_single, args=(row, query), daemon=True
        )
        thread.start()
        GLib.idle_add(self._scroll_to_row, row)

    def _scroll_to_row(self, row):
        adj = self.scroll.get_vadjustment()
        y = row.get_allocation().y
        if y > 0:
            adj.set_value(y)
        else:
            GLib.timeout_add(50, self._scroll_to_row, row)
        return False

    def _load_all_sequential(self):
        for title, query in list(SEED_QUERIES):
            row = self._row_map.get(title)
            if not row:
                continue
            try:
                entries = search_with_images(query)
                GLib.idle_add(self._populate_row, row, entries)
            except Exception as e:
                print(f"[Homepage] Search failed for '{query}': {e}")
                GLib.idle_add(self._show_row_error, row, str(e))

    def _fetch_single(self, row, query):
        try:
            entries = search_with_images(query)
            GLib.idle_add(self._populate_row, row, entries)
        except Exception as e:
            print(f"[Homepage] Search failed for '{query}': {e}")
            GLib.idle_add(self._show_row_error, row, str(e))

    def _populate_row(self, row, entries):
        row._all_results = entries
        row.clear()

        if not row._all_results:
            row._has_more = False
            label = Gtk.Label(label="Nothing here yet")
            label.add_css_class("dim-label")
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            row.card_box.append(label)
            return False

        batch = row._all_results[:INITIAL_BATCH]
        row._offset = len(batch)
        row._has_more = row._offset < len(row._all_results)

        for entry in batch:
            card = AnimeCard(entry, poster_url=entry.image)
            row.add_card(card)

        row._loading_more = False
        return False

    def _on_load_more(self, row, _widget):
        if row._loading_more or not row._has_more or not row._all_results:
            return
        row._loading_more = True
        batch = row._all_results[
            row._offset : row._offset + LOAD_MORE_BATCH
        ]
        row._offset += len(batch)
        row._has_more = row._offset < len(row._all_results)
        for entry in batch:
            card = AnimeCard(entry, poster_url=entry.image)
            row.add_card(card)
        row._loading_more = False

    def _show_row_error(self, row, msg):
        row.clear()
        row._has_more = False
        label = Gtk.Label(label=f"Could not load: {msg}")
        label.add_css_class("dim-label")
        label.set_margin_top(8)
        label.set_margin_bottom(8)
        row.card_box.append(label)
        return False

    def _on_card(self, row, series_entry):
        self.on_navigate(series_entry)

    def refresh(self):
        if not self._loaded:
            self._loaded = True
        self._build_continue_watching()
