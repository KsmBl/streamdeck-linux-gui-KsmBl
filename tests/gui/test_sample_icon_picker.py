from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QToolButton

from streamdeck_ui import gui

SAMPLE = "/usr/share/streamdeck/icons/samples/media/play.png"
CATEGORIES = {"media": [("Play", SAMPLE)]}


def _select_first_button(qtbot, main_window):
    buttons = main_window.ui.pages.widget(0).deck_buttons.findChildren(QToolButton)
    qtbot.mouseClick(buttons[0], Qt.LeftButton)


def _sample_button(main_window):
    tab = main_window.ui.button_states.currentWidget()
    return tab.button_form.findChild(QPushButton, "sample_icons")


def _mock_picker(mocker, *, accepted=True, icon_path=SAMPLE):
    picker = MagicMock()
    picker.exec.return_value = accepted
    picker.selected_icon_path.return_value = icon_path
    mocker.patch.object(gui, "SampleIconPicker", return_value=picker)
    return picker


@pytest.mark.serial
def test_sample_icon_picker_sets_icon(qtbot, api_and_window, mocker):
    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)

    mocker.patch.object(gui, "list_sample_icons", return_value=CATEGORIES)
    mocker.patch.object(gui, "build_browser_icons", return_value=[])
    mocker.patch.object(gui, "build_font_awesome_icons", return_value=[])
    mocker.patch.object(gui, "build_font_awesome_brand_icons", return_value=[])
    _mock_picker(mocker, accepted=True)
    icon_spy = mocker.spy(api, "set_button_icon")

    qtbot.mouseClick(_sample_button(main_window), Qt.LeftButton)

    icon_spy.assert_called_once()
    assert icon_spy.call_args.args[-1] == SAMPLE


@pytest.mark.serial
def test_sample_icon_picker_cancelled(qtbot, api_and_window, mocker):
    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)

    mocker.patch.object(gui, "list_sample_icons", return_value=CATEGORIES)
    mocker.patch.object(gui, "build_browser_icons", return_value=[])
    mocker.patch.object(gui, "build_font_awesome_icons", return_value=[])
    mocker.patch.object(gui, "build_font_awesome_brand_icons", return_value=[])
    _mock_picker(mocker, accepted=False)
    icon_spy = mocker.spy(api, "set_button_icon")

    qtbot.mouseClick(_sample_button(main_window), Qt.LeftButton)

    icon_spy.assert_not_called()
