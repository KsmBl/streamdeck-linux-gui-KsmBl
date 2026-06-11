import threading

from streamdeck_ui import tui
from tests.common import STREAMDECK_SERIAL, create_test_api_server


def _api():
    api = create_test_api_server()
    api.dimmers[STREAMDECK_SERIAL].reset.return_value = False
    return api


def test_classify_button_picks_glyph_colour_and_label():
    api = _api()
    # An empty button has no glyph and no label.
    api.set_button_text(STREAMDECK_SERIAL, 0, 0, "")
    glyph, color, label = tui.classify_button(api, STREAMDECK_SERIAL, 0, 0)
    assert (glyph, color, label) == ("", tui.C_DIM, "")
    # A command tile is green and shows its text.
    api.set_button_text(STREAMDECK_SERIAL, 0, 0, "Mute\nmic")
    api.set_button_command(STREAMDECK_SERIAL, 0, 0, "pactl set-sink-mute 0 toggle")
    glyph, color, label = tui.classify_button(api, STREAMDECK_SERIAL, 0, 0)
    assert color == tui.C_CMD and label == "Mute"
    # A live source takes precedence and tints the tile as a live source.
    api.set_button_live_source(STREAMDECK_SERIAL, 0, 0, "clock")
    glyph, color, label = tui.classify_button(api, STREAMDECK_SERIAL, 0, 0)
    assert color == tui.C_LIVE and glyph == "◷"


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


def test_attached_signal_delivers_from_a_background_thread():
    # The Stream Deck monitor emits ``attached`` from a worker thread; with no Qt
    # event loop running, the text UI must still see it (direct connection),
    # otherwise it sits forever on "Waiting for a Stream Deck".
    api = create_test_api_server()
    ui = tui.TextUI(api)
    tui.connect_signals(api, ui)

    def worker():
        api.plugevents.attached.emit(
            {"id": "x", "serial_number": "NEWDECK", "type": "Stream Deck Original", "layout": (3, 5)}
        )

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert ui.deck_id == "NEWDECK"


def test_tabs_list_pages_then_auto_pages():
    api = _api()
    auto = api.add_auto_page(STREAMDECK_SERIAL, "firefox")
    ui = tui.TextUI(api)
    ui.deck_id = STREAMDECK_SERIAL
    tabs = ui._tabs()
    # Normal pages first, numbered "1", "2"; then the auto page, flagged is_auto.
    assert [(p, label) for p, label, _is_auto in tabs[:2]] == [(0, "1"), (1, "2")]
    assert (auto, "firefox", True) in tabs


def test_change_tab_cycles_onto_an_auto_page():
    api = _api()
    auto = api.add_auto_page(STREAMDECK_SERIAL, "firefox")
    ui = tui.TextUI(api)
    ui.deck_id = STREAMDECK_SERIAL
    api.set_page(STREAMDECK_SERIAL, 1)  # the last normal page
    ui._change_tab(1)  # advances onto the Auto tab
    assert api.get_page(STREAMDECK_SERIAL) == auto


def test_wrap_label_keeps_words_and_newlines():
    assert tui.wrap_label("Mute the mic", 6, 3) == ["Mute", "the", "mic"]
    assert tui.wrap_label("Hi\nthere", 10, 3) == ["Hi", "there"]
    # Overflowing content is clipped to max_lines with an ellipsis on the last.
    assert tui.wrap_label("one two three four", 4, 2) == ["one", "two…"]


def test_change_page_skips_when_single_page():
    api = _api()
    ui = tui.TextUI(api)
    ui.deck_id = STREAMDECK_SERIAL
    start_page = api.get_page(STREAMDECK_SERIAL)
    ui._change_page(1)
    # The test deck has two normal pages, so paging advances.
    assert api.get_page(STREAMDECK_SERIAL) != start_page
    assert api.get_page(STREAMDECK_SERIAL) in api.get_pages(STREAMDECK_SERIAL)
