"""Live information sources for buttons.

A button can be configured with a *live source* whose value is rendered as the
button text and refreshed periodically (see the refresh timer in the GUI). The
values are read straight from the kernel via ``/proc`` and ``/sys`` plus the
standard library, so no extra runtime dependency is required and the feature is
Linux-only (which matches the rest of the application).
"""

import os
import time
from datetime import datetime
from typing import Dict, List, Tuple

# Source key -> human label, in the order shown in the button form. The empty
# key means "no live source" (the button shows its normal text instead).
LIVE_SOURCES: List[Tuple[str, str]] = [
    ("", "None"),
    ("clock", "Clock"),
    ("clock_seconds", "Clock (with seconds)"),
    ("date", "Date"),
    ("datetime", "Date & time"),
    ("cpu", "CPU usage"),
    ("cpu_temp", "CPU temperature"),
    ("memory", "Memory usage"),
    ("battery", "Battery"),
    ("network", "Network speed"),
]

_VALID_SOURCES = {key for key, _ in LIVE_SOURCES}

# Cached samples for the rate-based metrics (CPU and network), keyed so the
# first reading establishes a baseline and later readings report the delta.
_cpu_sample: Tuple[int, int] = (0, 0)
_net_sample: Tuple[float, int, int] = (0.0, 0, 0)


def is_live_source(source: str) -> bool:
    """Returns True when ``source`` is a known, non-empty live source."""
    return bool(source) and source in _VALID_SOURCES


def _read_cpu_percent() -> str:
    """Returns aggregate CPU usage since the previous call, as a percentage."""
    global _cpu_sample
    try:
        with open("/proc/stat", "r") as stat:
            fields = stat.readline().split()[1:]
    except OSError:
        return "CPU --"
    values = [int(v) for v in fields]
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    total = sum(values)

    prev_idle, prev_total = _cpu_sample
    _cpu_sample = (idle, total)
    delta_total = total - prev_total
    if prev_total == 0 or delta_total <= 0:
        return "CPU …"
    busy = 100.0 * (1.0 - (idle - prev_idle) / delta_total)
    return f"CPU\n{max(0.0, min(100.0, busy)):.0f}%"


# hwmon sensor names that report a CPU package temperature, most specific first.
_CPU_HWMON_NAMES = ("coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz")
# thermal_zone types that report a CPU temperature, most specific first.
_CPU_ZONE_TYPES = ("x86_pkg_temp", "cpu-thermal", "cpu_thermal", "acpitz")


def _read_first_temp_milli() -> int:
    """Returns a CPU temperature in milli-degrees Celsius, or -1 if unavailable.

    Prefers a dedicated CPU sensor under /sys/class/hwmon, then falls back to a
    matching /sys/class/thermal zone."""
    hwmon_base = "/sys/class/hwmon"
    by_name = {}
    try:
        for entry in os.listdir(hwmon_base):
            path = os.path.join(hwmon_base, entry)
            try:
                with open(os.path.join(path, "name")) as handle:
                    by_name[handle.read().strip()] = path
            except OSError:
                continue
    except OSError:
        by_name = {}
    for name in _CPU_HWMON_NAMES:
        sensor_path = by_name.get(name)
        if sensor_path:
            value = _read_int_file(os.path.join(sensor_path, "temp1_input"))
            if value > 0:
                return value

    thermal_base = "/sys/class/thermal"
    by_type = {}
    try:
        for entry in os.listdir(thermal_base):
            path = os.path.join(thermal_base, entry)
            try:
                with open(os.path.join(path, "type")) as handle:
                    by_type[handle.read().strip()] = path
            except OSError:
                continue
    except OSError:
        by_type = {}
    for zone_type in _CPU_ZONE_TYPES:
        zone_path = by_type.get(zone_type)
        if zone_path:
            value = _read_int_file(os.path.join(zone_path, "temp"))
            if value > 0:
                return value
    return -1


def _read_cpu_temp() -> str:
    """Returns the CPU temperature in degrees Celsius."""
    milli = _read_first_temp_milli()
    if milli < 0:
        return "TEMP --"
    return f"CPU\n{round(milli / 1000)}°C"


