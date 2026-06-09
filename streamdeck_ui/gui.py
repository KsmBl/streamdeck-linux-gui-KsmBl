"""Defines the QT powered interface for configuring Stream Decks"""

import os
import random
import shlex
import signal
import sys
from collections import deque
from functools import partial
from subprocess import Popen  # nosec - Need to allow users to specify arbitrary commands
from typing import Callable, Dict, List, Optional, Tuple, Union, cast

from importlib_metadata import PackageNotFoundError, version
from PIL import Image
from PySide6.QtCore import QMimeData, QSettings, QSignalBlocker, QSize, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QDesktopServices,
    QDrag,
    QFont,
    QIcon,
    QKeySequence,
    QPalette,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from streamdeck_ui.api import StreamDeckServer
from streamdeck_ui.cli.server import CLIStreamDeckServer
from streamdeck_ui.config import (
    APP_ICON_CACHE_DIR,
    APP_LOGO,
    APP_NAME,
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_FONT_COLOR,
    DEFAULT_FONT_FALLBACK_PATH,
    DEFAULT_FONT_SIZE,
    NEXT_PAGE_ICON,
    PREVIOUS_PAGE_ICON,
    STATE_FILE,
    STATE_FILE_BACKUP,
    SWITCH_PAGE_AUTO,
    SWITCH_PAGE_LEAVE_AUTO,
    SWITCH_PAGE_NEXT,
    SWITCH_PAGE_PREVIOUS,
    config_file_need_migration,
    do_config_file_migration,
)
from streamdeck_ui.display.text_filter import is_a_valid_text_filter_font
from streamdeck_ui.modules.applications import (
    DesktopApplication,
    list_desktop_applications,
    load_application_qicon,
    resolve_icon_to_file,
)
from streamdeck_ui.modules.control_presets import CONTROL_PRESETS, ControlPreset
from streamdeck_ui.modules.daemon import daemonize, kill_daemon, remove_pid_file, running_pid, write_pid_file
from streamdeck_ui.modules.focus import FocusWatcher, get_focused_app, list_open_apps
from streamdeck_ui.modules.font_icons import (
    add_drop_shadow,
    build_browser_icons,
    build_font_awesome_brand_icons,
    build_font_awesome_icons,
    build_nerd_font_icons,
    find_font_awesome_fonts,
    find_nerd_fonts,
    recolor_icon,
    render_named_solid_icon,
)
from streamdeck_ui.modules.fonts import DEFAULT_FONT_FAMILY, FONTS_DICT, find_font_info
from streamdeck_ui.modules.keyboard import (
    KEY_COMBO_MODIFIERS,
    KeyPressAutoComplete,
    get_valid_key_names,
    keyboard_press_keys,
    keyboard_write,
    qt_key_to_evdev_name,
)
from streamdeck_ui.modules.live import LIVE_SOURCES, is_live_source
from streamdeck_ui.modules.sample_icons import list_sample_icons
from streamdeck_ui.modules.snake import SnakeModel
from streamdeck_ui.modules.theme import (
    THEME_DEFAULT,
    THEME_MODERN,
    THEME_XP,
    apply_theme,
    get_modern_accent,
    get_theme,
    is_dark_mode_enabled,
    set_dark_mode_enabled,
    set_modern_accent,
    set_theme,
)
from streamdeck_ui.modules.utils.timers import debounce
from streamdeck_ui.semaphore import Semaphore, SemaphoreAcquireError
from streamdeck_ui.ui_button import Ui_ButtonForm
from streamdeck_ui.ui_main import Ui_MainWindow
from streamdeck_ui.ui_settings import Ui_SettingsDialog

# this ignore is just a workaround to set api with something
# and be able to test
api: StreamDeckServer = StreamDeckServer()

main_window: "MainWindow" = cast("MainWindow", None)
"Reference to the main window, used across multiple functions"

last_image_dir: str = ""
"Stores the last direction where user selected an image from"

selected_button: Optional[QToolButton] = None
"A reference to the currently selected button"

text_update_timer: Optional[QTimer] = None
"Timer used to delay updates to the button text"

focus_watcher: Optional[FocusWatcher] = None
"Background watcher that switches pages based on the focused application"

last_manual_page: Dict[str, int] = {}
"The last page the user selected themselves, per deck (used to restore it when a focused app has no bound page)"

_focus_switching: bool = False
"True while a page change is driven by the focus watcher (so it is not recorded as a manual selection)"

_last_focused_app: Optional[str] = None
"Most recent focused application reported by the watcher (read on hot paths to avoid a synchronous probe)"

deck_game: Optional["DeckSnake"] = None
"The on-deck Snake game while it is taking over a Stream Deck, else None"

BUTTON_STYLE = """
    QToolButton {
    margin: 2px;
    border: 2px solid #444444;
    border-radius: 8px;
    background-color: #000000;
    border-style: outset;}
    QToolButton:checked {
    margin: 2px;
    border: 2px solid #cccccc;
    border-radius: 8px;
    background-color: #000000;
    border-style: outset;}
"""

BUTTON_DRAG_STYLE = """
    QToolButton {
    margin: 2px;
    border: 2px solid #999999;
    border-radius: 8px;
    background-color: #000000;
    border-style: outset;}
"""

DEVICE_PAGE_STYLE = """
background-color: black
"""

dimmer_options = {
    "Never": 0,
    "10 Seconds": 10,
    "1 Minute": 60,
    "5 Minutes": 300,
    "10 Minutes": 600,
    "15 Minutes": 900,
    "30 Minutes": 1800,
    "1 Hour": 3600,
    "5 Hours": 7200,
    "10 Hours": 36000,
}


class DraggableButton(QToolButton):
    """A QToolButton that supports drag and drop and swaps the button properties on drop"""

    def __init__(self, parent, ui, api_: StreamDeckServer):
        super(DraggableButton, self).__init__(parent)

        self.setAcceptDrops(True)
        self.ui = ui
        self.api = api_

    def mouseMoveEvent(self, e):  # noqa: N802 - Part of QT signature.
        if e.buttons() != Qt.LeftButton:
            return

        self.api.reset_dimmer(_deck())

        mime_data = QMimeData()
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.MoveAction)

    def dropEvent(self, e):  # noqa: N802 - Part of QT signature.
        global selected_button

        self.setStyleSheet(BUTTON_STYLE)
        deck_id = _deck()
        page_id = _page()

        index = self.property("index")
        if e.source():
            source_index = e.source().property("index")
            # Ignore drag and drop on yourself
            if source_index == index:
                return

            self.api.swap_buttons(deck_id, page_id, source_index, index)
            # In the case that we've dragged the currently selected button, we have to
            # check the target button instead, so it appears that it followed the drag/drop
            if e.source().isChecked():
                e.source().setChecked(False)
                self.setChecked(True)
                selected_button = self
        else:
            # Handle drag and drop from outside the application
            if e.mimeData().hasUrls:
                file_name = e.mimeData().urls()[0].toLocalFile()
                self.api.set_button_icon(deck_id, page_id, index, file_name)

        if e.source():
            source_index = e.source().property("index")
            icon = self.api.get_button_icon_pixmap(deck_id, page_id, source_index)
            if icon:
                e.source().setIcon(icon)

        icon = self.api.get_button_icon_pixmap(deck_id, page_id, index)
        if icon:
            self.setIcon(icon)

    def dragEnterEvent(self, e):  # noqa: N802 - Part of QT signature.
        if type(self) is DraggableButton:
            e.setAccepted(True)
            self.setStyleSheet(BUTTON_DRAG_STYLE)
        else:
            e.setAccepted(False)

    def dragLeaveEvent(self, e):  # noqa: N802 - Part of QT signature.
        self.setStyleSheet(BUTTON_STYLE)

    def contextMenuEvent(self, e):  # noqa: N802 - Part of QT signature.
        # Make this button the selected one so the actions target it.
        siblings = self.parent().findChildren(DraggableButton)
        self.setChecked(True)
        button_clicked(self, siblings)

        menu = QMenu(self)
        copy_action = menu.addAction("Copy")
        paste_action = menu.addAction("Paste")
        menu.addSeparator()
        clear_action = menu.addAction("Clear")
        paste_action.setEnabled(_button_clipboard is not None)
        copy_action.triggered.connect(copy_selected_button)
        paste_action.triggered.connect(paste_selected_button)
        clear_action.triggered.connect(clear_selected_button)
        menu.exec(e.globalPos())


def handle_keypress(ui, deck_id: str, key: int, state: bool) -> None:
    # TODO: Handle both key down and key up events in future.
    # While the on-deck Snake game owns this deck, keys drive the game instead of
    # running button actions.
    if deck_game is not None and deck_game.deck_id == deck_id:
        if state:
            deck_game.on_key(key)
        return

    if state:
        if api.reset_dimmer(deck_id):
            return

        # On an auto page an overlay key acts in place of the underlying key, so
        # resolve the slot the action and state actually live on.
        page, key = api.resolve_overlay(deck_id, api.get_page(deck_id), key)
        command = api.get_button_command(deck_id, page, key)
        keys = api.get_button_keys(deck_id, page, key)
        write = api.get_button_write(deck_id, page, key)
        brightness_change = api.get_button_change_brightness(deck_id, page, key)
        switch_page = api.get_button_switch_page(deck_id, page, key)
        switch_state = api.get_button_switch_state(deck_id, page, key)

        if command:
            try:
                Popen(shlex.split(command))  # nosec, need to allow execution of arbitrary commands
            except Exception as error:
                print(f"The command '{command}' failed: {error}")
                show_tray_warning_message("The command failed to execute.")

        if keys:
            try:
                keyboard_press_keys(keys)
            except Exception as error:
                print(f"Could not press keys '{keys}': {error}")
                show_tray_warning_message(f"Unable to perform key press action. {error}")

        if write:
            try:
                keyboard_write(write)
            except Exception as error:
                print(f"Could not complete the write command: {error}")
                show_tray_warning_message("Unable to perform write action.")

        if brightness_change:
            try:
                api.change_brightness(deck_id, brightness_change)
            except Exception as error:
                print(f"Could not change brightness: {error}")
                show_tray_warning_message("Unable to change brightness.")

        if switch_page:
            target_page = _resolve_switch_page_target(deck_id, page, switch_page)
            if target_page is not None:
                api.set_page(deck_id, target_page)
                if _deck() == deck_id:
                    for page_tab in range(ui.pages.count()):
                        if ui.pages.widget(page_tab).property("page_id") == target_page:
                            ui.pages.setCurrentIndex(page_tab)
                            break
            else:
                show_tray_warning_message(
                    f"Unable to perform switch page, the page {switch_page} does not exist in your current settings"  # noqa: E713
                )

        if switch_state:
            switch_state_index = switch_state - 1
            if switch_state_index in api.get_button_states(deck_id, page, key):
                api.set_button_state(deck_id, page, key, switch_state_index)
                if _deck() == deck_id:
                    if _button() == key:
                        for button_state in range(ui.button_states.count()):
                            if ui.button_states.widget(button_state).property("button_state_id") == switch_state_index:
                                ui.button_states.setCurrentIndex(button_state)
                                break
                    redraw_button(key)
            else:
                show_tray_warning_message(
                    f"Unable to perform switch button state, the button state {switch_state} does not exist in your current settings"  # noqa: E713
                )

        if api.get_button_cycle_states(deck_id, page, key):
            states = api.get_button_states(deck_id, page, key)
            if len(states) > 1:
                current_state = api.get_button_state(deck_id, page, key)
                position = states.index(current_state) if current_state in states else 0
                next_state = states[(position + 1) % len(states)]
                api.set_button_state(deck_id, page, key, next_state)
                if _deck() == deck_id:
                    if _button() == key:
                        for button_state in range(ui.button_states.count()):
                            if ui.button_states.widget(button_state).property("button_state_id") == next_state:
                                ui.button_states.setCurrentIndex(button_state)
                                break
                    redraw_button(key)


def _resolve_switch_page_target(deck_id: str, current_page: int, switch_page: int) -> Optional[int]:
    """Resolves a button's switch_page value to a concrete target page id.

    A positive value is an absolute (1-based) page number. The sentinel values
    SWITCH_PAGE_NEXT / SWITCH_PAGE_PREVIOUS navigate relative to the current
    page, wrapping around at the ends. SWITCH_PAGE_AUTO enters the Auto group and
    SWITCH_PAGE_LEAVE_AUTO returns to the last normal page. Returns None if the
    target does not exist.
    """
    pages = api.get_pages(deck_id)
    if not pages:
        return None

    if switch_page in (SWITCH_PAGE_NEXT, SWITCH_PAGE_PREVIOUS):
        # Relative paging only walks the normal pages; auto pages and the overlay
        # are reached through the Auto group, not Prev/Next.
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
        return _auto_entry_page(deck_id)

    if switch_page == SWITCH_PAGE_LEAVE_AUTO:
        auto_pages = api.get_auto_pages(deck_id)
        last = last_manual_page.get(deck_id)
        if last is not None and last in pages and last not in auto_pages:
            return last
        normal = [page for page in pages if page not in auto_pages and page != api.get_overlay_page(deck_id)]
        return normal[0] if normal else None

    target_page = switch_page - 1
    return target_page if target_page in pages else None


def _auto_entry_page(deck_id: str) -> Optional[int]:
    """The auto page to show when entering the Auto group: the one bound to the
    currently focused application, else the first auto page.

    The focused app is read from the background watcher's last value (updated by
    handle_focus_changed) rather than probing synchronously, so entering the Auto
    group from a key press never blocks the UI on a subprocess."""
    auto_pages = api.get_auto_pages(deck_id)
    if not auto_pages:
        return None
    if _last_focused_app is not None:
        bound = api.get_focus_pages(deck_id).get(_last_focused_app)
        if bound in auto_pages:
            return bound
    home = api.get_home_page(deck_id)
    if home in auto_pages:
        return home
    return auto_pages[0]


def _deck() -> Optional[str]:
    """Returns the currently selected Stream Deck serial number"""
    if main_window.ui.device_list.count() == 0:
        return None
    return main_window.ui.device_list.itemData(main_window.ui.device_list.currentIndex())


def _page() -> Optional[int]:
    """Returns the currently selected page index"""
    tab_index = main_window.ui.pages.currentIndex()
    page = main_window.ui.pages.widget(tab_index)
    if page is None:
        return None
    if page.property("auto_tab"):
        # The Auto tab edits an auto/overlay page in place; ``editing_page`` is
        # the page being edited, or None while its list is shown.
        return getattr(page, "editing_page", None)
    return page.property("page_id")


def _button() -> Optional[int]:
    """Returns the currently selected button index"""
    if selected_button is None:
        return None
    index = selected_button.property("index")

    if index < 0:
        return None

    return index


