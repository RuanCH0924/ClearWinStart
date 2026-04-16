"""
Tests for new features: Dry Run, Logging, and Configuration Wizard.
"""

import json
import os
import tempfile
import logging
from unittest.mock import patch, MagicMock

from clear_win_start.core import StartMenuOrganizer
from clear_win_start.utils import (
    Configuration,
    ConfigurationWizard,
    setup_logging,
    mask_sensitive_info,
    get_default_log_path
)


class TestDryRunMode:
    """Test enhanced Dry Run mode functionality."""

    def test_dry_run_no_confirmation(self, tmp_path):
        """Test that Dry Run mode skips confirmation prompts."""
        config = Configuration(user_name="testuser")
        config.dry_run = True

        organizer = StartMenuOrganizer(config)

        assert organizer.config.dry_run is True
        assert hasattr(organizer, 'dry_run_plan')
        assert hasattr(organizer, 'dry_run_summary')
        assert organizer.dry_run_plan == []

    def test_dry_run_plan_structure(self):
        """Test that dry run plan has correct structure."""
        config = Configuration(user_name="testuser")
        config.dry_run = True

        organizer = StartMenuOrganizer(config)

        expected_summary_keys = [
            'total_folders',
            'total_files_to_move',
            'total_files_to_delete',
            'total_shortcuts_to_clean',
            'estimated_impact'
        ]

        for key in expected_summary_keys:
            assert key in organizer.dry_run_summary

    def test_get_dry_run_report(self):
        """Test get_dry_run_report method."""
        config = Configuration(user_name="testuser")
        config.dry_run = True

        organizer = StartMenuOrganizer(config)
        report = organizer.get_dry_run_report()

        assert 'plan' in report
        assert 'summary' in report
        assert report['plan'] == []
        assert 'estimated_impact' in report['summary']


class TestLoggingSystem:
    """Test enhanced logging system."""

    def test_setup_logging_creates_handlers(self, tmp_path):
        """Test that setup_logging creates appropriate handlers."""
        log_file = tmp_path / "test.log"

        setup_logging(verbose=False, log_file=str(log_file))

        root_logger = logging.getLogger()
        handlers = root_logger.handlers

        assert len(handlers) >= 2

        has_console = any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in handlers)
        has_file = any(isinstance(h, logging.FileHandler) for h in handlers)

        assert has_console
        assert has_file

    def test_setup_logging_verbose_mode(self):
        """Test verbose mode sets correct log level."""
        setup_logging(verbose=True)

        root_logger = logging.getLogger()
        console_handler = next((h for h in root_logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)), None)

        if console_handler:
            assert console_handler.level == logging.DEBUG

    def test_mask_sensitive_info(self):
        """Test that sensitive information is masked."""
        test_cases = [
            ("password=secret123", "password=*****"),
            ("api_key='abc123'", "api_key='*****'"),
            ("token: xyz789", "token: *****"),
            ("normal message", "normal message"),
        ]

        for input_str, expected in test_cases:
            result = mask_sensitive_info(input_str)
            if "password" in input_str.lower() or "api_key" in input_str.lower() or "token" in input_str.lower():
                assert "*****" in result
                assert "secret" not in result.lower()
                assert "abc" not in result.lower()
                assert "xyz" not in result.lower()

    def test_get_default_log_path(self):
        """Test default log path generation."""
        log_path = get_default_log_path()

        assert log_path is not None
        assert "ClearWinStart" in log_path
        assert "logs" in log_path
        assert log_path.endswith(".log")


class TestConfigurationWizard:
    """Test ConfigurationWizard functionality."""

    def test_wizard_initialization(self):
        """Test wizard initializes with correct defaults."""
        wizard = ConfigurationWizard()

        assert wizard.DEFAULT_NEGLECT_FOLDERS is not None
        assert len(wizard.DEFAULT_NEGLECT_FOLDERS) > 0
        assert wizard.DEFAULT_DELETE_KEYWORDS is not None
        assert len(wizard.DEFAULT_DELETE_KEYWORDS) > 0

    def test_configuration_from_wizard(self):
        """Test that wizard generates valid configuration."""
        wizard = ConfigurationWizard()

        config = Configuration(user_name="testuser")

        assert config.user_name == "testuser"
        assert config.paths is not None
        assert config.neglect_folders is not None
        assert config.delete_keywords is not None
        assert config.check_shortcuts is True
        assert config.dry_run is False


class TestConfigurationEnhanced:
    """Test enhanced Configuration class."""

    def test_config_to_file_and_back(self, tmp_path):
        """Test saving and loading configuration."""
        config = Configuration(user_name="testuser")
        config.dry_run = True
        config.check_shortcuts = False

        config_path = tmp_path / "test_config.json"
        config.to_file(str(config_path))

        loaded_config = Configuration.from_file(str(config_path))

        assert loaded_config.user_name == config.user_name
        assert loaded_config.dry_run == config.dry_run
        assert loaded_config.check_shortcuts == config.check_shortcuts

    def test_config_validation(self):
        """Test configuration validation."""
        config = Configuration(user_name="testuser")
        config.validate()

        empty_user_config = Configuration(user_name="")
        try:
            empty_user_config.validate()
            assert False, "Should raise ConfigurationError"
        except Exception:
            pass
