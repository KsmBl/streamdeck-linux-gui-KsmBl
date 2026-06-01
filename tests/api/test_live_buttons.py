from tests.common import STREAMDECK_SERIAL


def test_live_source_default_empty(api_server):
    assert api_server.get_button_live_source(STREAMDECK_SERIAL, 0, 0) == ""


def test_set_and_get_live_source(api_server):
    api_server.set_button_live_source(STREAMDECK_SERIAL, 0, 0, "clock")
    assert api_server.get_button_live_source(STREAMDECK_SERIAL, 0, 0) == "clock"


def test_invalid_live_source_is_ignored(api_server):
    api_server.set_button_live_source(STREAMDECK_SERIAL, 0, 0, "bogus")
    assert api_server.get_button_live_source(STREAMDECK_SERIAL, 0, 0) == ""


def test_live_source_overrides_text_in_filters(api_server, mock_filters):
    api_server.set_button_text(STREAMDECK_SERIAL, 0, 0, "static")
    api_server.set_button_live_source(STREAMDECK_SERIAL, 0, 0, "clock")

    # The most recently built TextFilter used the live clock value, not "static".
    text_filter = mock_filters["streamdeck_ui.api.TextFilter"]
    last_text = text_filter.call_args.args[0]
    assert last_text and last_text != "static"


def test_refresh_live_buttons_only_when_present(api_server):
    # No live buttons yet.
    assert api_server.refresh_live_buttons() is False

    page = api_server.get_page(STREAMDECK_SERIAL)
    api_server.set_button_live_source(STREAMDECK_SERIAL, page, 0, "clock")
    assert api_server.refresh_live_buttons() is True
