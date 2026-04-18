"""
Utility functions and classes for ClearWinStart.
"""

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import List, Optional

from clear_win_start.exceptions import ConfigurationError, PathNotFoundError


logger = logging.getLogger(__name__)


LOG_FORMAT = "%(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FORMAT_DETAILED = "[%(filename)s:%(lineno)d] - %(message)s"


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    COLORS = {
        'DEBUG': '\033[90m',      # Gray
        'INFO': '\033[0m',        # Default
        'WARNING': '\033[93m',    # Yellow
        'ERROR': '\033[91m',      # Red
        'CRITICAL': '\033[91m',   # Red
        'SUCCESS': '\033[92m',    # Green
    }
    
    PREFIXES = {
        'ERROR': '❌ ',
        'WARNING': '⚠️  ',
        'CRITICAL': '🚨 ',
    }
    
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Store original message
        message = record.getMessage()
        
        # Add prefix for certain levels
        if record.levelname in self.PREFIXES:
            message = self.PREFIXES[record.levelname] + message
        
        # Get color for level
        color = self.COLORS.get(record.levelname, '')
        
        # Format with color
        if color:
            return f"{color}{message}{self.RESET}"
        return message

SENSITIVE_KEYWORDS = [
    "password", "passwd", "pwd", "secret", "token", "api_key", "apikey",
    "auth", "credential", "private_key", "access_token", "refresh_token"
]


def mask_sensitive_info(message: str) -> str:
    """Mask sensitive information in log messages.

    Args:
        message: The log message to process.

    Returns:
        Message with sensitive information masked.
    """
    result = message
    for keyword in SENSITIVE_KEYWORDS:
        import re
        pattern = rf"({keyword}['\"]?\s*[:=]\s*['\"]?)([^'\"\s,}}]+)"
        result = re.sub(pattern, r"\1*****", result, flags=re.IGNORECASE)
    return result


