import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GObject", "2.0")
from gi.repository import GObject, Gtk


class CategoryRow(Gtk.Box):
    __gsignals__ = {
        "card-activated": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "load-more": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self, title: str):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self.set_margin_top(20)
        self._loading_more = False
        self._has_more = True

        self.title_label = Gtk.Label(label=title)
        self.title_label.set_halign(Gtk.Align.START)
        self.title_label.set_xalign(0)
        self.title_label.add_css_class("category-title")
        self.title_label.set_margin_bottom(8)
        self.append(self.title_label)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.EXTERNAL, Gtk.PolicyType.NEVER)
        self.scroll.set_propagate_natural_width(True)
        self.scroll.add_css_class("category-scroll")

        self.card_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=6
        )
        self.card_box.set_margin_bottom(4)
        self.card_box.set_halign(Gtk.Align.START)

        self.spacer = Gtk.Box()
        self.spacer.set_hexpand(True)
        self.card_box.append(self.spacer)

        self.scroll.set_child(self.card_box)
        self.append(self.scroll)

        self._adj = self.scroll.get_hadjustment()
        self._adj.connect("value-changed", self._on_scroll)

    def _on_scroll(self, adj):
        if self._loading_more or not self._has_more:
            return
        near_end = adj.get_value() + adj.get_page_size() >= adj.get_upper() - 300
        if near_end:
            self.emit("load-more", self)

    def add_card(self, card):
        gesture = Gtk.GestureClick()
        gesture.connect("pressed", self._on_card_pressed, card)
        card.add_controller(gesture)
        prev = self.spacer.get_prev_sibling()
        self.card_box.insert_child_after(card, prev)

    def _on_card_pressed(self, _gesture, _n_press, _x, _y, card):
        self.emit(
            "card-activated",
            card.result if hasattr(card, "result") else card.series,
        )

    def clear(self):
        child = self.card_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.card_box.remove(child)
            child = nxt
        self.card_box.append(self.spacer)
