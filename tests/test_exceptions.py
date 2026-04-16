"""
Unit tests for ClearWinStart.exceptions module.
"""

import pytest

from clear_win_start.exceptions import (
    ConfigurationError,
    PermissionError,
    PathNotFoundError,
    ShortcutParseError,
    StartMenuOrganizerError,
)


class TestExceptions:
    """Tests for custom exceptions."""

    def test_start_menu_organizer_error(self):
        """Test base exception."""
        exc = StartMenuOrganizerError("Test error")
        assert str(exc) == "Test error"
        assert exc.message == "Test error"

    def test_permission_error(self):
        """Test permission error."""
        exc = PermissionError("C:\\Test\\Path")
        assert "C:\\Test\\Path" in str(exc)
        assert exc.path == "C:\\Test\\Path"

    def test_path_not_found_error(self):
        """Test path not found error."""
        exc = PathNotFoundError("C:\\NonExistent")
        assert "C:\\NonExistent" in str(exc)
        assert exc.path == "C:\\NonExistent"

    def test_configuration_error(self):
        """Test configuration error."""
        exc = ConfigurationError("Invalid setting")
        assert "Invalid setting" in str(exc)
        assert "Configuration error" in str(exc)

    def test_shortcut_parse_error(self):
        """Test shortcut parse error."""
        exc = ShortcutParseError("test.lnk", "Invalid format")
        assert "test.lnk" in str(exc)
        assert exc.shortcut_path == "test.lnk"

    def test_exception_inheritance(self):
        """Test exception hierarchy."""
        exc = StartMenuOrganizerError("test")
        assert isinstance(exc, Exception)

        perm_exc = PermissionError("path")
        assert isinstance(perm_exc, StartMenuOrganizerError)
        assert isinstance(perm_exc, Exception)
