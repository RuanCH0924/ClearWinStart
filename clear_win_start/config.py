"""
Configuration dataclass + 序列化 + ConfigurationWizard。
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Protocol

from clear_win_start.paths import build_default_paths, expand_env_vars

__all__ = ["Configuration", "ConfigurationWizard", "ConsolePrompter", "confirm_action"]


logger = logging.getLogger(__name__)

# 「未配置」哨兵：区分「用户没写」（沿用默认值）与「用户显式写了空列表」（真的不启用）。
# 构造后 Configuration 里不会再残留该对象，外部拿到的始终是普通 list。
_UNSET: List[str] = []


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
    neglect_folders: List[str] = field(default_factory=lambda: _UNSET)
    delete_keywords: List[str] = field(default_factory=lambda: _UNSET)
    check_shortcuts: bool = False
    dedupe_shortcuts: bool = False
    backup_shortcuts: bool = False
    backup_dir: str = ""
    animation: bool = False
    dry_run: bool = False

    def __post_init__(self) -> None:
        DefaultConfig.load_from_file()

        if not self.paths:
            self.paths = build_default_paths(self.user_name)
        else:
            self.paths = [expand_env_vars(p) for p in self.paths]

        # 仅当"未配置"时回退默认值；显式传入的空列表表示"确实不启用"
        if self.neglect_folders is _UNSET:
            self.neglect_folders = DefaultConfig.NEGLECT_FOLDERS.copy()
        if self.delete_keywords is _UNSET:
            self.delete_keywords = DefaultConfig.DELETE_KEYWORDS.copy()
        if self.backup_dir:
            self.backup_dir = expand_env_vars(self.backup_dir)

    @classmethod
    def from_file(cls, config_path: str) -> "Configuration":
        """从 JSON 配置文件加载 Configuration。"""
        if not os.path.exists(config_path):
            # 用本模块自己的异常，避免 config → core 的反向依赖
            raise ConfigurationError(f"Config file not found: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON format: {e}")

        if "user_name" not in data:
            raise ConfigurationError("Missing required field: user_name")

        # 「未配置」保留哨兵 → 沿用默认值；「显式空列表」原样保留 → 真的不启用
        neglect_folders = _UNSET
        raw_folders = data.get("neglect_folders", _UNSET)
        if isinstance(raw_folders, list):
            neglect_folders = raw_folders

        delete_keywords = _UNSET
        raw_keywords = data.get("delete_keywords", _UNSET)
        if isinstance(raw_keywords, (list, dict)):
            delete_keywords = _normalize_keywords(raw_keywords)

        return cls(
            user_name=data["user_name"],
            paths=_normalize_paths(data.get("paths", [])),
            neglect_folders=neglect_folders,
            delete_keywords=delete_keywords,
            check_shortcuts=data.get("check_shortcuts", False),
            dedupe_shortcuts=data.get("dedupe_shortcuts", False),
            backup_shortcuts=data.get("backup_shortcuts", False),
            backup_dir=data.get("backup_dir", ""),
            animation=data.get("animation", False),
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
            "dedupe_shortcuts": self.dedupe_shortcuts,
            "backup_shortcuts": self.backup_shortcuts,
            "backup_dir": self.backup_dir,
            "animation": self.animation,
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
    items: Iterable[object]
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


class Prompter(Protocol):
    """向导提示接口：可注入 ``ConsolePrompter``（终端）或全屏面板实现。"""

    def header(self, title: str) -> None:
        ...

    def section(self, title: str) -> None:
        ...

    def note(self, text: str) -> None:
        ...

    def text(self, prompt: str, default: Optional[str] = None, required: bool = False) -> str:
        ...

    def yes_no(self, prompt: str, default: bool = False) -> bool:
        ...

    def list_input(self, prompt: str, allow_empty: bool = True) -> List[str]:
        ...


class ConsolePrompter:
    """默认的终端提示实现（逐行 print / input），保持向导既有行为。"""

    def header(self, title: str) -> None:
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60)

    def section(self, title: str) -> None:
        print(f"\n--- {title} ---")

    def note(self, text: str) -> None:
        print(text)

    def text(self, prompt: str, default: Optional[str] = None, required: bool = False) -> str:
        if default:
            response = input(f"{prompt} [{default}]: ").strip()
            return response if response else default
        response = input(f"{prompt}: ").strip()
        if required and not response:
            print("This field is required. Please try again.")
            return self.text(prompt, default, required)
        return response

    def yes_no(self, prompt: str, default: bool = False) -> bool:
        default_str = "Y/n" if default else "y/N"
        response = input(f"{prompt} ({default_str}): ").strip().lower()
        if not response:
            return default
        return response in ("y", "yes")

    def list_input(self, prompt: str, allow_empty: bool = True) -> List[str]:
        print(f"{prompt} (Enter empty line to finish)")
        items: List[str] = []
        while True:
            item = input("  - ").strip()
            if not item:
                break
            items.append(item)
        if not items and not allow_empty:
            print("At least one item is required. Please try again.")
            return self.list_input(prompt, allow_empty)
        return items


class ConfigurationWizard:
    """交互式配置生成向导（提示方式可通过 prompter 注入，以适配全屏面板）。"""

    DEFAULT_NEGLECT_FOLDERS: List[str] = [
        "Accessibility", "Accessories", "Administrative", "Tools",
        "desktop.ini", "Startup", "System Tools",
        "Administrative Tools", "Windows PowerShell",
        "Maintenance", "StartUp",
    ]

    # 说明：仅保留语义明确的入口类词（卸载/官网/更新/帮助/意见/关于）。
    # 早期版本还含"设置"，该词过于宽泛（会命中"Windows 设置"等合法入口），已移除。
    DEFAULT_DELETE_KEYWORDS: List[str] = [
        "卸载", "官网", "更新", "帮助", "意见", "关于",
        "install", "Website", "Setting", "Documentation", "Help", ".url",
    ]

    def __init__(self, prompter: Optional[Prompter] = None,
                 default_user_name: str = "") -> None:
        self.prompter: Prompter = prompter or ConsolePrompter()
        self.default_user_name = default_user_name

    # ---- 兼容旧的静态辅助接口（转发给 prompter） ----
    def print_header(self, title: str) -> None:
        self.prompter.header(title)

    def print_section(self, title: str) -> None:
        self.prompter.section(title)

    def get_input(self, prompt: str, default: Optional[str] = None, required: bool = False) -> str:
        return self.prompter.text(prompt, default, required)

    def get_yes_no(self, prompt: str, default: bool = False) -> bool:
        return self.prompter.yes_no(prompt, default)

    def get_list_input(self, prompt: str, allow_empty: bool = True) -> List[str]:
        return self.prompter.list_input(prompt, allow_empty)

    # ---- 入口 ----
    def run(self) -> Configuration:
        prompter = self.prompter
        prompter.header("ClearWinStart Configuration Wizard")

        prompter.note(
            "\nThis wizard will help you create a configuration file for organizing\n"
            "your Windows Start Menu. You can always edit the config.json file later.\n"
            "\nPress Enter to accept default values shown in brackets.\n"
        )

        prompter.section("Step 1: Basic Information")
        user_name = prompter.text(
            "Windows username（已自动检测，回车采用）",
            default=self.default_user_name or None,
            required=True,
        )
        config = Configuration(user_name=user_name)

        prompter.section("Step 2: Paths to Process")
        prompter.note(
            "\nThe following paths will be processed:\n"
            "  1. User Start Menu: %APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\n"
            "  2. System Start Menu: C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\n"
            "\nYou can add additional paths or modify these later.\n"
        )
        if not prompter.yes_no("Use default Start Menu paths", default=True):
            prompter.note("\nEnter additional paths to process:")
            config.paths = prompter.list_input("Enter paths (one per line)", allow_empty=False)

        prompter.section("Step 3: Folders to Preserve")
        prompter.note(
            "\nThese folders will NOT be processed (they contain important system shortcuts):\n"
            "  - Accessories, Administrative Tools, Startup, System Tools, etc.\n"
            "\nYou can customize this list to add or remove folders.\n"
        )
        if prompter.yes_no("Show default preserved folders", default=False):
            listing = "\nDefault folders:\n" + "\n".join(
                f"  - {folder}" for folder in self.DEFAULT_NEGLECT_FOLDERS
            )
            prompter.note(listing)
        if prompter.yes_no("Customize preserved folders", default=False):
            prompter.note("\nEnter folder names to preserve (one per line):")
            config.neglect_folders = prompter.list_input("Enter folder names", allow_empty=True)
        else:
            config.neglect_folders = self.DEFAULT_NEGLECT_FOLDERS.copy()

        prompter.section("Step 4: Keywords to Delete")
        prompter.note(
            "\nFiles and folders containing these keywords will be automatically deleted:\n"
            "  - Chinese: 卸载, 官网, 更新, 帮助, 意见, 关于\n"
            "  - English: install, Website, Setting, Documentation, Help\n"
            "  - Other: .url (URL shortcuts)\n"
        )
        if prompter.yes_no("Show default delete keywords", default=False):
            listing = "\nDefault keywords:\n" + "\n".join(
                f"  - {keyword}" for keyword in self.DEFAULT_DELETE_KEYWORDS
            )
            prompter.note(listing)
        if prompter.yes_no("Customize delete keywords", default=False):
            prompter.note("\nEnter keywords to match for deletion (one per line):")
            config.delete_keywords = prompter.list_input("Enter keywords", allow_empty=True)
        else:
            config.delete_keywords = self.DEFAULT_DELETE_KEYWORDS.copy()

        prompter.section("Step 5: Shortcut Validation")
        prompter.note(
            "\nWhen enabled, the tool will check if shortcuts point to existing files\n"
            "and remove invalid (broken) shortcuts.\n"
        )
        config.check_shortcuts = prompter.yes_no("Check and remove invalid shortcuts", default=True)
        prompter.note(
            "\nWhen enabled, the tool will also remove duplicate shortcuts that point\n"
            "to the same target path, keeping only one of each.\n"
        )
        config.dedupe_shortcuts = prompter.yes_no("Remove duplicate shortcuts", default=True)

        prompter.note(
            "\nWhen enabled, all shortcuts are copied to a backup folder on your\n"
            "Desktop before any changes are made.\n"
        )
        config.backup_shortcuts = prompter.yes_no(
            "Back up all shortcuts before cleanup", default=True
        )
        if config.backup_shortcuts:
            config.backup_dir = prompter.text(
                "Backup directory (blank = Desktop\\ClearWinStart_Backup)", default=""
            )

        prompter.section("Step 6: Dry Run Mode")
        prompter.note(
            "\nDry Run mode allows you to preview changes without actually making them.\n"
            "This is recommended for first-time users.\n"
        )
        config.dry_run = prompter.yes_no("Enable Dry Run mode by default", default=True)

        prompter.header("Configuration Complete!")
        prompter.note(
            f"\nSummary:\n"
            f"  Username: {config.user_name}\n"
            f"  Paths: {len(config.paths)} path(s)\n"
            f"  Preserved folders: {len(config.neglect_folders)} folder(s)\n"
            f"  Delete keywords: {len(config.delete_keywords)} keyword(s)\n"
            f"  Check shortcuts: {config.check_shortcuts}\n"
            f"  Dedupe shortcuts: {config.dedupe_shortcuts}\n"
            f"  Back up shortcuts: {config.backup_shortcuts}\n"
            f"  Dry run mode: {config.dry_run}\n"
        )
        return config

    def save_config(self, config: Configuration, output_path: Optional[str] = None) -> str:
        if output_path is None:
            output_path = self.prompter.text(
                "Enter output path for config file", default="config.json"
            )
        config.to_file(output_path)
        return output_path
