import pytest

from streamdeck_ui import gui
from tests.common import STREAMDECK_SERIAL


@pytest.mark.serial
def test_focus_switches_to_bound_page(api_and_window, mocker):
    main_window, api = api_and_window
    api.reset_dimmer = mocker.MagicMock(return_value=False)
    gui.last_manual_page[STREAMDECK_SERIAL] = 0
    api.set_page(STREAMDECK_SERIAL, 0)
    api.set_focus_page(STREAMDECK_SERIAL, "firefox", 1)

    gui.handle_focus_changed(main_window.ui, "firefox")
    assert api.get_page(STREAMDECK_SERIAL) == 1


@pytest.mark.serial
def test_focus_unmapped_app_restores_last_manual_page(api_and_window, mocker):
    main_window, api = api_and_window
    api.reset_dimmer = mocker.MagicMock(return_value=False)
    gui.last_manual_page[STREAMDECK_SERIAL] = 0
    api.set_page(STREAMDECK_SERIAL, 0)
    api.set_focus_page(STREAMDECK_SERIAL, "firefox", 1)

    # Focused app with a bound page -> its page.
    gui.handle_focus_changed(main_window.ui, "firefox")
    assert api.get_page(STREAMDECK_SERIAL) == 1

    # Focused app without a bound page -> back to the last manual page.
    gui.handle_focus_changed(main_window.ui, "some-unmapped-app")
    assert api.get_page(STREAMDECK_SERIAL) == 0


@pytest.mark.serial
def test_no_restore_when_deck_has_no_bindings(api_and_window, mocker):
    main_window, api = api_and_window
    api.reset_dimmer = mocker.MagicMock(return_value=False)
    api.set_page(STREAMDECK_SERIAL, 1)
    gui.last_manual_page[STREAMDECK_SERIAL] = 0  # would restore to 0 if active

    # No focus_pages on this deck -> feature inactive -> page is untouched.
    gui.handle_focus_changed(main_window.ui, "anything")
    assert api.get_page(STREAMDECK_SERIAL) == 1


@pytest.mark.serial
def test_manual_page_change_is_recorded(qtbot, api_and_window):
    main_window, api = api_and_window
    ui = main_window.ui
    for tab in range(ui.pages.count()):
        if ui.pages.widget(tab).property("page_id") == 1:
            ui.pages.setCurrentIndex(tab)
            break
    qtbot.wait(10)
    assert gui.last_manual_page.get(STREAMDECK_SERIAL) == 1
