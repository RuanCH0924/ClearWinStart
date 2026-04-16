"""
Pytest configuration and fixtures for ClearWinStart tests.
"""

import os
import tempfile
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from clear_win_start.utils import Configuration


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for testing.

    Yields:
        Path to temporary directory.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_config() -> Configuration:
    """Create a mock configuration for testing.

    Returns:
        Configuration instance.
    """
    return Configuration(
        user_name="test_user",
        paths=["C:\\Users\\test_user\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs"],
        neglect_folders=["Accessories", "Startup"],
        delete_keywords=["卸载", "官网", "test_delete"],
        check_shortcuts=True,
        dry_run=False,
    )


@pytest.fixture
def mock_config_file(temp_dir: str) -> str:
    """Create a temporary config file for testing.

    Args:
        temp_dir: Temporary directory path.

    Returns:
        Path to config file.
    """
    config_path = os.path.join(temp_dir, "config.json")
    config_content = """{
    "user_name": "test_user",
    "paths": ["C:\\\\Users\\\\test_user\\\\AppData\\\\Roaming\\\\Microsoft\\\\Windows\\\\Start Menu\\\\Programs"],
    "neglect_folders": ["Accessories"],
    "delete_keywords": ["卸载"],
    "check_shortcuts": true,
    "dry_run": false
}"""
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)
    return config_path


@pytest.fixture
def sample_start_menu_structure(temp_dir: str) -> str:
    """Create a sample Start Menu structure for testing.

    Args:
        temp_dir: Temporary directory path.

    Returns:
        Path to the test Start Menu.
    """
    start_menu = os.path.join(temp_dir, "Start Menu", "Programs")
    os.makedirs(start_menu, exist_ok=True)

    os.makedirs(os.path.join(start_menu, "Accessories"))
    os.makedirs(os.path.join(start_menu, "Startup"))
    os.makedirs(os.path.join(start_menu, "Application1"))
    os.makedirs(os.path.join(start_menu, "Application2", "SubFolder"))

    with open(os.path.join(start_menu, "Application1", "app1.exe"), "w") as f:
        f.write("mock exe")
    with open(os.path.join(start_menu, "Application2", "app2.exe"), "w") as f:
        f.write("mock exe")
    with open(os.path.join(start_menu, "Application2", "SubFolder", "app3.exe"), "w") as f:
        f.write("mock exe")

    with open(os.path.join(start_menu, "卸载.txt"), "w") as f:
        f.write("should be deleted")
    with open(os.path.join(start_menu, "官网.url"), "w") as f:
        f.write("should be deleted")

    return start_menu


@pytest.fixture
def mock_windows_username() -> Generator[None, None, None]:
    """Mock Windows username environment variable.

    Yields:
        None
    """
    with patch.dict(os.environ, {"USERNAME": "mock_user"}):
        yield
