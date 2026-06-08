from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from tests.common import STREAMDECK_SERIAL


def test_add_new_page(qtbot, api_and_window, mocker):
    """Test the behaviour of the add page button"""
    main_window, api = api_and_window

    method_spy = mocker.spy(api, "add_new_page")

    # check how many pages are present (two real pages + the synthetic Auto tab)
    assert main_window.ui.pages.count() == 3

    # click the add page button
    qtbot.mouseClick(main_window.ui.add_page, Qt.LeftButton)

    # check that the page was added
    assert main_window.ui.pages.count() == 4

    method_spy.assert_called_once()


def test_remove_page_with_confirmation(qtbot, api_and_window, mock_confirm_dialog_exec, mocker):
    """Test the behavior of the remove page button when user confirms the action."""
    main_window, api = api_and_window

    method_spy = mocker.spy(api, "remove_page")

    # ensure that the confirmation dialog returns yes
    mock_confirm_dialog_exec.return_value = QMessageBox.StandardButton.Yes

    # check how many pages are present (two real pages + the synthetic Auto tab)
    assert main_window.ui.pages.count() == 3

    # click the remove page button
    qtbot.mouseClick(main_window.ui.remove_page, Qt.LeftButton)

    # check that the page was removed (one real page + the Auto tab)
    assert main_window.ui.pages.count() == 2

    method_spy.assert_called_once()


def test_remove_page_with_no_confirmation(qtbot, api_and_window, mock_confirm_dialog_exec, mocker):
    """Test the remove page menu item when user cancels the action."""
    main_window, api = api_and_window

    method_spy = mocker.spy(api, "remove_page")

    # ensure that the confirmation dialog returns yes
    mock_confirm_dialog_exec.return_value = QMessageBox.StandardButton.No

    # check how many pages are present (two real pages + the synthetic Auto tab)
    assert main_window.ui.pages.count() == 3

    # click the remove page button
    qtbot.mouseClick(main_window.ui.remove_page, Qt.LeftButton)

    # check that the page was not removed
    assert main_window.ui.pages.count() == 3

    method_spy.assert_not_called()


def test_removing_bound_page_clears_app_binding_and_stops_watcher(
    qtbot, api_and_window, mock_confirm_dialog_exec, mocker
):
    """Deleting a page bound to an application clears the binding, so the deck
    falls back to the last selected page and the focus watcher is torn down."""
    main_window, api = api_and_window

    # Bind the currently shown page to an application.
    current_page = api.get_page(STREAMDECK_SERIAL)
    api.set_focus_page(STREAMDECK_SERIAL, "firefox", current_page)
    assert api.get_focus_pages(STREAMDECK_SERIAL) == {"firefox": current_page}

    watcher_spy = mocker.patch("streamdeck_ui.gui.update_focus_watcher")
    mock_confirm_dialog_exec.return_value = QMessageBox.StandardButton.Yes

    qtbot.mouseClick(main_window.ui.remove_page, Qt.LeftButton)

    # The deleted page's application binding is gone...
    assert api.get_focus_pages(STREAMDECK_SERIAL) == {}
    # ...and the watcher state was re-evaluated after deletion.
    watcher_spy.assert_called()
