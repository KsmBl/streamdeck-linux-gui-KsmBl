from tests.common import STREAMDECK_SERIAL


def test_focus_follow_default_off(api_server):
    assert api_server.get_focus_follow(STREAMDECK_SERIAL) is False


def test_set_focus_follow(api_server):
    api_server.set_focus_follow(STREAMDECK_SERIAL, True)
    assert api_server.get_focus_follow(STREAMDECK_SERIAL) is True


def test_set_and_get_focus_page(api_server):
    api_server.set_focus_page(STREAMDECK_SERIAL, "firefox", 1)
    assert api_server.get_focus_pages(STREAMDECK_SERIAL) == {"firefox": 1}
    assert api_server.get_focus_app_for_page(STREAMDECK_SERIAL, 1) == "firefox"
    assert api_server.get_focus_app_for_page(STREAMDECK_SERIAL, 0) is None


def test_remove_focus_page(api_server):
    api_server.set_focus_page(STREAMDECK_SERIAL, "firefox", 1)
    api_server.set_focus_page(STREAMDECK_SERIAL, "chromium", 0)
    api_server.remove_focus_page(STREAMDECK_SERIAL, 1)
    assert api_server.get_focus_pages(STREAMDECK_SERIAL) == {"chromium": 0}
