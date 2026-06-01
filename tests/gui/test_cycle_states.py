import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QToolButton

from streamdeck_ui import gui
from tests.common import STREAMDECK_SERIAL


def _select_first_button(qtbot, main_window):
    buttons = main_window.ui.pages.widget(0).deck_buttons.findChildren(QToolButton)
    qtbot.mouseClick(buttons[0], Qt.LeftButton)


@pytest.mark.serial
def test_cycle_checkbox_present_and_persists(qtbot, api_and_window):
    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)
    page = api.get_page(STREAMDECK_SERIAL)

    tab = main_window.ui.button_states.currentWidget()
    checkbox = tab.button_form.findChild(QCheckBox, "cycle_states")
    assert checkbox is not None

    checkbox.setChecked(True)
    assert api.get_button_cycle_states(STREAMDECK_SERIAL, page, 0) is True


@pytest.mark.serial
def test_press_advances_through_states_and_wraps(qtbot, api_and_window, mocker):
    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)
    page = api.get_page(STREAMDECK_SERIAL)

    # A real key press first wakes the dimmer; keep the display awake here so
    # each press exercises the cycle action.
    mocker.patch.object(api, "reset_dimmer", return_value=False)

    # Ensure the button has more than one state, start at the first and cycle.
    if len(api.get_button_states(STREAMDECK_SERIAL, page, 0)) < 2:
        api.add_new_button_state(STREAMDECK_SERIAL, page, 0)
    states = api.get_button_states(STREAMDECK_SERIAL, page, 0)
    assert len(states) > 1
    api.set_button_state(STREAMDECK_SERIAL, page, 0, states[0])
    api.set_button_cycle_states(STREAMDECK_SERIAL, page, 0, True)

    # Each press advances to the next state...
    for expected in states[1:]:
        gui.handle_keypress(main_window.ui, STREAMDECK_SERIAL, 0, True)
        assert api.get_button_state(STREAMDECK_SERIAL, page, 0) == expected

    # ...and the press after the last state wraps back to the first.
    gui.handle_keypress(main_window.ui, STREAMDECK_SERIAL, 0, True)
    assert api.get_button_state(STREAMDECK_SERIAL, page, 0) == states[0]
