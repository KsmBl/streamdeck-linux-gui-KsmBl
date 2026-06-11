"""A text (terminal) user interface for the Stream Deck.

This is a zero-dependency, curses based front end for users who run without a
graphical desktop — over SSH, on a headless server, or from a bare TTY. It drives
a connected Stream Deck (running button actions, page switches, live tiles) and
lets you edit buttons, pages and brightness, all from the terminal.

It deliberately uses the standard library :mod:`curses` so it adds no runtime
dependency and works anywhere a terminal does. Graphical-only conveniences (the
icon picker, font/colour pickers, the on-deck game and focus-following auto
pages) live in the Qt UI; the text UI focuses on the actions a headless user
needs to keep their deck working.
"""

import curses
import os
import sys
import textwrap
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt

from streamdeck_ui.api import StreamDeckServer
from streamdeck_ui.config import (
    STATE_FILE,
    SWITCH_PAGE_AUTO,
    SWITCH_PAGE_LEAVE_AUTO,
    SWITCH_PAGE_NEXT,
    SWITCH_PAGE_PREVIOUS,
)
from streamdeck_ui.modules import actions, live
from streamdeck_ui.semaphore import Semaphore, SemaphoreAcquireError

# How often (in whole loop ticks of TICK_MS) to refresh live tiles like the clock
# and CPU usage. The render loop wakes every TICK_MS to poll the keyboard.
TICK_MS = 150
LIVE_REFRESH_TICKS = 7  # ~1 second

# The button fields the editor can change, as (hot key, label, getter, setter).
_EDIT_FIELDS: List[Tuple[str, str, str, str]] = [
    ("t", "Text", "get_button_text", "set_button_text"),
    ("c", "Command", "get_button_command", "set_button_command"),
    ("k", "Keys", "get_button_keys", "set_button_keys"),
    ("w", "Write", "get_button_write", "set_button_write"),
]

# --- colour pairs ---------------------------------------------------------
# Allocated in _init_colors(); referenced everywhere via _pair().
C_HEADER = 1  # the top title bar (text on the brand colour)
C_BRAND = 2  # the "STREAM DECK" wordmark
C_ACCENT = 3  # cyan accents (rules, highlights)
C_DIM = 4  # muted labels and empty tiles
C_FOOTER = 5  # the bottom hint bar
C_KEYCAP = 6  # a highlighted key "cap" in hints/editor
C_SELECTED = 7  # the selected tile's border
C_SELBG = 8  # the selected tile's interior fill
C_PANEL = 9  # detail-panel values
C_CMD = 10  # action accent: command
C_KEYS = 11  # action accent: key combo
C_WRITE = 12  # action accent: type text
C_PAGE = 13  # action accent: switch page
C_LIVE = 14  # action accent: live tile
C_BRIGHT = 15  # action accent: brightness / gauge
C_TEXT = 16  # a plain text-only key

# Per-action presentation: the order here is the classification priority.
_SWITCH_PAGE_LABELS = {
    SWITCH_PAGE_NEXT: "next page",
    SWITCH_PAGE_PREVIOUS: "prev page",
    SWITCH_PAGE_AUTO: "auto group",
    SWITCH_PAGE_LEAVE_AUTO: "leave auto",
}


def classify_button(api: StreamDeckServer, deck_id: str, page: int, button: int) -> Tuple[str, int, str]:
    """Describes a button as ``(glyph, colour_pair, label)`` for the grid.

    The glyph hints at the kind of action, the colour pair tints the tile, and
    the label is the most meaningful single line to show (the button text when
    set, otherwise a description of the action).
    """
    text_lines = api.get_button_text(deck_id, page, button).strip().splitlines()
    text = text_lines[0] if text_lines and text_lines[0] else ""

    source = api.get_button_live_source(deck_id, page, button)
    if live.is_live_source(source):
        return ("◷", C_LIVE, text or _live_label(source))
    if api.get_button_command(deck_id, page, button):
        return ("»", C_CMD, text or "command")
    keys = api.get_button_keys(deck_id, page, button)
    if keys:
        return ("⌨", C_KEYS, text or keys)
    if api.get_button_write(deck_id, page, button):
        return ("✎", C_WRITE, text or "type text")
    switch_page = api.get_button_switch_page(deck_id, page, button)
    if switch_page:
        return ("⇆", C_PAGE, text or _switch_page_label(switch_page))
    if api.get_button_change_brightness(deck_id, page, button):
        return ("☀", C_BRIGHT, text or "brightness")
    if api.get_button_icon(deck_id, page, button):
        return ("▦", C_TEXT, text or os.path.basename(api.get_button_icon(deck_id, page, button)))
    if text:
        return ("•", C_TEXT, text)
    return ("", C_DIM, "")


