import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton

from streamdeck_ui import gui
from tests.common import STREAMDECK_SERIAL


def _select_first_button(qtbot, main_window):
    buttons = main_window.ui.pages.widget(0).deck_buttons.findChildren(QToolButton)
    qtbot.mouseClick(buttons[0], Qt.LeftButton)


@pytest.mark.serial
def test_copy_then_clear_then_paste_restores_button(qtbot, api_and_window):
    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)

    api.set_button_text(STREAMDECK_SERIAL, 0, 0, "Hello")
    api.set_button_keys(STREAMDECK_SERIAL, 0, 0, "ctrl+c")

    gui.copy_selected_button()
    gui.clear_selected_button()

    assert api.get_button_text(STREAMDECK_SERIAL, 0, 0) == ""
    assert api.get_button_keys(STREAMDECK_SERIAL, 0, 0) == ""

    gui.paste_selected_button()

    assert api.get_button_text(STREAMDECK_SERIAL, 0, 0) == "Hello"
    assert api.get_button_keys(STREAMDECK_SERIAL, 0, 0) == "ctrl+c"


@pytest.mark.serial
def test_paste_without_copy_is_noop(qtbot, api_and_window, mocker):
    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)

    # Ensure nothing is on the clipboard.
    gui._button_clipboard = None
    spy = mocker.spy(api, "set_button_multi_state")

    gui.paste_selected_button()

    spy.assert_not_called()


@pytest.mark.serial
def test_clear_resets_selected_button(qtbot, api_and_window):
    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)

    api.set_button_text(STREAMDECK_SERIAL, 0, 0, "Bye")
    gui.clear_selected_button()

    assert api.get_button_text(STREAMDECK_SERIAL, 0, 0) == ""
