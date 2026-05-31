from unittest.mock import MagicMock

import pytest

from streamdeck_ui import gui
from tests.common import STREAMDECK_SERIAL


@pytest.mark.serial
def test_page_settings_dialog_selected_app(qtbot):
    dialog = gui.PageSettingsDialog(None, "Page 1", "firefox", ["firefox", "kitty"])
    qtbot.addWidget(dialog)

    assert dialog.selected_app() == "firefox"

    dialog.app.setCurrentText("")
    assert dialog.selected_app() is None

    dialog.app.setCurrentText("  Chromium ")
    assert dialog.selected_app() == "chromium"


@pytest.mark.serial
def test_show_page_settings_binds_app(api_and_window, mocker):
    main_window, api = api_and_window

    dialog = MagicMock()
    dialog.exec.return_value = True
    dialog.selected_app.return_value = "firefox"
    mocker.patch.object(gui, "PageSettingsDialog", return_value=dialog)
    mocker.patch.object(gui, "list_open_apps", return_value=[])
    # Don't start a real background watcher during the test.
    mocker.patch.object(gui, "update_focus_watcher")

    gui.show_page_settings(main_window)

    assert api.get_focus_pages(STREAMDECK_SERIAL).get("firefox") == gui._page()


@pytest.mark.serial
def test_show_page_settings_clears_app(api_and_window, mocker):
    main_window, api = api_and_window
    page_id = gui._page()
    api.set_focus_page(STREAMDECK_SERIAL, "firefox", page_id)

    dialog = MagicMock()
    dialog.exec.return_value = True
    dialog.selected_app.return_value = None  # cleared
    mocker.patch.object(gui, "PageSettingsDialog", return_value=dialog)
    mocker.patch.object(gui, "list_open_apps", return_value=[])
    mocker.patch.object(gui, "update_focus_watcher")

    gui.show_page_settings(main_window)

    assert api.get_focus_pages(STREAMDECK_SERIAL) == {}
