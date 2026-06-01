from tests.common import STREAMDECK_SERIAL


def test_cycle_states_default_off(api_server):
    assert api_server.get_button_cycle_states(STREAMDECK_SERIAL, 0, 0) is False


def test_set_and_get_cycle_states(api_server):
    api_server.set_button_cycle_states(STREAMDECK_SERIAL, 0, 0, True)
    assert api_server.get_button_cycle_states(STREAMDECK_SERIAL, 0, 0) is True

    api_server.set_button_cycle_states(STREAMDECK_SERIAL, 0, 0, False)
    assert api_server.get_button_cycle_states(STREAMDECK_SERIAL, 0, 0) is False
