import types

from streamdeck_ui.api import StreamDeckServer
from tests.common import STREAMDECK_SERIAL


def _restore_real_save(api):
    """The fixture replaces saving with a mock; restore the real deferred-save
    methods so the coalescing behaviour can be exercised."""
    for name in ("_save_state", "_write_state_now", "flush_state"):
        setattr(api, name, types.MethodType(getattr(StreamDeckServer, name), api))


def test_deferred_save_coalesces_into_one_write(api_server, mocker):
    _restore_real_save(api_server)
    writes = mocker.patch.object(api_server, "export_config")

    # A burst of edits...
    api_server.set_button_text(STREAMDECK_SERIAL, 0, 0, "a")
    api_server.set_button_text(STREAMDECK_SERIAL, 0, 0, "b")
    api_server.set_button_keys(STREAMDECK_SERIAL, 0, 1, "ctrl+a")

    # ...is not written synchronously...
    writes.assert_not_called()

    # ...and collapses into a single write when flushed.
    api_server.flush_state()
    writes.assert_called_once()


def test_flush_state_without_pending_change_does_not_write(api_server, mocker):
    _restore_real_save(api_server)
    writes = mocker.patch.object(api_server, "export_config")
    api_server.flush_state()
    writes.assert_not_called()


def test_batch_synchronizes_once(api_server):
    handler = api_server.display_handlers[STREAMDECK_SERIAL]
    handler.synchronize.reset_mock()

    with api_server.batch():
        api_server.set_button_text(STREAMDECK_SERIAL, 0, 0, "a")
        api_server.set_button_text(STREAMDECK_SERIAL, 0, 1, "b")
        # Per-button synchronisation is suspended inside the batch.
        handler.synchronize.assert_not_called()

    # Exactly one synchronisation happens when the batch ends.
    handler.synchronize.assert_called_once()
