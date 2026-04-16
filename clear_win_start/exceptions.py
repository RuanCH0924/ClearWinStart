"""
Custom exceptions for organize_start_menu package.
"""


class StartMenuOrganizerError(Exception):
    """Base exception for Start Menu Organizer."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class PermissionError(StartMenuOrganizerError):
    """Raised when permission is denied to access a file or directory."""

    def __init__(self, path: str) -> None:
        self.path = path
        message = f"Permission denied: Unable to access '{path}'. Please check folder permissions."
        super().__init__(message)


class PathNotFoundError(StartMenuOrganizerError):
    """Raised when a specified path does not exist."""

    def __init__(self, path: str) -> None:
        self.path = path
        message = f"Path not found: '{path}' does not exist."
        super().__init__(message)


class ConfigurationError(StartMenuOrganizerError):
    """Raised when there is an error in the configuration."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Configuration error: {message}")


class ShortcutParseError(StartMenuOrganizerError):
    """Raised when a shortcut file cannot be parsed."""

    def __init__(self, shortcut_path: str, reason: str) -> None:
        self.shortcut_path = shortcut_path
        message = f"Failed to parse shortcut '{shortcut_path}': {reason}"
        super().__init__(message)