def setup_logging(
    verbose: bool = False,
    log_file: Optional[str] = None,
    log_level_console: Optional[str] = None,
    log_level_file: Optional[str] = None,
    max_bytes: int = 10485760,
    backup_count: int = 5
) -> None:
    """Setup logging configuration with file output and rotation.

    Args:
        verbose: If True, set log level to DEBUG; otherwise INFO.
        log_file: Path to log file. If None, only console logging is used.
        log_level_console: Override console log level (DEBUG, INFO, WARNING, ERROR).
        log_level_file: Override file log level.
        max_bytes: Maximum size of log file before rotation (default: 10MB).
        backup_count: Number of backup files to keep (default: 5).
    """
    console_level = getattr(logging, (log_level_console or ("DEBUG" if verbose else "INFO")))
    file_level = getattr(logging, (log_level_file or ("DEBUG" if verbose else "INFO")))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_formatter = ColoredFormatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(file_level)
        file_formatter = logging.Formatter(LOG_FORMAT_DETAILED, datefmt=LOG_DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    logging.getLogger("clear_win_start").setLevel(logging.DEBUG if verbose else logging.INFO)


def create_log_filter_sensitive() -> logging.Filter:
    """Create a log filter that masks sensitive information.

    Returns:
        A logging.Filter instance.
    """
    class SensitiveInfoFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.msg = mask_sensitive_info(str(record.msg))
            if record.args:
                record.args = tuple(
                    mask_sensitive_info(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )
            return True
    return SensitiveInfoFilter()


def expand_env_vars(path: str) -> str:
    """Expand environment variables in path.

    Args:
        path: Path string with environment variables.

    Returns:
        Expanded path with environment variables replaced.
    """
    if not path:
        return path

    result = os.path.expandvars(path)
    result = result.replace('%APPDATA%', os.environ.get('APPDATA', ''))
    result = result.replace('%USERPROFILE%', os.environ.get('USERPROFILE', ''))
    result = result.replace('%LOCALAPPDATA%', os.environ.get('LOCALAPPDATA', ''))
    result = result.replace('%PROGRAMFILES%', os.environ.get('PROGRAMFILES', ''))
    result = result.replace('%PROGRAMFILES(X86)%', os.environ.get('PROGRAMFILES(X86)', ''))
    return result


class DefaultConfig:
    """Default configuration values loaded from config file."""

    _instance = None
    _config_loaded = False

    NEGLECT_FOLDERS = [
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

    DELETE_KEYWORDS = [
        "卸载", "官网", "更新", "帮助", "意见", "设置", "关于",
        "install", "Website", "Setting", "Documentation", "Help",
        ".url",
    ]

    @classmethod
    def load_from_file(cls, config_path: Optional[str] = None) -> None:
        """Load default configuration from JSON file.

        Args:
            config_path: Path to config file. If None, searches in standard locations.
        """
        if cls._config_loaded:
            return

        if config_path is None:
            config_path = cls._find_config_file()

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if "neglect_folders" in data and data["neglect_folders"]:
                    cls.NEGLECT_FOLDERS = data["neglect_folders"]

                if "delete_keywords" in data:
                    keywords = data["delete_keywords"]
                    if isinstance(keywords, list):
                        cls.DELETE_KEYWORDS = keywords
                    elif isinstance(keywords, dict):
                        all_keywords = []
                        for key in ["chinese", "english", "other"]:
                            if key in keywords:
                                all_keywords.extend(keywords[key])
                        if all_keywords:
                            cls.DELETE_KEYWORDS = all_keywords

                cls._config_loaded = True

            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")

    @classmethod
    def _find_config_file(cls) -> Optional[str]:
        """Find config file in standard locations.

        Returns:
            Path to config file or None if not found.
        """
        search_paths = [
            os.path.join(os.getcwd(), "default-config.json"),
            os.path.join(os.path.dirname(__file__), "..", "default-config.json"),
            os.path.join(os.environ.get('APPDATA', ''), "ClearWinStart", "default-config.json"),
        ]

        for path in search_paths:
            if os.path.exists(path):
                return path

        return None

    @classmethod
    def reset(cls) -> None:
        """Reset loaded configuration to defaults."""
        cls._config_loaded = False
        cls.NEGLECT_FOLDERS = [
            "Accessibility", "Accessories", "Administrative",
            "Administrative Tools", "desktop.ini", "Maintenance",
            "StartUp", "Startup", "System Tools", "Tools",
            "Windows PowerShell",
        ]
        cls.DELETE_KEYWORDS = [
            "卸载", "官网", "更新", "帮助", "意见", "设置", "关于",
            "install", "Website", "Setting", "Documentation", "Help",
            ".url",
        ]


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
        """Initialize default configuration from config file."""
        DefaultConfig.load_from_file()

        if not self.paths:
            self.paths = [
                fr"C:\Users\{self.user_name}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs",
                r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
            ]
        else:
            self.paths = [expand_env_vars(p) for p in self.paths]

        if not self.neglect_folders:
            self.neglect_folders = DefaultConfig.NEGLECT_FOLDERS.copy()

        if not self.delete_keywords:
            self.delete_keywords = DefaultConfig.DELETE_KEYWORDS.copy()

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

        paths = data.get("paths", [])
        if isinstance(paths, dict):
            paths = [expand_env_vars(p) for p in paths.values()]
        elif isinstance(paths, list):
            paths = [expand_env_vars(p) for p in paths]

        delete_keywords = data.get("delete_keywords", [])
        if isinstance(delete_keywords, dict):
            all_keywords = []
            for key in ["chinese", "english", "other"]:
                if key in delete_keywords:
                    all_keywords.extend(delete_keywords[key])
            delete_keywords = all_keywords if all_keywords else []

        return cls(
            user_name=data["user_name"],
            paths=paths,
            neglect_folders=data.get("neglect_folders", []),
            delete_keywords=delete_keywords,
            check_shortcuts=data.get("check_shortcuts", True),
            dry_run=data.get("dry_run", False),
        )

    def to_file(self, config_path: str, include_metadata: bool = True) -> None:
        """Save configuration to a JSON file.

        Args:
            config_path: Path to save the configuration file.
            include_metadata: Whether to include version and description metadata.
        """
        data = {
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


def get_default_log_path() -> str:
    """Get the default log file path.

    Returns:
        Path to the default log file in user's AppData directory.
    """
    log_dir = os.path.join(
        os.environ.get("APPDATA", ""),
        "ClearWinStart",
        "logs"
    )
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    log_filename = f"clear_win_start_{datetime.now().strftime('%Y%m%d')}.log"
    return os.path.join(log_dir, log_filename)


class ConfigurationWizard:
    """Interactive configuration wizard for generating config files."""

    DEFAULT_NEGLECT_FOLDERS = [
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

    DEFAULT_DELETE_KEYWORDS = [
        "卸载", "官网", "更新", "帮助", "意见", "设置", "关于",
        "install", "Website", "Setting", "Documentation", "Help", ".url",
    ]

    @staticmethod
    def print_header(title: str) -> None:
        """Print a formatted header."""
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60)

    @staticmethod
    def print_section(title: str) -> None:
        """Print a formatted section title."""
        print(f"\n--- {title} ---")

    @staticmethod
    def get_input(prompt: str, default: Optional[str] = None, required: bool = False) -> str:
        """Get user input with optional default value.

        Args:
            prompt: The prompt to display.
            default: Default value if user presses Enter.
            required: Whether input is required.

        Returns:
            User input or default value.
        """
        if default:
            response = input(f"{prompt} [{default}]: ").strip()
            return response if response else default
        else:
            response = input(f"{prompt}: ").strip()
            if required and not response:
                print("This field is required. Please try again.")
                return ConfigurationWizard.get_input(prompt, default, required)
            return response

    @staticmethod
    def get_yes_no(prompt: str, default: bool = False) -> bool:
        """Get yes/no input from user.

        Args:
            prompt: The prompt to display.
            default: Default value if user presses Enter.

        Returns:
            True for yes, False for no.
        """
        default_str = "Y/n" if default else "y/N"
        response = input(f"{prompt} ({default_str}): ").strip().lower()
        if not response:
            return default
        return response in ["y", "yes"]

    @staticmethod
    def get_list_input(prompt: str, allow_empty: bool = True) -> List[str]:
        """Get list input from user.

        Args:
            prompt: The prompt to display.
            allow_empty: Whether empty list is allowed.

        Returns:
            List of items entered by user.
        """
        print(f"{prompt} (Enter empty line to finish)")
        items = []
        while True:
            item = input("  - ").strip()
            if not item:
                break
            items.append(item)

        if not items and not allow_empty:
            print("At least one item is required. Please try again.")
            return ConfigurationWizard.get_list_input(prompt, allow_empty)

        return items

    def run(self) -> Configuration:
        """Run the interactive configuration wizard.

        Returns:
            Configuration instance with user-provided settings.
        """
        self.print_header("ClearWinStart Configuration Wizard")

        print("""
This wizard will help you create a configuration file for organizing
your Windows Start Menu. You can always edit the config.json file later.

Press Enter to accept default values shown in brackets.
        """)

        self.print_section("Step 1: Basic Information")
        user_name = self.get_input(
            "Enter your Windows username",
            required=True
        )

        config = Configuration(user_name=user_name)

        self.print_section("Step 2: Paths to Process")
        print("""
The following paths will be processed:
  1. User Start Menu: %APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs
  2. System Start Menu: C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs

You can add additional paths or modify these later.
        """)

        use_default_paths = self.get_yes_no(
            "Use default Start Menu paths",
            default=True
        )

        if not use_default_paths:
            print("\nEnter additional paths to process:")
            config.paths = self.get_list_input(
                "Enter paths (one per line)",
                allow_empty=False
            )

        self.print_section("Step 3: Folders to Preserve")
        print("""
These folders will NOT be processed (they contain important system shortcuts):
  - Accessories, Administrative Tools, Startup, System Tools, etc.

You can customize this list to add or remove folders.
        """)

        show_default = self.get_yes_no(
            "Show default preserved folders",
            default=False
        )

        if show_default:
            print("\nDefault folders:")
            for folder in self.DEFAULT_NEGLECT_FOLDERS:
                print(f"  - {folder}")

        customize_folders = self.get_yes_no(
            "Customize preserved folders",
            default=False
        )

        if customize_folders:
            print("\nEnter folder names to preserve (one per line):")
            config.neglect_folders = self.get_list_input(
                "Enter folder names",
                allow_empty=True
            )
        else:
            config.neglect_folders = self.DEFAULT_NEGLECT_FOLDERS.copy()

        self.print_section("Step 4: Keywords to Delete")
        print("""
Files and folders containing these keywords will be automatically deleted:
  - Chinese: 卸载, 官网, 更新, 帮助, 意见, 设置, 关于
  - English: install, Website, Setting, Documentation, Help
  - Other: .url (URL shortcuts)
        """)

        show_default = self.get_yes_no(
            "Show default delete keywords",
            default=False
        )

        if show_default:
            print("\nDefault keywords:")
            for keyword in self.DEFAULT_DELETE_KEYWORDS:
                print(f"  - {keyword}")

        customize_keywords = self.get_yes_no(
            "Customize delete keywords",
            default=False
        )

        if customize_keywords:
            print("\nEnter keywords to match for deletion (one per line):")
            config.delete_keywords = self.get_list_input(
                "Enter keywords",
                allow_empty=True
            )
        else:
            config.delete_keywords = self.DEFAULT_DELETE_KEYWORDS.copy()

        self.print_section("Step 5: Shortcut Validation")
        print("""
When enabled, the tool will check if shortcuts point to existing files
and remove invalid (broken) shortcuts.
        """)

        config.check_shortcuts = self.get_yes_no(
            "Check and remove invalid shortcuts",
            default=True
        )

        self.print_section("Step 6: Dry Run Mode")
        print("""
Dry Run mode allows you to preview changes without actually making them.
This is recommended for first-time users.
        """)

        config.dry_run = self.get_yes_no(
            "Enable Dry Run mode by default",
            default=True
        )

        self.print_header("Configuration Complete!")
        print(f"""
Summary:
  Username: {config.user_name}
  Paths: {len(config.paths)} path(s)
  Preserved folders: {len(config.neglect_folders)} folder(s)
  Delete keywords: {len(config.delete_keywords)} keyword(s)
  Check shortcuts: {config.check_shortcuts}
  Dry run mode: {config.dry_run}
        """)

        return config

    def save_config(self, config: Configuration, output_path: Optional[str] = None) -> str:
        """Save configuration to file.

        Args:
            config: Configuration instance to save.
            output_path: Optional output path. If None, uses default.

        Returns:
            Path where configuration was saved.
        """
        if output_path is None:
            output_path = self.get_input(
                "Enter output path for config file",
                default="config.json"
            )

        config.to_file(output_path)
        return output_path


def shorten_start_menu_path(full_path: str, user_start_menu: Optional[str] = None, 
                            system_start_menu: Optional[str] = None) -> str:
    """Shorten start menu paths for cleaner display in logs.

    Args:
        full_path: The full path to shorten.
        user_start_menu: User's start menu base path.
        system_start_menu: System start menu base path.

    Returns:
        Shortened path with standard prefix.
    """
    import os as _os
    
    # Default paths
    if user_start_menu is None:
        user_start_menu = _os.path.join(
            _os.environ.get("APPDATA", ""),
            "Microsoft", "Windows", "Start Menu", "Programs"
        )
    
    if system_start_menu is None:
        system_start_menu = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"
    
    # Check if path matches user start menu
    if full_path.startswith(user_start_menu):
        relative = full_path[len(user_start_menu):].lstrip(_os.sep)
        return f"[USER] {relative}"
    
    # Check if path matches system start menu
    if full_path.startswith(system_start_menu):
        relative = full_path[len(system_start_menu):].lstrip(_os.sep)
        return f"[SYS] {relative}"
    
    # For other paths, try to use user profile shorthand
    user_profile = _os.environ.get("USERPROFILE", "")
    if user_profile and full_path.startswith(user_profile):
        relative = full_path[len(user_profile):].lstrip(_os.sep)
        return f"~/{relative}"
    
    return full_path