def _button_state() -> Optional[int]:
    """Returns the currently selected button state index"""
    tab_index = main_window.ui.button_states.currentIndex()
    state = main_window.ui.button_states.widget(tab_index)
    return state.property("button_state_id")


def handle_change_page() -> None:
    """Change the Stream Deck to the desired page and update
    the on-screen buttons.
    """
    global selected_button

    if selected_button:
        selected_button.setChecked(False)
        selected_button = None

    deck_id = _deck()

    # Selecting the Auto tab enters the Auto group on the hardware (showing the
    # auto page bound to the focused app, else the first auto page) so the deck
    # then follows the focused application.
    current_tab = main_window.ui.pages.currentWidget()
    if deck_id is not None and current_tab is not None and current_tab.property("auto_tab"):
        # Returning to the Auto tab always shows its list (not a stale editor).
        current_tab.editing_page = None
        stack = getattr(current_tab, "auto_stack", None)
        panel = getattr(current_tab, "auto_panel", None)
        if stack is not None and panel is not None:
            stack.setCurrentWidget(panel)
            panel.refresh()
        # When the Auto tab is selected by the focus watcher the page is already
        # set; only a manual selection should pick the auto entry page.
        if not _focus_switching:
            entry = _auto_entry_page(deck_id)
            if entry is not None and api.get_page(deck_id) != entry:
                api.set_page(deck_id, entry)
                api.reset_dimmer(deck_id)
        build_button_state_pages()
        return

    page_id = _page()
    if deck_id is not None and page_id is not None:
        api.set_page(deck_id, page_id)
        if not _focus_switching and not api.is_auto_page(deck_id, page_id) and page_id != api.get_overlay_page(deck_id):
            # Remember pages the user chooses, so we can return to them when a
            # focused application has no page of its own.
            last_manual_page[deck_id] = page_id
        redraw_buttons()
        api.reset_dimmer(deck_id)
    build_button_state_pages()


def handle_change_button_state() -> None:
    """Change the Stream Deck to the desired button state and update
    the on-screen buttons.
    """
    deck_id = _deck()
    page_id = _page()
    button_id = _button()
    button_state_id = _button_state()
    if deck_id is not None and page_id is not None and button_id is not None and button_state_id is not None:
        api.set_button_state(deck_id, page_id, button_id, button_state_id)
        redraw_button(button_id)
        api.reset_dimmer(deck_id)


def handle_new_page() -> None:
    deck_id = _deck()
    if not deck_id:
        return

    # Add the new page to the api
    new_page_index = api.add_new_page(deck_id)
    build_device(main_window.ui)

    # look for the new page in the ui
    for page in range(main_window.ui.pages.count()):
        if main_window.ui.pages.widget(page).property("page_id") == new_page_index:
            main_window.ui.pages.setCurrentIndex(page)
            break
    main_window.ui.remove_page.setEnabled(True)


def handle_clone_page() -> None:
    """Creates a copy of the current page (all of its buttons) and switches to it."""
    deck_id = _deck()
    page_id = _page()
    if deck_id is None or page_id is None:
        return

    new_page_index = api.clone_page(deck_id, page_id)
    build_device(main_window.ui)

    for page in range(main_window.ui.pages.count()):
        if main_window.ui.pages.widget(page).property("page_id") == new_page_index:
            main_window.ui.pages.setCurrentIndex(page)
            break
    main_window.ui.remove_page.setEnabled(True)


def handle_delete_page_with_confirmation() -> None:
    confirm = QMessageBox(main_window)
    confirm.setWindowTitle("Delete Page")
    confirm.setText("Are you sure you want to delete this page?")
    confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    confirm.setIcon(QMessageBox.Icon.Question)
    button = confirm.exec()
    if button == QMessageBox.StandardButton.Yes:
        handle_delete_page()


def handle_delete_page() -> None:
    deck_id = _deck()
    page_id = _page()
    if deck_id is None or page_id is None:
        return

    pages = api.get_pages(deck_id)
    if len(pages) == 1:
        return

    new_page = _closest_page(page_id, pages)
    tab_index_to_move = -1
    tab_index_to_remove = -1
    for tab_index in range(main_window.ui.pages.count()):
        tab = main_window.ui.pages.widget(tab_index)
        if tab.property("page_id") == new_page:
            tab_index_to_move = tab_index
        if tab.property("page_id") == page_id:
            tab_index_to_remove = tab_index

    main_window.ui.pages.setCurrentIndex(tab_index_to_move)
    # Removing the page also clears any application binding it had; reflect that
    # in the tab labels and stop the focus watcher if no bindings remain.
    api.remove_page(deck_id, page_id)
    main_window.ui.pages.removeTab(tab_index_to_remove)
    refresh_focus_tab_tooltips(main_window.ui, deck_id)
    update_focus_watcher(main_window.ui)
    if main_window.ui.pages.count() == 1:
        main_window.ui.remove_page.setEnabled(False)


def handle_new_button_state() -> None:
    deck_id = _deck()
    page_id = _page()
    button_id = _button()

    if deck_id is None or page_id is None or button_id is None:
        return

    new_button_state_index = api.add_new_button_state(deck_id, page_id, button_id)
    build_button_state_pages()

    for button_state in range(main_window.ui.button_states.count()):
        if main_window.ui.button_states.widget(button_state).property("button_state_id") == new_button_state_index:
            main_window.ui.button_states.setCurrentIndex(button_state)
            break
    main_window.ui.remove_button_state.setEnabled(True)


def handle_delete_button_state_with_confirmation() -> None:
    confirm = QMessageBox(main_window)
    confirm.setWindowTitle("Delete Button State")
    confirm.setText("Are you sure you want to delete this button state?")
    confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    confirm.setIcon(QMessageBox.Icon.Question)
    button = confirm.exec()
    if button == QMessageBox.StandardButton.Yes:
        handle_delete_button_state()


def handle_delete_button_state() -> None:
    deck_id = _deck()
    page_id = _page()
    button_id = _button()
    button_state_id = _button_state()
    if deck_id is None or page_id is None or button_id is None or button_state_id is None:
        return

    api.remove_button_state(deck_id, page_id, button_id, button_state_id)
    main_window.ui.button_states.removeTab(main_window.ui.button_states.currentIndex())
    if main_window.ui.button_states.count() == 1:
        main_window.ui.remove_button_state.setEnabled(False)


def _closest_page(page: int, pages: List[int]) -> int:
    if page not in pages:
        return -1
    page_index = pages.index(page)
    if page_index == 0:
        return pages[1]
    elif page_index == len(pages) - 1:
        return pages[page_index - 1]
    else:
        prev_page = pages[page_index - 1]
        next_page = pages[page_index + 1]
        if abs(page - prev_page) <= abs(page - next_page):
            return prev_page
        else:
            return next_page


def redraw_buttons() -> None:
    deck_id = _deck()
    page_id = _page()
    if deck_id is None or page_id is None:
        return
    current_tab = main_window.ui.pages.currentWidget()
    buttons = current_tab.findChildren(QToolButton)
    for button in buttons:
        if not button.isHidden():
            # When rebuilding the buttons, we hide the old ones
            # and mark for deletion. They still hang around so
            # ignore them here
            icon = api.get_button_icon_pixmap(deck_id, page_id, button.property("index"))
            if icon is not None:
                button.setIcon(icon)


def redraw_button(button_index: int) -> None:
    deck_id = _deck()
    page_id = _page()
    if deck_id is None or page_id is None:
        return

    current_tab = main_window.ui.pages.currentWidget()
    buttons = current_tab.findChildren(QToolButton)
    for button in buttons:
        if not button.isHidden():
            if button.property("index") == button_index:
                icon = api.get_button_icon_pixmap(deck_id, page_id, button.property("index"))
                if icon is not None:
                    button.setIcon(icon)


def set_brightness(value: int) -> None:
    deck_id = _deck()
    if deck_id is None:
        return
    api.set_brightness(deck_id, value)


def refresh_live_buttons() -> None:
    """Timer tick: re-render live buttons on each deck and mirror the change in
    the in-app preview grid for the page currently shown."""
    if main_window is None:
        return
    # The on-deck game has stopped the render loop; a synchronize() now would
    # block, so skip the live refresh entirely while it owns a deck.
    if deck_game is not None:
        return
    if not api.refresh_live_buttons():
        return

    deck_id = _deck()
    page_id = _page()
    if deck_id is None or page_id is None:
        return
    current_tab = main_window.ui.pages.currentWidget()
    if current_tab is None:
        return
    for button in current_tab.findChildren(QToolButton):
        if button.isHidden():
            continue
        index = button.property("index")
        if index is not None and is_live_source(api.get_button_live_source(deck_id, page_id, index)):
            icon = api.get_button_icon_pixmap(deck_id, page_id, index)
            if icon is not None:
                button.setIcon(icon)


def set_brightness_dimmed(value: int) -> None:
    deck_id = _deck()
    if deck_id is None:
        return
    api.set_brightness_dimmed(deck_id, value)
    api.reset_dimmer(deck_id)


def button_clicked(clicked_button, buttons) -> None:
    """This method build the button states tabs user interface.
    It is called when a button is clicked on the main page."""
    global selected_button
    selected_button = clicked_button

    # uncheck all other buttons
    for button in buttons:
        if button == clicked_button:
            continue
        button.setChecked(False)
    # if no button is selected, do nothing
    if selected_button is None:
        return
    if not selected_button.isChecked():
        selected_button = None
        return

    deck_id = _deck()
    if deck_id is not None:
        api.reset_dimmer(deck_id)
    build_button_state_pages()


# Holds a deep copy of a button's full multi-state config for copy/paste.
_button_clipboard = None


def copy_selected_button() -> None:
    """Copies the currently selected button (all of its states) to the clipboard."""
    global _button_clipboard
    deck_id = _deck()
    page_id = _page()
    button_id = _button()
    if deck_id is None or page_id is None or button_id is None:
        return
    _button_clipboard = api.get_button_multi_state(deck_id, page_id, button_id)


def paste_selected_button() -> None:
    """Pastes a previously copied button over the currently selected one."""
    deck_id = _deck()
    page_id = _page()
    button_id = _button()
    if deck_id is None or page_id is None or button_id is None or _button_clipboard is None:
        return
    api.set_button_multi_state(deck_id, page_id, button_id, _button_clipboard)
    redraw_button(button_id)
    build_button_state_pages()


def clear_selected_button() -> None:
    """Resets the currently selected button back to an empty state."""
    deck_id = _deck()
    page_id = _page()
    button_id = _button()
    if deck_id is None or page_id is None or button_id is None:
        return
    api.clear_button(deck_id, page_id, button_id)
    redraw_button(button_id)
    build_button_state_pages()


def test_selected_button() -> None:
    """Runs the currently selected button's action as if the physical key was
    pressed, so the user can verify it without touching the Stream Deck."""
    deck_id = _deck()
    page_id = _page()
    button_id = _button()
    if deck_id is None or page_id is None or button_id is None:
        return
    handle_keypress(main_window.ui, deck_id, button_id, True)


def build_button_state_pages():
    ui = main_window.ui
    blocker = QSignalBlocker(ui.button_states)
    deck_id = _deck()
    page_id = _page()
    button_id = _button()
    active_tab_index = 0

    try:
        if ui.button_states.count() > 0:
            ui.button_states.clear()

        if button_id is not None and deck_id is not None and page_id is not None:
            current_state = api.get_button_state(deck_id, page_id, button_id)

            for button_state_id in api.get_button_states(deck_id, page_id, button_id):
                page = QWidget()
                page.setLayout(QVBoxLayout())
                page.setProperty("deck_id", deck_id)
                page.setProperty("page_id", page_id)
                page.setProperty("button_id", button_id)
                page.setProperty("button_state_id", button_state_id)
                label = _build_tab_label("State", button_state_id)
                tab_index = ui.button_states.addTab(page, label)
                page_tab = ui.button_states.widget(tab_index)
                build_button_state_form(page_tab)
                if button_state_id == current_state:
                    active_tab_index = tab_index
        else:
            # No button is selected: show a friendly placeholder instead of an
            # empty, disabled form.
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page.setProperty("deck_id", deck_id)
            page.setProperty("page_id", page_id)
            page.setProperty("button_id", button_id)
            page.setProperty("button_state_id", None)
            placeholder = QLabel("Select a key above to configure it.", page)
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: grey;")
            page_layout.addStretch(1)
            page_layout.addWidget(placeholder)
            page_layout.addStretch(1)
            label = _build_tab_label("State", 0)
            ui.button_states.addTab(page, label)

        some_state = button_id is not None and ui.button_states.count() > 0
        more_than_one_state = button_id is not None and ui.button_states.count() > 1

        ui.remove_button_state.setEnabled(more_than_one_state)

        if some_state:
            ui.button_states.setCurrentIndex(active_tab_index)
            ui.add_button_state.setEnabled(True)
            redraw_button(button_id)
        else:
            ui.add_button_state.setEnabled(False)
    finally:
        blocker.unblock()


