from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
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
    picker.selected_color.return_value = None
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
def test_picker_search_and_color(qtbot):
    categories = {
        "media": [("Play", "/x/play.png"), ("Stop", "/x/stop.png")],
        "volume": [("Volume Up", "/x/vol.png")],
    }
    picker = gui.SampleIconPicker(None, categories)
    qtbot.addWidget(picker)

    # Searching spans all categories and filters by name.
    picker.search.setText("vol")
    visible = [picker.list.item(i).text() for i in range(picker.list.count())]
    assert visible == ["Volume Up"]

    # No tint by default; a chosen colour is returned when "Recolor" is on.
    assert picker.selected_color() is None
    picker._color = QColor("#123456")
    picker.recolor.setChecked(True)
    assert picker.selected_color() == "#123456"


@pytest.mark.serial
def test_media_presets_are_valid_keys():
    from streamdeck_ui.modules.keyboard import get_valid_key_names

    valid = set(get_valid_key_names())
    assert all(keys in valid for _label, keys in gui.MEDIA_KEY_PRESETS)


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
