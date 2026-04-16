"""
Unit tests for ClearWinStart.utils module.
"""

import json
import os
import tempfile

import pytest

from clear_win_start.exceptions import ConfigurationError, PathNotFoundError
from clear_win_start.utils import (
    Configuration,
    confirm_action,
    get_windows_username,
    setup_logging,
)


class TestConfiguration:
    """Tests for Configuration class."""

    def test_init_with_user_name(self):
        """Test initialization with user name only."""
        config = Configuration(user_name="test_user")
        assert config.user_name == "test_user"
        assert len(config.paths) > 0
        assert len(config.neglect_folders) > 0
        assert len(config.delete_keywords) > 0

    def test_init_with_all_params(self):
        """Test initialization with all parameters."""
        config = Configuration(
            user_name="test_user",
            paths=["C:\\Path1", "C:\\Path2"],
            neglect_folders=["Folder1"],
            delete_keywords=["keyword1"],
            check_shortcuts=False,
            dry_run=True,
        )
        assert config.paths == ["C:\\Path1", "C:\\Path2"]
        assert config.neglect_folders == ["Folder1"]
        assert config.delete_keywords == ["keyword1"]
        assert config.check_shortcuts is False
        assert config.dry_run is True

    def test_from_file(self, mock_config_file: str):
        """Test loading configuration from file."""
        config = Configuration.from_file(mock_config_file)
        assert config.user_name == "test_user"
        assert len(config.paths) > 0

    def test_from_file_not_found(self):
        """Test loading from non-existent file."""
        with pytest.raises(PathNotFoundError):
            Configuration.from_file("C:\\NonExistent\\config.json")

    def test_from_file_invalid_json(self, temp_dir: str):
        """Test loading from invalid JSON file."""
        config_path = os.path.join(temp_dir, "invalid.json")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        with pytest.raises(ConfigurationError):
            Configuration.from_file(config_path)

    def test_from_file_missing_user_name(self, temp_dir: str):
        """Test loading from file missing required fields."""
        config_path = os.path.join(temp_dir, "missing.json")
        with open(config_path, "w") as f:
            json.dump({"paths": []}, f)

        with pytest.raises(ConfigurationError):
            Configuration.from_file(config_path)

    def test_to_file(self, temp_dir: str):
        """Test saving configuration to file."""
        config = Configuration(
            user_name="test_user",
            paths=["C:\\Path1"],
            check_shortcuts=True,
        )
        config_path = os.path.join(temp_dir, "output.json")
        config.to_file(config_path)

        assert os.path.exists(config_path)
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["user_name"] == "test_user"

    def test_validate_success(self):
        """Test validation with valid configuration."""
        config = Configuration(user_name="test_user")
        config.validate()

    def test_validate_empty_user_name(self):
        """Test validation with empty user name."""
        config = Configuration(user_name="")
        with pytest.raises(ConfigurationError):
            config.validate()

    def test_validate_empty_paths(self):
        """Test validation with empty paths."""
        config = Configuration(user_name="test", paths=["C:\\Path1"])
        config.paths = []
        with pytest.raises(ConfigurationError):
            config.validate()


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_confirm_action_yes(self, monkeypatch):
        """Test confirm_action with yes input."""
        monkeypatch.setattr("builtins.input", lambda x: "y")
        assert confirm_action("Continue?") is True

    def test_confirm_action_no(self, monkeypatch):
        """Test confirm_action with no input."""
        monkeypatch.setattr("builtins.input", lambda x: "n")
        assert confirm_action("Continue?") is False

    def test_confirm_action_yes_full(self, monkeypatch):
        """Test confirm_action with 'yes' input."""
        monkeypatch.setattr("builtins.input", lambda x: "yes")
        assert confirm_action("Continue?") is True

    def test_confirm_action_invalid_then_yes(self, monkeypatch):
        """Test confirm_action with invalid then valid input."""
        inputs = iter(["invalid", "yes"])
        monkeypatch.setattr("builtins.input", lambda x: next(inputs))
        assert confirm_action("Continue?") is True

    def test_get_windows_username(self, mock_windows_username):
        """Test getting Windows username."""
        username = get_windows_username()
        assert username == "mock_user"

    def test_setup_logging_info(self):
        """Test logging setup at INFO level."""
        import logging

        setup_logging(verbose=False)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) > 0
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                assert handler.level == logging.INFO

    def test_setup_logging_debug(self):
        """Test logging setup at DEBUG level."""
        import logging

        setup_logging(verbose=True)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) > 0
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                assert handler.level == logging.DEBUG