def build_button_state_form(tab) -> None:
    if hasattr(tab, "button_form"):
        for widget in tab.findChildren(QWidget):
            widget.hide()
            widget.deleteLater()

        tab.button_form.hide()
        tab.button_form.deleteLater()
        del tab.children()[0]
        del tab.button_form

    base_widget = QWidget(tab)
    tab.children()[0].addWidget(base_widget)

    tab.button_form = base_widget

    tab_ui = Ui_ButtonForm()
    tab_ui.setupUi(base_widget)

    deck_id = _deck()
    page_id = _page()
    button_id = _button()
    button_state_id = tab.property("button_state_id")

    # set values
    # reset the button configuration to the default
    _reset_build_button_state_form(tab_ui)

    if deck_id is None or page_id is None or button_id is None or button_state_id is None:
        enable_button_configuration(tab_ui, False)
        return

    enable_button_configuration(tab_ui, True)
    button_state = api.get_button_state_object(deck_id, page_id, button_id, button_state_id)

    tab_ui.text.setText(button_state.text)
    tab_ui.command.setText(button_state.command)
    tab_ui.keys.setText(button_state.keys)
    tab_ui.write.setPlainText(button_state.write)
    tab_ui.change_brightness.setValue(button_state.brightness_change)
    tab_ui.text_font_size.setValue(button_state.font_size or DEFAULT_FONT_SIZE)
    tab_ui.text_color.setPalette(QPalette(button_state.font_color or DEFAULT_FONT_COLOR))
    tab_ui.background_color.setPalette(QPalette(button_state.background_color or DEFAULT_BACKGROUND_COLOR))
    tab_ui.change_brightness.setValue(button_state.brightness_change)
    tab_ui.switch_page.setValue(button_state.switch_page)
    tab_ui.switch_state.setValue(button_state.switch_state)

    with QSignalBlocker(tab_ui.live_source):
        tab_ui.live_source.clear()
        for source_key, source_label in LIVE_SOURCES:
            tab_ui.live_source.addItem(source_label, userData=source_key)
        current_live = tab_ui.live_source.findData(button_state.live_source)
        tab_ui.live_source.setCurrentIndex(current_live if current_live >= 0 else 0)

    with QSignalBlocker(tab_ui.cycle_states):
        tab_ui.cycle_states.setChecked(button_state.cycle_states)

    font_family, font_style = find_font_info(button_state.font or DEFAULT_FONT_FALLBACK_PATH)
    prepare_button_state_form_text_font_list(tab_ui, font_family)
    prepare_button_state_form_text_font_style_list(tab_ui, font_family, font_style)

    # completer for keys
    keys_autocomplete = KeyPressAutoComplete()
    tab_ui.keys.setCompleter(keys_autocomplete)
    tab_ui.keys.textChanged.connect(keys_autocomplete.update_prefix)

    # connect signals
    tab_ui.text.textChanged.connect(partial(debounced_update_button_text, tab_ui))
    tab_ui.command.textChanged.connect(partial(debounced_update_button_attribute, "command"))
    tab_ui.select_application.clicked.connect(partial(show_application_picker, tab_ui))
    tab_ui.keys.textChanged.connect(partial(debounced_update_button_attribute, "keys"))
    tab_ui.key_combo.clicked.connect(partial(show_key_combine_dialog, tab_ui))
    media_menu = QMenu(tab_ui.media_keys)
    for preset_label, preset_keys in MEDIA_KEY_PRESETS:
        media_menu.addAction(preset_label, partial(apply_media_preset, tab_ui, preset_keys))
    tab_ui.media_keys.setMenu(media_menu)
    tab_ui.write.textChanged.connect(lambda: debounced_update_button_attribute("write", tab_ui.write.toPlainText()))
    tab_ui.change_brightness.valueChanged.connect(partial(update_button_attribute, "change_brightness"))
    tab_ui.text_font_size.valueChanged.connect(partial(update_displayed_button_attribute, "font_size"))
    tab_ui.text_font.currentTextChanged.connect(lambda: update_button_attribute_font(tab_ui, "family"))
    tab_ui.text_font_style.currentTextChanged.connect(lambda: update_button_attribute_font(tab_ui, "style"))
    tab_ui.text_color.clicked.connect(partial(show_button_state_font_color_dialog, tab_ui))
    tab_ui.background_color.clicked.connect(partial(show_button_state_background_color_dialog, tab_ui))
    tab_ui.switch_page.valueChanged.connect(partial(update_button_attribute, "switch_page"))
    tab_ui.set_next_page.clicked.connect(partial(configure_page_navigation, tab_ui, "next"))
    tab_ui.set_previous_page.clicked.connect(partial(configure_page_navigation, tab_ui, "previous"))
    tab_ui.set_auto_page.clicked.connect(partial(configure_page_navigation, tab_ui, "auto"))
    tab_ui.set_leave_auto_page.clicked.connect(partial(configure_page_navigation, tab_ui, "leave_auto"))
    tab_ui.switch_state.valueChanged.connect(partial(update_button_attribute, "switch_state"))
    tab_ui.add_image.clicked.connect(partial(show_button_state_image_dialog))
    tab_ui.sample_icons.clicked.connect(show_sample_icon_picker)
    tab_ui.upload_gif.clicked.connect(show_gif_upload_dialog)
    tab_ui.remove_image.clicked.connect(show_button_state_remove_image_dialog)
    tab_ui.text_h_align.clicked.connect(partial(update_align_text_horizontal))
    tab_ui.text_v_align.clicked.connect(partial(update_align_text_vertical))
    tab_ui.test_action.clicked.connect(test_selected_button)
    tab_ui.live_source.currentIndexChanged.connect(partial(update_live_source, tab_ui))
    tab_ui.cycle_states.toggled.connect(partial(update_button_attribute, "cycle_states"))


def enable_button_configuration(ui: Ui_ButtonForm, enabled: bool):
    ui.text.setEnabled(enabled)
    ui.command.setEnabled(enabled)
    ui.select_application.setEnabled(enabled)
    ui.keys.setEnabled(enabled)
    ui.key_combo.setEnabled(enabled)
    ui.media_keys.setEnabled(enabled)
    ui.text_font.setEnabled(enabled)
    ui.text_font_style.setEnabled(enabled)
    ui.text_font_size.setEnabled(enabled)
    ui.write.setEnabled(enabled)
    ui.change_brightness.setEnabled(enabled)
    ui.switch_page.setEnabled(enabled)
    ui.set_next_page.setEnabled(enabled)
    ui.set_previous_page.setEnabled(enabled)
    ui.switch_state.setEnabled(enabled)
    ui.add_image.setEnabled(enabled)
    ui.sample_icons.setEnabled(enabled)
    ui.upload_gif.setEnabled(enabled)
    ui.remove_image.setEnabled(enabled)
    ui.text_h_align.setEnabled(enabled)
    ui.text_v_align.setEnabled(enabled)
    ui.test_action.setEnabled(enabled)
    ui.live_source.setEnabled(enabled)
    ui.cycle_states.setEnabled(enabled)
    ui.text_color.setEnabled(enabled)
    ui.background_color.setEnabled(enabled)
    # default black color looks like it's enabled even when it's not
    # we set it to white when disabled to make it more obvious
    if enabled:
        ui.background_color.setPalette(QPalette(DEFAULT_BACKGROUND_COLOR))
    else:
        ui.background_color.setPalette(QPalette(DEFAULT_FONT_COLOR))


def prepare_button_state_form_text_font_list(ui: Ui_ButtonForm, current_font_family: str) -> None:
    """Prepares the font selection combo box with all available fonts"""
    blocker = QSignalBlocker(ui.text_font)
    try:
        ui.text_font.clear()
        ui.text_font.clearEditText()
        for i, font_family in enumerate(FONTS_DICT):
            ui.text_font.addItem(font_family)
            font = QFont(font_family)
            ui.text_font.setItemData(i, font)
            ui.text_font.setItemData(i, font, Qt.FontRole)  # type: ignore [attr-defined]
        ui.text_font.setCurrentText(current_font_family)
    finally:
        blocker.unblock()


def prepare_button_state_form_text_font_style_list(
    ui: Ui_ButtonForm, current_font_family: str, current_font_style: str
) -> None:
    """Prepares the font style selection combo box with all available styles for the selected font"""
    blocker = QSignalBlocker(ui.text_font_style)
    try:
        ui.text_font_style.clear()
        ui.text_font_style.clearEditText()
        for _i, font_style in enumerate(FONTS_DICT[current_font_family]):
            ui.text_font_style.addItem(font_style)
        if current_font_style:
            ui.text_font_style.setCurrentText(current_font_style)
    finally:
        blocker.unblock()


def show_button_state_font_color_dialog(ui: Ui_ButtonForm) -> None:
    current_color = ui.text_color.palette().color(QPalette.ColorRole.Button)
    color = QColorDialog.getColor(current_color, ui.text_color, "Select text color")

    if color.isValid():
        ui.text_color.setPalette(QPalette(color))
        color_hex = color.name()
        update_displayed_button_attribute("font_color", color_hex)


def show_button_state_background_color_dialog(ui: Ui_ButtonForm) -> None:
    current_color = ui.background_color.palette().color(QPalette.ColorRole.Button)
    color = QColorDialog.getColor(current_color, ui.background_color, "Select background color")

    if color.isValid():
        ui.background_color.setPalette(QPalette(color))
        color_hex = color.name()
        update_displayed_button_attribute("background_color", color_hex)


def show_button_state_image_dialog() -> None:
    global last_image_dir
    deck_id = _deck()
    page_id = _page()
    button_id = _button()

    if deck_id is None or page_id is None or button_id is None:
        return

    image_file = api.get_button_icon(deck_id, page_id, button_id)

    if not image_file:
        if not last_image_dir:
            image_file = os.path.expanduser("~")
        else:
            image_file = last_image_dir

    file_name = QFileDialog.getOpenFileName(
        main_window, "Open Image", image_file, "Image Files (*.png *.jpg *.bmp *.svg *.gif)"
    )[0]

    if file_name:
        if file_name == image_file:
            # if the user selects the same file name, clear out the last image
            # this will allow the image to update in the case where the user edited the image
            # and saved over the original file
            update_displayed_button_attribute("icon", "")
        last_image_dir = os.path.dirname(file_name)
        update_displayed_button_attribute("icon", file_name)


def show_gif_upload_dialog() -> None:
    """Lets the user pick an animated GIF to use as the key image. The render
    pipeline already animates GIF frames, so this just sets the icon path."""
    global last_image_dir
    deck_id = _deck()
    page_id = _page()
    button_id = _button()

    if deck_id is None or page_id is None or button_id is None:
        return

    start_dir = last_image_dir or os.path.expanduser("~")
    file_name = QFileDialog.getOpenFileName(main_window, "Upload GIF", start_dir, "Animated GIF (*.gif)")[0]
    if file_name:
        last_image_dir = os.path.dirname(file_name)
        update_displayed_button_attribute("icon", file_name)


def show_button_state_remove_image_dialog() -> None:
    deck_id = _deck()
    page_id = _page()
    button_id = _button()

    if deck_id is None or page_id is None or button_id is None:
        return

    image = api.get_button_icon(deck_id, page_id, button_id)
    if image:
        confirm = QMessageBox(main_window)
        confirm.setWindowTitle("Remove image")
        confirm.setText("Are you sure you want to remove the image for this button?")
        confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm.setIcon(QMessageBox.Icon.Question)
        button = confirm.exec()
        if button == QMessageBox.StandardButton.Yes:
            update_displayed_button_attribute("icon", "")


class ApplicationPicker(QDialog):
    """A searchable dialog that lists installed applications so the user can
    map one to a button without knowing its launch command. The selected
    application's icon is shown so the user can choose a fitting icon for it."""

    def __init__(self, parent, applications: List[DesktopApplication]):
        super().__init__(parent)
        self.setWindowTitle("Select Application")
        self.resize(420, 520)
        self._applications = applications

        layout = QVBoxLayout(self)

        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Search applications...")
        self.search.setClearButtonEnabled(True)
        layout.addWidget(self.search)

        self.list = QListWidget(self)
        self.list.setIconSize(QSize(32, 32))
        layout.addWidget(self.list)

        self.use_icon = QCheckBox("Use the application's icon for this button", self)
        self.use_icon.setChecked(True)
        layout.addWidget(self.use_icon)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        layout.addWidget(self.button_box)

        for application in applications:
            item = QListWidgetItem(application.name)
            item.setData(Qt.ItemDataRole.UserRole, application)
            icon = load_application_qicon(application.icon_name)
            if not icon.isNull():
                item.setIcon(icon)
            item.setToolTip(application.command)
            self.list.addItem(item)

        if self.list.count():
            self.list.setCurrentRow(0)

        self.search.textChanged.connect(self._filter)
        self.list.itemDoubleClicked.connect(lambda _item: self.accept())
        self.list.itemSelectionChanged.connect(self._update_ok_enabled)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self._update_ok_enabled()

    def _filter(self, text: str) -> None:
        needle = text.strip().lower()
        first_visible = None
        for row in range(self.list.count()):
            item = self.list.item(row)
            application = item.data(Qt.ItemDataRole.UserRole)
            matches = needle in application.name.lower() or needle in application.command.lower()
            item.setHidden(not matches)
            if matches and first_visible is None:
                first_visible = item
        # Keep a sensible selection as the user types
        if self.list.currentItem() is None or self.list.currentItem().isHidden():
            if first_visible is not None:
                self.list.setCurrentItem(first_visible)
        self._update_ok_enabled()

    def _update_ok_enabled(self) -> None:
        current = self.list.currentItem()
        enabled = current is not None and not current.isHidden()
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    def selected_application(self) -> Optional[DesktopApplication]:
        item = self.list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)


def show_application_picker(ui: Ui_ButtonForm) -> None:
    """Lets the user pick an installed application. The button command is set to
    the application's launch command and, if requested, the button icon is set
    to a fitting icon resolved from the application."""
    deck_id = _deck()
    page_id = _page()
    button_id = _button()

    if deck_id is None or page_id is None or button_id is None:
        return

    applications = list_desktop_applications()
    if not applications:
        QMessageBox.information(
            main_window,
            "No applications found",
            "No installed applications could be found on this system.",
        )
        return

    picker = ApplicationPicker(main_window, applications)
    if not picker.exec():
        return

    application = picker.selected_application()
    if application is None:
        return

    # Update the field for display, but block its signals so we don't also
    # schedule the debounced text handler. We store the value directly instead,
    # which is immediate and predictable.
    blocker = QSignalBlocker(ui.command)
    ui.command.setText(application.command)
    del blocker
    update_button_attribute("command", application.command)

    if picker.use_icon.isChecked():
        icon_path = resolve_icon_to_file(application.icon_name, APP_ICON_CACHE_DIR)
        if icon_path:
            update_displayed_button_attribute("icon", icon_path)
        else:
            show_tray_warning_message(f"No icon could be found for {application.name}.")


IconProvider = Union[List[Tuple[str, str]], Callable[[], List[Tuple[str, str]]]]


class _IconBuildWorker(QThread):
    """Builds one icon category off the GUI thread: it runs the (potentially
    expensive) provider — which renders glyphs from a font — and precomputes the
    drop-shadow image for each icon, so the GUI thread only has to create QIcons.
    Emits ``built(category, [(name, original_path, shadow_path), ...])``."""

    built = Signal(str, list)

    def __init__(self, parent, category: str, provider: IconProvider):
        super().__init__(parent)
        self._category = category
        self._provider = provider

    def run(self) -> None:  # noqa: N802 - QThread entry point
        try:
            entries = list(self._provider()) if callable(self._provider) else list(self._provider)
            result = [(name, path, add_drop_shadow(path)) for name, path in entries]
        except Exception as error:  # noqa: BLE001 - a broken provider must not crash the UI
            print(f"Could not build icon category '{self._category}': {error}")
            result = []
        self.built.emit(self._category, result)


