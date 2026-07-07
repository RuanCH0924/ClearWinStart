"""
ClearWinStart - Windows Start Menu Organization Tool.

A tool to organize Windows Start Menu by flattening nested folders
and cleaning up invalid shortcuts.
"""

__version__ = "1.0.0"

# 公共 API（用户面向）
from clear_win_start.config import Configuration, ConfigurationWizard
from clear_win_start.core import StartMenuOrganizer
from clear_win_start.paths import expand_env_vars
from clear_win_start.cli import (
    PreviewWindow,
    create_preview_from_stats,
)

__all__ = [
    "Configuration",
    "ConfigurationWizard",
    "PreviewWindow",
    "StartMenuOrganizer",
    "create_preview_from_stats",
    "expand_env_vars",
    "__version__",
]
