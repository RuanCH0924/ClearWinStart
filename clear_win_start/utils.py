"""
Utility functions and classes for ClearWinStart.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

from clear_win_start.exceptions import ConfigurationError, PathNotFoundError


logger = logging.getLogger(__name__)


@dataclass
class Configuration:
    """Configuration for the Start Menu organizer."""

    user_name: str
    paths: List[str] = field(default_factory=list)
    neglect_folders: List[str] = field(default_factory=list)
    delete_keywords: List[str] = field(default_factory=list)
    check_shortcuts: bool = True
    dry_run: bool = False

    def __post_init__(self) -> None:
        """Initialize default paths if not provided."""
        if not self.paths:
            self.paths = [
                fr"C:\Users\{self.user_name}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs",
                r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
            ]

        if not self.neglect_folders:
            self.neglect_folders = [
                "Accessibility",
                "Accessories",
                "Administrative",
                "Tools",
                "desktop.ini",
                "Startup",
                "System Tools",
                "Administrative Tools",
                "Windows PowerShell",
                "Maintenance",
                "StartUp",
            ]

        if not self.delete_keywords:
            self.delete_keywords = [
                "卸载",
                "官网",
                "更新",
                "帮助",
                "意见",
                "设置",
                "关于",
                "install",
                "Website",
                "Setting",
                "Documentation",
                "Help",
                ".url",
            ]

    @classmethod
    def from_file(cls, config_path: str) -> "Configuration":
        """Load configuration from a JSON file.

        Args:
            config_path: Path to the JSON configuration file.

        Returns:
            Configuration instance.

        Raises:
            PathNotFoundError: If config file does not exist.
            ConfigurationError: If config file is invalid.
        """
        if not os.path.exists(config_path):
            raise PathNotFoundError(config_path)

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON format: {e}")

        required_fields = ["user_name"]
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            raise ConfigurationError(f"Missing required fields: {', '.join(missing_fields)}")

        return cls(
            user_name=data["user_name"],
            paths=data.get("paths", []),
            neglect_folders=data.get("neglect_folders", []),
            delete_keywords=data.get("delete_keywords", []),
            check_shortcuts=data.get("check_shortcuts", True),
            dry_run=data.get("dry_run", False),
        )

    def to_file(self, config_path: str) -> None:
        """Save configuration to a JSON file.

        Args:
            config_path: Path to save the configuration file.
        """
        data = {
            "user_name": self.user_name,
            "paths": self.paths,
            "neglect_folders": self.neglect_folders,
            "delete_keywords": self.delete_keywords,
            "check_shortcuts": self.check_shortcuts,
            "dry_run": self.dry_run,
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        logger.info(f"Configuration saved to {config_path}")

    def validate(self) -> None:
        """Validate the configuration.

        Raises:
            ConfigurationError: If configuration is invalid.
        """
        if not self.user_name:
            raise ConfigurationError("user_name cannot be empty")

        if not isinstance(self.paths, list) or not self.paths:
            raise ConfigurationError("paths must be a non-empty list")

        for path in self.paths:
            if not isinstance(path, str):
                raise ConfigurationError(f"Invalid path type: {type(path)}")


def confirm_action(message: str) -> bool:
    """Prompt user for confirmation.

    Args:
        message: The confirmation message to display.

    Returns:
        True if user confirms, False otherwise.
    """
    while True:
        response = input(f"{message} (y/n): ").strip().lower()
        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            return False
        print("Please enter 'y' or 'n'")


def get_windows_username() -> Optional[str]:
    """Get the current Windows username.

    Returns:
        The Windows username or None if it cannot be determined.
    """
    return os.environ.get("USERNAME") or os.environ.get("USER")


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration.

    Args:
        verbose: If True, set log level to DEBUG; otherwise INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
