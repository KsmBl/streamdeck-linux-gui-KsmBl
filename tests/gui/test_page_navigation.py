from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QToolButton

from streamdeck_ui.config import NEXT_PAGE_ICON, PREVIOUS_PAGE_ICON, SWITCH_PAGE_NEXT, SWITCH_PAGE_PREVIOUS


def _select_first_button(qtbot, main_window):
    buttons = main_window.ui.pages.widget(0).deck_buttons.findChildren(QToolButton)
    qtbot.mouseClick(buttons[0], Qt.LeftButton)


def _nav_button(main_window, name):
    tab = main_window.ui.button_states.currentWidget()
    return tab.button_form.findChild(QPushButton, name)


def _button_ids(main_window):
    tab = main_window.ui.button_states.currentWidget()
    return (
        tab.property("deck_id"),
        tab.property("page_id"),
        tab.property("button_id"),
    )


def test_next_page_button_sets_action_and_icon(qtbot, api_and_window):
    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)

    qtbot.mouseClick(_nav_button(main_window, "set_next_page"), Qt.LeftButton)

    deck_id, page_id, button_id = _button_ids(main_window)
    assert api.get_button_switch_page(deck_id, page_id, button_id) == SWITCH_PAGE_NEXT
    assert api.get_button_icon(deck_id, page_id, button_id) == NEXT_PAGE_ICON


def test_previous_page_button_sets_action_and_icon(qtbot, api_and_window):
    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)

    qtbot.mouseClick(_nav_button(main_window, "set_previous_page"), Qt.LeftButton)

    deck_id, page_id, button_id = _button_ids(main_window)
    assert api.get_button_switch_page(deck_id, page_id, button_id) == SWITCH_PAGE_PREVIOUS
    assert api.get_button_icon(deck_id, page_id, button_id) == PREVIOUS_PAGE_ICON


def test_next_page_keypress_navigates_relative(qtbot, api_and_window, mocker):
    main_window, api = api_and_window

    # behave like the streamdeck is active
    api.reset_dimmer = mocker.MagicMock()
    api.reset_dimmer.return_value = False

    _select_first_button(qtbot, main_window)
    qtbot.mouseClick(_nav_button(main_window, "set_next_page"), Qt.LeftButton)

    deck_id, page_id, button_id = _button_ids(main_window)
    set_page_spy = mocker.spy(api, "set_page")

    # We are on page 0; pressing the key should move to the next page (1).
    assert api.get_page(deck_id) == 0
    api.streamdeck_keys.key_pressed.emit(deck_id, button_id, True)

    set_page_spy.assert_any_call(deck_id, 1)
    assert api.get_page(deck_id) == 1


def test_previous_page_keypress_wraps_around(qtbot, api_and_window, mocker):
    main_window, api = api_and_window

    api.reset_dimmer = mocker.MagicMock()
    api.reset_dimmer.return_value = False

    _select_first_button(qtbot, main_window)
    qtbot.mouseClick(_nav_button(main_window, "set_previous_page"), Qt.LeftButton)

    deck_id, page_id, button_id = _button_ids(main_window)
    set_page_spy = mocker.spy(api, "set_page")

    # On page 0, "previous" wraps to the last page (1 for the test deck).
    assert api.get_page(deck_id) == 0
    assert api.get_pages(deck_id) == [0, 1]
    api.streamdeck_keys.key_pressed.emit(deck_id, button_id, True)

    set_page_spy.assert_any_call(deck_id, 1)
    assert api.get_page(deck_id) == 1
