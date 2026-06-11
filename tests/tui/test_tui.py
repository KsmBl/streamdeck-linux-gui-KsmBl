from streamdeck_ui import tui
from tests.common import STREAMDECK_SERIAL, create_test_api_server


def _api():
    api = create_test_api_server()
    api.dimmers[STREAMDECK_SERIAL].reset.return_value = False
    return api


def test_button_summary_prefers_live_then_text_then_placeholder():
    api = _api()
    # Empty button shows a placeholder.
    api.set_button_text(STREAMDECK_SERIAL, 0, 0, "")
    assert tui.button_summary(api, STREAMDECK_SERIAL, 0, 0) == "·"
    # Text wins when present.
    api.set_button_text(STREAMDECK_SERIAL, 0, 0, "Mute\nmic")
    assert tui.button_summary(api, STREAMDECK_SERIAL, 0, 0) == "Mute"
    # A live source takes precedence over the text.
    api.set_button_live_source(STREAMDECK_SERIAL, 0, 0, "clock")
    assert tui.button_summary(api, STREAMDECK_SERIAL, 0, 0) == "~clock"


def test_deck_grid_matches_layout():
    api = _api()
    assert tui.deck_grid(api, STREAMDECK_SERIAL) == api.get_deck_layout(STREAMDECK_SERIAL)


def test_keypress_runs_button_command(mocker):
    api = _api()
    popen = mocker.patch("streamdeck_ui.modules.actions.Popen")
    api.set_button_command(STREAMDECK_SERIAL, 0, 0, "true")

    ui = tui.TextUI(api)
    ui.deck_id = STREAMDECK_SERIAL
    ui.on_keypress(STREAMDECK_SERIAL, 0, True)

    popen.assert_called_once_with(["true"])
    # Pressing a key also moves the selection to that key for visual feedback.
    assert ui.selected == 0


def test_keypress_switches_page():
    api = _api()
    api.set_button_switch_page(STREAMDECK_SERIAL, 0, 0, 2)  # 1-based -> page index 1
    ui = tui.TextUI(api)
    ui.deck_id = STREAMDECK_SERIAL
    ui.on_keypress(STREAMDECK_SERIAL, 0, True)
    assert api.get_page(STREAMDECK_SERIAL) == 1


def test_change_page_skips_when_single_page():
    api = _api()
    ui = tui.TextUI(api)
    ui.deck_id = STREAMDECK_SERIAL
    start_page = api.get_page(STREAMDECK_SERIAL)
    ui._change_page(1)
    # The test deck has two normal pages, so paging advances.
    assert api.get_page(STREAMDECK_SERIAL) != start_page
    assert api.get_page(STREAMDECK_SERIAL) in api.get_pages(STREAMDECK_SERIAL)
