import re

from streamdeck_ui.modules import live


def test_none_source_is_not_live_and_empty():
    assert live.is_live_source("") is False
    assert live.is_live_source("bogus") is False
    assert live.live_text("") == ""
    assert live.live_text("bogus") == ""


def test_known_sources_are_live():
    for key, _label in live.LIVE_SOURCES:
        if key:
            assert live.is_live_source(key) is True


def test_clock_matches_time_format():
    assert re.fullmatch(r"\d{2}:\d{2}", live.live_text("clock"))
    assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", live.live_text("clock_seconds"))


def test_metric_sources_return_non_empty_text():
    # These read from /proc and /sys; on the first call rate metrics may show a
    # placeholder, but they must always return some text to render.
    for key in ("date", "datetime", "cpu", "memory", "battery", "network"):
        assert live.live_text(key)


def test_cpu_reports_percentage_after_two_samples():
    live.live_text("cpu")  # establish a baseline
    text = live.live_text("cpu")
    assert "CPU" in text
