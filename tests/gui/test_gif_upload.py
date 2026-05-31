import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton

from streamdeck_ui import gui


def _select_first_button(qtbot, main_window):
    buttons = main_window.ui.pages.widget(0).deck_buttons.findChildren(QToolButton)
    qtbot.mouseClick(buttons[0], Qt.LeftButton)


@pytest.mark.serial
def test_gif_upload_sets_icon(qtbot, api_and_window, mocker):
    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)

    mocker.patch.object(gui.QFileDialog, "getOpenFileName", return_value=("/tmp/anim.gif", ""))
    icon_spy = mocker.spy(api, "set_button_icon")

    gui.show_gif_upload_dialog()

    icon_spy.assert_called_once()
    assert icon_spy.call_args.args[-1] == "/tmp/anim.gif"


@pytest.mark.serial
def test_gif_upload_cancelled(qtbot, api_and_window, mocker):
    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)

    mocker.patch.object(gui.QFileDialog, "getOpenFileName", return_value=("", ""))
    icon_spy = mocker.spy(api, "set_button_icon")

    gui.show_gif_upload_dialog()

    icon_spy.assert_not_called()
