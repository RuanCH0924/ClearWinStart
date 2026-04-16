"""
ClearWinStart - Windows Start Menu Organization Tool

A tool to organize Windows Start Menu by flattening nested folders
and cleaning up invalid shortcuts.
"""

__version__ = "1.0.0"
__author__ = "Ruan CH"

from clear_win_start.core import StartMenuOrganizer
from clear_win_start.utils import Configuration

__all__ = ["StartMenuOrganizer", "Configuration", "__version__"]
