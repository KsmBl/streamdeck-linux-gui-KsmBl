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
from typing import Dict, List, Optional, Tuple

from streamdeck_ui.api import StreamDeckServer
from streamdeck_ui.config import STATE_FILE
from streamdeck_ui.modules import actions, live
from streamdeck_ui.semaphore import Semaphore, SemaphoreAcquireError

# How often (in whole loop ticks of TICK_MS) to refresh live tiles like the clock
# and CPU usage. The render loop wakes every TICK_MS to poll the keyboard.
TICK_MS = 200
LIVE_REFRESH_TICKS = 5  # ~1 second

# The button fields the editor can change, as (hot key, label, getter, setter).
# Each getter/setter is the name of the matching StreamDeckServer method.
_EDIT_FIELDS: List[Tuple[str, str, str, str]] = [
    ("t", "Text", "get_button_text", "set_button_text"),
    ("c", "Command", "get_button_command", "set_button_command"),
    ("k", "Keys", "get_button_keys", "set_button_keys"),
    ("w", "Write", "get_button_write", "set_button_write"),
]


def button_summary(api: StreamDeckServer, deck_id: str, page: int, button: int) -> str:
    """A short, single-line description of a button for the grid cell.

    Prefers the live source, then the button text, then an icon file name, then a
    hint at the configured action, and finally a placeholder for an empty button.
    """
    source = api.get_button_live_source(deck_id, page, button)
    if live.is_live_source(source):
        return f"~{source}"
    text = api.get_button_text(deck_id, page, button).strip().splitlines()
    if text and text[0]:
        return text[0]
    icon = api.get_button_icon(deck_id, page, button)
    if icon:
        return os.path.basename(icon)
    if api.get_button_command(deck_id, page, button):
        return "$ cmd"
    if api.get_button_keys(deck_id, page, button):
        return "keys"
    if api.get_button_write(deck_id, page, button):
        return "write"
    if api.get_button_switch_page(deck_id, page, button):
        return "page>"
    return "·"


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
        self.editing = False
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

    def _change_page(self, step: int) -> None:
        if self.deck_id is None:
            return
        pages = self.api.get_pages(self.deck_id)
        auto = self.api.get_auto_pages(self.deck_id)
        overlay = self.api.get_overlay_page(self.deck_id)
        normal = [p for p in pages if p not in auto and p != overlay]
        if not normal:
            return
        current = self._page()
        index = normal.index(current) if current in normal else 0
        target = normal[(index + step) % len(normal)]
        self.api.set_page(self.deck_id, target)
        self.last_manual_page[self.deck_id] = target
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
        curses.curs_set(0)
        stdscr.nodelay(False)
        stdscr.timeout(TICK_MS)
        try:
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)  # selected
            curses.init_pair(2, curses.COLOR_CYAN, -1)  # header / hints
        except curses.error:
            pass

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
        if ch in (ord("q"), ord("Q")):
            return False
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
        elif ch in (ord("]"), curses.KEY_NPAGE):
            self._change_page(1)
        elif ch in (ord("["), curses.KEY_PPAGE):
            self._change_page(-1)
        elif ch == ord("\t"):
            self._next_deck()
        elif ch == ord("+"):
            self.api.set_brightness(self.deck_id, min(100, self.api.get_brightness(self.deck_id) + 10))
        elif ch == ord("-"):
            self.api.set_brightness(self.deck_id, max(0, self.api.get_brightness(self.deck_id) - 10))
        elif ch in (ord("\n"), curses.KEY_ENTER, ord("e")):
            self._edit_button(stdscr)
        elif ch in (ord("x"), ord("X")):
            self.api.clear_button(self.deck_id, self._page(), self.selected)
            self._set_message(f"Cleared button {self.selected + 1}")
        elif ch in (ord("a"), ord("A")):
            page = self.api.add_new_page(self.deck_id)
            self.api.set_page(self.deck_id, page)
            self.last_manual_page[self.deck_id] = page
            self._set_message(f"Added page {page + 1}")
        elif ch in (ord("d"), ord("D")):
            if len(self.api.get_pages(self.deck_id)) > 1:
                page = self._page()
                self._change_page(-1)
                self.api.remove_page(self.deck_id, page)
                self._set_message(f"Removed page {page + 1}")
            else:
                self._set_message("Cannot remove the only page")
        return True

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
                value = self._prompt(stdscr, "Switch to page number (blank = none): ")
                if value is not None:
                    self.api.set_button_switch_page(deck_id, page, button, int(value) if value.isdigit() else 0)
                continue
            if ch in (ord("b"), ord("B")):
                value = self._prompt(stdscr, "Brightness change (e.g. -10, blank = none): ")
                if value is not None:
                    try:
                        self.api.set_button_change_brightness(deck_id, page, button, int(value or 0))
                    except ValueError:
                        self._set_message("Brightness change must be a number")
                continue
            for hotkey, label, getter, setter in _EDIT_FIELDS:
                if ch == ord(hotkey):
                    current = getattr(self.api, getter)(deck_id, page, button)
                    value = self._prompt(stdscr, f"{label}: ", current)
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
        """Reads a line of text at the bottom of the screen.

        Returns the entered string, or None if the user pressed Esc to cancel.
        """
        buffer = list(initial)
        curses.curs_set(1)
        try:
            while True:
                height, width = stdscr.getmaxyx()
                text = label + "".join(buffer)
                stdscr.move(height - 1, 0)
                stdscr.clrtoeol()
                _safe_addstr(stdscr, height - 1, 0, text[: width - 1], curses.A_BOLD)
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
            curses.curs_set(0)

    # -- Rendering -----------------------------------------------------------

    def _render(self, stdscr) -> None:
        if not self._dirty:
            return
        self._dirty = False
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        self._render_header(stdscr, width)

        if self.deck_id is None:
            _safe_addstr(stdscr, 2, 2, "No Stream Deck connected. Waiting…")
        else:
            self._render_grid(stdscr, width, height)

        hints = "←↑↓→/hjkl move  [ ] page  Tab deck  +/- bright  Enter edit  x clear  a/d page  q quit"
        _safe_addstr(stdscr, height - 2, 0, hints[: width - 1], _pair(2))
        _safe_addstr(stdscr, height - 1, 0, self.message[: width - 1])
        stdscr.refresh()

    def _render_header(self, stdscr, width: int) -> None:
        if self.deck_id is None:
            title = " Stream Deck — text UI "
        else:
            deck = self.api.decks_by_serial.get(self.deck_id)
            deck_type = deck.deck_type() if deck else "Stream Deck"
            pages = self.api.get_pages(self.deck_id)
            page = self._page()
            page_no = pages.index(page) + 1 if page in pages else 1
            brightness = self.api.get_brightness(self.deck_id)
            title = f" {deck_type}  {self.deck_id}   Page {page_no}/{len(pages)}   " f"Brightness {brightness}% "
        _safe_addstr(stdscr, 0, 0, title.ljust(width - 1)[: width - 1], _pair(2) | curses.A_BOLD)

    def _render_grid(self, stdscr, width: int, height: int) -> None:
        rows, cols = self._layout()
        if rows == 0 or cols == 0:
            return
        page = self._page()
        top = 2
        avail_h = height - top - 2
        cell_w = max(8, (width - 1) // cols)
        cell_h = max(3, avail_h // rows)
        for index in range(rows * cols):
            r, c = divmod(index, cols)
            y = top + r * cell_h
            x = c * cell_w
            selected = index == self.selected
            self._render_cell(stdscr, y, x, cell_w - 1, cell_h - 1, index, page, selected)

    def _render_cell(self, stdscr, y: int, x: int, w: int, h: int, index: int, page: int, selected: bool) -> None:
        deck_id = self.deck_id
        assert deck_id is not None  # nosec - cells are only drawn with a deck selected
        attr = _pair(1) if selected else 0
        label = button_summary(self.api, deck_id, page, index)
        for row in range(h):
            _safe_addstr(stdscr, y + row, x, " " * w, attr)
        _safe_addstr(stdscr, y, x, f"{index + 1}".rjust(w - 1)[:w], attr | curses.A_DIM)
        mid = y + h // 2
        _safe_addstr(stdscr, mid, x, label.center(w)[:w], attr | (curses.A_BOLD if selected else 0))

    def _render_editor(self, stdscr, page: int, button: int) -> None:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        _safe_addstr(
            stdscr, 0, 0, f" Edit button {button + 1} (page {page + 1}) ".ljust(width - 1), _pair(2) | curses.A_BOLD
        )
        api = self.api
        deck_id = self.deck_id
        assert deck_id is not None  # nosec - the editor is only reachable with a deck selected
        live_source = api.get_button_live_source(deck_id, page, button)
        switch_page = api.get_button_switch_page(deck_id, page, button)
        rows = [
            ("t", "Text", api.get_button_text(deck_id, page, button).replace("\n", "\\n")),
            ("c", "Command", api.get_button_command(deck_id, page, button)),
            ("k", "Keys", api.get_button_keys(deck_id, page, button)),
            ("w", "Write", api.get_button_write(deck_id, page, button)),
            ("p", "Switch page", str(switch_page) if switch_page else ""),
            ("b", "Brightness ±", str(api.get_button_change_brightness(deck_id, page, button) or "")),
            ("l", "Live source", live_source or "(none) — press l to cycle"),
        ]
        for offset, (hotkey, label, value) in enumerate(rows):
            _safe_addstr(stdscr, 2 + offset, 2, f"[{hotkey}] {label:<14}", curses.A_BOLD)
            _safe_addstr(stdscr, 2 + offset, 22, value[: width - 24])
        _safe_addstr(stdscr, height - 1, 0, "Press a letter to edit · q/Esc to go back"[: width - 1], _pair(2))
        stdscr.refresh()


def _pair(number: int) -> int:
    try:
        return curses.color_pair(number)
    except curses.error:
        return 0


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
    api.plugevents.attached.connect(ui.on_attached)
    api.plugevents.detached.connect(ui.on_detached)
    api.streamdeck_keys.key_pressed.connect(ui.on_keypress)

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
