"""Tests for SanitizeFilter class."""

from checkend.filters.sanitize_filter import FILTERED_VALUE, SanitizeFilter


class TestSanitizeFilter:
    def setup_method(self):
        self.filter = SanitizeFilter(["password", "secret", "token"])

    def test_filter_simple_dict(self):
        data = {"username": "john", "password": "secret123"}
        result = self.filter.filter(data)
        assert result["username"] == "john"
        assert result["password"] == FILTERED_VALUE

    def test_filter_nested_dict(self):
        data = {
            "user": {
                "name": "John",
                "credentials": {
                    "password": "secret123",
                    "api_token": "abc123",
                },
            }
        }
        result = self.filter.filter(data)
        assert result["user"]["name"] == "John"
        assert result["user"]["credentials"]["password"] == FILTERED_VALUE
        assert result["user"]["credentials"]["api_token"] == FILTERED_VALUE

    def test_filter_list_of_dicts(self):
        data = [
            {"name": "Alice", "password": "pass1"},
            {"name": "Bob", "password": "pass2"},
        ]
        result = self.filter.filter(data)
        assert result[0]["name"] == "Alice"
        assert result[0]["password"] == FILTERED_VALUE
        assert result[1]["name"] == "Bob"
        assert result[1]["password"] == FILTERED_VALUE

    def test_filter_case_insensitive(self):
        data = {
            "PASSWORD": "value1",
            "Password": "value2",
            "password": "value3",
        }
        result = self.filter.filter(data)
        assert result["PASSWORD"] == FILTERED_VALUE
        assert result["Password"] == FILTERED_VALUE
        assert result["password"] == FILTERED_VALUE

    def test_filter_partial_match(self):
        data = {
            "user_password": "secret",
            "password_hash": "hash",
            "secret_key": "key",
        }
        result = self.filter.filter(data)
        assert result["user_password"] == FILTERED_VALUE
        assert result["password_hash"] == FILTERED_VALUE
        assert result["secret_key"] == FILTERED_VALUE

    def test_filter_preserves_non_sensitive_data(self):
        data = {
            "id": 123,
            "name": "Test",
            "active": True,
            "value": 3.14,
            "items": [1, 2, 3],
        }
        result = self.filter.filter(data)
        assert result == data

    def test_filter_handles_none(self):
        data = {"key": None, "password": None}
        result = self.filter.filter(data)
        assert result["key"] is None
        assert result["password"] == FILTERED_VALUE

    def test_filter_truncates_long_strings(self):
        long_string = "x" * 15000
        data = {"message": long_string}
        result = self.filter.filter(data)
        assert len(result["message"]) == 10003  # 10000 + '...'
        assert result["message"].endswith("...")

    def test_filter_handles_circular_reference(self):
        data = {"key": "value"}
        data["self"] = data  # Circular reference
        result = self.filter.filter(data)
        assert result["key"] == "value"
        assert result["self"] == "[CIRCULAR]"

    def test_filter_handles_deep_nesting(self):
        data = {"level": 0}
        current = data
        for i in range(15):
            current["nested"] = {"level": i + 1}
            current = current["nested"]

        result = self.filter.filter(data)
        # Should not raise, should handle max depth
        assert result["level"] == 0

    def test_filter_converts_non_standard_types(self):
        class CustomClass:
            def __str__(self):
                return "custom_value"

        data = {"custom": CustomClass()}
        result = self.filter.filter(data)
        assert result["custom"] == "custom_value"

    def test_filter_empty_dict(self):
        result = self.filter.filter({})
        assert result == {}

    def test_filter_empty_list(self):
        result = self.filter.filter([])
        assert result == []

    def test_filter_primitives(self):
        assert self.filter.filter("string") == "string"
        assert self.filter.filter(123) == 123
        assert self.filter.filter(3.14) == 3.14
        assert self.filter.filter(True) is True
        assert self.filter.filter(None) is None
