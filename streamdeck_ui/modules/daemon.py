"""Run the Stream Deck UI as a detached background daemon.

This lets the Stream Deck keep working without the configuration window (or the
launching terminal) staying open. It performs the classic double-fork so the
process is fully detached from the controlling terminal.
"""

import os
import signal
import sys

from streamdeck_ui.config import DAEMON_PID_FILE, LOG_FILE


def daemonize(log_file: str = LOG_FILE) -> None:
    """Detaches the current process from the controlling terminal.

    Must be called before the Qt application is created (forking a running Qt
    application is not supported). After this returns, the caller is the
    detached daemon process; the original process and the intermediate fork have
    already exited. Standard streams are redirected to ``log_file``.
    """
    # First fork: let the launching shell return immediately and make sure we
    # are not a process group leader, which is required for setsid().
    if os.fork() > 0:
        os._exit(0)

    os.setsid()

    # Second fork: guarantees the daemon can never re-acquire a controlling
    # terminal.
    if os.fork() > 0:
        os._exit(0)

    os.chdir("/")
    sys.stdout.flush()
    sys.stderr.flush()

    # Reopen the standard file descriptors (0/1/2). stdin is detached from the
    # terminal; stdout/stderr go to the log file so daemon output is not lost.
    devnull_fd = os.open(os.devnull, os.O_RDONLY)
    os.dup2(devnull_fd, 0)
    os.close(devnull_fd)

    try:
        log_fd = os.open(log_file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    except OSError:
        log_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(log_fd, 1)
    os.dup2(log_fd, 2)
    os.close(log_fd)


def write_pid_file(path: str = DAEMON_PID_FILE) -> None:
    """Records the current process id so a running instance can be found and
    stopped later (e.g. via ``--daemon-kill``)."""
    try:
        with open(path, "w") as pid_file:
            pid_file.write(str(os.getpid()))
    except OSError:
        pass


def remove_pid_file(path: str = DAEMON_PID_FILE) -> None:
    """Removes the PID file if present."""
    try:
        os.remove(path)
    except OSError:
        pass


def _read_pid(path: str) -> "int | None":
    try:
        with open(path) as pid_file:
            return int(pid_file.read().strip())
    except (OSError, ValueError):
        return None


def kill_daemon(path: str = DAEMON_PID_FILE) -> str:
    """Stops a running Stream Deck instance recorded in the PID file.

    Returns one of: ``"killed"`` (a SIGTERM was sent), ``"not-running"`` (no PID
    file), ``"stale"`` (the recorded process no longer exists) or ``"error"``.
    """
    pid = _read_pid(path)
    if pid is None:
        return "not-running"

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        remove_pid_file(path)
        return "stale"
    except OSError:
        return "error"

    return "killed"