def _read_memory_percent() -> str:
    """Returns used memory as a percentage of total."""
    info: Dict[str, int] = {}
    try:
        with open("/proc/meminfo", "r") as meminfo:
            for line in meminfo:
                key, _, rest = line.partition(":")
                info[key] = int(rest.strip().split()[0])  # kB
    except (OSError, ValueError, IndexError):
        return "MEM --"
    total = info.get("MemTotal", 0)
    available = info.get("MemAvailable", info.get("MemFree", 0))
    if total <= 0:
        return "MEM --"
    used = 100.0 * (total - available) / total
    return f"MEM\n{max(0.0, min(100.0, used)):.0f}%"


def _find_battery_dir() -> str:
    base = "/sys/class/power_supply"
    try:
        for name in sorted(os.listdir(base)):
            path = os.path.join(base, name)
            if os.path.isfile(os.path.join(path, "capacity")) and name.lower().startswith("bat"):
                return path
    except OSError:
        return ""
    return ""


def _read_int_file(path: str) -> int:
    try:
        with open(path, "r") as handle:
            return int(handle.read().strip())
    except (OSError, ValueError):
        return -1


def _read_battery() -> str:
    """Returns the battery percentage and a charging marker."""
    battery_dir = _find_battery_dir()
    if not battery_dir:
        return "No\nbattery"
    capacity = _read_int_file(os.path.join(battery_dir, "capacity"))
    if capacity < 0:
        return "BAT --"
    status = ""
    try:
        with open(os.path.join(battery_dir, "status"), "r") as handle:
            status = handle.read().strip().lower()
    except OSError:
        status = ""
    marker = "⚡" if status == "charging" else ""
    return f"BAT{marker}\n{capacity}%"


def _read_network_bytes() -> Tuple[int, int]:
    rx = tx = 0
    try:
        with open("/proc/net/dev", "r") as netdev:
            lines = netdev.readlines()[2:]
    except OSError:
        return (0, 0)
    for line in lines:
        name, _, data = line.partition(":")
        if name.strip() == "lo":
            continue
        fields = data.split()
        if len(fields) >= 9:
            rx += int(fields[0])
            tx += int(fields[8])
    return (rx, tx)


def _format_rate(bytes_per_second: float) -> str:
    if bytes_per_second >= 1024 * 1024:
        return f"{bytes_per_second / (1024 * 1024):.1f}M"
    if bytes_per_second >= 1024:
        return f"{bytes_per_second / 1024:.0f}K"
    return f"{bytes_per_second:.0f}B"


def _read_network() -> str:
    """Returns the up/down network throughput since the previous call."""
    global _net_sample
    now = time.monotonic()
    rx, tx = _read_network_bytes()
    prev_time, prev_rx, prev_tx = _net_sample
    _net_sample = (now, rx, tx)
    elapsed = now - prev_time
    if prev_time == 0.0 or elapsed <= 0:
        return "NET …"
    down = _format_rate((rx - prev_rx) / elapsed)
    up = _format_rate((tx - prev_tx) / elapsed)
    return f"↓{down}\n↑{up}"


def live_text(source: str) -> str:
    """Returns the current text for the given live source.

    Unknown or empty sources return an empty string. Multi-line results use a
    newline so the value and its label stack on the key.
    """
    if not is_live_source(source):
        return ""
    if source == "clock":
        return datetime.now().strftime("%H:%M")
    if source == "clock_seconds":
        return datetime.now().strftime("%H:%M:%S")
    if source == "date":
        return datetime.now().strftime("%a\n%d %b")
    if source == "datetime":
        return datetime.now().strftime("%H:%M\n%d %b")
    if source == "cpu":
        return _read_cpu_percent()
    if source == "cpu_temp":
        return _read_cpu_temp()
    if source == "memory":
        return _read_memory_percent()
    if source == "battery":
        return _read_battery()
    if source == "network":
        return _read_network()
    return ""