class SampleIconPicker(QDialog):
    """A searchable dialog of ready-made icons grouped by category, with an
    optional colour tint. Expensive categories are rendered on a background
    thread so the dialog never freezes while building thousands of glyphs."""

    def __init__(self, parent, categories: Dict[str, IconProvider]):
        super().__init__(parent)
        self.setWindowTitle("Sample Icons")
        self.resize(520, 560)
        self._providers = categories
        # category -> [(display_name, original_path, shadow_path), ...]
        self._materialized: Dict[str, List[Tuple[str, str, str]]] = {}
        self._build_queue: List[str] = []
        self._worker: Optional[_IconBuildWorker] = None

        layout = QVBoxLayout(self)

        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Search icons...")
        self.search.setClearButtonEnabled(True)
        layout.addWidget(self.search)

        self.category = QComboBox(self)
        self.category.addItem("All categories", userData=None)
        for category in categories:
            self.category.addItem(category.replace("_", " ").title(), userData=category)
        layout.addWidget(self.category)

        self.list = QListWidget(self)
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setIconSize(QSize(64, 64))
        self.list.setGridSize(QSize(96, 96))
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setMovement(QListWidget.Movement.Static)
        self.list.setUniformItemSizes(True)
        layout.addWidget(self.list)

        color_row = QHBoxLayout()
        self.recolor = QCheckBox("Recolor", self)
        color_row.addWidget(self.recolor)
        self.color_button = QPushButton(self)
        self.color_button.setMaximumWidth(60)
        self.color_button.setEnabled(False)
        self._color = QColor("#ffffff")
        self.color_button.setPalette(QPalette(self._color))
        color_row.addWidget(self.color_button)
        color_row.addStretch(1)
        layout.addLayout(color_row)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        layout.addWidget(self.button_box)

        # Default to the first concrete category so opening the dialog is fast.
        if self.category.count() > 1:
            self.category.setCurrentIndex(1)
        self._refresh()

        self.search.textChanged.connect(self._refresh)
        self.category.currentIndexChanged.connect(self._refresh)
        self.recolor.toggled.connect(self.color_button.setEnabled)
        self.color_button.clicked.connect(self._choose_color)
        self.list.itemDoubleClicked.connect(lambda _item: self.accept())
        self.list.itemSelectionChanged.connect(self._update_ok_enabled)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def _ensure_built(self, categories: List[str]) -> None:
        """Makes categories available. Cheap (already-listed) categories are built
        inline; expensive provider callables are queued for background rendering."""
        for category in categories:
            if category in self._materialized or category in self._build_queue:
                continue
            provider = self._providers[category]
            if callable(provider):
                self._build_queue.append(category)
            else:
                self._materialized[category] = [(name, path, add_drop_shadow(path)) for name, path in provider]
        self._pump_queue()

    def _pump_queue(self) -> None:
        """Starts building the next queued category if none is in flight."""
        if self._worker is not None or not self._build_queue:
            return
        category = self._build_queue.pop(0)
        self._worker = _IconBuildWorker(self, category, self._providers[category])
        self._worker.built.connect(self._on_built)
        self._worker.start()

    def _on_built(self, category: str, entries: list) -> None:
        self._materialized[category] = entries
        self._worker = None
        self._pump_queue()
        # Show the freshly built icons if they belong to the current view.
        self._refresh()

    def _refresh(self) -> None:
        search = self.search.text().strip().lower()
        selected = self.category.currentData()
        # Searching, or the "All categories" entry, spans every category.
        categories = list(self._providers) if (search or selected is None) else [selected]

        self._ensure_built(categories)

        self.list.clear()
        pending = False
        for category in categories:
            if category not in self._materialized:
                pending = True
                continue
            for display_name, original_path, shadow_path in self._materialized[category]:
                if search and search not in display_name.lower():
                    continue
                # The drop-shadow image (built off-thread) keeps light icons
                # visible on light backgrounds; the stored icon path is the original.
                item = QListWidgetItem(QIcon(shadow_path), display_name)
                item.setData(Qt.ItemDataRole.UserRole, original_path)
                item.setToolTip(f"{category.replace('_', ' ').title()}: {display_name}")
                self.list.addItem(item)

        if pending and self.list.count() == 0:
            placeholder = QListWidgetItem("Loading icons…")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(placeholder)
        elif self.list.count():
            self.list.setCurrentRow(0)
        self._update_ok_enabled()

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(self._color, self, "Select icon color")
        if color.isValid():
            self._color = color
            self.color_button.setPalette(QPalette(color))

    def _update_ok_enabled(self) -> None:
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(self.list.currentItem() is not None)

    def selected_icon_path(self) -> Optional[str]:
        item = self.list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def selected_color(self) -> Optional[str]:
        """Returns the chosen tint colour as a hex string, or None to keep the
        icon unchanged."""
        return self._color.name() if self.recolor.isChecked() else None

    def done(self, result: int) -> None:  # noqa: A003 - QDialog override
        # Let any in-flight build finish before the dialog (the worker's parent)
        # is torn down, so the QThread is never destroyed while running.
        self._build_queue.clear()
        if self._worker is not None:
            self._worker.built.disconnect()
            self._worker.wait()
            self._worker = None
        super().done(result)


_MAX_RECENT_ICONS = 12


def _get_recent_icons() -> List[str]:
    """Returns recently chosen sample-icon paths, most recent first, dropping
    any that no longer exist on disk."""
    if main_window is None:
        return []
    stored = main_window.settings.value("recent_icons", [])
    if isinstance(stored, str):  # QSettings can collapse a single-item list
        stored = [stored]
    return [path for path in (stored or []) if os.path.exists(path)]


def _add_recent_icon(path: str) -> None:
    """Records a sample-icon path as recently used."""
    if main_window is None:
        return
    recent = [existing for existing in _get_recent_icons() if existing != path]
    recent.insert(0, path)
    main_window.settings.setValue("recent_icons", recent[:_MAX_RECENT_ICONS])


def show_sample_icon_picker() -> None:
    """Lets the user choose one of the bundled sample icons for the selected
    button."""
    deck_id = _deck()
    page_id = _page()
    button_id = _button()

    if deck_id is None or page_id is None or button_id is None:
        return

    categories: Dict[str, IconProvider] = dict(list_sample_icons())

    # Real browser icons (system theme, falling back to colourised Font Awesome
    # brands) are cheap to build, so they are added eagerly when present. The
    # large Font Awesome categories are added lazily (built only when viewed).
    browsers = build_browser_icons()
    if browsers:
        categories["browsers"] = browsers
    fonts = find_font_awesome_fonts()
    if fonts["solid"]:
        categories["Font Awesome"] = build_font_awesome_icons
    if fonts["brands"]:
        categories["Font Awesome Brands"] = build_font_awesome_brand_icons
    if find_nerd_fonts():
        categories["Nerd Font"] = build_nerd_font_icons

    if not categories:
        QMessageBox.information(main_window, "No sample icons", "No sample icons were found.")
        return

    # Surface recently used icons as the first category for quick reuse.
    recent_paths = _get_recent_icons()
    if recent_paths:
        recent_entries = [
            (os.path.splitext(os.path.basename(path))[0].replace("_", " ").title(), path) for path in recent_paths
        ]
        categories = {"recent": recent_entries, **categories}

    picker = SampleIconPicker(main_window, categories)
    if not picker.exec():
        return

    icon_path = picker.selected_icon_path()
    if icon_path:
        _add_recent_icon(icon_path)
        color = picker.selected_color()
        if color:
            icon_path = recolor_icon(icon_path, color)
        update_displayed_button_attribute("icon", icon_path)


