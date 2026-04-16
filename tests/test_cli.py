"""
Unit tests for ClearWinStart.cli module.
"""

import pytest

from clear_win_start.cli import build_config, create_parser, main
from clear_win_start.utils import Configuration


class TestArgParser:
    """Tests for argument parser."""

    def test_parser_creation(self):
        """Test parser creation."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "clear-win-start"

    def test_version_argument(self, capsys):
        """Test version argument."""
        with pytest.raises(SystemExit):
            main(["--version"])
        captured = capsys.readouterr()
        assert "clear-win-start" in captured.out

    def test_help_argument(self, capsys):
        """Test help argument."""
        with pytest.raises(SystemExit):
            main(["--help"])
        captured = capsys.readouterr()
        assert "organize" in captured.out.lower()


class TestBuildConfig:
    """Tests for build_config function."""

    def test_build_config_with_user_name(self, mock_windows_username):
        """Test building config with explicit user name."""
        args = create_parser().parse_args(["--user-name", "test"])
        config = build_config(args)
        assert config.user_name == "test"

    def test_build_config_auto_detect_username(self, mock_windows_username):
        """Test building config with auto-detected user name."""
        args = create_parser().parse_args([])
        config = build_config(args)
        assert config.user_name == "mock_user"

    def test_build_config_with_config_file(self, mock_config_file, mock_windows_username):
        """Test building config from file."""
        args = create_parser().parse_args(["--config", mock_config_file])
        config = build_config(args)
        assert config.user_name == "mock_user"

    def test_build_config_dry_run(self, mock_windows_username):
        """Test dry run flag."""
        args = create_parser().parse_args(["--dry-run"])
        config = build_config(args)
        assert config.dry_run is True

    def test_build_config_auto_confirm(self, mock_windows_username):
        """Test auto confirm flag."""
        args = create_parser().parse_args(["--auto-confirm"])
        config = build_config(args)
        assert config.dry_run is False

    def test_build_config_no_check_shortcuts(self, mock_windows_username):
        """Test no check shortcuts flag."""
        args = create_parser().parse_args(["--no-check-shortcuts"])
        config = build_config(args)
        assert config.check_shortcuts is False

    def test_build_config_with_paths(self, mock_windows_username):
        """Test custom paths."""
        args = create_parser().parse_args(["--paths", "C:\\Path1", "C:\\Path2"])
        config = build_config(args)
        assert config.paths == ["C:\\Path1", "C:\\Path2"]

    def test_build_config_with_neglect_folders(self, mock_windows_username):
        """Test custom neglect folders."""
        args = create_parser().parse_args(["--neglect-folders", "Folder1", "Folder2"])
        config = build_config(args)
        assert config.neglect_folders == ["Folder1", "Folder2"]

    def test_build_config_with_delete_keywords(self, mock_windows_username):
        """Test custom delete keywords."""
        args = create_parser().parse_args(["--delete-keywords", "kw1", "kw2"])
        config = build_config(args)
        assert config.delete_keywords == ["kw1", "kw2"]


class TestMain:
    """Tests for main function."""

    def test_main_validate_only(self, mock_config_file, mock_windows_username, capsys, temp_dir):
        """Test validate-only mode."""
        import os
        config_path = os.path.join(temp_dir, "test_config.json")
        config_content = {
            "user_name": "test_user",
            "paths": [temp_dir],
        }
        import json
        with open(config_path, "w") as f:
            json.dump(config_content, f)
        args = ["--config", config_path, "--validate-only"]
        result = main(args)
        assert result == 0

    def test_main_keyboard_interrupt(self, monkeypatch, mock_windows_username, temp_dir):
        """Test keyboard interrupt handling during confirmation."""
        import sys
        import builtins
        import os

        config_path = os.path.join(temp_dir, "test_config.json")
        import json
        with open(config_path, "w") as f:
            json.dump({
                "user_name": "mock_user",
                "paths": [temp_dir],
                "dry_run": False
            }, f)

        original_input = builtins.input
        builtins.input = lambda x: (_ for _ in ()).throw(KeyboardInterrupt)
        try:
            args = ["--config", config_path]
            result = main(args)
            assert result == 130
        finally:
            builtins.input = original_input
