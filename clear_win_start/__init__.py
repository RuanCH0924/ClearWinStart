"""
ClearWinStart - Windows Start Menu Organization Tool

A tool to organize Windows Start Menu by flattening nested folders
and cleaning up invalid shortcuts.
"""

__version__ = "1.0.0"
__author__ = "Ruan CH"

from clear_win_start.core import StartMenuOrganizer
from clear_win_start.utils import (
    Configuration,
    ConfigurationWizard,
    setup_logging,
    DefaultConfig,
    expand_env_vars,
)
from clear_win_start.preview import PreviewWindow, InteractiveConfirm, create_preview_from_stats

__all__ = [
    "StartMenuOrganizer",
    "Configuration",
    "ConfigurationWizard",
    "setup_logging",
    "DefaultConfig",
    "expand_env_vars",
    "PreviewWindow",
    "InteractiveConfirm",
    "create_preview_from_stats",
    "__version__"
]
