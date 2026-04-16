"""
Unit tests for ClearWinStart.core module.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from clear_win_start.core import StartMenuOrganizer
from clear_win_start.exceptions import PathNotFoundError, PermissionError
from clear_win_start.utils import Configuration


class TestStartMenuOrganizer:
    """Tests for StartMenuOrganizer class."""

    def test_init_with_config(self, mock_config: Configuration):
        """Test initialization with configuration."""
        organizer = StartMenuOrganizer(mock_config)
        assert organizer.config == mock_config
        assert organizer.stats["folders_processed"] == 0

    def test_init_without_config(self):
        """Test initialization without configuration."""
        organizer = StartMenuOrganizer()
        assert organizer.config.user_name == ""

    def test_reset_stats(self, mock_config: Configuration):
        """Test statistics reset."""
        organizer = StartMenuOrganizer(mock_config)
        organizer.stats["folders_processed"] = 5
        organizer._reset_stats()
        assert organizer.stats["folders_processed"] == 0

    def test_get_folders_to_process(
        self, mock_config: Configuration, sample_start_menu_structure: str
    ):
        """Test getting folders to process."""
        mock_config.paths = [sample_start_menu_structure]
        organizer = StartMenuOrganizer(mock_config)
        folders = organizer._get_folders_to_process(sample_start_menu_structure)
        assert "Application1" in folders
        assert "Application2" in folders
        assert "Accessories" not in folders
        assert "Startup" not in folders

    def test_process_folder_dry_run(
        self, mock_config: Configuration, sample_start_menu_structure: str
    ):
        """Test folder processing in dry run mode."""
        mock_config.paths = [sample_start_menu_structure]
        mock_config.dry_run = True
        organizer = StartMenuOrganizer(mock_config)

        initial_files = len(os.listdir(sample_start_menu_structure))
        organizer._process_folder(sample_start_menu_structure, "Application1")
        final_files = len(os.listdir(sample_start_menu_structure))
        assert initial_files == final_files

    def test_process_folder(
        self, mock_config: Configuration, sample_start_menu_structure: str
    ):
        """Test folder processing."""
        mock_config.paths = [sample_start_menu_structure]
        organizer = StartMenuOrganizer(mock_config)

        result = organizer._process_folder(sample_start_menu_structure, "Application1")

        assert result is True
        assert os.path.exists(os.path.join(sample_start_menu_structure, "app1.exe"))
        assert not os.path.exists(os.path.join(sample_start_menu_structure, "Application1"))

    def test_process_nested_folder(
        self, mock_config: Configuration, sample_start_menu_structure: str
    ):
        """Test processing nested folder."""
        mock_config.paths = [sample_start_menu_structure]
        organizer = StartMenuOrganizer(mock_config)

        nested_path = os.path.join(sample_start_menu_structure, "Application2", "SubFolder")
        organizer._process_nested_folder(nested_path, sample_start_menu_structure)

        assert os.path.exists(os.path.join(sample_start_menu_structure, "app3.exe"))
        assert not os.path.exists(nested_path)

    def test_clean_keyword_files(
        self, mock_config: Configuration, sample_start_menu_structure: str
    ):
        """Test cleaning keyword files."""
        mock_config.paths = [sample_start_menu_structure]
        organizer = StartMenuOrganizer(mock_config)

        organizer._clean_keyword_files(sample_start_menu_structure)

        assert not os.path.exists(os.path.join(sample_start_menu_structure, "卸载.txt"))
        assert not os.path.exists(os.path.join(sample_start_menu_structure, "官网.url"))

    def test_validate_paths_valid(
        self, mock_config: Configuration, sample_start_menu_structure: str
    ):
        """Test path validation with valid paths."""
        mock_config.paths = [sample_start_menu_structure]
        organizer = StartMenuOrganizer(mock_config)
        errors = organizer.validate_paths()
        assert len(errors) == 0

    def test_validate_paths_invalid(self, mock_config: Configuration):
        """Test path validation with invalid paths."""
        mock_config.paths = ["C:\\NonExistent\\Path"]
        organizer = StartMenuOrganizer(mock_config)
        errors = organizer.validate_paths()
        assert len(errors) > 0

    def test_get_stats(self, mock_config: Configuration):
        """Test getting statistics."""
        organizer = StartMenuOrganizer(mock_config)
        organizer.stats["files_moved"] = 10
        stats = organizer.get_stats()
        assert stats["files_moved"] == 10

    def test_organize_path_not_found(self, mock_config: Configuration):
        """Test organize with non-existent path."""
        mock_config.paths = ["C:\\NonExistent\\Path"]
        organizer = StartMenuOrganizer(mock_config)
        stats = organizer.organize(auto_confirm=True)
        assert "folders_processed" in stats
