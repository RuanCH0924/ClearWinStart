"""
Core functionality for organizing Windows Start Menu.
"""

import logging
import os
import shutil
from typing import List, Optional

import send2trash

from clear_win_start.config import Configuration
from clear_win_start.paths import shorten_start_menu_path

logger = logging.getLogger(__name__)


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


class ShortcutParseError(StartMenuOrganizerError):
    """Raised when a shortcut file cannot be parsed."""
    def __init__(self, shortcut_path: str, reason: str) -> None:
        self.shortcut_path = shortcut_path
        message = f"Failed to parse shortcut '{shortcut_path}': {reason}"
        super().__init__(message)


class StartMenuOrganizer:
    """Main class for organizing Windows Start Menu."""

    EMPTY_STATS: dict = {
        "folders_processed": 0,
        "files_moved": 0,
        "files_deleted": 0,
        "shortcuts_cleaned": 0,
    }
    EMPTY_SUMMARY: dict = {
        "total_folders": 0,
        "total_files_to_move": 0,
        "total_files_to_delete": 0,
        "total_shortcuts_to_clean": 0,
        "total_shortcuts_invalid": 0,
        "estimated_impact": "Low",
    }

    def __init__(self, config: Optional[Configuration] = None) -> None:
        """Initialize the organizer.

        Args:
            config: Configuration instance. If None, uses default settings.
        """
        self.config = config or Configuration(user_name="")
        self.stats: dict = dict(self.EMPTY_STATS)
        self.dry_run_plan: List[dict] = []
        self.dry_run_summary: dict = dict(self.EMPTY_SUMMARY)

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
                logger.warning(f"⚠ 路径不存在: {path}")
            except PermissionError as e:
                logger.error(str(e))

        return self.stats

    def _reset_stats(self) -> None:
        """重置统计计数器与 dry-run 计划。"""
        self.stats = dict(self.EMPTY_STATS)
        self.dry_run_plan = []
        self.dry_run_summary = dict(self.EMPTY_SUMMARY)

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

        logger.info(f"▶ 正在处理: {shorten_start_menu_path(path)}")

        if not auto_confirm and not self.config.dry_run and not preview_only:
            response = input(f"处理此路径？(y/n): ").strip().lower()
            if response not in ["y", "yes"]:
                logger.info(f"  → 已跳过")
                return

        folders = self._get_folders_to_process(path)
        logger.info(f"  发现 {len(folders)} 个待处理文件夹")

        if self.config.dry_run or preview_only:
            self._generate_dry_run_plan(path, folders)

        if preview_only or self.config.dry_run:
            return

        for folder in folders:
            self._process_folder(path, folder)

        self._clean_keyword_files(path)

        if self.config.check_shortcuts:
            self._clean_invalid_shortcuts(path)

        logger.info(f"✔ 处理完成: {shorten_start_menu_path(path)}")

    def _generate_dry_run_plan(self, path: str, folders: List[str]) -> None:
        """Generate detailed dry run plan for the given path.

        Args:
            path: Base path being processed.
            folders: List of folders to be processed.
        """
        logger.info("")
        logger.info(f"  执行计划")
        logger.info(f"  {'─' * 40}")

        plan_entry = {
            "path": path,
            "folders_to_process": [],
            "files_to_move": [],
            "files_to_delete": [],
            "shortcuts_to_validate": [],
        }

        def _record_move(src: str, dst: str) -> None:
            plan_entry["files_to_move"].append({"source": src, "destination": dst})
            self.dry_run_summary["total_files_to_move"] += 1
            logger.info(f"    ▸ {shorten_start_menu_path(src)}")
            logger.info(f"      → {shorten_start_menu_path(dst)}")

        for folder in folders:
            folder_path = os.path.join(path, folder)
            plan_entry["folders_to_process"].append(folder)
            self.dry_run_summary["total_folders"] += 1
            logger.info(f"  ▾ {folder}")

            try:
                for src_root in [folder_path, *self._subdirs(folder_path)]:
                    for item in os.listdir(src_root):
                        item_path = os.path.join(src_root, item)
                        if os.path.isfile(item_path):
                            _record_move(item_path, os.path.join(path, item))
            except OSError as e:
                logger.error(f"  ✘ 扫描文件夹出错: {folder} - {e}")

        for item in os.listdir(path):
            item_path = os.path.join(path, item)

            if any(keyword in item for keyword in self.config.delete_keywords):
                matched_keywords = [k for k in self.config.delete_keywords if k in item]
                plan_entry["files_to_delete"].append({
                    "path": item_path,
                    "type": "file" if os.path.isfile(item_path) else "folder",
                    "reason": f"包含关键词: {matched_keywords}"
                })
                self.dry_run_summary["total_files_to_delete"] += 1
                short_path = shorten_start_menu_path(item_path)
                logger.info(f"  ✗ {short_path}")

            elif item.lower().endswith(".lnk") and self.config.check_shortcuts:
                plan_entry["shortcuts_to_validate"].append(item_path)
                self.dry_run_summary["total_shortcuts_to_clean"] += 1
                # 在预览阶段就验证快捷方式有效性
                try:
                    if not self._is_valid_shortcut(item_path):
                        self.dry_run_summary["total_shortcuts_invalid"] += 1
                        logger.info(f"  ! {item}（无效快捷方式）")
                except Exception:
                    pass  # 验证失败时不计数，执行时再处理

        self.dry_run_plan.append(plan_entry)
        self._update_impact_assessment()
        self._print_dry_run_summary()

    def _update_impact_assessment(self) -> None:
        """更新影响评估等级。"""
        total_operations = (
            self.dry_run_summary["total_files_to_move"] +
            self.dry_run_summary["total_files_to_delete"] +
            self.dry_run_summary["total_shortcuts_to_clean"] +
            self.dry_run_summary["total_shortcuts_invalid"]
        )

        if total_operations > 50:
            self.dry_run_summary["estimated_impact"] = "高"
        elif total_operations > 20:
            self.dry_run_summary["estimated_impact"] = "中"
        else:
            self.dry_run_summary["estimated_impact"] = "低"

    def _print_dry_run_summary(self) -> None:
        """打印干跑模式统计摘要。"""
        logger.info("")
        logger.info(f"  {'─' * 40}")
        logger.info(f"  摘要")
        logger.info(f"  - 待处理文件夹: {self.dry_run_summary['total_folders']}")
        logger.info(f"  - 待移动文件: {self.dry_run_summary['total_files_to_move']}")
        logger.info(f"  - 待删除文件/文件夹: {self.dry_run_summary['total_files_to_delete']}")
        invalid = self.dry_run_summary['total_shortcuts_invalid']
        found = self.dry_run_summary['total_shortcuts_to_clean']
        if invalid > 0:
            logger.info(f"  - 快捷方式: 共 {found} 个, 其中 {invalid} 个无效")
        else:
            logger.info(f"  - 快捷方式: 共 {found} 个（均有效）")
        logger.info(f"  - 影响评估: {self.dry_run_summary['estimated_impact']}")
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

    @staticmethod
    def _subdirs(root: str) -> List[str]:
        """递归返回 root 下所有子目录的扁平列表（不包含 root 自身）。"""
        result: List[str] = []
        try:
            for entry in os.listdir(root):
                full = os.path.join(root, entry)
                if os.path.isdir(full):
                    result.append(full)
                    result.extend(StartMenuOrganizer._subdirs(full))
        except OSError:
            pass
        return result

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

            send2trash.send2trash(folder_path)
            logger.debug(f"Removed empty folder: {folder_name}")
            self.stats["folders_processed"] += 1
            return True

        except OSError as e:
            logger.error(f"  ✘ 处理文件夹出错: {folder_name} - {e}")
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

        try:
            send2trash.send2trash(source_path)
        except Exception:
            pass
        logger.debug(f"移除嵌套文件夹: {shorten_start_menu_path(source_path)}")

    def _move_file(self, source: str, dest: str) -> None:
        """Move a file to destination.

        Args:
            source: Source file path.
            dest: Destination file path.
        """
        if self.config.dry_run:
            short_src = shorten_start_menu_path(source)
            short_dst = shorten_start_menu_path(dest)
            logger.info(f"  ~ {short_src}")
            logger.info(f"    → {short_dst}")
            return

        if os.path.exists(dest):
            if os.path.isfile(dest):
                send2trash.send2trash(dest)
                logger.debug(f"已覆盖同名文件: {shorten_start_menu_path(dest)}")
            else:
                try:
                    send2trash.send2trash(dest)
                except Exception:
                    pass
                logger.debug(f"已覆盖同名文件夹: {shorten_start_menu_path(dest)}")

        shutil.move(source, dest)
        logger.debug(f"已移动文件: {os.path.basename(source)}")
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
                        send2trash.send2trash(item_path)
                        logger.info(f"  ✗ {item} → 回收站（关键词匹配）")
                        self.stats["files_deleted"] += 1
                    elif os.path.isdir(item_path):
                        send2trash.send2trash(item_path)
                        logger.info(f"  ✗ {item} → 回收站（关键词文件夹匹配）")
                        self.stats["files_deleted"] += 1
                except OSError as e:
                    logger.error(f"  ✘ 删除失败: {item} - {e}")

    def _clean_invalid_shortcuts(self, base_path: str) -> None:
        """Remove invalid .lnk shortcuts.

        Args:
            base_path: Path to clean.
        """
        try:
            from win32com.client import Dispatch
        except ImportError:
            logger.warning("⚠ 未安装 pywin32，跳过快捷方式验证")
            return

        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)

            if not item.lower().endswith(".lnk") or not os.path.isfile(item_path):
                continue

            if not self._is_valid_shortcut(item_path):
                try:
                    send2trash.send2trash(item_path)
                    logger.info(f"  ! {item} → 回收站（无效快捷方式）")
                    self.stats["shortcuts_cleaned"] += 1
                except OSError as e:
                    logger.error(f"  ✘ 移除失败: {item} - {e}")

    def _is_valid_shortcut(self, shortcut_path: str) -> bool:
        """检查快捷方式是否有效。

        保守策略：只有明确判定目标路径是普通文件且不存在时才视为无效。
        读取异常、路径含引号、环境变量、特殊协议等情况均视为有效，避免误删。

        Args:
            shortcut_path: Path to the shortcut file.

        Returns:
            True if shortcut is valid, False otherwise.
        """
        try:
            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            target_path = shortcut.TargetPath
            arguments = shortcut.Arguments or ""

            # 没有 TargetPath — 检查是否有其他属性表明是有效的快捷方式
            if not target_path:
                # UWP/Store 应用也可能通过 Arguments 或 AppUserModelID 工作
                # 但如果所有属性都为空，说明快捷方式已损坏
                if arguments.strip():
                    return True
                # 也检查 IconLocation 是否指向有效路径
                icon = shortcut.IconLocation or ""
                if icon.strip() and not icon.startswith(","):
                    return True
                # 没有任何目标信息 — 无效
                logger.debug(f"快捷方式无任何目标信息: {shortcut_path}")
                return False

            # 清理路径中的引号
            clean_path = target_path.strip().strip('"\'')

            # 尝试多种路径变体检查目标是否存在
            candidates = [
                clean_path,
                os.path.expandvars(clean_path),
                target_path.strip(),
                os.path.expandvars(target_path.strip()),
            ]
            for candidate in candidates:
                try:
                    if os.path.exists(candidate):
                        return True
                except Exception:
                    continue

            # 特殊协议路径（shell: / app: / ms: 等），视为有效
            special_protocols = ("shell:", "app:", "ms:", "ms-resource:", "://")
            if any(clean_path.lower().startswith(p) for p in special_protocols):
                return True

            # 包含通配符或 AppUserModelID（常见于 UWP 应用引用）
            if "!" in clean_path or "*" in clean_path:
                return True

            # 目标路径明确不存在 — 无效
            logger.debug(f"无效快捷方式: {shortcut_path} -> {clean_path} 不存在")
            return False

        except Exception as e:
            logger.debug(f"读取快捷方式失败: {shortcut_path}: {e}")
            # 读取失败时保守处理 — 视为有效，避免误删
            return True

    def validate_paths(self) -> List[str]:
        """Validate configured paths.

        Returns:
            List of invalid path errors.
        """
        errors = []
        for path in self.config.paths:
            if not os.path.exists(path):
                errors.append(f"路径不存在: {path}")
            elif not os.access(path, os.R_OK):
                errors.append(f"路径不可读: {path}")
        return errors

    def get_stats(self) -> dict:
        """Get operation statistics.

        Returns:
            Dictionary containing statistics.
        """
        return self.stats.copy()
