from unittest.mock import patch

import pytest

from streamdeck_ui.modules import daemon


def test_daemonize_detaches_and_redirects():
    """In the surviving child both forks return 0; the process should create a
    new session and redirect the three standard streams."""
    with patch("os.fork", return_value=0) as fork, patch("os.setsid") as setsid, patch("os.chdir") as chdir, patch(
        "os.dup2"
    ) as dup2, patch("os.open", return_value=7), patch("os.close"), patch("sys.stdout.flush"), patch(
        "sys.stderr.flush"
    ):
        daemon.daemonize("/tmp/streamdeck-test.log")

    assert fork.call_count == 2
    setsid.assert_called_once()
    chdir.assert_called_once_with("/")
    # stdin, stdout and stderr are all redirected.
    assert dup2.call_count == 3


def test_daemonize_parent_exits():
    """The original (parent) process must exit after the first fork."""
    with patch("os.fork", return_value=4321), patch("os._exit", side_effect=SystemExit) as exit_mock, patch(
        "os.setsid"
    ) as setsid:
        with pytest.raises(SystemExit):
            daemon.daemonize("/tmp/streamdeck-test.log")

    exit_mock.assert_called_once_with(0)
    # We exited before reaching setsid.
    setsid.assert_not_called()
