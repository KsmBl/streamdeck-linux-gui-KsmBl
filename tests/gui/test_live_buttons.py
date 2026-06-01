import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QToolButton

from streamdeck_ui import gui
from tests.common import STREAMDECK_SERIAL


def _select_first_button(qtbot, main_window):
    buttons = main_window.ui.pages.widget(0).deck_buttons.findChildren(QToolButton)
    qtbot.mouseClick(buttons[0], Qt.LeftButton)


@pytest.mark.serial
def test_live_source_combo_is_populated(qtbot, api_and_window):
    main_window, _api = api_and_window
    _select_first_button(qtbot, main_window)

    tab = main_window.ui.button_states.currentWidget()
    combo = tab.button_form.findChild(QComboBox, "live_source")
    assert combo is not None
    # The first entry is "None" and the clock source is selectable.
    assert combo.itemData(0) == ""
    assert combo.findData("clock") > 0


@pytest.mark.serial
def test_choosing_live_source_updates_button(qtbot, api_and_window):
    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)
    page = api.get_page(STREAMDECK_SERIAL)

    tab = main_window.ui.button_states.currentWidget()
    combo = tab.button_form.findChild(QComboBox, "live_source")
    combo.setCurrentIndex(combo.findData("clock"))

    assert api.get_button_live_source(STREAMDECK_SERIAL, page, 0) == "clock"

    # Selecting "None" again clears it.
    combo.setCurrentIndex(combo.findData(""))
    assert api.get_button_live_source(STREAMDECK_SERIAL, page, 0) == ""
