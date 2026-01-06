"""Tests for app.bot.formatters module."""

import pytest

from app.bot.formatters import (
    format_uptime,
    format_bytes,
    format_percentage,
    truncate,
)


class TestFormatUptime:
    """Tests for format_uptime function."""

    def test_seconds_only(self):
        assert format_uptime("45") == "45s"

    def test_seconds_with_suffix(self):
        assert format_uptime("45s") == "45s"

    def test_minutes_and_seconds(self):
        assert format_uptime("125") == "2m 5s"

    def test_hours_minutes_seconds(self):
        assert format_uptime("3665") == "1h 1m 5s"

    def test_days_hours_minutes(self):
        assert format_uptime("90061") == "1d 1h 1m 1s"

    def test_already_formatted(self):
        assert format_uptime("1d2h3m4s") == "1d2h3m4s"

    def test_zero_seconds(self):
        assert format_uptime("0") == "0s"

    def test_invalid_input(self):
        assert format_uptime("invalid") == "invalid"

    def test_empty_string(self):
        assert format_uptime("") == ""


class TestFormatBytes:
    """Tests for format_bytes function."""

    def test_bytes(self):
        assert format_bytes("500") == "500 B"

    def test_kilobytes(self):
        assert format_bytes("1536") == "1.5 KB"

    def test_megabytes(self):
        assert format_bytes("1572864") == "1.5 MB"

    def test_gigabytes(self):
        assert format_bytes("1610612736") == "1.5 GB"

    def test_terabytes(self):
        assert format_bytes("1649267441664") == "1.5 TB"

    def test_integer_input(self):
        assert format_bytes(1024) == "1.0 KB"

    def test_zero(self):
        assert format_bytes("0") == "0 B"

    def test_invalid_input(self):
        assert format_bytes("invalid") == "invalid"


class TestFormatPercentage:
    """Tests for format_percentage function."""

    def test_half_used(self):
        assert format_percentage(500, 1000) == 50.0

    def test_fully_used(self):
        assert format_percentage(0, 1000) == 100.0

    def test_none_used(self):
        assert format_percentage(1000, 1000) == 0.0

    def test_zero_total(self):
        assert format_percentage(500, 0) == 0.0

    def test_rounds_to_one_decimal(self):
        result = format_percentage(333, 1000)
        assert result == 66.7


class TestTruncate:
    """Tests for truncate function."""

    def test_short_text_unchanged(self):
        text = "Hello World"
        assert truncate(text, 100) == text

    def test_exact_length_unchanged(self):
        text = "Hello"
        assert truncate(text, 5) == text

    def test_long_text_truncated(self):
        text = "Hello World"
        result = truncate(text, 8)
        assert result == "Hello..."
        assert len(result) == 8

    def test_default_limit(self):
        text = "A" * 5000
        result = truncate(text)
        assert len(result) == 4096

    def test_empty_string(self):
        assert truncate("", 10) == ""
