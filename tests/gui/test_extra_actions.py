import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton

from streamdeck_ui import gui
from tests.common import STREAMDECK_SERIAL


def _select_first_button(qtbot, main_window):
    buttons = main_window.ui.pages.widget(0).deck_buttons.findChildren(QToolButton)
    qtbot.mouseClick(buttons[0], Qt.LeftButton)


@pytest.mark.serial
def test_clone_page_adds_page_copy(qtbot, api_and_window, mocker):
    main_window, api = api_and_window
    api.set_button_text(STREAMDECK_SERIAL, 0, 0, "Original")

    pages_before = len(api.get_pages(STREAMDECK_SERIAL))
    spy = mocker.spy(api, "clone_page")

    gui.handle_clone_page()

    assert spy.call_count == 1
    pages_after = api.get_pages(STREAMDECK_SERIAL)
    assert len(pages_after) == pages_before + 1
    # the new page is a copy of page 0
    new_page = pages_after[-1]
    assert api.get_button_text(STREAMDECK_SERIAL, new_page, 0) == "Original"


@pytest.mark.serial
def test_page_settings_clone_button_clones_page(qtbot, api_and_window, mocker):
    main_window, api = api_and_window

    dialog = mocker.MagicMock()
    dialog.exec.return_value = True
    dialog.clone_requested = True
    mocker.patch.object(gui, "PageSettingsDialog", return_value=dialog)
    mocker.patch.object(gui, "list_open_apps", return_value=[])
    clone_spy = mocker.spy(api, "clone_page")
    set_focus_spy = mocker.spy(api, "set_focus_page")

    gui.show_page_settings(main_window)

    clone_spy.assert_called_once()
    # A clone request must not also create a focus binding.
    set_focus_spy.assert_not_called()


@pytest.mark.serial
def test_change_brightness_all(qtbot, api_and_window, mocker):
    main_window, api = api_and_window
    spy = mocker.spy(api, "change_brightness")

    gui.change_brightness_all(10)

    # one call per connected deck
    assert spy.call_count == len(api.decks_by_serial)
    for call in spy.call_args_list:
        assert call.args[-1] == 10


@pytest.mark.serial
def test_test_action_runs_keypress(qtbot, api_and_window, mocker):
    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)

    handle_spy = mocker.patch.object(gui, "handle_keypress")

    gui.test_selected_button()

    handle_spy.assert_called_once()
    # state argument is True (key down)
    assert handle_spy.call_args.args[-1] is True
