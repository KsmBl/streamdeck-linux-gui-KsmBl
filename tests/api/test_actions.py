from streamdeck_ui.config import SWITCH_PAGE_LEAVE_AUTO, SWITCH_PAGE_NEXT, SWITCH_PAGE_PREVIOUS
from streamdeck_ui.modules import actions
from tests.common import STREAMDECK_SERIAL


def _no_dim(api):
    # The test fixture's dimmer is a MagicMock whose reset() is truthy; make the
    # press fall through to the real action instead of just waking the display.
    api.dimmers[STREAMDECK_SERIAL].reset.return_value = False


def _resolver(api):
    def resolve(deck_id, page, switch_page):
        return actions.resolve_switch_page(api, deck_id, page, switch_page, last_manual_page={}, last_focused_app=None)

    return resolve


def test_dimmed_press_is_consumed(api_server):
    api_server.dimmers[STREAMDECK_SERIAL].reset.return_value = True
    result = actions.execute_key_action(api_server, STREAMDECK_SERIAL, 0, resolve_switch_page=_resolver(api_server))
    assert result is None


def test_command_runs(api_server, mocker):
    _no_dim(api_server)
    popen = mocker.patch("streamdeck_ui.modules.actions.Popen")
    api_server.set_button_command(STREAMDECK_SERIAL, 0, 0, "echo hi there")
    actions.execute_key_action(api_server, STREAMDECK_SERIAL, 0, resolve_switch_page=_resolver(api_server))
    popen.assert_called_once_with(["echo", "hi", "there"])


def test_keys_and_write(api_server, mocker):
    _no_dim(api_server)
    press = mocker.patch("streamdeck_ui.modules.actions.keyboard_press_keys")
    write = mocker.patch("streamdeck_ui.modules.actions.keyboard_write")
    api_server.set_button_keys(STREAMDECK_SERIAL, 0, 0, "ctrl+c")
    api_server.set_button_write(STREAMDECK_SERIAL, 0, 0, "hello")
    actions.execute_key_action(api_server, STREAMDECK_SERIAL, 0, resolve_switch_page=_resolver(api_server))
    press.assert_called_once_with("ctrl+c")
    write.assert_called_once_with("hello")


def test_switch_page_absolute(api_server, mocker):
    _no_dim(api_server)
    mocker.patch("streamdeck_ui.modules.actions.Popen")
    api_server.set_button_switch_page(STREAMDECK_SERIAL, 0, 0, 2)  # 1-based -> page index 1
    result = actions.execute_key_action(api_server, STREAMDECK_SERIAL, 0, resolve_switch_page=_resolver(api_server))
    assert result.switched_to_page == 1
    assert api_server.get_page(STREAMDECK_SERIAL) == 1


def test_switch_state(api_server):
    _no_dim(api_server)
    api_server.add_new_button_state(STREAMDECK_SERIAL, 0, 0)  # button 0 now has states 0 and 1
    api_server.set_button_switch_state(STREAMDECK_SERIAL, 0, 0, 2)  # switch to state index 1
    result = actions.execute_key_action(api_server, STREAMDECK_SERIAL, 0, resolve_switch_page=_resolver(api_server))
    assert result.new_button_state == 1
    assert api_server.get_button_state(STREAMDECK_SERIAL, 0, 0) == 1


def test_cycle_states(api_server):
    _no_dim(api_server)
    api_server.add_new_button_state(STREAMDECK_SERIAL, 0, 0)
    api_server.set_button_cycle_states(STREAMDECK_SERIAL, 0, 0, True)
    result = actions.execute_key_action(api_server, STREAMDECK_SERIAL, 0, resolve_switch_page=_resolver(api_server))
    assert result.new_button_state == 1


def test_resolve_switch_page_relative():
    class FakeApi:
        def get_pages(self, _serial):
            return [0, 1, 2]

        def get_auto_pages(self, _serial):
            return []

        def get_overlay_page(self, _serial):
            return None

    api = FakeApi()
    assert (
        actions.resolve_switch_page(
            api, STREAMDECK_SERIAL, 0, SWITCH_PAGE_NEXT, last_manual_page={}, last_focused_app=None
        )
        == 1
    )
    assert (
        actions.resolve_switch_page(
            api, STREAMDECK_SERIAL, 0, SWITCH_PAGE_PREVIOUS, last_manual_page={}, last_focused_app=None
        )
        == 2
    )


def test_resolve_leave_auto_uses_last_manual_page():
    class FakeApi:
        def get_pages(self, _serial):
            return [0, 1, 2]

        def get_auto_pages(self, _serial):
            return [2]

        def get_overlay_page(self, _serial):
            return None

    target = actions.resolve_switch_page(
        FakeApi(),
        STREAMDECK_SERIAL,
        2,
        SWITCH_PAGE_LEAVE_AUTO,
        last_manual_page={STREAMDECK_SERIAL: 1},
        last_focused_app=None,
    )
    assert target == 1
