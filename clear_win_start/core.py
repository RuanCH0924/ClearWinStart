"""
Core functionality for organizing Windows Start Menu.
"""

import logging
import os
import shutil
from datetime import datetime
from typing import List, Optional

from clear_win_start.exceptions import (
    PermissionError,
    PathNotFoundError,
    ShortcutParseError,
)
from clear_win_start.utils import Configuration
from clear_win_start.preview import (
    PreviewItem,
    ActionType,
    create_preview_from_stats
)

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
        self.dry_run_plan: List[dict] = []
        self.dry_run_summary: dict = {
            "total_folders": 0,
            "total_files_to_move": 0,
            "total_files_to_delete": 0,
            "total_shortcuts_to_clean": 0,
            "estimated_impact": "Low",
        }

    def organize(self, auto_confirm: bool = False, preview_only: bool = False) -> dict:
        """Organize all configured Start Menu paths.

        Args:
            auto_confirm: If True, skip confirmation prompts.
            preview_only: If True, only generate preview without executing.

        Returns:
            Dictionary containing operation statistics.
        """
        self._reset_stats()

        for path in self.config.paths:
            try:
                self._process_path(path, auto_confirm, preview_only)
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
        self.dry_run_plan = []
        self.dry_run_summary = {
            "total_folders": 0,
            "total_files_to_move": 0,
            "total_files_to_delete": 0,
            "total_shortcuts_to_clean": 0,
            "estimated_impact": "Low",
        }

    def _process_path(self, path: str, auto_confirm: bool = False,
                      preview_only: bool = False) -> None:
        """Process a single Start Menu path.

        Args:
            path: Path to process.
            auto_confirm: If True, skip confirmation prompts.
            preview_only: If True, only generate preview without executing.

        Raises:
            PathNotFoundError: If path does not exist.
            PermissionError: If permission is denied.
        """
        if not os.path.exists(path):
            raise PathNotFoundError(path)

        if not os.access(path, os.W_OK):
            raise PermissionError(path)

        logger.info(f"Processing: {path}")

        if not auto_confirm and not self.config.dry_run and not preview_only:
            response = input(f"Process this path? (y/n): ").strip().lower()
            if response not in ["y", "yes"]:
                logger.info("Skipped by user")
                return

        folders = self._get_folders_to_process(path)
        logger.info(f"Found {len(folders)} folders to process")

        if self.config.dry_run or preview_only:
            self._generate_dry_run_plan(path, folders)

        if preview_only:
            return

        for folder in folders:
            self._process_folder(path, folder)

        self._clean_keyword_files(path)

        if self.config.check_shortcuts:
            self._clean_invalid_shortcuts(path)

        logger.info(f"Completed: {path}")

    def _generate_dry_run_plan(self, path: str, folders: List[str]) -> None:
        """Generate detailed dry run plan for the given path.

        Args:
            path: Base path being processed.
            folders: List of folders to be processed.
        """
        logger.info("=" * 60)
        logger.info("DRY RUN - Execution Plan Report")
        logger.info("=" * 60)
        logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Base Path: {path}")
        logger.info("")

        plan_entry = {
            "path": path,
            "folders_to_process": [],
            "files_to_move": [],
            "files_to_delete": [],
            "shortcuts_to_validate": [],
        }

        for folder in folders:
            folder_path = os.path.join(path, folder)
            plan_entry["folders_to_process"].append(folder)
            self.dry_run_summary["total_folders"] += 1

            logger.info(f"[FOLDER] Will process: {folder}")

            try:
                for item in os.listdir(folder_path):
                    item_path = os.path.join(folder_path, item)
                    dest_path = os.path.join(path, item)

                    if os.path.isfile(item_path):
                        plan_entry["files_to_move"].append({
                            "source": item_path,
                            "destination": dest_path
                        })
                        self.dry_run_summary["total_files_to_move"] += 1
                        logger.info(f"  [MOVE] {item_path} -> {dest_path}")

                    elif os.path.isdir(item_path):
                        for nested_item in os.listdir(item_path):
                            nested_path = os.path.join(item_path, nested_item)
                            nested_dest = os.path.join(path, nested_item)

                            if os.path.isfile(nested_path):
                                plan_entry["files_to_move"].append({
                                    "source": nested_path,
                                    "destination": nested_dest
                                })
                                self.dry_run_summary["total_files_to_move"] += 1
                                logger.info(f"  [MOVE] {nested_path} -> {nested_dest}")

            except OSError as e:
                logger.error(f"Error scanning folder {folder}: {e}")

        for item in os.listdir(path):
            item_path = os.path.join(path, item)

            if any(keyword in item for keyword in self.config.delete_keywords):
                matched_keywords = [k for k in self.config.delete_keywords if k in item]
                plan_entry["files_to_delete"].append({
                    "path": item_path,
                    "type": "file" if os.path.isfile(item_path) else "folder",
                    "reason": f"Contains keyword: {matched_keywords}"
                })
                self.dry_run_summary["total_files_to_delete"] += 1
                logger.info(f"[DELETE] {item_path} (keyword match)")

            elif item.lower().endswith(".lnk") and self.config.check_shortcuts:
                plan_entry["shortcuts_to_validate"].append(item_path)
                self.dry_run_summary["total_shortcuts_to_clean"] += 1

        self.dry_run_plan.append(plan_entry)
        self._update_impact_assessment()
        self._print_dry_run_summary()

        logger.info("=" * 60)
        logger.info("End of Dry Run Report")
        logger.info("=" * 60)

    def _update_impact_assessment(self) -> None:
        """Update the estimated impact level based on operations."""
        total_operations = (
            self.dry_run_summary["total_files_to_move"] +
            self.dry_run_summary["total_files_to_delete"] +
            self.dry_run_summary["total_shortcuts_to_clean"]
        )

        if total_operations > 50:
            self.dry_run_summary["estimated_impact"] = "High"
        elif total_operations > 20:
            self.dry_run_summary["estimated_impact"] = "Medium"
        else:
            self.dry_run_summary["estimated_impact"] = "Low"

    def _print_dry_run_summary(self) -> None:
        """Print dry run summary statistics."""
        logger.info("")
        logger.info("Summary:")
        logger.info(f"  - Folders to process: {self.dry_run_summary['total_folders']}")
        logger.info(f"  - Files to move: {self.dry_run_summary['total_files_to_move']}")
        logger.info(f"  - Files/folders to delete: {self.dry_run_summary['total_files_to_delete']}")
        logger.info(f"  - Shortcuts to validate: {self.dry_run_summary['total_shortcuts_to_clean']}")
        logger.info(f"  - Estimated Impact: {self.dry_run_summary['estimated_impact']}")
        logger.info("")

    def get_dry_run_report(self) -> dict:
        """Get the complete dry run report.

        Returns:
            Dictionary containing the full dry run plan and summary.
        """
        return {
            "plan": self.dry_run_plan,
            "summary": self.dry_run_summary.copy()
        }

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
