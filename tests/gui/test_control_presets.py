import pytest
from PySide6.QtWidgets import QMessageBox, QPushButton

from streamdeck_ui import gui
from streamdeck_ui.modules.control_presets import ControlAction, ControlPreset
from tests.common import STREAMDECK_SERIAL

PRESET = ControlPreset(
    "Test",
    [
        ControlAction("New\nTab", "ctrl+t"),
        ControlAction("Reload", "f5"),
    ],
)


def _apply_preset_button(main_window):
    return main_window.ui.apply_preset


@pytest.mark.serial
def test_controls_button_has_a_menu(qtbot, api_and_window):
    main_window, _api = api_and_window
    menu = _apply_preset_button(main_window).menu()
    assert menu is not None
    assert [action.text() for action in menu.actions()] == [
        "Firefox",
        "Vivaldi",
        "Thunar (files)",
        "Vim",
        "Media player",
        "GIMP",
        "Discord",
        "VLC",
    ]


@pytest.mark.serial
def test_applying_preset_fills_the_page(qtbot, api_and_window, mocker):
    main_window, api = api_and_window
    page = api.get_page(STREAMDECK_SERIAL)
    count = api.get_page_button_count(STREAMDECK_SERIAL, page)

    # Seed a button beyond the preset so we can confirm the page is cleared.
    api.set_button_text(STREAMDECK_SERIAL, page, count - 1, "stale")

    mocker.patch.object(QMessageBox, "exec", return_value=QMessageBox.StandardButton.Yes)

    gui.apply_control_preset_to_page(PRESET)

    assert api.get_button_text(STREAMDECK_SERIAL, page, 0) == "New\nTab"
    assert api.get_button_keys(STREAMDECK_SERIAL, page, 0) == "ctrl+t"
    assert api.get_button_text(STREAMDECK_SERIAL, page, 1) == "Reload"
    assert api.get_button_keys(STREAMDECK_SERIAL, page, 1) == "f5"
    # Buttons not covered by the preset are cleared.
    assert api.get_button_text(STREAMDECK_SERIAL, page, count - 1) == ""


@pytest.mark.serial
def test_cancelling_leaves_page_untouched(qtbot, api_and_window, mocker):
    main_window, api = api_and_window
    page = api.get_page(STREAMDECK_SERIAL)
    api.set_button_text(STREAMDECK_SERIAL, page, 0, "keep me")

    mocker.patch.object(QMessageBox, "exec", return_value=QMessageBox.StandardButton.No)

    gui.apply_control_preset_to_page(PRESET)

    assert api.get_button_text(STREAMDECK_SERIAL, page, 0) == "keep me"
    assert api.get_button_keys(STREAMDECK_SERIAL, page, 0) == ""
