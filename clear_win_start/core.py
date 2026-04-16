"""
Core functionality for organizing Windows Start Menu.
"""

import logging
import os
import shutil
from typing import List, Optional

from clear_win_start.exceptions import (
    PermissionError,
    PathNotFoundError,
    ShortcutParseError,
)
from clear_win_start.utils import Configuration

logger = logging.getLogger(__name__)


class StartMenuOrganizer:
    """Main class for organizing Windows Start Menu."""

    def __init__(self, config: Optional[Configuration] = None) -> None:
        """Initialize the organizer.

        Args:
            config: Configuration instance. If None, uses default settings.
        """
        self.config = config or Configuration(user_name="")
        self.stats = {
            "folders_processed": 0,
            "files_moved": 0,
            "files_deleted": 0,
            "shortcuts_cleaned": 0,
        }

    def organize(self, auto_confirm: bool = False) -> dict:
        """Organize all configured Start Menu paths.

        Args:
            auto_confirm: If True, skip confirmation prompts.

        Returns:
            Dictionary containing operation statistics.
        """
        self._reset_stats()

        for path in self.config.paths:
            try:
                self._process_path(path, auto_confirm)
            except PathNotFoundError:
                logger.warning(f"Path does not exist: {path}")
            except PermissionError as e:
                logger.error(str(e))

        return self.stats

    def _reset_stats(self) -> None:
        """Reset statistics counters."""
        self.stats = {
            "folders_processed": 0,
            "files_moved": 0,
            "files_deleted": 0,
            "shortcuts_cleaned": 0,
        }

    def _process_path(self, path: str, auto_confirm: bool = False) -> None:
        """Process a single Start Menu path.

        Args:
            path: Path to process.
            auto_confirm: If True, skip confirmation prompts.

        Raises:
            PathNotFoundError: If path does not exist.
            PermissionError: If permission is denied.
        """
        if not os.path.exists(path):
            raise PathNotFoundError(path)

        if not os.access(path, os.W_OK):
            raise PermissionError(path)

        logger.info(f"Processing: {path}")

        if not auto_confirm:
            response = input(f"Process this path? (y/n): ").strip().lower()
            if response not in ["y", "yes"]:
                logger.info("Skipped by user")
                return

        folders = self._get_folders_to_process(path)
        logger.info(f"Found {len(folders)} folders to process")

        for folder in folders:
            self._process_folder(path, folder)

        self._clean_keyword_files(path)

        if self.config.check_shortcuts:
            self._clean_invalid_shortcuts(path)

        logger.info(f"Completed: {path}")

    def _get_folders_to_process(self, path: str) -> List[str]:
        """Get list of folders to process.

        Args:
            path: Base path to search.

        Returns:
            List of folder names to process.
        """
        folders = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path) and item not in self.config.neglect_folders:
                folders.append(item)
        return folders

    def _process_folder(self, base_path: str, folder_name: str) -> bool:
        """Process a single folder.

        Args:
            base_path: Base path containing the folder.
            folder_name: Name of the folder to process.

        Returns:
            True if successful, False otherwise.
        """
        folder_path = os.path.join(base_path, folder_name)
        logger.debug(f"Processing folder: {folder_name}")

        try:
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                dest_path = os.path.join(base_path, item)

                if os.path.isfile(item_path):
                    self._move_file(item_path, dest_path)
                elif os.path.isdir(item_path):
                    self._process_nested_folder(item_path, base_path)

            os.rmdir(folder_path)
            logger.debug(f"Removed empty folder: {folder_name}")
            self.stats["folders_processed"] += 1
            return True

        except OSError as e:
            logger.error(f"Error processing folder {folder_name}: {e}")
            return False

    def _process_nested_folder(self, source_path: str, base_path: str) -> None:
        """Process a nested folder and move its contents.

        Args:
            source_path: Path to the nested folder.
            base_path: Destination base path.
        """
        for item in os.listdir(source_path):
            item_path = os.path.join(source_path, item)
            dest_path = os.path.join(base_path, item)

            if os.path.isfile(item_path):
                self._move_file(item_path, dest_path)
            elif os.path.isdir(item_path):
                self._process_nested_folder(item_path, base_path)

        shutil.rmtree(source_path, ignore_errors=True)
        logger.debug(f"Removed nested folder: {source_path}")

    def _move_file(self, source: str, dest: str) -> None:
        """Move a file to destination.

        Args:
            source: Source file path.
            dest: Destination file path.
        """
        if self.config.dry_run:
            logger.info(f"[DRY RUN] Would move: {source} -> {dest}")
            return

        if os.path.exists(dest):
            if os.path.isfile(dest):
                os.remove(dest)
                logger.debug(f"Removed existing file: {dest}")
            else:
                shutil.rmtree(dest, ignore_errors=True)
                logger.debug(f"Removed existing folder: {dest}")

        shutil.move(source, dest)
        logger.debug(f"Moved file: {os.path.basename(source)}")
        self.stats["files_moved"] += 1

    def _clean_keyword_files(self, base_path: str) -> None:
        """Delete files and folders containing specified keywords.

        Args:
            base_path: Path to clean.
        """
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)

            if any(keyword in item for keyword in self.config.delete_keywords):
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                        logger.info(f"Deleted keyword file: {item}")
                        self.stats["files_deleted"] += 1
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        logger.info(f"Deleted keyword folder: {item}")
                        self.stats["files_deleted"] += 1
                except OSError as e:
                    logger.error(f"Error deleting {item}: {e}")

    def _clean_invalid_shortcuts(self, base_path: str) -> None:
        """Remove invalid .lnk shortcuts.

        Args:
            base_path: Path to clean.
        """
        try:
            from win32com.client import Dispatch
        except ImportError:
            logger.warning("pywin32 not installed, skipping shortcut validation")
            return

        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)

            if not item.lower().endswith(".lnk") or not os.path.isfile(item_path):
                continue

            if not self._is_valid_shortcut(item_path):
                try:
                    os.remove(item_path)
                    logger.info(f"Removed invalid shortcut: {item}")
                    self.stats["shortcuts_cleaned"] += 1
                except OSError as e:
                    logger.error(f"Error removing shortcut {item}: {e}")

    def _is_valid_shortcut(self, shortcut_path: str) -> bool:
        """Check if a shortcut points to an existing target.

        Args:
            shortcut_path: Path to the shortcut file.

        Returns:
            True if shortcut is valid, False otherwise.
        """
        try:
            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            target_path = shortcut.Targetpath

            if not target_path:
                return False

            return os.path.exists(target_path)

        except Exception as e:
            logger.debug(f"Shortcut validation failed for {shortcut_path}: {e}")
            return False

    def validate_paths(self) -> List[str]:
        """Validate configured paths.

        Returns:
            List of invalid path errors.
        """
        errors = []
        for path in self.config.paths:
            if not os.path.exists(path):
                errors.append(f"Path does not exist: {path}")
            elif not os.access(path, os.R_OK):
                errors.append(f"Path not readable: {path}")
        return errors

    def get_stats(self) -> dict:
        """Get operation statistics.

        Returns:
            Dictionary containing statistics.
        """
        return self.stats.copy()