class KeyCombineDialog(QDialog):
    """Builds a key combination for the Press Keys field so the user does not
    need to know the textual key names. Modifiers are toggled with checkboxes,
    the main key can be typed/picked, or the whole shortcut can be captured live
    with the Record button."""

    # Lone modifier presses we ignore while recording, waiting for a real key.
    _LONE_MODIFIERS = (
        Qt.Key.Key_Control,
        Qt.Key.Key_Shift,
        Qt.Key.Key_Alt,
        Qt.Key.Key_AltGr,
        Qt.Key.Key_Meta,
        Qt.Key.Key_Super_L,
        Qt.Key.Key_Super_R,
    )

    def __init__(self, parent, initial: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Build Key Combination")
        self.setMinimumWidth(360)
        self._recording = False

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Modifiers", self))
        modifier_row = QHBoxLayout()
        self._modifier_boxes: Dict[str, QCheckBox] = {}
        for modifier in KEY_COMBO_MODIFIERS:
            box = QCheckBox(modifier, self)
            box.toggled.connect(self._update_preview)
            self._modifier_boxes[modifier] = box
            modifier_row.addWidget(box)
        layout.addLayout(modifier_row)

        layout.addWidget(QLabel("Key", self))
        key_row = QHBoxLayout()
        self.key_combo = QComboBox(self)
        self.key_combo.setEditable(True)
        self.key_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.key_combo.addItem("")
        self.key_combo.addItems(get_valid_key_names())
        completer = self.key_combo.completer()
        if completer is not None:
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.key_combo.editTextChanged.connect(self._update_preview)
        key_row.addWidget(self.key_combo, 1)

        self.record_button = QPushButton("Record", self)
        self.record_button.setCheckable(True)
        self.record_button.setToolTip("Capture a key combination by pressing it")
        self.record_button.toggled.connect(self._toggle_recording)
        key_row.addWidget(self.record_button)
        layout.addLayout(key_row)

        self.preview = QLabel(self)
        layout.addWidget(self.preview)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._load_initial(initial)
        self._update_preview()

    def _load_initial(self, initial: str) -> None:
        # Only the first section (before any ",") maps onto the builder.
        first_section = initial.split(",")[0]
        for part in (p.strip().lower() for p in first_section.split("+")):
            if not part:
                continue
            if part in self._modifier_boxes:
                self._modifier_boxes[part].setChecked(True)
            else:
                self.key_combo.setEditText(part)

    def combination(self) -> str:
        modifiers = [name for name in KEY_COMBO_MODIFIERS if self._modifier_boxes[name].isChecked()]
        key = self.key_combo.currentText().strip().lower()
        parts = modifiers + ([key] if key else [])
        return "+".join(parts)

    def _update_preview(self, *_args) -> None:
        combo = self.combination()
        self.preview.setText(f"Result:  {combo}" if combo else "Result:  (empty)")
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setEnabled(bool(combo))

    def _toggle_recording(self, recording: bool) -> None:
        self._recording = recording
        self.record_button.setText("Press a key…" if recording else "Record")
        if recording:
            self.grabKeyboard()
        else:
            self.releaseKeyboard()

    def keyPressEvent(self, event) -> None:
        if not self._recording:
            super().keyPressEvent(event)
            return
        if event.key() in self._LONE_MODIFIERS:
            return

        modifiers = event.modifiers()
        self._modifier_boxes["ctrl"].setChecked(bool(modifiers & Qt.KeyboardModifier.ControlModifier))
        self._modifier_boxes["shift"].setChecked(bool(modifiers & Qt.KeyboardModifier.ShiftModifier))
        self._modifier_boxes["alt"].setChecked(bool(modifiers & Qt.KeyboardModifier.AltModifier))
        self._modifier_boxes["super"].setChecked(bool(modifiers & Qt.KeyboardModifier.MetaModifier))
        if "alt_gr" in self._modifier_boxes:
            self._modifier_boxes["alt_gr"].setChecked(bool(modifiers & Qt.KeyboardModifier.GroupSwitchModifier))

        name = qt_key_to_evdev_name(event.key(), event.text())
        if name is not None:
            self.key_combo.setEditText(name)

        # Stop recording (releases the keyboard grab via the toggled handler).
        self.record_button.setChecked(False)
        self._update_preview()

    def closeEvent(self, event) -> None:
        if self._recording:
            self.releaseKeyboard()
        super().closeEvent(event)


def show_key_combine_dialog(ui: Ui_ButtonForm) -> None:
    """Opens the key-combination builder and writes the result into the Press
    Keys field of the selected button."""
    deck_id = _deck()
    page_id = _page()
    button_id = _button()
    if deck_id is None or page_id is None or button_id is None:
        return

    dialog = KeyCombineDialog(main_window, ui.keys.text())
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    combo = dialog.combination()
    if not combo:
        return

    blocker = QSignalBlocker(ui.keys)
    ui.keys.setText(combo)
    del blocker
    update_button_attribute("keys", combo)


# Ready-made multimedia / brightness key actions. The values are evdev key
# names accepted by the "Press Keys" field.
MEDIA_KEY_PRESETS = [
    ("Volume Up", "volumeup"),
    ("Volume Down", "volumedown"),
    ("Volume Mute", "mute"),
    ("Play / Pause", "playpause"),
    ("Next Track", "nextsong"),
    ("Previous Track", "previoussong"),
    ("Stop", "stopcd"),
    ("Brightness Up", "brightnessup"),
    ("Brightness Down", "brightnessdown"),
]


def apply_media_preset(ui: Ui_ButtonForm, keys: str, _checked: bool = False) -> None:
    """Sets the selected button's Press Keys action to a media/brightness key."""
    deck_id = _deck()
    page_id = _page()
    button_id = _button()

    if deck_id is None or page_id is None or button_id is None:
        return

    blocker = QSignalBlocker(ui.keys)
    ui.keys.setText(keys)
    del blocker
    update_button_attribute("keys", keys)


def configure_page_navigation(ui: Ui_ButtonForm, direction: str, _checked: bool = False) -> None:
    """Turns the selected key into a page navigation key. It sets the relative
    switch-page action and applies a premade icon so the key works out of the
    box. ``direction`` is ``next``/``previous`` for relative paging or
    ``auto``/``leave_auto`` to enter/leave the Auto group."""
    deck_id = _deck()
    page_id = _page()
    button_id = _button()

    if deck_id is None or page_id is None or button_id is None:
        return

    icon: Optional[str]
    if direction == "next":
        switch_page, icon = SWITCH_PAGE_NEXT, NEXT_PAGE_ICON
    elif direction == "previous":
        switch_page, icon = SWITCH_PAGE_PREVIOUS, PREVIOUS_PAGE_ICON
    elif direction == "auto":
        switch_page, icon = SWITCH_PAGE_AUTO, render_named_solid_icon("wand-magic-sparkles")
    else:
        switch_page, icon = SWITCH_PAGE_LEAVE_AUTO, render_named_solid_icon("right-from-bracket")

    # Clear any absolute page number shown in the spinbox first (this fires the
    # valueChanged signal and stores 0), then store the relative sentinel.
    ui.switch_page.setValue(0)
    update_button_attribute("switch_page", switch_page)
    if icon:
        update_displayed_button_attribute("icon", icon)


def update_align_text_vertical() -> None:
    deck_id = _deck()
    page_id = _page()
    button_id = _button()
    align_changes = {
        "": "middle-bottom",
        "bottom": "middle-bottom",
        "middle-bottom": "middle",
        "middle": "middle-top",
        "middle-top": "top",
    }
    if deck_id is not None and page_id is not None and button_id is not None:
        current_position = api.get_button_text_vertical_align(deck_id, page_id, button_id)
        next_position = align_changes.get(current_position, "")
        update_displayed_button_attribute("text_vertical_align", next_position)


def update_align_text_horizontal() -> None:
    deck_id = _deck()
    page_id = _page()
    button_id = _button()
    align_changes = {
        "": "left",
        "left": "right",
        "center": "left",
    }
    if deck_id is not None and page_id is not None and button_id is not None:
        current_position = api.get_button_text_horizontal_align(deck_id, page_id, button_id)
        next_position = align_changes.get(current_position, "")
        update_displayed_button_attribute("text_horizontal_align", next_position)


@debounce(timeout=500)
def debounced_update_button_text(ui: Ui_ButtonForm) -> None:
    """Instead of directly updating the text (label) associated with
    the button, add a small delay. If this is called before the
    timer fires, delay it again. Effectively this creates an update
    queue. It makes the textbox more response, as rendering the button
    and saving to the API each time can feel somewhat slow.
    """
    text = ui.text.toPlainText()
    update_displayed_button_attribute("text", text)


@debounce(timeout=500)
def debounced_update_button_attribute(attribute: str, value: str) -> None:
    """Instead of directly updating the attribute associated with
    the button, add a small delay. If this is called before the
    timer fires, delay it again. Effectively this creates an update
    queue. It makes the textbox more response, as rendering the button
    and saving to the API each time can feel somewhat slow.
    """
    update_button_attribute(attribute, value)


def update_button_attribute_font(ui: Ui_ButtonForm, kind: str) -> None:
    """Update the font associated with the button"""
    font_family = ui.text_font.currentText()
    font_style = ui.text_font_style.currentText()
    # when the font family changes, update the font style list
    if kind == "family":
        prepare_button_state_form_text_font_style_list(ui, font_family, "")
        font_style = list(FONTS_DICT[font_family])[0]

    font = FONTS_DICT[font_family][font_style]

    # if the font is not valid, we roll back the change to current value
    # in case rollback fails, we set the default font
    if is_a_valid_text_filter_font(font):
        update_displayed_button_attribute("font", font)
    else:
        deck_id = _deck()
        page_id = _page()
        button_id = _button()
        if deck_id is not None and page_id is not None and button_id is not None:
            current_font = api.get_button_font(deck_id, page_id, button_id)
            font_family, _ = find_font_info(current_font)
            ui.text_font.setCurrentText(font_family)
        else:
            ui.text_font.setCurrentText(DEFAULT_FONT_FAMILY)


def _reset_build_button_state_form(ui: Ui_ButtonForm):
    """Clears the configuration for a button and disables editing of them."""
    ui.text.clear()
    ui.command.clear()
    ui.keys.clear()
    ui.text_font.clearEditText()
    ui.text_font_size.setValue(0)
    ui.text_color.setPalette(QPalette(DEFAULT_FONT_COLOR))
    ui.background_color.setPalette(QPalette(DEFAULT_BACKGROUND_COLOR))
    ui.write.clear()
    ui.change_brightness.setValue(0)
    ui.switch_page.setValue(0)
    ui.switch_state.setValue(0)


def browse_documentation():
    url = QUrl("https://streamdeck-linux-gui.github.io/streamdeck-linux-gui/")
    QDesktopServices.openUrl(url)


def browse_github():
    url = QUrl("https://github.com/streamdeck-linux-gui/streamdeck-linux-gui")
    QDesktopServices.openUrl(url)


def build_buttons(ui, tab) -> None:
    global selected_button

    if hasattr(tab, "deck_buttons"):
        buttons = tab.findChildren(QToolButton)
        for button in buttons:
            button.hide()
            # Mark them as hidden. They will be GC'd later
            button.deleteLater()

        tab.deck_buttons.hide()
        tab.deck_buttons.deleteLater()
        # Remove the inner page
        del tab.children()[0]
        # Remove the property
        del tab.deck_buttons

    selected_button = None
    # When rebuilding any selection is cleared

    deck_id = _deck()

    if not deck_id:
        return
    deck_rows, deck_columns = api.get_deck_layout(deck_id)

    # Create a new base_widget with tab as it's parent
    # This is effectively a "blank tab"
    base_widget = QWidget(tab)

    # Add an inner page (QtWidget) to the page
    tab.children()[0].addWidget(base_widget)

    # Set a property - this allows us to check later
    # if we've already created the buttons
    tab.deck_buttons = base_widget

    row_layout = QVBoxLayout(base_widget)
    index = 0
    buttons = []
    for _row in range(deck_rows):
        column_layout = QHBoxLayout()
        row_layout.addLayout(column_layout)

        for _column in range(deck_columns):
            button = DraggableButton(base_widget, ui, api)
            button.setCheckable(True)
            button.setProperty("index", index)
            button.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            button.setIconSize(QSize(80, 80))
            button.setStyleSheet(BUTTON_STYLE)
            buttons.append(button)
            column_layout.addWidget(button)
            index += 1

        column_layout.addStretch(1)
    row_layout.addStretch(1)

    # Note that the button click event captures the ui variable, the current button
    #  and all the other buttons
    for button in buttons:
        button.clicked.connect(
            lambda checked=False, current_button=button, all_buttons=buttons: button_clicked(
                current_button, all_buttons
            )
        )


def export_config(window, api) -> None:
    file_name = QFileDialog.getSaveFileName(
        window, "Export Config", os.path.expanduser("~/streamdeck_ui_export.json"), "JSON (*.json)"
    )[0]
    if not file_name:
        return

    api.export_config(file_name)


def import_config(window, api) -> None:
    file_name = QFileDialog.getOpenFileName(window, "Import Config", os.path.expanduser("~"), "Config Files (*.json)")[
        0
    ]
    if not file_name:
        return

    api.import_config(file_name)
    redraw_buttons()


def _build_tab_label(prefix: str, page_id: int) -> str:
    return f"{prefix} {page_id + 1}" if page_id == 0 else f"{page_id + 1}"


def build_device(ui, _device_index=None) -> None:
    """This method builds the device configuration user interface.
    It is called if you switch to a different Stream Deck,
    a Stream Deck is added or when the last one is removed.
    It must deal with the case where there is no Stream Deck as
    a result.
    """
    blocker = QSignalBlocker(ui.pages)
    try:
        deck_id = _deck()
        style = DEVICE_PAGE_STYLE if ui.device_list.count() > 0 else ""

        # the device was removed while we were building the ui, then we skip
        if deck_id is None:
            return

        # On first use, seed the Auto group with one page per control preset,
        # bound to its application (done once per deck).
        if not api.is_auto_seeded(deck_id):
            api.seed_default_auto_pages(deck_id)
            update_focus_watcher(ui)

        # clear the pages
        if ui.pages.count() > 0:
            ui.pages.clear()

        current_page = api.get_page(deck_id)
        active_tab_index = 0

        auto_pages = api.get_auto_pages(deck_id)
        overlay_page = api.get_overlay_page(deck_id)

        # Add the normal pages only. Auto pages and the overlay live inside the
        # Auto tab and are edited in place there (no separate tab in the strip).
        for page_id in api.get_pages(deck_id):
            if page_id in auto_pages or page_id == overlay_page:
                continue
            page = QWidget()
            page.setLayout(QGridLayout())
            page.setProperty("deck_id", deck_id)
            page.setProperty("page_id", page_id)
            page.setStyleSheet(style)
            label = _build_tab_label("Page", page_id)
            tab_index = ui.pages.addTab(page, label)
            page_tab = ui.pages.widget(tab_index)
            build_buttons(ui, page_tab)
            if page_id == current_page:
                active_tab_index = tab_index

        # Append the synthetic Auto tab (a manager for the auto pages + overlay).
        auto_tab_index = ui.pages.addTab(_build_auto_tab(ui, deck_id), "Auto")

        # If the deck is currently on an auto page, the Auto tab represents it.
        if current_page in auto_pages or current_page == overlay_page:
            active_tab_index = auto_tab_index

        # A built-in Snake mini-game (purely in-window; not tied to a deck page).
        snake_tab = QWidget()
        snake_tab.setProperty("deck_id", deck_id)
        snake_layout = QVBoxLayout(snake_tab)
        snake_layout.setContentsMargins(0, 0, 0, 0)
        snake_layout.addWidget(SnakeGame(snake_tab))
        ui.pages.addTab(snake_tab, "🐍 Snake")

        # Only real (page-bearing) tabs count towards the "can a page be removed" check.
        normal_tabs = sum(1 for tab in range(ui.pages.count()) if ui.pages.widget(tab).property("page_id") is not None)
        ui.remove_page.setEnabled(normal_tabs > 1)

        if ui.device_list.count() > 0:
            ui.settingsButton.setEnabled(True)
            ui.add_page.setEnabled(True)
            # Set the active page for this device
            ui.pages.setCurrentIndex(active_tab_index)

            # Show which application each page is bound to.
            refresh_focus_tab_tooltips(ui, deck_id)
            # Baseline for "return to the last manual page" is the current page.
            last_manual_page.setdefault(deck_id, api.get_page(deck_id))

            # Draw the buttons for the active page
            redraw_buttons()
        else:
            ui.settingsButton.setEnabled(False)
            ui.add_page.setEnabled(False)
    finally:
        blocker.unblock()


class MainWindow(QMainWindow):
    """Represents the main streamdeck-ui configuration Window. A QMainWindow
    object provides a lot of standard main window features out the box.

    The QtCreator UI designer allows you to create a UI quickly. It compiles
    into a class called Ui_MainWindow() and everything comes together by
    calling the setupUi() method and passing a reference to the QMainWindow.
    """

    ui: Ui_MainWindow
    "A reference to all the UI objects for the main window"

    tray: QSystemTrayIcon
    "A reference to the system tray icon"

    window_shown: bool
    settings: QSettings

    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.window_shown = True
        self.settings = QSettings("streamdeck-ui", "streamdeck-ui")
        self.restoreGeometry(self.settings.value("geometry", self.saveGeometry()))

    def closeEvent(self, event) -> None:  # noqa: N802 - Part of QT signature.
        self.settings.setValue("geometry", self.saveGeometry())
        self.window_shown = False
        self.hide()
        event.ignore()

    def systray_clicked(self, status=None) -> None:
        if status is QSystemTrayIcon.ActivationReason.Context:
            return
        if self.window_shown:
            self.hide()
            self.window_shown = False
            return

        self.bring_to_top()

    def bring_to_top(self):
        self.show()
        self.activateWindow()
        self.raise_()
        self.window_shown = True

    def about_dialog(self):
        title = "About StreamDeck UI"
        description = "A Linux compatible UI for the Elgato Stream Deck."
        app = QApplication.instance()
        body = [description, "Version {}\n".format(app.applicationVersion())]
        dependencies = ("streamdeck", "pyside6", "pillow", "evdev")
        for dep in dependencies:
            try:
                dist_version = version(dep)
                body.append("{} {}".format(dep, dist_version))
            except PackageNotFoundError:
                pass
        QMessageBox.about(self, title, "\n".join(body))


def update_displayed_button_attribute(attribute: str, value: Union[str, int]) -> None:
    """Updates the given attribute for the currently selected button.
    and updates the icon of the current selected button."""
    updated = update_button_attribute(attribute, value)

    if not updated:
        return

    deck_id = _deck()
    page_id = _page()
    button_id = _button()

    if deck_id is None or page_id is None or button_id is None:
        return

    icon = api.get_button_icon_pixmap(deck_id, page_id, button_id)
    if icon is not None and selected_button is not None:
        selected_button.setIcon(icon)


def update_live_source(tab_ui: Ui_ButtonForm, _index: int = 0) -> None:
    """Applies the chosen live information source to the selected button and
    refreshes its preview so the live value (or restored text) shows at once."""
    source = tab_ui.live_source.currentData() or ""
    update_displayed_button_attribute("live_source", source)


def update_button_attribute(attribute: str, value: Union[str, int]) -> bool:
    """
    Updates the given attribute for the currently selected button.
    and updates the icon of the current selected button.
    """
    deck_id = _deck()
    page_id = _page()
    button_id = _button()

    if deck_id is None or page_id is None or button_id is None:
        return False

    update_function = getattr(api, f"set_button_{attribute}")
    update_function(deck_id, page_id, button_id, value)

    return True


def change_brightness(deck_id: str, brightness: int):
    """Changes the brightness of the given streamdeck, but does not save
    the state."""
    api.decks_by_serial[deck_id].set_brightness(brightness)


class SettingsDialog(QDialog):
    ui: Ui_SettingsDialog

    def __init__(self, parent):
        super().__init__(parent)
        self.ui = Ui_SettingsDialog()
        self.ui.setupUi(self)
        self.show()


def show_settings(window: MainWindow) -> None:
    """Shows the settings dialog and allows the user the change deck specific
    settings. Settings are not saved until OK is clicked."""
    deck_id = _deck()

    if deck_id is None:
        return

    settings = SettingsDialog(window)
    api.stop_dimmer(deck_id)

    for label, value in dimmer_options.items():
        settings.ui.dim.addItem(f"{label}", userData=value)

    existing_timeout = api.get_display_timeout(deck_id)
    existing_index = next((i for i, (k, v) in enumerate(dimmer_options.items()) if v == existing_timeout), None)

    if existing_index is None:
        settings.ui.dim.addItem(f"Custom: {existing_timeout}s", userData=existing_timeout)
        existing_index = settings.ui.dim.count() - 1
        settings.ui.dim.setCurrentIndex(existing_index)
    else:
        settings.ui.dim.setCurrentIndex(existing_index)

    existing_brightness_dimmed = api.get_brightness_dimmed(deck_id)
    settings.ui.brightness_dimmed.setValue(existing_brightness_dimmed)

    settings.ui.label_streamdeck.setText(deck_id)
    settings.ui.brightness.setValue(api.get_brightness(deck_id))
    settings.ui.brightness.valueChanged.connect(partial(change_brightness, deck_id))
    settings.ui.dim.currentIndexChanged.connect(partial(disable_dim_settings, settings))
    if settings.exec():
        if existing_index != settings.ui.dim.currentIndex():
            api.set_display_timeout(deck_id, settings.ui.dim.currentData())
        set_brightness(settings.ui.brightness.value())
        set_brightness_dimmed(settings.ui.brightness_dimmed.value())
    else:
        # User cancelled, reset to original brightness
        change_brightness(deck_id, api.get_brightness(deck_id))

    api.reset_dimmer(deck_id)


def disable_dim_settings(settings: SettingsDialog, _index: int) -> None:
    disable = dimmer_options.get(settings.ui.dim.currentText()) == 0
    settings.ui.brightness_dimmed.setDisabled(disable)
    settings.ui.label_brightness_dimmed.setDisabled(disable)


def toggle_dim_all() -> None:
    api.toggle_dimmers()


def change_brightness_all(amount: int) -> None:
    """Adjusts the brightness of every connected deck by the given amount.
    Used by the system tray brightness up/down actions."""
    for deck_id in api.decks_by_serial:
        api.change_brightness(deck_id, amount)


def _selected_theme_name() -> str:
    """Returns the theme key for the currently checked View-menu theme action."""
    ui = main_window.ui
    if ui.actionThemeXP.isChecked():
        return THEME_XP
    if ui.actionThemeModern.isChecked():
        return THEME_MODERN
    return THEME_DEFAULT


def _apply_current_theme() -> None:
    """Applies the selected base theme together with the dark-mode toggle."""
    app = QApplication.instance()
    if app is None or main_window is None:
        return
    apply_theme(
        app,
        _selected_theme_name(),
        main_window.ui.actionDarkMode.isChecked(),
        get_modern_accent(main_window.settings),
    )


def select_theme(theme: str, _checked: bool = False) -> None:
    """Applies and persists the chosen base theme (default / XP / modern).

    The base theme is independent of dark mode, which is applied on top."""
    if main_window is None:
        return
    _apply_current_theme()
    set_theme(main_window.settings, theme)


def toggle_dark_mode(checked: bool) -> None:
    """Applies and persists dark mode. Dark mode darkens whichever base theme is
    currently selected, so it is independent of the theme choice."""
    if main_window is None:
        return
    _apply_current_theme()
    set_dark_mode_enabled(main_window.settings, checked)


def choose_modern_accent() -> None:
    """Lets the user pick the Modern theme accent colour, then applies it.

    Switches to the Modern theme if it is not already active so the change is
    visible immediately."""
    if main_window is None:
        return
    current = QColor(get_modern_accent(main_window.settings))
    color = QColorDialog.getColor(current, main_window, "Choose the modern theme accent colour")
    if not color.isValid():
        return
    set_modern_accent(main_window.settings, color.name())
    if not main_window.ui.actionThemeModern.isChecked():
        main_window.ui.actionThemeModern.setChecked(True)
        set_theme(main_window.settings, THEME_MODERN)
    _apply_current_theme()


def _switch_to_page(ui, deck_id: str, target_page: int) -> None:
    """Switches a deck to the given page and reflects it in the UI when that
    deck is the one currently shown. Marked as a focus-driven switch so it is
    not recorded as a manual page selection."""
    global _focus_switching
    _focus_switching = True
    try:
        api.set_page(deck_id, target_page)
        if _deck() == deck_id:
            auto = api.is_auto_page(deck_id, target_page)
            for tab in range(ui.pages.count()):
                widget = ui.pages.widget(tab)
                # An (unrevealed) auto page is represented by the Auto tab.
                if widget.property("page_id") == target_page or (auto and widget.property("auto_tab")):
                    ui.pages.setCurrentIndex(tab)
                    break
    finally:
        _focus_switching = False


def handle_focus_changed(ui, app: str) -> None:
    """Switches each deck to the page bound to the now-focused application.

    Switching only happens while the deck is already inside the Auto group ("on
    the auto tab"): the deck follows the focused application between its auto
    pages, falling back to the Home dashboard when the focused app has no preset.
    Runs in the GUI thread (queued signal from the watcher)."""
    global _last_focused_app
    _last_focused_app = app
    for deck_id in list(api.decks_by_serial.keys()):
        try:
            auto_pages = api.get_auto_pages(deck_id)
            # Only follow the focus while the deck is in the Auto group.
            if not auto_pages or api.get_page(deck_id) not in auto_pages:
                continue

            target_page = api.get_focus_pages(deck_id).get(app)
            # The focused app has no auto page of its own; fall back to the Home
            # dashboard (and only stay put if there is no Home page either).
            if target_page is None or target_page not in auto_pages:
                target_page = api.get_home_page(deck_id)
            if target_page is None or target_page not in auto_pages:
                continue
            if api.get_page(deck_id) == target_page:
                continue
            api.reset_dimmer(deck_id)
            _switch_to_page(ui, deck_id, target_page)
        except Exception as error:  # noqa: BLE001 - a deck may detach mid-iteration
            print(f"Could not switch page for the focused application: {error}")


def update_focus_watcher(ui) -> None:
    """Starts or stops the focus watcher depending on whether any attached deck
    has auto pages to follow the focused application between."""
    global focus_watcher
    wanted = any(api.get_auto_pages(deck_id) for deck_id in api.decks_by_serial)

    if wanted and focus_watcher is None:
        focus_watcher = FocusWatcher()
        focus_watcher.focus_changed.connect(partial(handle_focus_changed, ui))
        focus_watcher.start()
    elif not wanted and focus_watcher is not None:
        focus_watcher.stop()
        focus_watcher = None


def stop_focus_watcher() -> None:
    """Stops the focus watcher if it is running."""
    global focus_watcher
    if focus_watcher is not None:
        focus_watcher.stop()
        focus_watcher = None


def refresh_focus_tab_tooltips(ui, deck_id: str) -> None:
    """Shows the bound application in each page tab's label and tooltip."""
    for tab in range(ui.pages.count()):
        widget = ui.pages.widget(tab)
        page_id = widget.property("page_id")
        if page_id is None:  # the synthetic Auto tab carries no page id
            continue
        # Auto pages and the overlay keep their Auto-tab labels.
        if page_id in api.get_auto_pages(deck_id) or page_id == api.get_overlay_page(deck_id):
            continue
        base_label = _build_tab_label("Page", page_id)
        app = api.get_focus_app_for_page(deck_id, page_id)
        ui.pages.setTabText(tab, f"{base_label}  ·  {app}" if app else base_label)
        ui.pages.setTabToolTip(tab, f"Shown when '{app}' is focused" if app else "")


class PageSettingsDialog(QDialog):
    """Per-page settings. Lets the user bind the page to an application so it is
    shown automatically when that application is focused."""

    def __init__(self, parent, page_label: str, current_app: Optional[str], candidates: List[str]):
        super().__init__(parent)
        self.setWindowTitle(f"Page Settings — {page_label}")
        self.resize(420, 150)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Show this page automatically when this application is focused:", self))

        row = QHBoxLayout()
        self.app = QComboBox(self)
        self.app.setEditable(True)
        self.app.addItem("")  # empty entry = no binding
        for candidate in candidates:
            self.app.addItem(candidate)
        self.app.setCurrentText(current_app or "")
        row.addWidget(self.app)

        self.use_focused = QPushButton("Use focused", self)
        self.use_focused.setToolTip("Fill in the application that is focused right now")
        row.addWidget(self.use_focused)
        layout.addLayout(row)

        hint = QLabel(
            "Leave empty for no binding. Detection works on X11, Sway and Hyprland "
            "(and KDE with kdotool); some Wayland compositors (e.g. GNOME) are not supported.",
            self,
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: grey;")
        layout.addWidget(hint)

        self.clone_requested = False
        self.clone_page = QPushButton("Clone this page", self)
        self.clone_page.setToolTip("Create a copy of this page with all of its buttons")
        layout.addWidget(self.clone_page)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        layout.addWidget(self.button_box)

        self.use_focused.clicked.connect(self._fill_focused)
        self.clone_page.clicked.connect(self._request_clone)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def _request_clone(self) -> None:
        self.clone_requested = True
        self.accept()

    def _fill_focused(self) -> None:
        app = get_focused_app()
        if app:
            self.app.setCurrentText(app)
        else:
            QMessageBox.information(
                self,
                "Focused application not detected",
                "The focused application could not be detected on this system.",
            )

    def selected_app(self) -> Optional[str]:
        text = self.app.currentText().strip().lower()
        return text or None


def show_page_settings(window: "MainWindow") -> None:
    """Opens the per-page settings dialog for the current page."""
    deck_id = _deck()
    page_id = _page()
    if deck_id is None or page_id is None:
        return

    current_app = api.get_focus_app_for_page(deck_id, page_id)
    candidates = sorted(set(list_open_apps()) | set(api.get_focus_pages(deck_id).keys()))

    dialog = PageSettingsDialog(window, _build_tab_label("Page", page_id), current_app, candidates)
    if not dialog.exec():
        return

    if dialog.clone_requested is True:
        handle_clone_page()
        return

    app = dialog.selected_app()
    # Replace any existing binding for this page.
    api.remove_focus_page(deck_id, page_id)
    if app:
        api.set_focus_page(deck_id, app, page_id)
    refresh_focus_tab_tooltips(window.ui, deck_id)
    update_focus_watcher(window.ui)


class AppBindingDialog(QDialog):
    """Picks the application a preset page follows, with a 5-second *detect*
    button (so the target window can be focused first) and an optional control
    preset to seed a new page with."""

    _DETECT_SECONDS = 5

    def __init__(self, parent, title: str, current_app: Optional[str], candidates: List[str], with_preset: bool):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(440, 170)
        self._remaining = 0

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Application (its window class / app id) shown on this auto page:", self))

        row = QHBoxLayout()
        self.app = QComboBox(self)
        self.app.setEditable(True)
        self.app.addItem("")
        for candidate in candidates:
            self.app.addItem(candidate)
        self.app.setCurrentText(current_app or "")
        row.addWidget(self.app, 1)

        self.detect = QPushButton("Detect application (5s)", self)
        self.detect.setToolTip("Wait 5 seconds — focus the target window — then capture the focused application")
        row.addWidget(self.detect)
        layout.addLayout(row)

        self.preset: Optional[QComboBox] = None
        if with_preset:
            layout.addWidget(QLabel("Fill the new page with a control preset:", self))
            self.preset = QComboBox(self)
            self.preset.addItem("(blank page)", userData=None)
            for preset in CONTROL_PRESETS:
                self.preset.addItem(preset.name, userData=preset)
            layout.addWidget(self.preset)

        hint = QLabel(
            "Detection works on X11, Sway and Hyprland (and KDE with kdotool); some "
            "Wayland compositors (e.g. GNOME) are not supported.",
            self,
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: grey;")
        layout.addWidget(hint)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        layout.addWidget(self.button_box)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self.detect.clicked.connect(self._start_detect)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def _start_detect(self) -> None:
        self._remaining = self._DETECT_SECONDS
        self.detect.setEnabled(False)
        self.detect.setText(f"Detecting in {self._remaining}…")
        self._timer.start()

    def _tick(self) -> None:
        self._remaining -= 1
        if self._remaining > 0:
            self.detect.setText(f"Detecting in {self._remaining}…")
            return
        self._timer.stop()
        self.detect.setEnabled(True)
        self.detect.setText("Detect application (5s)")
        app = get_focused_app()
        if app:
            self.app.setCurrentText(app)
        else:
            QMessageBox.information(
                self,
                "Focused application not detected",
                "The focused application could not be detected on this system.",
            )

    def selected_app(self) -> Optional[str]:
        text = self.app.currentText().strip().lower()
        return text or None

    def selected_preset(self) -> Optional[ControlPreset]:
        return self.preset.currentData() if self.preset is not None else None


def _build_auto_tab(ui, deck_id: str) -> QWidget:
    """Builds the synthetic Auto tab: a stacked widget whose first page is the
    AutoPagePanel (the list of auto pages + overlay) and whose second page is an
    in-place button editor, so editing an auto page never adds a tab to the strip."""
    auto_tab = QWidget()
    auto_tab.setProperty("deck_id", deck_id)
    auto_tab.setProperty("auto_tab", True)
    auto_tab.editing_page = None  # type: ignore[attr-defined]

    outer = QVBoxLayout(auto_tab)
    outer.setContentsMargins(0, 0, 0, 0)
    stack = QStackedWidget(auto_tab)
    outer.addWidget(stack)

    # The editor: a back bar plus a button grid the existing editing UI fills in.
    editor = QWidget()
    editor_layout = QVBoxLayout(editor)
    editor_layout.setContentsMargins(0, 0, 0, 0)
    top = QHBoxLayout()
    back = QPushButton("← Back to Auto list", editor)
    label = QLabel("", editor)
    top.addWidget(back)
    top.addWidget(label, 1)
    editor_layout.addLayout(top)
    grid = QWidget(editor)
    grid.setLayout(QGridLayout())
    grid.setProperty("deck_id", deck_id)
    grid.setStyleSheet(DEVICE_PAGE_STYLE)
    editor_layout.addWidget(grid, 1)

    panel = AutoPagePanel(auto_tab, ui, deck_id, stack, editor, grid, label, back)
    stack.addWidget(panel)
    stack.addWidget(editor)
    stack.setCurrentWidget(panel)

    auto_tab.auto_stack = stack  # type: ignore[attr-defined]
    auto_tab.auto_panel = panel  # type: ignore[attr-defined]
    return auto_tab


def _rebuild_to_auto_tab(ui) -> None:
    """Rebuilds the device UI and selects the Auto tab (it is always last)."""
    build_device(ui)
    if ui.pages.count():
        ui.pages.setCurrentIndex(ui.pages.count() - 1)


class AutoPagePanel(QWidget):
    """The contents of the Auto tab: a manager for the per-application auto pages
    and the shared overlay drawn on top of them. Editing a page happens in place
    (in the Auto tab's stacked editor), so no extra tab appears in the strip."""

    def __init__(self, auto_tab, ui, deck_id: str, stack, editor, grid, label, back):
        super().__init__(auto_tab)
        self._ui = ui
        self._deck_id = deck_id
        self._auto_tab = auto_tab
        self._stack = stack
        self._editor = editor
        self._grid = grid
        self._label = label

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Auto pages follow the focused application while the deck is in the Auto group. "
            "Add a page per application, then use a 'Go to Auto' key to enter and a 'Leave Auto' "
            "key (handy on the overlay) to return.",
            self,
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.list = QListWidget(self)
        layout.addWidget(self.list, 1)

        buttons = QHBoxLayout()
        self.add_button = QPushButton("Add application", self)
        self.change_button = QPushButton("Change application", self)
        self.edit_button = QPushButton("Edit buttons", self)
        self.remove_button = QPushButton("Remove", self)
        for button in (self.add_button, self.change_button, self.edit_button, self.remove_button):
            buttons.addWidget(button)
        layout.addLayout(buttons)

        overlay_row = QHBoxLayout()
        overlay_row.addWidget(QLabel("Overlay (drawn on top of every auto page):", self))
        self.edit_overlay_button = QPushButton("Edit overlay", self)
        self.remove_overlay_button = QPushButton("Remove overlay", self)
        overlay_row.addWidget(self.edit_overlay_button)
        overlay_row.addWidget(self.remove_overlay_button)
        layout.addLayout(overlay_row)

        reset_row = QHBoxLayout()
        reset_row.addStretch(1)
        self.reset_button = QPushButton("Reset to defaults", self)
        self.reset_button.setToolTip("Delete all auto pages and the overlay and restore the default presets")
        reset_row.addWidget(self.reset_button)
        layout.addLayout(reset_row)

        self.add_button.clicked.connect(self._add)
        self.change_button.clicked.connect(self._change)
        self.edit_button.clicked.connect(self._edit)
        self.remove_button.clicked.connect(self._remove)
        self.edit_overlay_button.clicked.connect(self._edit_overlay)
        self.remove_overlay_button.clicked.connect(self._remove_overlay)
        self.reset_button.clicked.connect(self._reset)
        back.clicked.connect(self._leave_editor)
        self.list.itemSelectionChanged.connect(self._update_enabled)
        self.list.itemDoubleClicked.connect(lambda _item: self._edit())

        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        home = api.get_home_page(self._deck_id)
        # Sort by application name; Home is pinned first and unbound pages last.
        entries = []
        for page in api.get_auto_pages(self._deck_id):
            app = api.get_focus_app_for_page(self._deck_id, page)
            if page == home:
                label, sort_key = "Home (shown when the focused app has no preset)", ""
            else:
                label, sort_key = (app or "(no application)"), (app or "\uffff").lower()
            entries.append((sort_key, label, page))
        for _key, label, page in sorted(entries, key=lambda entry: entry[0]):
            item = QListWidgetItem(f"{label}  —  Page {page + 1}", self.list)
            item.setData(Qt.ItemDataRole.UserRole, page)
        self.remove_overlay_button.setEnabled(api.get_overlay_page(self._deck_id) is not None)
        self._update_enabled()

    def _update_enabled(self) -> None:
        has_selection = self.list.currentItem() is not None
        self.change_button.setEnabled(has_selection)
        self.edit_button.setEnabled(has_selection)
        self.remove_button.setEnabled(has_selection)

    def _selected_page(self) -> Optional[int]:
        item = self.list.currentItem()
        return None if item is None else item.data(Qt.ItemDataRole.UserRole)

    def _candidates(self) -> List[str]:
        return sorted(set(list_open_apps()) | set(api.get_focus_pages(self._deck_id).keys()))

    def _enter_editor(self, page: int, title: str) -> None:
        """Shows the in-place button editor for an auto/overlay page."""
        self._auto_tab.editing_page = page
        self._label.setText(title)
        build_buttons(self._ui, self._grid)
        self._stack.setCurrentWidget(self._editor)
        api.set_page(self._deck_id, page)
        api.reset_dimmer(self._deck_id)
        redraw_buttons()
        self._mark_overlaid_keys(page)
        build_button_state_pages()

    def _mark_overlaid_keys(self, page: int) -> None:
        """Greys out and labels keys that the overlay covers on this page, so it
        is clear that editing them has no effect (the overlay wins)."""
        for button in self._grid.findChildren(QToolButton):
            index = button.property("index")
            if index is None:
                continue
            source_page, _ = api.resolve_overlay(self._deck_id, page, index)
            if source_page != page:
                button.setEnabled(False)
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
                button.setIcon(QIcon())
                button.setText("overlay")
                button.setToolTip("Covered by the overlay — editing this key has no effect here")

    def _leave_editor(self) -> None:
        """Returns from the editor to the auto-page list."""
        global selected_button
        self._auto_tab.editing_page = None
        selected_button = None
        self._stack.setCurrentWidget(self)
        entry = _auto_entry_page(self._deck_id)
        if entry is not None:
            api.set_page(self._deck_id, entry)
            api.reset_dimmer(self._deck_id)
        self.refresh()
        build_button_state_pages()

    def _add(self) -> None:
        dialog = AppBindingDialog(self, "Add auto page", None, self._candidates(), with_preset=True)
        if not dialog.exec():
            return
        api.add_auto_page(self._deck_id, dialog.selected_app() or "", dialog.selected_preset())
        self.refresh()
        update_focus_watcher(self._ui)

    def _change(self) -> None:
        page = self._selected_page()
        if page is None:
            return
        current = api.get_focus_app_for_page(self._deck_id, page)
        dialog = AppBindingDialog(self, "Change application", current, self._candidates(), with_preset=False)
        if not dialog.exec():
            return
        api.remove_focus_page(self._deck_id, page)
        app = dialog.selected_app()
        if app:
            api.set_focus_page(self._deck_id, app, page)
        self.refresh()
        update_focus_watcher(self._ui)

    def _edit(self) -> None:
        page = self._selected_page()
        if page is None:
            return
        app = api.get_focus_app_for_page(self._deck_id, page) or "(no application)"
        self._enter_editor(page, f"Editing auto page — {app}")

    def _remove(self) -> None:
        page = self._selected_page()
        if page is None:
            return
        confirm = QMessageBox(self)
        confirm.setWindowTitle("Remove auto page")
        confirm.setText("Remove this auto page and all of its buttons?")
        confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm.setDefaultButton(QMessageBox.StandardButton.No)
        confirm.setIcon(QMessageBox.Icon.Question)
        if confirm.exec() != QMessageBox.StandardButton.Yes:
            return
        api.remove_auto_page(self._deck_id, page)
        self.refresh()
        update_focus_watcher(self._ui)

    def _edit_overlay(self) -> None:
        overlay = api.get_overlay_page(self._deck_id)
        if overlay is None:
            overlay = api.add_new_page(self._deck_id)
            api.set_overlay_page(self._deck_id, overlay)
        self._enter_editor(overlay, "Editing overlay (drawn over every auto page)")

    def _remove_overlay(self) -> None:
        overlay = api.get_overlay_page(self._deck_id)
        if overlay is None:
            return
        confirm = QMessageBox(self)
        confirm.setWindowTitle("Remove overlay")
        confirm.setText("Remove the overlay layer and its page?")
        confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm.setDefaultButton(QMessageBox.StandardButton.No)
        confirm.setIcon(QMessageBox.Icon.Question)
        if confirm.exec() != QMessageBox.StandardButton.Yes:
            return
        api.clear_overlay_page(self._deck_id)
        api.remove_page(self._deck_id, overlay)
        self.refresh()

    def _reset(self) -> None:
        confirm = QMessageBox(self)
        confirm.setWindowTitle("Reset auto pages")
        confirm.setText(
            "Delete all auto pages and the overlay and restore the default presets?\n\nThis cannot be undone."
        )
        confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm.setDefaultButton(QMessageBox.StandardButton.No)
        confirm.setIcon(QMessageBox.Icon.Warning)
        if confirm.exec() != QMessageBox.StandardButton.Yes:
            return
        api.reset_auto_pages(self._deck_id)
        update_focus_watcher(self._ui)
        # Rebuild after the slot returns (this panel is replaced) and land on the
        # freshly seeded Auto tab.
        QTimer.singleShot(0, partial(_rebuild_to_auto_tab, self._ui))


class SnakeGame(QWidget):
    """A self-contained Snake mini-game in its own tab. The grid is the
    playfield; the rightmost column holds the direction controls and a restart
    button. Play with the on-screen controls or the arrow / WASD keys."""

    ROWS = 5
    COLS = 8  # the last column is the control column; the rest is playfield

    _EMPTY = "#15161b"
    _BODY = "#3aa657"
    _HEAD = "#7cfc8a"
    _FOOD = "#e05561"
    _DELTAS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._width = self.COLS - 1
        self._height = self.ROWS

        outer = QVBoxLayout(self)
        top_row = QHBoxLayout()
        self._status = QLabel(self)
        top_row.addWidget(self._status, 1)
        self._deck_button = QPushButton("Play on Stream Deck", self)
        self._deck_button.setToolTip("Take over the connected Stream Deck and play on its keys")
        self._deck_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._deck_button.clicked.connect(self._toggle_deck)
        top_row.addWidget(self._deck_button)
        outer.addLayout(top_row)

        board = QWidget(self)
        grid = QGridLayout(board)
        grid.setSpacing(4)
        outer.addWidget(board, 1)
        outer.addStretch(1)

        self._cells: Dict[Tuple[int, int], QToolButton] = {}
        for y in range(self._height):
            for x in range(self._width):
                cell = QToolButton(board)
                cell.setEnabled(False)
                cell.setFixedSize(QSize(54, 54))
                grid.addWidget(cell, y, x)
                self._cells[(x, y)] = cell

        for row, (label, action) in enumerate(
            [("▲", "up"), ("▼", "down"), ("◀", "left"), ("▶", "right"), ("⟳", "restart")]
        ):
            if row >= self.ROWS:
                break
            button = QPushButton(label, board)
            button.setFixedSize(QSize(54, 54))
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.clicked.connect(partial(self._control, action))
            grid.addWidget(button, row, self.COLS - 1)

        self._timer = QTimer(self)
        self._timer.setInterval(180)
        self._timer.timeout.connect(self._tick)
        self._reset()

    def _reset(self) -> None:
        cx, cy = self._width // 2, self._height // 2
        # The snake is a deque with the tail at index 0 and the head at index -1.
        self._snake: "deque[Tuple[int, int]]" = deque([(cx - 2, cy), (cx - 1, cy), (cx, cy)])
        self._dir = (1, 0)
        self._next_dir = (1, 0)
        self._alive = True
        self._score = 0
        self._place_food()
        self._render()
        self._status.setText("Snake — press an arrow (or a control) to start.  Score: 0")

    def _place_food(self) -> None:
        free = [(x, y) for x in range(self._width) for y in range(self._height) if (x, y) not in self._snake]
        self._food = random.choice(free) if free else None

    def _control(self, action: str) -> None:
        if action == "restart":
            self._reset()
        else:
            self._set_direction(self._DELTAS[action])
        self.setFocus()

    def _set_direction(self, delta: Tuple[int, int]) -> None:
        if not self._alive:
            return
        # Ignore a reversal straight back onto the neck.
        if delta == (-self._dir[0], -self._dir[1]):
            return
        self._next_dir = delta
        if not self._timer.isActive():
            self._timer.start()

    def _tick(self) -> None:
        if not self._alive:
            return
        self._dir = self._next_dir
        head_x, head_y = self._snake[-1]
        new_head = (head_x + self._dir[0], head_y + self._dir[1])

        will_grow = new_head == self._food
        body = set(self._snake)
        if not will_grow:
            body.discard(self._snake[0])  # the tail moves out of the way this tick
        if not (0 <= new_head[0] < self._width) or not (0 <= new_head[1] < self._height) or new_head in body:
            self._game_over()
            return

        self._snake.append(new_head)
        if will_grow:
            self._score += 1
            self._place_food()
            if self._food is None:
                self._game_over(win=True)
                return
            self._status.setText(f"Score: {self._score}")
        else:
            self._snake.popleft()
        self._render()

    def _game_over(self, win: bool = False) -> None:
        self._alive = False
        self._timer.stop()
        prefix = "You win! " if win else "Game over! "
        self._status.setText(f"{prefix}Score: {self._score}  —  press ⟳ to restart")

    def _render(self) -> None:
        head = self._snake[-1]
        body = set(self._snake)
        for (x, y), cell in self._cells.items():
            if (x, y) == head:
                color = self._HEAD
            elif (x, y) in body:
                color = self._BODY
            elif (x, y) == self._food:
                color = self._FOOD
            else:
                color = self._EMPTY
            cell.setStyleSheet(f"background-color: {color}; border: 1px solid #2a2c34; border-radius: 6px;")

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        mapping = {
            Qt.Key.Key_Up: "up",
            Qt.Key.Key_W: "up",
            Qt.Key.Key_Down: "down",
            Qt.Key.Key_S: "down",
            Qt.Key.Key_Left: "left",
            Qt.Key.Key_A: "left",
            Qt.Key.Key_Right: "right",
            Qt.Key.Key_D: "right",
        }
        action = mapping.get(event.key())
        if action is not None:
            self._control(action)
            event.accept()
        elif event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter) and not self._alive:
            self._control("restart")
            event.accept()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        self.setFocus()

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().hideEvent(event)
        self._timer.stop()
        # Leaving the tab returns the deck to its normal display.
        if deck_game is not None:
            deck_game.stop()
            self._deck_button.setText("Play on Stream Deck")

    def _toggle_deck(self) -> None:
        if deck_game is not None:
            deck_game.stop()
            self._deck_button.setText("Play on Stream Deck")
            return
        deck_id = _deck()
        deck = api.decks_by_serial.get(deck_id) if deck_id is not None else None
        if deck_id is None or deck is None or not deck.is_visual():
            QMessageBox.information(self, "No Stream Deck", "Connect a Stream Deck to play on its keys.")
            return
        rows, cols = api.get_deck_layout(deck_id)
        if cols < 2 or rows < 2:
            QMessageBox.information(self, "Stream Deck too small", "This Stream Deck has too few keys for the game.")
            return
        DeckSnake(main_window.ui, deck_id).start()
        self._deck_button.setText("Stop on Stream Deck")


class DeckSnake:
    """Plays Snake on the physical Stream Deck. While active it pauses the normal
    render loop and draws the game straight to the keys; the rightmost column
    becomes the controls. Two-button relative turning (turn left / turn right,
    plus restart) keeps it playable on any deck size."""

    _EMPTY = (18, 19, 24)
    _BODY = (58, 166, 87)
    _HEAD = (124, 252, 138)
    _FOOD = (224, 85, 97)
    _CONTROL_BG = (40, 42, 52)
    _CONTROL_ICONS = {"left": "rotate-left", "right": "rotate-right", "restart": "arrows-rotate"}

    def __init__(self, ui, deck_id: str):
        self._ui = ui
        self.deck_id = deck_id
        self.display = api.display_handlers[deck_id]
        self.rows, self.cols = api.get_deck_layout(deck_id)
        self.play_w = self.cols - 1
        self.play_h = self.rows
        self.model = SnakeModel(self.play_w, self.play_h)

        last = self.cols - 1
        self._controls: Dict[int, str] = {0 * self.cols + last: "left"}
        if self.rows >= 2:
            self._controls[1 * self.cols + last] = "right"
        if self.rows >= 3:
            self._controls[2 * self.cols + last] = "restart"
        self._icon_cache: Dict[str, Optional[Image.Image]] = {}

        self.timer = QTimer()
        self.timer.setInterval(180)
        self.timer.timeout.connect(self._tick)

    def start(self) -> None:
        global deck_game
        deck_game = self
        api.reset_dimmer(self.deck_id)
        self.display.stop()  # pause the normal render loop; we draw the keys directly
        self.model.reset()
        self._render()

    def stop(self, restore: bool = True) -> None:
        global deck_game
        self.timer.stop()
        if deck_game is self:
            deck_game = None
        if restore:
            try:
                self.display.start()  # resume normal rendering (redraws the page)
            except Exception as error:  # noqa: BLE001 - never let teardown crash the UI
                print(f"Could not resume the display after the on-deck game: {error}")

    def on_key(self, key: int) -> None:
        action = self._controls.get(key)
        if action == "restart":
            self.model.reset()
        elif action == "left":
            self.model.turn(left=True)
        elif action == "right":
            self.model.turn(left=False)
        else:
            return
        api.reset_dimmer(self.deck_id)
        if self.model.alive and not self.timer.isActive():
            self.timer.start()
        self._render()

    def _tick(self) -> None:
        if not self.model.step():
            self.timer.stop()
        self._render()

    def _render(self) -> None:
        try:
            head = self.model.head
            body = set(self.model.snake)
            for index in range(self.rows * self.cols):
                self.display.set_image(index, self._key_image(index, body, head))
        except Exception as error:  # noqa: BLE001 - rendering must never crash the game/UI
            print(f"Snake render error: {error}")

    def _key_image(self, index: int, body: set, head: Tuple[int, int]) -> Image.Image:
        if index in self._controls:
            return self._control_image(self._controls[index])
        col, row = index % self.cols, index // self.cols
        if col < self.play_w and row < self.play_h:
            cell = (col, row)
            if cell == head:
                color = self._HEAD
            elif cell in body:
                color = self._BODY
            elif cell == self.model.food:
                color = self._FOOD
            else:
                color = self._EMPTY
            return Image.new("RGB", self.display.size, color)
        return Image.new("RGB", self.display.size, (0, 0, 0))

    def _control_image(self, action: str) -> Image.Image:
        image = Image.new("RGB", self.display.size, self._CONTROL_BG)
        glyph = self._load_icon(action)
        if glyph is not None:
            image.paste(glyph, ((image.width - glyph.width) // 2, (image.height - glyph.height) // 2), glyph)
        return image

    def _load_icon(self, action: str) -> Optional[Image.Image]:
        if action not in self._icon_cache:
            icon: Optional[Image.Image] = None
            path = render_named_solid_icon(self._CONTROL_ICONS[action])
            if path:
                try:
                    glyph = Image.open(path).convert("RGBA")
                    side = int(min(self.display.size) * 0.6)
                    glyph.thumbnail((side, side))
                    icon = glyph
                except (OSError, ValueError):
                    icon = None
            self._icon_cache[action] = icon
        return self._icon_cache[action]


def build_control_presets_menu(ui) -> None:
    """Populates the Controls… button with a menu of application control
    surfaces that can be laid out onto the current page."""
    presets_menu = QMenu(ui.apply_preset)
    for preset in CONTROL_PRESETS:
        presets_menu.addAction(preset.name, partial(apply_control_preset_to_page, preset))
    ui.apply_preset.setMenu(presets_menu)


def apply_control_preset_to_page(preset: ControlPreset, _checked: bool = False) -> None:
    """Replaces the buttons on the current page with a preset's control keys.

    Each action is laid out on a key in order, filling as many keys as the page
    has; any remaining keys are cleared so the page is a clean control surface.
    """
    deck_id = _deck()
    page_id = _page()
    if deck_id is None or page_id is None:
        return

    count = api.get_page_button_count(deck_id, page_id)

    confirm = QMessageBox(main_window)
    confirm.setWindowTitle("Apply control preset")
    confirm.setText(
        f"Replace the {count} buttons on this page with the “{preset.name}” controls?\n\n"
        "The current buttons on this page will be cleared."
    )
    confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    confirm.setDefaultButton(QMessageBox.StandardButton.No)
    confirm.setIcon(QMessageBox.Icon.Question)
    if confirm.exec() != QMessageBox.StandardButton.Yes:
        return

    api.apply_control_preset(deck_id, page_id, preset)

    redraw_buttons()
    build_button_state_pages()


def create_main_window(api: StreamDeckServer, app: QApplication) -> MainWindow:
    """Creates the main application window and configures slots and signals"""
    global main_window

    main_window = MainWindow()
    ui = main_window.ui

    ui.settingsButton.clicked.connect(partial(show_settings, main_window))
    ui.add_page.clicked.connect(handle_new_page)
    ui.remove_page.clicked.connect(handle_delete_page_with_confirmation)
    ui.add_button_state.clicked.connect(handle_new_button_state)
    ui.add_button_state.setEnabled(False)
    ui.remove_button_state.clicked.connect(handle_delete_button_state_with_confirmation)
    ui.remove_button_state.setEnabled(False)
    ui.actionExport.triggered.connect(partial(export_config, main_window, api))
    ui.actionImport.triggered.connect(partial(import_config, main_window, api))
    ui.actionExit.triggered.connect(app.exit)
    ui.actionAbout.triggered.connect(main_window.about_dialog)
    ui.actionDocs.triggered.connect(browse_documentation)
    ui.actionGithub.triggered.connect(browse_github)
    # The three base themes are an exclusive choice; dark mode is a separate
    # toggle layered on top of whichever theme is selected.
    theme_group = QActionGroup(main_window)
    theme_group.setExclusive(True)
    theme_group.addAction(ui.actionThemeDefault)
    theme_group.addAction(ui.actionThemeXP)
    theme_group.addAction(ui.actionThemeModern)
    theme_actions = {
        THEME_DEFAULT: ui.actionThemeDefault,
        THEME_XP: ui.actionThemeXP,
        THEME_MODERN: ui.actionThemeModern,
    }
    theme_actions.get(get_theme(main_window.settings), ui.actionThemeDefault).setChecked(True)
    ui.actionThemeDefault.triggered.connect(partial(select_theme, THEME_DEFAULT))
    ui.actionThemeXP.triggered.connect(partial(select_theme, THEME_XP))
    ui.actionThemeModern.triggered.connect(partial(select_theme, THEME_MODERN))
    ui.actionDarkMode.setChecked(is_dark_mode_enabled(main_window.settings))
    ui.actionDarkMode.toggled.connect(toggle_dark_mode)
    ui.actionModernAccent.triggered.connect(choose_modern_accent)
    ui.page_settings.clicked.connect(partial(show_page_settings, main_window))
    build_control_presets_menu(ui)
    ui.settingsButton.setEnabled(False)
    ui.button_states.clear()
    build_button_state_pages()

    ui = main_window.ui
    # allow call redraw_button from ui instance
    ui.redraw_button = redraw_button  # type: ignore [attr-defined]

    # Keyboard shortcuts for the selected button: copy / paste / clear.
    QShortcut(QKeySequence.StandardKey.Copy, main_window, activated=copy_selected_button)
    QShortcut(QKeySequence.StandardKey.Paste, main_window, activated=paste_selected_button)
    QShortcut(QKeySequence.StandardKey.Delete, main_window, activated=clear_selected_button)

    api.streamdeck_keys.key_pressed.connect(partial(handle_keypress, ui))

    ui.device_list.currentIndexChanged.connect(partial(build_device, ui))
    ui.pages.currentChanged.connect(lambda: handle_change_page())
    ui.button_states.currentChanged.connect(lambda: handle_change_button_state())
    api.plugevents.attached.connect(partial(streamdeck_attached, ui))
    api.plugevents.detached.connect(partial(streamdeck_detached, ui))
    api.plugevents.cpu_changed.connect(partial(streamdeck_cpu_changed, ui))

    # Refresh live buttons (clock, CPU, …) once a second. Parented to the window
    # so its lifetime is tied to it; it is a no-op when no live buttons exist.
    live_timer = QTimer(main_window)
    live_timer.setInterval(1000)
    live_timer.timeout.connect(refresh_live_buttons)
    live_timer.start()
    main_window.live_timer = live_timer  # type: ignore[attr-defined]

    return main_window


def show_migration_config_warning_and_check(app: QApplication) -> None:
    """Shows a warning dialog when a different configuration version is detected.
    If the user confirms the migration, the configuration is migrated and the
    application continues. Otherwise, the application exits."""
    if not config_file_need_migration(STATE_FILE):
        return

    confirm = QMessageBox(main_window)
    confirm.setWindowTitle("Old configuration detected")
    confirm.setText(
        "The configuration file format has changed. \n"
        "Do you want to upgrade your configuration to the new format?\n\n"
        f"If you confirm a copy of your current configuration will be created in {STATE_FILE_BACKUP}\n"
        "Otherwise the application will exit."
    )
    confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    confirm.setIcon(QMessageBox.Icon.Warning)
    button = confirm.exec()

    if button == QMessageBox.StandardButton.No:
        app.quit()
        sys.exit()

    if button == QMessageBox.StandardButton.Yes:
        do_config_file_migration()


def create_tray(logo: QIcon, app: QApplication) -> QSystemTrayIcon:
    """Creates a system tray with the provided icon and parent. The main
    window passed will be activated when clicked.
    """
    main_window.tray = QSystemTrayIcon(logo, app)
    main_window.tray.activated.connect(main_window.systray_clicked)  # type: ignore [attr-defined]

    menu = QMenu()
    action_brightness_up = QAction("Brightness up", main_window)
    action_brightness_up.triggered.connect(partial(change_brightness_all, 10))  # type: ignore [attr-defined]
    action_brightness_down = QAction("Brightness down", main_window)
    action_brightness_down.triggered.connect(partial(change_brightness_all, -10))  # type: ignore [attr-defined]
    action_dim = QAction("Dim display (toggle)", main_window)
    action_dim.triggered.connect(toggle_dim_all)  # type: ignore [attr-defined]
    action_configure = QAction("Configure...", main_window)
    action_configure.triggered.connect(main_window.bring_to_top)  # type: ignore [attr-defined]
    menu.addAction(action_brightness_up)
    menu.addAction(action_brightness_down)
    menu.addSeparator()
    menu.addAction(action_dim)
    menu.addAction(action_configure)
    menu.addSeparator()
    action_exit = QAction("Exit", main_window)
    action_exit.triggered.connect(app.exit)  # type: ignore [attr-defined]
    menu.addAction(action_exit)
    main_window.tray.setContextMenu(menu)
    return main_window.tray


def show_tray_warning_message(message: str) -> None:
    """Shows a warning message in the system tray"""
    main_window.tray.showMessage("Warning", message, QSystemTrayIcon.MessageIcon.Warning, 5000)


def streamdeck_cpu_changed(ui, serial_number: str, cpu: int):
    if cpu > 100:
        cpu = 100
    if _deck() == serial_number:
        ui.cpu_usage.setValue(cpu)
        ui.cpu_usage.setToolTip(f"Rendering CPU usage: {cpu}%")
        ui.cpu_usage.update()


def streamdeck_attached(ui, deck: Dict):
    serial_number = deck["serial_number"]
    blocker = QSignalBlocker(ui.device_list)
    try:
        ui.device_list.addItem(f"{deck['type']} - {serial_number}", userData=serial_number)
    finally:
        blocker.unblock()
    build_device(ui)
    update_focus_watcher(ui)


def streamdeck_detached(ui, serial_number):
    # If the on-deck game owned this deck, abandon it (the display is gone).
    if deck_game is not None and deck_game.deck_id == serial_number:
        deck_game.stop(restore=False)
    index = ui.device_list.findData(serial_number)
    if index != -1:
        # Should not be (how can you remove a device that was never attached?)
        # Check anyway
        blocker = QSignalBlocker(ui.device_list)
        try:
            ui.device_list.removeItem(index)
        finally:
            blocker.unblock()
        build_device(ui)
        update_focus_watcher(ui)


def configure_signals(app: QApplication, cli: CLIStreamDeckServer):
    """Configures the termination signals for the application."""
    # Configure signal handlers
    # https://stackoverflow.com/a/4939113/192815
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)  # type: ignore [attr-defined] # Let interpreter run to handle signal

    # Handle SIGTERM so we release semaphore and shutdown API gracefully
    signal.signal(signal.SIGTERM, partial(sigterm_handler, app, cli))

    # Handle <ctrl+c>
    signal.signal(signal.SIGINT, partial(sigterm_handler, app, cli))


def sigterm_handler(app, cli, signal_value, frame):
    print("Received signal", signal_value, frame)
    stop_focus_watcher()
    api.stop()
    cli.stop()
    app.quit()
    remove_pid_file()
    if signal_value == signal.SIGTERM:
        # Indicate to systemd that it was a clean termination
        print("Exiting normally")
        sys.exit()
    else:
        # Terminations for other reasons are treated as an error condition
        sys.exit(1)


def start(_exit: bool = False) -> None:
    global main_window
    if "-h" in sys.argv or "--help" in sys.argv:
        print(f"Usage: {os.path.basename(sys.argv[0])}")
        print("Flags:")
        print("  -h, --help\tShow this message")
        print("  -n, --no-ui\tRun the program without showing a UI")
        print("  -d, --daemon\tRun detached in the background (implies --no-ui)")
        print("  --daemon-kill\tStop the running background instance and exit")
        print("  --daemon-status\tReport whether an instance is running and exit")
        return

    if "--daemon-status" in sys.argv:
        pid = running_pid()
        print(f"Stream Deck is running (PID {pid})." if pid else "Stream Deck is not running.")
        return

    if "--daemon-kill" in sys.argv:
        messages = {
            "killed": "Stopped the running Stream Deck instance.",
            "not-running": "No running Stream Deck instance was found.",
            "stale": "Removed a stale PID file; no process was running.",
            "error": "Failed to stop the running Stream Deck instance.",
        }
        print(messages[kill_daemon()])
        return

    show_ui = not ("-n" in sys.argv or "--no-ui" in sys.argv)

    # A daemon runs detached from the terminal and never shows a window. We must
    # detach before the Qt application is created.
    if "-d" in sys.argv or "--daemon" in sys.argv:
        show_ui = False
        daemonize()

    try:
        app_version = version("streamdeck-linux-gui")
    except PackageNotFoundError:
        app_version = "devel"

    try:
        with Semaphore("/tmp/streamdeck_ui.lock"):  # nosec - this file is only observed with advisory lock
            # The semaphore was created, so this is the first instance

            # Record our PID so the instance can be stopped later (--daemon-kill).
            write_pid_file()

            # The QApplication object holds the Qt event loop, and you need one of these
            # for your application
            app = QApplication(sys.argv)
            app.setApplicationName(APP_NAME)
            app.setApplicationVersion(app_version)
            logo = QIcon(APP_LOGO)
            app.setWindowIcon(logo)

            # Apply the saved light/dark theme before building the window so it
            # is rendered with the correct palette from the start.
            startup_settings = QSettings("streamdeck-ui", "streamdeck-ui")
            apply_theme(
                app,
                get_theme(startup_settings),
                is_dark_mode_enabled(startup_settings),
                get_modern_accent(startup_settings),
            )

            main_window = create_main_window(api, app)
            create_tray(logo, app)

            # check if we want to continue with the configuration migrate
            show_migration_config_warning_and_check(app)

            # read the state file if it exists
            if os.path.isfile(STATE_FILE):
                api.open_config(STATE_FILE)
            api.start()

            cli = CLIStreamDeckServer(api, main_window.ui)
            cli.start()

            configure_signals(app, cli)

            main_window.tray.show()
            if show_ui:
                main_window.show()

            if _exit:
                return
            else:
                app.exec()
                stop_focus_watcher()
                api.stop()
                cli.stop()
                remove_pid_file()
                sys.exit()

    except SemaphoreAcquireError:
        # The semaphore already exists, so another instance is running
        sys.exit()


if __name__ == "__main__":
    start()