def _live_label(source: str) -> str:
    for key, label in live.LIVE_SOURCES:
        if key == source:
            return label
    return source


def _switch_page_label(switch_page: int) -> str:
    return _SWITCH_PAGE_LABELS.get(switch_page, f"page {switch_page}")


def deck_grid(api: StreamDeckServer, deck_id: str) -> Tuple[int, int]:
    """Returns the (rows, columns) layout of the given deck."""
    return api.get_deck_layout(deck_id)


class TextUI:
    """Holds the interactive state and renders the terminal interface."""

    def __init__(self, api: StreamDeckServer) -> None:
        self.api = api
        self.deck_id: Optional[str] = None
        self.selected = 0
        self.message = "Waiting for a Stream Deck…"
        self.show_help = False
        # Per-deck record of the last page the user navigated to manually, used to
        # resolve "leave auto" switch-page actions.
        self.last_manual_page: Dict[str, int] = {}
        self.last_focused_app: Optional[str] = None
        self._dirty = True

    # -- Stream Deck signal handlers (may run on background threads) ----------

    def on_attached(self, info: dict) -> None:
        serial = info["serial_number"]
        if self.deck_id is None:
            self.deck_id = serial
            self.message = f"Connected to {serial}"
        self._dirty = True

    def on_detached(self, serial: str) -> None:
        if self.deck_id == serial:
            remaining = [s for s in self.api.decks_by_serial if s != serial]
            self.deck_id = remaining[0] if remaining else None
            self.selected = 0
        self.message = f"{serial} disconnected"
        self._dirty = True

    def on_keypress(self, serial: str, key: int, state: bool) -> None:
        if not state:
            return
        if serial == self.deck_id:
            self.selected = key
        actions.execute_key_action(
            self.api,
            serial,
            key,
            resolve_switch_page=self._resolve_switch_page,
            on_warning=self._set_message,
        )
        self._dirty = True

    def _resolve_switch_page(self, deck_id: str, current_page: int, switch_page: int) -> Optional[int]:
        return actions.resolve_switch_page(
            self.api,
            deck_id,
            current_page,
            switch_page,
            last_manual_page=self.last_manual_page,
            last_focused_app=self.last_focused_app,
        )

    def _set_message(self, message: str) -> None:
        self.message = message
        self._dirty = True

    # -- Deck / page / button helpers ----------------------------------------

    def _layout(self) -> Tuple[int, int]:
        if self.deck_id is None:
            return (0, 0)
        try:
            return deck_grid(self.api, self.deck_id)
        except Exception:
            return (0, 0)

    def _button_count(self) -> int:
        rows, cols = self._layout()
        return rows * cols

    def _page(self) -> int:
        return self.api.get_page(self.deck_id) if self.deck_id else 0

    def _normal_pages(self) -> List[int]:
        if self.deck_id is None:
            return []
        pages = self.api.get_pages(self.deck_id)
        auto = self.api.get_auto_pages(self.deck_id)
        overlay = self.api.get_overlay_page(self.deck_id)
        return [p for p in pages if p not in auto and p != overlay]

    def _page_no(self) -> int:
        normal = self._normal_pages()
        current = self._page()
        return normal.index(current) + 1 if current in normal else 1

    def _change_page(self, step: int) -> None:
        if self.deck_id is None:
            return
        normal = self._normal_pages()
        if not normal:
            return
        current = self._page()
        index = normal.index(current) if current in normal else 0
        target = normal[(index + step) % len(normal)]
        self.api.set_page(self.deck_id, target)
        self.last_manual_page[self.deck_id] = target
        self.selected = min(self.selected, max(0, self._button_count() - 1))

    def _tabs(self) -> List[Tuple[int, str, bool]]:
        """The ordered tab strip as ``(page_id, label, is_auto)``.

        Normal pages come first (numbered), then the auto pages (the Home
        dashboard first, then one per application, alphabetically) so the whole
        configuration — including the Auto group — is reachable from the strip.
        The overlay page is a compositing layer, not a tab, so it is excluded.
        """
        deck_id = self.deck_id
        if deck_id is None:
            return []
        auto = self.api.get_auto_pages(deck_id)
        overlay = self.api.get_overlay_page(deck_id)
        home = self.api.get_home_page(deck_id)
        tabs: List[Tuple[int, str, bool]] = []
        for number, page in enumerate(self._normal_pages(), start=1):
            tabs.append((page, str(number), False))

        def auto_label(page: int) -> str:
            if page == home:
                return "home"
            return self.api.get_focus_app_for_page(deck_id, page) or "auto"

        autos = [page for page in auto if page != overlay]
        for page in sorted(autos, key=lambda p: ("" if p == home else auto_label(p).lower())):
            tabs.append((page, auto_label(page), True))
        return tabs

    def _change_tab(self, step: int) -> None:
        tabs = self._tabs()
        deck_id = self.deck_id
        if deck_id is None or not tabs:
            return
        ids = [tab[0] for tab in tabs]
        current = self._page()
        index = ids.index(current) if current in ids else 0
        target_index = (index + step) % len(ids)
        target, _label, is_auto = tabs[target_index]
        self.api.set_page(deck_id, target)
        if not is_auto:
            self.last_manual_page[deck_id] = target
        self.selected = min(self.selected, max(0, self._button_count() - 1))

    def _next_deck(self) -> None:
        serials = list(self.api.decks_by_serial)
        if not serials:
            return
        if self.deck_id in serials:
            self.deck_id = serials[(serials.index(self.deck_id) + 1) % len(serials)]
        else:
            self.deck_id = serials[0]
        self.selected = 0

    # -- Main loop -----------------------------------------------------------

    def run(self, stdscr: "curses.window") -> None:
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        stdscr.nodelay(False)
        stdscr.timeout(TICK_MS)
        _init_colors()

        tick = 0
        while True:
            self._render(stdscr)
            ch = stdscr.getch()
            tick += 1
            if tick >= LIVE_REFRESH_TICKS:
                tick = 0
                try:
                    self.api.refresh_live_buttons()
                except Exception:
                    pass
                self._dirty = True
            if ch == -1:
                continue
            if not self._handle_key(stdscr, ch):
                break

    def _handle_key(self, stdscr, ch: int) -> bool:
        """Processes one key press. Returns False to quit."""
        self._dirty = True
        if self.show_help:
            self.show_help = False
            return True
        if ch in (ord("q"), ord("Q")):
            return False
        if ch in (ord("?"), ord("/")):
            self.show_help = True
            return True
        if ch == curses.KEY_RESIZE:
            return True
        if self.deck_id is None:
            return True

        rows, cols = self._layout()
        count = rows * cols
        if ch in (curses.KEY_LEFT, ord("h")):
            if self.selected % cols > 0:
                self.selected -= 1
        elif ch in (curses.KEY_RIGHT, ord("l")):
            if self.selected % cols < cols - 1 and self.selected + 1 < count:
                self.selected += 1
        elif ch in (curses.KEY_UP, ord("k")):
            if self.selected - cols >= 0:
                self.selected -= cols
        elif ch in (curses.KEY_DOWN, ord("j")):
            if self.selected + cols < count:
                self.selected += cols
        elif ch in (ord("\t"), ord("]"), curses.KEY_NPAGE, ord(".")):
            self._change_tab(1)
        elif ch in (curses.KEY_BTAB, ord("["), curses.KEY_PPAGE, ord(",")):
            self._change_tab(-1)
        elif ch == ord("`"):
            self._next_deck()
        elif ch == ord("+"):
            self.api.set_brightness(self.deck_id, min(100, self.api.get_brightness(self.deck_id) + 10))
            self._set_message(f"Brightness {self.api.get_brightness(self.deck_id)}%")
        elif ch == ord("-"):
            self.api.set_brightness(self.deck_id, max(0, self.api.get_brightness(self.deck_id) - 10))
            self._set_message(f"Brightness {self.api.get_brightness(self.deck_id)}%")
        elif ch in (ord("\n"), curses.KEY_ENTER, ord("e")):
            self._edit_button(stdscr)
        elif ch in (ord("x"), ord("X")):
            self.api.clear_button(self.deck_id, self._page(), self.selected)
            self._set_message(f"Cleared key {self.selected + 1}")
        elif ch in (ord("a"), ord("A")):
            page = self.api.add_new_page(self.deck_id)
            self.api.set_page(self.deck_id, page)
            self.last_manual_page[self.deck_id] = page
            self._set_message(f"Added page {self._page_no()}")
        elif ch in (ord("d"), ord("D")):
            self._delete_current_tab()
        return True

    def _delete_current_tab(self) -> None:
        """Removes the page behind the active tab — an auto page (with its app
        binding) or, if it is a normal page and not the last one, a normal page."""
        if self.deck_id is None:
            return
        page = self._page()
        if self.api.is_auto_page(self.deck_id, page):
            self._change_tab(-1)
            self.api.remove_auto_page(self.deck_id, page)
            self._set_message("Removed auto page")
        elif len(self._normal_pages()) > 1:
            self._change_tab(-1)
            self.api.remove_page(self.deck_id, page)
            self._set_message("Removed page")
        else:
            self._set_message("Cannot remove the only page")

    # -- Button editor -------------------------------------------------------

    def _edit_button(self, stdscr) -> None:
        deck_id = self.deck_id
        assert deck_id is not None  # nosec - the editor is only reachable with a deck selected
        page = self._page()
        button = self.selected
        while True:
            self._render_editor(stdscr, page, button)
            ch = stdscr.getch()
            if ch in (ord("q"), 27, curses.KEY_LEFT):  # q / Esc / Left
                return
            if ch in (ord("l"), ord("L")):
                self._cycle_live_source(page, button)
                continue
            if ch in (ord("p"), ord("P")):
                value = self._prompt(stdscr, "Switch to page number (blank = none)")
                if value is not None:
                    self.api.set_button_switch_page(deck_id, page, button, int(value) if value.isdigit() else 0)
                continue
            if ch in (ord("b"), ord("B")):
                value = self._prompt(stdscr, "Brightness change, e.g. -10 (blank = none)")
                if value is not None:
                    try:
                        self.api.set_button_change_brightness(deck_id, page, button, int(value or 0))
                    except ValueError:
                        self._set_message("Brightness change must be a number")
                continue
            for hotkey, label, getter, setter in _EDIT_FIELDS:
                if ch == ord(hotkey):
                    current = getattr(self.api, getter)(deck_id, page, button)
                    value = self._prompt(stdscr, label, current)
                    if value is not None:
                        getattr(self.api, setter)(deck_id, page, button, value)
                    break

    def _cycle_live_source(self, page: int, button: int) -> None:
        deck_id = self.deck_id
        assert deck_id is not None  # nosec - only called from the editor, which holds a deck
        keys = [key for key, _ in live.LIVE_SOURCES]
        current = self.api.get_button_live_source(deck_id, page, button)
        index = keys.index(current) if current in keys else 0
        self.api.set_button_live_source(deck_id, page, button, keys[(index + 1) % len(keys)])

    def _prompt(self, stdscr, label: str, initial: str = "") -> Optional[str]:
        """Reads a line of text in a highlighted bar. Returns None on Esc."""
        buffer = list(initial)
        try:
            curses.curs_set(1)
        except curses.error:
            pass
        try:
            while True:
                height, width = stdscr.getmaxyx()
                y = height - 1
                _fill_row(stdscr, y, width, _pair(C_KEYCAP))
                prompt = f"  {label}: "
                _safe_addstr(stdscr, y, 0, prompt, _pair(C_KEYCAP) | curses.A_BOLD)
                _safe_addstr(stdscr, y, len(prompt), "".join(buffer)[: width - len(prompt) - 2], _pair(C_KEYCAP))
                stdscr.refresh()
                ch = stdscr.getch()
                if ch in (ord("\n"), curses.KEY_ENTER):
                    return "".join(buffer)
                if ch == 27:  # Esc
                    return None
                if ch in (curses.KEY_BACKSPACE, 127, 8):
                    if buffer:
                        buffer.pop()
                elif 32 <= ch < 127:
                    buffer.append(chr(ch))
        finally:
            try:
                curses.curs_set(0)
            except curses.error:
                pass

    # -- Rendering -----------------------------------------------------------

    def _render(self, stdscr) -> None:
        if not self._dirty:
            return
        self._dirty = False
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        if height < 10 or width < 36:
            _safe_addstr(stdscr, 0, 0, "Terminal too small.")
            stdscr.refresh()
            return

        self._render_header(stdscr, width)
        body_top = 3
        body_height = height - body_top - 2  # leave a status line and the footer
        if self.deck_id is None:
            self._render_waiting(stdscr, body_top, width, body_height)
        else:
            panel_w = 30 if width >= 80 else 0
            grid_w = width - panel_w
            self._render_grid(stdscr, body_top, 0, grid_w, body_height)
            if panel_w:
                self._render_detail(stdscr, body_top, grid_w, panel_w, body_height)

        _safe_addstr(stdscr, height - 2, 1, _truncate(self.message, width - 2), _pair(C_ACCENT))
        self._render_footer(stdscr, height, width)
        if self.show_help:
            self._render_help(stdscr, height, width)
        stdscr.refresh()

    def _render_header(self, stdscr, width: int) -> None:
        _fill_row(stdscr, 0, width, _pair(C_HEADER))
        _safe_addstr(stdscr, 0, 1, "▌", _pair(C_ACCENT) | curses.A_BOLD)
        _safe_addstr(stdscr, 0, 3, "STREAM DECK", _pair(C_BRAND) | curses.A_BOLD)
        if self.deck_id is not None:
            deck = self.api.decks_by_serial.get(self.deck_id)
            deck_type = deck.deck_type() if deck else "Stream Deck"
            _safe_addstr(stdscr, 0, 15, f"· {deck_type}", _pair(C_HEADER))
            _safe_addstr(stdscr, 0, max(15, width - len(self.deck_id) - 2), self.deck_id, _pair(C_HEADER))

            # Info line: the tab strip on the left, brightness gauge on the right.
            brightness = self.api.get_brightness(self.deck_id)
            gauge = f"☀ {brightness:3d}% " + _bar(brightness, 12)
            gauge_x = max(20, width - len(gauge) - 1)
            _safe_addstr(stdscr, 1, gauge_x, gauge, _pair(C_BRIGHT) | curses.A_BOLD)
            self._render_tabs(stdscr, 1, 1, gauge_x - 2)
        else:
            _safe_addstr(stdscr, 0, 15, "· waiting for a device", _pair(C_HEADER))
        _safe_addstr(stdscr, 2, 0, "─" * (width - 1), _pair(C_DIM))

    def _render_tabs(self, stdscr, y: int, left: int, width: int) -> None:
        tabs = self._tabs()
        if not tabs or width < 6:
            return
        current = self._page()
        ids = [tab[0] for tab in tabs]
        active = ids.index(current) if current in ids else 0

        # Each tab renders as " glyph label "; auto tabs carry a ⟳ marker. Keep a
        # horizontal window around the active tab so long strips stay readable.
        labels = [(f" ⟳{label} " if is_auto else f" {label} ") for _id, label, is_auto in tabs]
        start = 0
        while sum(len(labels[i]) for i in range(start, active + 1)) > width - 2 and start < active:
            start += 1

        x = left
        if start > 0:
            _safe_addstr(stdscr, y, x, "‹", _pair(C_DIM))
            x += 2
        prev_auto = False
        for index in range(start, len(tabs)):
            _id, _label, is_auto = tabs[index]
            cap = labels[index]
            if is_auto and not prev_auto and index > start:
                _safe_addstr(stdscr, y, x, "│", _pair(C_DIM))  # divider before the Auto group
                x += 2
            prev_auto = is_auto
            if x + len(cap) > left + width - 1:
                _safe_addstr(stdscr, y, x, "›", _pair(C_DIM))
                break
            if index == active:
                attr = _pair(C_KEYCAP) | curses.A_BOLD
            else:
                attr = (_pair(C_PAGE) if is_auto else _pair(C_ACCENT)) | curses.A_BOLD
            _safe_addstr(stdscr, y, x, cap, attr)
            x += len(cap)

    def _render_waiting(self, stdscr, top: int, width: int, height: int) -> None:
        lines = ["", "◷  No Stream Deck connected", "", "Plug one in — it will appear automatically.", ""]
        start = top + max(0, (height - len(lines)) // 2)
        for offset, text in enumerate(lines):
            attr = _pair(C_ACCENT) | curses.A_BOLD if "No Stream Deck" in text else _pair(C_DIM)
            _safe_addstr(stdscr, start + offset, max(0, (width - len(text)) // 2), text, attr)

    def _render_grid(self, stdscr, top: int, left: int, width: int, height: int) -> None:
        rows, cols = self._layout()
        if rows == 0 or cols == 0 or height < 3:
            return
        tile_w = max(9, width // cols)
        tile_h = max(3, min(7, height // rows))
        used_w = tile_w * cols
        used_h = tile_h * rows
        offset_x = left + max(0, (width - used_w) // 2)
        offset_y = top + max(0, (height - used_h) // 2)
        for index in range(rows * cols):
            r, c = divmod(index, cols)
            y = offset_y + r * tile_h
            x = offset_x + c * tile_w
            if y + tile_h - 1 > top + height:
                break
            self._render_tile(stdscr, y, x, tile_w - 1, tile_h - 1, index, index == self.selected)

    def _render_tile(self, stdscr, y: int, x: int, w: int, h: int, index: int, selected: bool) -> None:
        deck_id = self.deck_id
        assert deck_id is not None  # nosec - tiles are only drawn with a deck selected
        if w < 4 or h < 2:
            return
        page = self._page()
        glyph, color, label = classify_button(self.api, deck_id, page, index)
        # Prefer the button's own text (wrapped to fill the tile), falling back to
        # the action descriptor for keys that have no label of their own.
        text = self.api.get_button_text(deck_id, page, index).strip()
        content = text or label
        empty = not glyph and not content

        if selected:
            for row in range(1, h - 1):
                _safe_addstr(stdscr, y + row, x + 1, " " * (w - 2), _pair(C_SELBG))
            border_attr = _pair(C_SELECTED) | curses.A_BOLD
            content_attr = _pair(C_SELBG) | curses.A_BOLD
        else:
            border_attr = _pair(C_DIM) if empty else _pair(color)
            content_attr = _pair(C_DIM) if empty else _pair(color) | curses.A_BOLD

        _draw_box(stdscr, y, x, w, h, border_attr, heavy=selected)
        # Index in the top-left corner, the action glyph in the top-right; this
        # frees the whole interior for the wrapped text content.
        _safe_addstr(stdscr, y, x + 1, str(index + 1), border_attr)
        if glyph:
            _safe_addstr(stdscr, y, x + w - 2, glyph, border_attr)

        inner_w = w - 2
        lines = wrap_label(content, inner_w, h - 2) if content else (["·"] if empty else [])
        start_row = y + 1 + max(0, (h - 2 - len(lines)) // 2)
        for offset, line in enumerate(lines):
            _safe_addstr(stdscr, start_row + offset, x + 1, line.center(inner_w), content_attr)

    def _render_detail(self, stdscr, top: int, left: int, width: int, height: int) -> None:
        deck_id = self.deck_id
        assert deck_id is not None  # nosec - the panel is only drawn with a deck selected
        page = self._page()
        button = self.selected
        _draw_box(stdscr, top, left, width, height, _pair(C_ACCENT))
        _safe_addstr(stdscr, top, left + 2, f" Key {button + 1} ", _pair(C_ACCENT) | curses.A_BOLD)

        _, color, _ = classify_button(self.api, deck_id, page, button)
        fields = [
            ("Text", self.api.get_button_text(deck_id, page, button).replace("\n", " "), C_PANEL),
            ("Command", self.api.get_button_command(deck_id, page, button), C_CMD),
            ("Keys", self.api.get_button_keys(deck_id, page, button), C_KEYS),
            ("Write", self.api.get_button_write(deck_id, page, button), C_WRITE),
            ("Switch", self._detail_switch_page(deck_id, page, button), C_PAGE),
            ("Bright ±", self._detail_brightness(deck_id, page, button), C_BRIGHT),
            ("Live", self._detail_live(deck_id, page, button), C_LIVE),
        ]
        row = top + 2
        for name, value, value_color in fields:
            if row >= top + height - 1:
                break
            _safe_addstr(stdscr, row, left + 2, f"{name:<8}", _pair(C_DIM))
            shown = value if value else "—"
            attr = _pair(value_color) if value else _pair(C_DIM)
            _safe_addstr(stdscr, row, left + 11, _truncate(shown, width - 13), attr)
            row += 1
        if row < top + height - 1:
            _safe_addstr(stdscr, row + 1, left + 2, "↵ edit this key", _pair(C_DIM))

    def _detail_switch_page(self, deck_id: str, page: int, button: int) -> str:
        value = self.api.get_button_switch_page(deck_id, page, button)
        return _switch_page_label(value) if value else ""

    def _detail_brightness(self, deck_id: str, page: int, button: int) -> str:
        value = self.api.get_button_change_brightness(deck_id, page, button)
        return f"{value:+d}" if value else ""

    def _detail_live(self, deck_id: str, page: int, button: int) -> str:
        source = self.api.get_button_live_source(deck_id, page, button)
        return _live_label(source) if live.is_live_source(source) else ""

    def _render_footer(self, stdscr, height: int, width: int) -> None:
        y = height - 1
        _fill_row(stdscr, y, width, _pair(C_FOOTER))
        hints = [
            ("Tab", "tab"),
            ("⇧Tab", "back"),
            ("↑↓←→", "move"),
            ("↵", "edit"),
            ("x", "clear"),
            ("a d", "tab±"),
            ("+ -", "bright"),
            ("?", "help"),
            ("q", "quit"),
        ]
        x = 1
        for key, label in hints:
            cap = f" {key} "
            if x + len(cap) + len(label) + 3 >= width:
                break
            _safe_addstr(stdscr, y, x, cap, _pair(C_KEYCAP) | curses.A_BOLD)
            x += len(cap)
            _safe_addstr(stdscr, y, x, f" {label}", _pair(C_FOOTER))
            x += len(label) + 2

    def _render_editor(self, stdscr, page: int, button: int) -> None:
        deck_id = self.deck_id
        assert deck_id is not None  # nosec - the editor is only reachable with a deck selected
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        self._render_header(stdscr, width)

        switch_page = self.api.get_button_switch_page(deck_id, page, button)
        brightness = self.api.get_button_change_brightness(deck_id, page, button)
        rows = [
            ("t", "Text", self.api.get_button_text(deck_id, page, button).replace("\n", "\\n"), C_PANEL),
            ("c", "Command", self.api.get_button_command(deck_id, page, button), C_CMD),
            ("k", "Keys", self.api.get_button_keys(deck_id, page, button), C_KEYS),
            ("w", "Write", self.api.get_button_write(deck_id, page, button), C_WRITE),
            ("p", "Switch page", _switch_page_label(switch_page) if switch_page else "", C_PAGE),
            ("b", "Brightness ±", f"{brightness:+d}" if brightness else "", C_BRIGHT),
            ("l", "Live source", self._detail_live(deck_id, page, button), C_LIVE),
        ]

        box_w = min(width - 4, 64)
        box_h = len(rows) + 6
        box_y = max(3, (height - box_h) // 2)
        box_x = max(0, (width - box_w) // 2)
        for row in range(1, box_h - 1):
            _safe_addstr(stdscr, box_y + row, box_x + 1, " " * (box_w - 2), _pair(C_PANEL))
        _draw_box(stdscr, box_y, box_x, box_w, box_h, _pair(C_ACCENT) | curses.A_BOLD)
        _safe_addstr(
            stdscr,
            box_y,
            box_x + 2,
            f" Edit Key {button + 1} · Page {self._page_no()} ",
            _pair(C_ACCENT) | curses.A_BOLD,
        )

        row_y = box_y + 2
        for hotkey, name, value, color in rows:
            _safe_addstr(stdscr, row_y, box_x + 3, f" {hotkey} ", _pair(C_KEYCAP) | curses.A_BOLD)
            _safe_addstr(stdscr, row_y, box_x + 7, f"{name:<13}", _pair(C_DIM))
            shown = value if value else "—"
            attr = _pair(color) | curses.A_BOLD if value else _pair(C_DIM)
            _safe_addstr(stdscr, row_y, box_x + 21, _truncate(shown, box_w - 23), attr)
            row_y += 1
        _safe_addstr(stdscr, box_y + box_h - 2, box_x + 3, "press a letter to edit · q / Esc to go back", _pair(C_DIM))
        stdscr.refresh()

    def _render_help(self, stdscr, height: int, width: int) -> None:
        entries = [
            ("Navigation", ""),
            ("↑ ↓ ← →  /  h j k l", "move between keys"),
            ("Tab  /  Shift+Tab", "next / previous tab"),
            ("[  ]   or  , .", "previous / next tab"),
            ("`  (backtick)", "switch to the next deck"),
            ("", ""),
            ("Actions", ""),
            ("Enter  /  e", "edit the selected key"),
            ("x", "clear the selected key"),
            ("a  /  d", "add / delete a page/tab"),
            ("+  /  -", "brightness up / down"),
            ("", ""),
            ("Editor", ""),
            ("t c k w", "text · command · keys · write"),
            ("p  b  l", "switch page · brightness · live source"),
            ("q  /  Esc", "close help or go back"),
        ]
        box_w = min(width - 4, 52)
        box_h = min(height - 2, len(entries) + 4)
        box_y = max(1, (height - box_h) // 2)
        box_x = max(0, (width - box_w) // 2)
        for row in range(1, box_h - 1):
            _safe_addstr(stdscr, box_y + row, box_x + 1, " " * (box_w - 2), _pair(C_PANEL))
        _draw_box(stdscr, box_y, box_x, box_w, box_h, _pair(C_ACCENT) | curses.A_BOLD)
        _safe_addstr(stdscr, box_y, box_x + 2, " Keyboard shortcuts ", _pair(C_ACCENT) | curses.A_BOLD)
        row_y = box_y + 2
        for key, label in entries:
            if row_y >= box_y + box_h - 1:
                break
            if key and not label:  # a section heading
                _safe_addstr(stdscr, row_y, box_x + 2, key, _pair(C_BRIGHT) | curses.A_BOLD)
            elif key:
                _safe_addstr(stdscr, row_y, box_x + 3, f"{key:<20}", _pair(C_ACCENT) | curses.A_BOLD)
                _safe_addstr(stdscr, row_y, box_x + 24, _truncate(label, box_w - 26), _pair(C_PANEL))
            row_y += 1


# --- drawing helpers ------------------------------------------------------


def _init_colors() -> None:
    """Allocates the colour palette, degrading gracefully on poor terminals."""
    if not curses.has_colors():
        return
    curses.start_color()
    base = -1  # the terminal's own background (requires use_default_colors)
    try:
        curses.use_default_colors()
    except curses.error:
        base = curses.COLOR_BLACK
    rich = curses.COLORS >= 256

    def c(rich_color: int, basic_color: int) -> int:
        return rich_color if rich else basic_color

    brand_bg = c(24, curses.COLOR_BLUE)
    pairs = {
        C_HEADER: (c(254, curses.COLOR_WHITE), brand_bg),
        C_BRAND: (c(231, curses.COLOR_WHITE), brand_bg),
        C_ACCENT: (c(45, curses.COLOR_CYAN), base),
        C_DIM: (c(245, curses.COLOR_WHITE), base),
        C_FOOTER: (c(252, curses.COLOR_WHITE), c(236, curses.COLOR_BLACK)),
        C_KEYCAP: (c(236, curses.COLOR_BLACK), c(45, curses.COLOR_CYAN)),
        C_SELECTED: (c(51, curses.COLOR_CYAN), base),
        C_SELBG: (c(231, curses.COLOR_WHITE), c(25, curses.COLOR_BLUE)),
        C_PANEL: (c(253, curses.COLOR_WHITE), base),
        C_CMD: (c(78, curses.COLOR_GREEN), base),
        C_KEYS: (c(75, curses.COLOR_BLUE), base),
        C_WRITE: (c(215, curses.COLOR_YELLOW), base),
        C_PAGE: (c(176, curses.COLOR_MAGENTA), base),
        C_LIVE: (c(80, curses.COLOR_CYAN), base),
        C_BRIGHT: (c(221, curses.COLOR_YELLOW), base),
        C_TEXT: (c(252, curses.COLOR_WHITE), base),
    }
    for pair_id, (fg, bg) in pairs.items():
        try:
            curses.init_pair(pair_id, fg, bg)
        except curses.error:
            pass


def _pair(pair_id: int) -> int:
    try:
        return curses.color_pair(pair_id)
    except curses.error:
        return 0


def _bar(value: int, width: int) -> str:
    filled = max(0, min(width, round(value / 100 * width)))
    return "█" * filled + "░" * (width - filled)


def _truncate(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width == 1:
        return "…"
    return text[: width - 1] + "…"


def wrap_label(text: str, width: int, max_lines: int) -> List[str]:
    """Wraps a key's text to fit a tile, honouring any explicit newlines.

    Returns at most ``max_lines`` lines, each no wider than ``width``; the last
    line is ellipsised when the content does not fit, so a key shows as much of
    its text as the tile allows.
    """
    if width <= 0 or max_lines <= 0:
        return []
    lines: List[str] = []
    for paragraph in text.split("\n"):
        wrapped = textwrap.wrap(paragraph, width) if paragraph.strip() else [""]
        lines.extend(wrapped)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        # Mark that the text was clipped so the user knows there is more.
        last = lines[-1]
        lines[-1] = last[: width - 1] + "…" if len(last) >= width else (last + "…")[:width]
    return lines


def _fill_row(stdscr, y: int, width: int, attr: int) -> None:
    _safe_addstr(stdscr, y, 0, " " * (width - 1), attr)


def _draw_box(stdscr, y: int, x: int, w: int, h: int, attr: int, heavy: bool = False) -> None:
    if heavy:
        tl, tr, bl, br, hz, vt = "┏", "┓", "┗", "┛", "━", "┃"
    else:
        tl, tr, bl, br, hz, vt = "╭", "╮", "╰", "╯", "─", "│"
    _safe_addstr(stdscr, y, x, tl + hz * (w - 2) + tr, attr)
    for row in range(1, h - 1):
        _safe_addstr(stdscr, y + row, x, vt, attr)
        _safe_addstr(stdscr, y + row, x + w - 1, vt, attr)
    _safe_addstr(stdscr, y + h - 1, x, bl + hz * (w - 2) + br, attr)


def _safe_addstr(stdscr, y: int, x: int, text: str, attr: int = 0) -> None:
    """Writes text, swallowing the curses errors raised when it would fall off
    the edge of a small terminal."""
    height, width = stdscr.getmaxyx()
    if y < 0 or y >= height or x < 0 or x >= width:
        return
    try:
        stdscr.addstr(y, x, text[: width - x - 1], attr)
    except curses.error:
        pass


def connect_signals(api: StreamDeckServer, ui: "TextUI") -> None:
    """Wires the deck monitor and key-press signals to the text UI.

    The monitor and key callbacks emit from background threads. Unlike the
    graphical UI there is no Qt event loop here to pump a queued cross-thread
    delivery, so the signals are connected with a *direct* connection: the
    handlers run synchronously in the emitting thread. They only touch simple
    state and run button actions, exactly as the GUI does on its key-callback
    thread.
    """
    api.plugevents.attached.connect(ui.on_attached, Qt.ConnectionType.DirectConnection)
    api.plugevents.detached.connect(ui.on_detached, Qt.ConnectionType.DirectConnection)
    api.streamdeck_keys.key_pressed.connect(ui.on_keypress, Qt.ConnectionType.DirectConnection)


def start() -> None:
    if "-h" in sys.argv or "--help" in sys.argv:
        print(f"Usage: {os.path.basename(sys.argv[0])}")
        print("A terminal (text) interface for the Stream Deck, for use without a graphical desktop.")
        print("Flags:")
        print("  -h, --help\tShow this message")
        return

    api = StreamDeckServer()
    if os.path.isfile(STATE_FILE):
        api.open_config(STATE_FILE)

    ui = TextUI(api)
    connect_signals(api, ui)

    try:
        with Semaphore("/tmp/streamdeck_ui.lock"):  # nosec - advisory lock shared with the GUI
            api.start()
            try:
                curses.wrapper(ui.run)
            finally:
                api.stop()
    except SemaphoreAcquireError:
        print("Stream Deck is already running (GUI or another instance). Close it first.")


if __name__ == "__main__":
    start()
