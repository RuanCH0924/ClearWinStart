"""
Configuration dataclass + 序列化 + ConfigurationWizard。
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

from clear_win_start.paths import build_default_paths, expand_env_vars

__all__ = ["Configuration", "ConfigurationWizard", "confirm_action"]


logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when there is an error in the configuration."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Configuration error: {message}")


class DefaultConfig:
    """启动时从 `default-config.json` 加载的内置默认配置。"""

    NEGLECT_FOLDERS: List[str] = [
        "Accessibility",
        "Accessories",
        "Administrative",
        "Administrative Tools",
        "desktop.ini",
        "Maintenance",
        "StartUp",
        "Startup",
        "System Tools",
        "Tools",
        "Windows PowerShell",
    ]

    DELETE_KEYWORDS: List[str] = []

    _config_loaded: bool = False

    @classmethod
    def load_from_file(cls, config_path: Optional[str] = None) -> None:
        """从 JSON 文件加载默认值；已加载则直接返回。"""
        if cls._config_loaded:
            return

        path = config_path or cls._find_config_file()
        if not (path and os.path.exists(path)):
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config from {path}: {e}")
            return

        folders = data.get("neglect_folders")
        if isinstance(folders, list) and folders:
            cls.NEGLECT_FOLDERS = folders

        keywords = data.get("delete_keywords")
        if isinstance(keywords, list):
            if keywords:
                cls.DELETE_KEYWORDS = keywords
        elif isinstance(keywords, dict):
            collected: List[str] = []
            for key in ("chinese", "english", "other"):
                if isinstance(keywords.get(key), list):
                    collected.extend(keywords[key])
            if collected:
                cls.DELETE_KEYWORDS = collected

        cls._config_loaded = True

    @classmethod
    def _find_config_file(cls) -> Optional[str]:
        """按优先级查找默认配置文件。"""
        candidates = [
            os.path.join(os.getcwd(), "default-config.json"),
            os.path.join(os.path.dirname(__file__), "..", "default-config.json"),
            os.path.join(os.environ.get("APPDATA", ""), "ClearWinStart", "default-config.json"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    @classmethod
    def reset(cls) -> None:
        """重置为内置默认值（用于配置页"恢复默认"）。"""
        cls._config_loaded = False
        cls.NEGLECT_FOLDERS = [
            "Accessibility", "Accessories", "Administrative",
            "Administrative Tools", "desktop.ini", "Maintenance",
            "StartUp", "Startup", "System Tools", "Tools",
            "Windows PowerShell",
        ]
        cls.DELETE_KEYWORDS = []


@dataclass
class Configuration:
    """Start Menu 整理器的运行时配置。"""

    user_name: str
    paths: List[str] = field(default_factory=list)
    neglect_folders: List[str] = field(default_factory=list)
    delete_keywords: List[str] = field(default_factory=list)
    check_shortcuts: bool = False
    dry_run: bool = False

    def __post_init__(self) -> None:
        DefaultConfig.load_from_file()

        if not self.paths:
            self.paths = build_default_paths(self.user_name)
        else:
            self.paths = [expand_env_vars(p) for p in self.paths]

        if not self.neglect_folders:
            self.neglect_folders = DefaultConfig.NEGLECT_FOLDERS.copy()
        if not self.delete_keywords:
            self.delete_keywords = DefaultConfig.DELETE_KEYWORDS.copy()

    @classmethod
    def from_file(cls, config_path: str) -> "Configuration":
        """从 JSON 配置文件加载 Configuration。"""
        from clear_win_start.core import PathNotFoundError

        if not os.path.exists(config_path):
            raise PathNotFoundError(config_path)

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON format: {e}")

        if "user_name" not in data:
            raise ConfigurationError("Missing required field: user_name")

        return cls(
            user_name=data["user_name"],
            paths=_normalize_paths(data.get("paths", [])),
            neglect_folders=data.get("neglect_folders", []),
            delete_keywords=_normalize_keywords(data.get("delete_keywords", [])),
            check_shortcuts=data.get("check_shortcuts", False),
            dry_run=data.get("dry_run", False),
        )

    def to_file(self, config_path: str, include_metadata: bool = True) -> None:
        """把 Configuration 序列化到 JSON 文件。"""
        data: dict = {
            "user_name": self.user_name,
            "paths": self.paths,
            "neglect_folders": self.neglect_folders,
            "delete_keywords": self.delete_keywords,
            "check_shortcuts": self.check_shortcuts,
            "dry_run": self.dry_run,
        }
        if include_metadata:
            data["version"] = "1.0.0"
            data["description"] = "Generated by ClearWinStart"

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"Configuration saved to {config_path}")

    def validate(self) -> None:
        """校验配置的合法性。"""
        if not self.user_name:
            raise ConfigurationError("user_name cannot be empty")
        if not isinstance(self.paths, list) or not self.paths:
            raise ConfigurationError("paths must be a non-empty list")
        for path in self.paths:
            if not isinstance(path, str):
                raise ConfigurationError(f"Invalid path type: {type(path)}")


def _normalize_paths(raw) -> List[str]:
    """接受 list 或 dict，统一返回展开环境变量后的路径列表。"""
    if isinstance(raw, dict):
        items = raw.values()
    elif isinstance(raw, list):
        items = raw
    else:
        return []
    return [expand_env_vars(p) for p in items if isinstance(p, str)]


def _normalize_keywords(raw) -> List[str]:
    """接受 list 或 dict{ chinese, english, other }，统一返回扁平列表。"""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        collected: List[str] = []
        for key in ("chinese", "english", "other"):
            if isinstance(raw.get(key), list):
                collected.extend(raw[key])
        return collected
    return []


def confirm_action(message: str) -> bool:
    """交互式 y/n 确认。"""
    while True:
        response = input(f"{message} (y/n): ").strip().lower()
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'")


# ----------------------------------------------------------------------
# ConfigurationWizard（保持 CLI 兼容）
# ----------------------------------------------------------------------


class ConfigurationWizard:
    """交互式配置生成向导（CLI 终端使用）。"""

    DEFAULT_NEGLECT_FOLDERS: List[str] = [
        "Accessibility", "Accessories", "Administrative", "Tools",
        "desktop.ini", "Startup", "System Tools",
        "Administrative Tools", "Windows PowerShell",
        "Maintenance", "StartUp",
    ]

    DEFAULT_DELETE_KEYWORDS: List[str] = [
        "卸载", "官网", "更新", "帮助", "意见", "设置", "关于",
        "install", "Website", "Setting", "Documentation", "Help", ".url",
    ]

    # ---- 终端打印辅助 ----
    @staticmethod
    def print_header(title: str) -> None:
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60)

    @staticmethod
    def print_section(title: str) -> None:
        print(f"\n--- {title} ---")

    @staticmethod
    def get_input(prompt: str, default: Optional[str] = None, required: bool = False) -> str:
        if default:
            response = input(f"{prompt} [{default}]: ").strip()
            return response if response else default
        response = input(f"{prompt}: ").strip()
        if required and not response:
            print("This field is required. Please try again.")
            return ConfigurationWizard.get_input(prompt, default, required)
        return response

    @staticmethod
    def get_yes_no(prompt: str, default: bool = False) -> bool:
        default_str = "Y/n" if default else "y/N"
        response = input(f"{prompt} ({default_str}): ").strip().lower()
        if not response:
            return default
        return response in ("y", "yes")

    @staticmethod
    def get_list_input(prompt: str, allow_empty: bool = True) -> List[str]:
        print(f"{prompt} (Enter empty line to finish)")
        items: List[str] = []
        while True:
            item = input("  - ").strip()
            if not item:
                break
            items.append(item)
        if not items and not allow_empty:
            print("At least one item is required. Please try again.")
            return ConfigurationWizard.get_list_input(prompt, allow_empty)
        return items

    # ---- 入口 ----
    def run(self) -> Configuration:
        self.print_header("ClearWinStart Configuration Wizard")

        print(
            "\nThis wizard will help you create a configuration file for organizing\n"
            "your Windows Start Menu. You can always edit the config.json file later.\n"
            "\nPress Enter to accept default values shown in brackets.\n"
        )

        self.print_section("Step 1: Basic Information")
        user_name = self.get_input("Enter your Windows username", required=True)
        config = Configuration(user_name=user_name)

        self.print_section("Step 2: Paths to Process")
        print(
            "\nThe following paths will be processed:\n"
            "  1. User Start Menu: %APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\n"
            "  2. System Start Menu: C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\n"
            "\nYou can add additional paths or modify these later.\n"
        )
        if not self.get_yes_no("Use default Start Menu paths", default=True):
            print("\nEnter additional paths to process:")
            config.paths = self.get_list_input("Enter paths (one per line)", allow_empty=False)

        self.print_section("Step 3: Folders to Preserve")
        print(
            "\nThese folders will NOT be processed (they contain important system shortcuts):\n"
            "  - Accessories, Administrative Tools, Startup, System Tools, etc.\n"
            "\nYou can customize this list to add or remove folders.\n"
        )
        if self.get_yes_no("Show default preserved folders", default=False):
            print("\nDefault folders:")
            for folder in self.DEFAULT_NEGLECT_FOLDERS:
                print(f"  - {folder}")
        if self.get_yes_no("Customize preserved folders", default=False):
            print("\nEnter folder names to preserve (one per line):")
            config.neglect_folders = self.get_list_input("Enter folder names", allow_empty=True)
        else:
            config.neglect_folders = self.DEFAULT_NEGLECT_FOLDERS.copy()

        self.print_section("Step 4: Keywords to Delete")
        print(
            "\nFiles and folders containing these keywords will be automatically deleted:\n"
            "  - Chinese: 卸载, 官网, 更新, 帮助, 意见, 设置, 关于\n"
            "  - English: install, Website, Setting, Documentation, Help\n"
            "  - Other: .url (URL shortcuts)\n"
        )
        if self.get_yes_no("Show default delete keywords", default=False):
            print("\nDefault keywords:")
            for keyword in self.DEFAULT_DELETE_KEYWORDS:
                print(f"  - {keyword}")
        if self.get_yes_no("Customize delete keywords", default=False):
            print("\nEnter keywords to match for deletion (one per line):")
            config.delete_keywords = self.get_list_input("Enter keywords", allow_empty=True)
        else:
            config.delete_keywords = self.DEFAULT_DELETE_KEYWORDS.copy()

        self.print_section("Step 5: Shortcut Validation")
        print(
            "\nWhen enabled, the tool will check if shortcuts point to existing files\n"
            "and remove invalid (broken) shortcuts.\n"
        )
        config.check_shortcuts = self.get_yes_no("Check and remove invalid shortcuts", default=True)

        self.print_section("Step 6: Dry Run Mode")
        print(
            "\nDry Run mode allows you to preview changes without actually making them.\n"
            "This is recommended for first-time users.\n"
        )
        config.dry_run = self.get_yes_no("Enable Dry Run mode by default", default=True)

        self.print_header("Configuration Complete!")
        print(
            f"\nSummary:\n"
            f"  Username: {config.user_name}\n"
            f"  Paths: {len(config.paths)} path(s)\n"
            f"  Preserved folders: {len(config.neglect_folders)} folder(s)\n"
            f"  Delete keywords: {len(config.delete_keywords)} keyword(s)\n"
            f"  Check shortcuts: {config.check_shortcuts}\n"
            f"  Dry run mode: {config.dry_run}\n"
        )
        return config

    def save_config(self, config: Configuration, output_path: Optional[str] = None) -> str:
        if output_path is None:
            output_path = self.get_input("Enter output path for config file", default="config.json")
        config.to_file(output_path)
        return output_path
