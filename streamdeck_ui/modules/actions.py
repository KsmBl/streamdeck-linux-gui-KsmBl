"""Headless execution of a button's configured actions.

Turning a Stream Deck key press into real effects — running a command, sending
key strokes, switching page or button state — is shared by the graphical UI
(:mod:`streamdeck_ui.gui`) and the text UI (:mod:`streamdeck_ui.tui`). Keeping
the logic here, free of any Qt or widget dependency, lets the text UI drive a
deck on a machine with no graphical session.
"""

import shlex
from dataclasses import dataclass
from subprocess import Popen  # nosec - users may configure arbitrary commands
from typing import Callable, Dict, Optional

from streamdeck_ui.config import SWITCH_PAGE_AUTO, SWITCH_PAGE_LEAVE_AUTO, SWITCH_PAGE_NEXT, SWITCH_PAGE_PREVIOUS
from streamdeck_ui.modules.keyboard import keyboard_press_keys, keyboard_write

# A resolver maps a button's ``switch_page`` value (with its current page) to a
# concrete target page id, or None when the target does not exist.
SwitchPageResolver = Callable[[str, int, int], Optional[int]]


@dataclass
class KeyActionResult:
    """Describes what executing a key press changed, so a UI can mirror it.

    ``page`` / ``button`` are the slot the action actually ran on (after any
    overlay redirection). ``switched_to_page`` and ``new_button_state`` are set
    only when the press changed the active page or button state respectively.
    """

    page: int
    button: int
    switched_to_page: Optional[int] = None
    new_button_state: Optional[int] = None


def auto_entry_page(api, deck_id: str, last_focused_app: Optional[str]) -> Optional[int]:
    """The auto page to show when entering the Auto group: the one bound to the
    currently focused application, else the Home page, else the first auto page."""
    auto_pages = api.get_auto_pages(deck_id)
    if not auto_pages:
        return None
    if last_focused_app is not None:
        bound = api.get_focus_pages(deck_id).get(last_focused_app)
        if bound in auto_pages:
            return bound
    home = api.get_home_page(deck_id)
    if home in auto_pages:
        return home
    return auto_pages[0]


def resolve_switch_page(
    api,
    deck_id: str,
    current_page: int,
    switch_page: int,
    *,
    last_manual_page: Dict[str, int],
    last_focused_app: Optional[str],
) -> Optional[int]:
    """Resolves a button's switch_page value to a concrete target page id.

    A positive value is an absolute (1-based) page number. ``SWITCH_PAGE_NEXT`` /
    ``SWITCH_PAGE_PREVIOUS`` navigate relative to the current page (wrapping),
    walking only the normal pages. ``SWITCH_PAGE_AUTO`` enters the Auto group and
    ``SWITCH_PAGE_LEAVE_AUTO`` returns to the last normal page. Returns None when
    the target does not exist.
    """
    pages = api.get_pages(deck_id)
    if not pages:
        return None

    if switch_page in (SWITCH_PAGE_NEXT, SWITCH_PAGE_PREVIOUS):
        auto_pages = api.get_auto_pages(deck_id)
        overlay_page = api.get_overlay_page(deck_id)
        normal = [page for page in pages if page not in auto_pages and page != overlay_page]
        if not normal:
            return None
        if current_page not in normal:
            return normal[0]
        step = 1 if switch_page == SWITCH_PAGE_NEXT else -1
        return normal[(normal.index(current_page) + step) % len(normal)]

    if switch_page == SWITCH_PAGE_AUTO:
        return auto_entry_page(api, deck_id, last_focused_app)

    if switch_page == SWITCH_PAGE_LEAVE_AUTO:
        auto_pages = api.get_auto_pages(deck_id)
        last = last_manual_page.get(deck_id)
        if last is not None and last in pages and last not in auto_pages:
            return last
        normal = [page for page in pages if page not in auto_pages and page != api.get_overlay_page(deck_id)]
        return normal[0] if normal else None

    target_page = switch_page - 1
    return target_page if target_page in pages else None


def execute_key_action(
    api,
    deck_id: str,
    key: int,
    *,
    resolve_switch_page: SwitchPageResolver,
    on_warning: Optional[Callable[[str], None]] = None,
) -> Optional[KeyActionResult]:
    """Runs the configured action(s) for a pressed key.

    Returns a :class:`KeyActionResult` describing any page/state change, or None
    when nothing actionable ran (the press only woke the display from a dimmed
    state). ``resolve_switch_page`` turns a ``switch_page`` value into a target
    page; ``on_warning`` (if given) is called with a human-readable message when
    an action cannot be completed.
    """

    def warn(message: str) -> None:
        if on_warning is not None:
            on_warning(message)

    if api.reset_dimmer(deck_id):
        return None

    # On an auto page an overlay key acts in place of the underlying key, so
    # resolve the slot the action and state actually live on.
    page, key = api.resolve_overlay(deck_id, api.get_page(deck_id), key)
    command = api.get_button_command(deck_id, page, key)
    keys = api.get_button_keys(deck_id, page, key)
    write = api.get_button_write(deck_id, page, key)
    brightness_change = api.get_button_change_brightness(deck_id, page, key)
    switch_page = api.get_button_switch_page(deck_id, page, key)
    switch_state = api.get_button_switch_state(deck_id, page, key)

    result = KeyActionResult(page=page, button=key)

    if command:
        try:
            Popen(shlex.split(command))  # nosec - need to allow execution of arbitrary commands
        except Exception as error:
            print(f"The command '{command}' failed: {error}")
            warn("The command failed to execute.")

    if keys:
        try:
            keyboard_press_keys(keys)
        except Exception as error:
            print(f"Could not press keys '{keys}': {error}")
            warn(f"Unable to perform key press action. {error}")

    if write:
        try:
            keyboard_write(write)
        except Exception as error:
            print(f"Could not complete the write command: {error}")
            warn("Unable to perform write action.")

    if brightness_change:
        try:
            api.change_brightness(deck_id, brightness_change)
        except Exception as error:
            print(f"Could not change brightness: {error}")
            warn("Unable to change brightness.")

    if switch_page:
        target_page = resolve_switch_page(deck_id, page, switch_page)
        if target_page is not None:
            api.set_page(deck_id, target_page)
            result.switched_to_page = target_page
        else:
            warn(f"Unable to perform switch page, the page {switch_page} does not exist in your current settings")

    if switch_state:
        switch_state_index = switch_state - 1
        if switch_state_index in api.get_button_states(deck_id, page, key):
            api.set_button_state(deck_id, page, key, switch_state_index)
            result.new_button_state = switch_state_index
        else:
            warn(
                f"Unable to perform switch button state, the button state {switch_state} "
                "does not exist in your current settings"
            )

    if api.get_button_cycle_states(deck_id, page, key):
        states = api.get_button_states(deck_id, page, key)
        if len(states) > 1:
            current_state = api.get_button_state(deck_id, page, key)
            position = states.index(current_state) if current_state in states else 0
            next_state = states[(position + 1) % len(states)]
            api.set_button_state(deck_id, page, key, next_state)
            result.new_button_state = next_state

    return result
