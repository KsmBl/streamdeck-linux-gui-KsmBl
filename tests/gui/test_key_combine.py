import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton

from streamdeck_ui import gui
from streamdeck_ui.gui import KeyCombineDialog


def _select_first_button(qtbot, main_window):
    buttons = main_window.ui.pages.widget(0).deck_buttons.findChildren(QToolButton)
    qtbot.mouseClick(buttons[0], Qt.LeftButton)
    return buttons[0]


@pytest.mark.serial
def test_combination_from_checkboxes(qtbot):
    dialog = KeyCombineDialog(None)
    qtbot.addWidget(dialog)

    dialog._modifier_boxes["ctrl"].setChecked(True)
    dialog._modifier_boxes["shift"].setChecked(True)
    dialog.key_combo.setEditText("a")

    assert dialog.combination() == "ctrl+shift+a"


@pytest.mark.serial
def test_combination_empty_when_nothing_set(qtbot):
    dialog = KeyCombineDialog(None)
    qtbot.addWidget(dialog)

    assert dialog.combination() == ""


@pytest.mark.serial
def test_load_initial_parses_existing_combo(qtbot):
    dialog = KeyCombineDialog(None, "ctrl+alt+delete")
    qtbot.addWidget(dialog)

    assert dialog._modifier_boxes["ctrl"].isChecked()
    assert dialog._modifier_boxes["alt"].isChecked()
    assert dialog.key_combo.currentText() == "delete"
    assert dialog.combination() == "ctrl+alt+delete"


@pytest.mark.serial
def test_show_key_combine_dialog_sets_keys_field(qtbot, api_and_window, mocker):
    from PySide6.QtWidgets import QWidget

    from streamdeck_ui.ui_button import Ui_ButtonForm

    main_window, api = api_and_window
    _select_first_button(qtbot, main_window)

    # Stub the dialog so it "returns" a chosen combination without user input.
    def fake_exec(self):
        self._modifier_boxes["super"].setChecked(True)
        self.key_combo.setEditText("l")
        return gui.QDialog.DialogCode.Accepted

    mocker.patch.object(KeyCombineDialog, "exec", fake_exec)
    keys_spy = mocker.spy(api, "set_button_keys")

    ui = Ui_ButtonForm()
    holder = QWidget()
    ui.setupUi(holder)
    qtbot.addWidget(holder)

    gui.show_key_combine_dialog(ui)

    assert ui.keys.text() == "super+l"
    keys_spy.assert_called_once()
    assert keys_spy.call_args.args[-1] == "super+l"
