"""Tests for IgnoreFilter class."""

from checkend.filters.ignore_filter import IgnoreFilter


class CustomError(Exception):
    pass


class AnotherError(Exception):
    pass


class TestIgnoreFilter:
    def test_ignore_by_class(self):
        filter = IgnoreFilter([ValueError])
        assert filter.should_ignore(ValueError("test")) is True
        assert filter.should_ignore(TypeError("test")) is False

    def test_ignore_by_class_inheritance(self):
        filter = IgnoreFilter([Exception])
        assert filter.should_ignore(ValueError("test")) is True
        assert filter.should_ignore(TypeError("test")) is True

    def test_ignore_by_string_exact_match(self):
        filter = IgnoreFilter(["ValueError"])
        assert filter.should_ignore(ValueError("test")) is True
        assert filter.should_ignore(TypeError("test")) is False

    def test_ignore_by_string_full_path(self):
        filter = IgnoreFilter(["builtins.ValueError"])
        assert filter.should_ignore(ValueError("test")) is True

    def test_ignore_custom_exception_by_class(self):
        filter = IgnoreFilter([CustomError])
        assert filter.should_ignore(CustomError("test")) is True
        assert filter.should_ignore(AnotherError("test")) is False

    def test_ignore_custom_exception_by_string(self):
        filter = IgnoreFilter(["CustomError"])
        assert filter.should_ignore(CustomError("test")) is True

    def test_ignore_by_regex(self):
        filter = IgnoreFilter([r".*Error"])
        assert filter.should_ignore(ValueError("test")) is True
        assert filter.should_ignore(TypeError("test")) is True
        assert filter.should_ignore(CustomError("test")) is True  # CustomError matches .*Error

    def test_ignore_multiple_patterns(self):
        filter = IgnoreFilter([ValueError, "TypeError", r"Custom.*"])
        assert filter.should_ignore(ValueError("test")) is True
        assert filter.should_ignore(TypeError("test")) is True
        assert filter.should_ignore(CustomError("test")) is True
        assert filter.should_ignore(AnotherError("test")) is False

    def test_empty_ignore_list(self):
        filter = IgnoreFilter([])
        assert filter.should_ignore(ValueError("test")) is False
        assert filter.should_ignore(CustomError("test")) is False

    def test_ignore_keyboard_interrupt(self):
        filter = IgnoreFilter([KeyboardInterrupt])
        assert filter.should_ignore(KeyboardInterrupt()) is True

    def test_ignore_system_exit(self):
        filter = IgnoreFilter([SystemExit])
        assert filter.should_ignore(SystemExit()) is True
