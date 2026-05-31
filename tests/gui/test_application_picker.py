from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QToolButton

from streamdeck_ui import gui
from streamdeck_ui.modules.applications import DesktopApplication

FIREFOX = DesktopApplication(name="Firefox", command="firefox", icon_name="firefox")


def _select_first_button(qtbot, main_window):
    buttons = main_window.ui.pages.widget(0).deck_buttons.findChildren(QToolButton)
    qtbot.mouseClick(buttons[0], Qt.LeftButton)
    return buttons[0]


def _select_application_button(main_window):
    current_state_tab = main_window.ui.button_states.currentWidget()
    return current_state_tab.button_form.findChild(QPushButton, "select_application")


def _mock_picker(mocker, *, accepted=True, application=FIREFOX, use_icon=True):
    """Replaces the ApplicationPicker dialog with a configured mock so the tests
    do not have to drive a modal dialog."""
    picker = MagicMock()
    picker.exec.return_value = accepted
    picker.selected_application.return_value = application
    picker.use_icon.isChecked.return_value = use_icon
    mocker.patch.object(gui, "ApplicationPicker", return_value=picker)
    return picker


@pytest.mark.serial
def test_application_picker_sets_command_and_icon(qtbot, api_and_window, mocker):
    """Picking an application sets both the button command and a resolved icon."""
    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)

    mocker.patch.object(gui, "list_desktop_applications", return_value=[FIREFOX])
    mocker.patch.object(gui, "resolve_icon_to_file", return_value="/tmp/firefox.png")
    _mock_picker(mocker, use_icon=True)

    command_spy = mocker.spy(api, "set_button_command")
    icon_spy = mocker.spy(api, "set_button_icon")

    qtbot.mouseClick(_select_application_button(main_window), Qt.LeftButton)

    command_spy.assert_called_once()
    assert command_spy.call_args.args[-1] == "firefox"
    icon_spy.assert_called_once()
    assert icon_spy.call_args.args[-1] == "/tmp/firefox.png"


@pytest.mark.serial
def test_application_picker_can_skip_icon(qtbot, api_and_window, mocker):
    """When 'use icon' is unchecked, only the command is set."""
    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)

    mocker.patch.object(gui, "list_desktop_applications", return_value=[FIREFOX])
    resolve_spy = mocker.patch.object(gui, "resolve_icon_to_file", return_value="/tmp/firefox.png")
    _mock_picker(mocker, use_icon=False)

    command_spy = mocker.spy(api, "set_button_command")

    qtbot.mouseClick(_select_application_button(main_window), Qt.LeftButton)

    command_spy.assert_called_once()
    resolve_spy.assert_not_called()


@pytest.mark.serial
def test_application_picker_cancelled(qtbot, api_and_window, mocker):
    """Cancelling the dialog changes nothing."""
    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)

    mocker.patch.object(gui, "list_desktop_applications", return_value=[FIREFOX])
    _mock_picker(mocker, accepted=False)

    command_spy = mocker.spy(api, "set_button_command")

    qtbot.mouseClick(_select_application_button(main_window), Qt.LeftButton)

    command_spy.assert_not_called()
