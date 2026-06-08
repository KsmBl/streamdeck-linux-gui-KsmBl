import pytest

from streamdeck_ui import gui
from tests.common import STREAMDECK_SERIAL


@pytest.mark.serial
def test_focus_switches_between_auto_pages(api_and_window, mocker):
    """While the deck is on an auto page, focusing a bound app switches to its
    auto page."""
    main_window, api = api_and_window
    api.reset_dimmer = mocker.MagicMock(return_value=False)
    # Both fixture pages belong to the Auto group; page 1 is bound to Firefox.
    api.state[STREAMDECK_SERIAL].auto_pages = [0, 1]
    api.set_focus_page(STREAMDECK_SERIAL, "firefox", 1)
    api.set_page(STREAMDECK_SERIAL, 0)

    gui.handle_focus_changed(main_window.ui, "firefox")
    assert api.get_page(STREAMDECK_SERIAL) == 1


@pytest.mark.serial
def test_focus_unmapped_app_stays_on_current_auto_page(api_and_window, mocker):
    """A focused app with no auto page leaves the deck on its current auto page
    (no return to the last manual page while in the Auto group)."""
    main_window, api = api_and_window
    api.reset_dimmer = mocker.MagicMock(return_value=False)
    api.state[STREAMDECK_SERIAL].auto_pages = [0, 1]
    api.set_focus_page(STREAMDECK_SERIAL, "firefox", 1)
    api.set_page(STREAMDECK_SERIAL, 0)

    gui.handle_focus_changed(main_window.ui, "firefox")
    assert api.get_page(STREAMDECK_SERIAL) == 1

    # Focused app without an auto page -> stay put.
    gui.handle_focus_changed(main_window.ui, "some-unmapped-app")
    assert api.get_page(STREAMDECK_SERIAL) == 1


@pytest.mark.serial
def test_no_switch_when_not_on_an_auto_page(api_and_window, mocker):
    """Focus changes are ignored unless the deck is currently in the Auto group."""
    main_window, api = api_and_window
    api.reset_dimmer = mocker.MagicMock(return_value=False)
    # Page 1 is an auto page bound to Firefox, but the deck is on normal page 0.
    api.state[STREAMDECK_SERIAL].auto_pages = [1]
    api.set_focus_page(STREAMDECK_SERIAL, "firefox", 1)
    api.set_page(STREAMDECK_SERIAL, 0)

    gui.handle_focus_changed(main_window.ui, "firefox")
    assert api.get_page(STREAMDECK_SERIAL) == 0


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
