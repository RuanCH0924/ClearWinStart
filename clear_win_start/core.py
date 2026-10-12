"""
Core functionality for organizing Windows Start Menu.
"""

import logging
import os
import re
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import send2trash

from clear_win_start.config import Configuration
from clear_win_start.console import ICONS, Dashboard
from clear_win_start.paths import get_default_backup_dir, shorten_start_menu_path

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

    # 被视为「快捷方式」的文件扩展名
    SHORTCUT_EXTENSIONS: tuple = (".lnk", ".url")

    EMPTY_STATS: dict = {
        "folders_processed": 0,
        "files_moved": 0,
        "files_deleted": 0,
        "shortcuts_cleaned": 0,
        "shortcuts_deduped": 0,
        "shortcuts_backed_up": 0,
    }
    EMPTY_SUMMARY: dict = {
        "total_folders": 0,
        "total_files_to_move": 0,
        "total_files_to_delete": 0,
        "total_shortcuts_to_clean": 0,
        "total_shortcuts_invalid": 0,
        "total_shortcuts_duplicate": 0,
        "total_shortcuts_to_backup": 0,
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
        self._backup_run_dir: Optional[str] = None
        self._processed_paths: List[str] = []
        self._dashboard: Optional[Dashboard] = None
        self._phase_done = 0
        self._phase_total = 0

    def organize(self, auto_confirm: bool = False, preview_only: bool = False,
                 dashboard: Optional[Dashboard] = None) -> dict:
        """Organize all configured Start Menu paths.

        Args:
            auto_confirm: If True, skip confirmation prompts.
            preview_only: If True, only generate preview without executing.
            dashboard: 外部（全流程统一）提供的全屏面板。给定时本方法只向它推送进度，
                不负责其生命周期；未给定且非干跑时，本方法自行创建并在结束时关闭。

        Returns:
            Dictionary containing operation statistics.
        """
        self._reset_stats()

        # 全屏面板优先复用外部传入的（实现启动→执行→结果全程同一块面板）
        own_dashboard = False
        if dashboard is not None:
            self._dashboard = dashboard
        elif not (self.config.dry_run or preview_only):
            self._dashboard = Dashboard("ClearWinStart", context=self._dashboard_context())
            self._dashboard.start()
            own_dashboard = True

        try:
            total_paths = len(self.config.paths)
            for index, path in enumerate(self.config.paths, 1):
                try:
                    self._process_path(path, auto_confirm, preview_only, index, total_paths)
                except PathNotFoundError:
                    logger.warning(f"路径不存在: {path}")
                except PermissionError as e:
                    logger.error(str(e))

            # 重复快捷方式需在所有待处理路径之间比对，故放在路径处理之后
            if self.config.dedupe_shortcuts:
                self._dedupe_across_paths(preview_only)
        finally:
            if own_dashboard and self._dashboard is not None:
                self._dashboard.close()
            self._dashboard = None

        if (self.config.dry_run or preview_only) and self.dry_run_plan:
            self._update_impact_assessment()
            self._print_dry_run_summary()

        return self.stats

    def _reset_stats(self) -> None:
        """重置统计计数器与 dry-run 计划。"""
        self.stats = dict(self.EMPTY_STATS)
        self.dry_run_plan = []
        self.dry_run_summary = dict(self.EMPTY_SUMMARY)
        self._backup_run_dir = None
        self._processed_paths = []
        self._dashboard = None
        self._phase_done = 0
        self._phase_total = 0

    def _dashboard_context(self) -> str:
        """全屏面板顶部「配置」行内容：用户名与待扫描路径数。"""
        user = self.config.user_name or "未指定"
        return f"用户 {user} · {len(self.config.paths)} 个路径"

    def _dashboard_sync(self, phase: Optional[str] = None,
                        current: Optional[int] = None,
                        total: Optional[int] = None) -> None:
        """把当前阶段/进度/计数推送到全屏面板（面板未启用时为空操作）。"""
        if self._dashboard is None:
            return
        self._dashboard.update(
            phase=phase,
            current=current,
            total=total,
            counters={
                "移动": self.stats["files_moved"],
                "删除": self.stats["files_deleted"],
                "去重": self.stats["shortcuts_deduped"],
                "备份": self.stats["shortcuts_backed_up"],
            },
        )

    def _ask_confirm(self) -> str:
        """在面板暂停的状态下询问用户，随后恢复面板。"""
        if self._dashboard is not None:
            self._dashboard.pause()
        try:
            return input("处理此路径？(y/n): ").strip().lower()
        finally:
            if self._dashboard is not None:
                self._dashboard.resume()

    def _process_path(self, path: str, auto_confirm: bool = False,
                      preview_only: bool = False, index: int = 1,
                      total: int = 1) -> None:
        """Process a single Start Menu path.

        Args:
            path: Path to process.
            auto_confirm: If True, skip confirmation prompts.
            preview_only: If True, only generate preview without executing.
            index: 当前路径序号（用于进度显示）。
            total: 路径总数（用于进度显示）。

        Raises:
            PathNotFoundError: If path does not exist.
            PermissionError: If permission is denied.
        """
        if not os.path.exists(path):
            raise PathNotFoundError(path)

        if not os.access(path, os.W_OK):
            raise PermissionError(path)

        label = shorten_start_menu_path(path)
        prefix = f"[{index}/{total}] " if total > 1 else ""
        logger.info(f"{ICONS['path']} {prefix}正在处理: {label}")

        if not auto_confirm and not self.config.dry_run and not preview_only:
            response = self._ask_confirm()
            if response not in ["y", "yes"]:
                logger.info(f"  {ICONS['move']} 已跳过")
                return

        folders = self._get_folders_to_process(path)
        logger.info(f"  发现 {len(folders)} 个待处理文件夹")

        # 记录真正参与处理的路径，供跨路径去重使用
        self._processed_paths.append(path)

        if self.config.dry_run or preview_only:
            self._generate_dry_run_plan(path, folders)

        if preview_only or self.config.dry_run:
            return

        if self.config.backup_shortcuts:
            self._backup_shortcuts(path)

        self._phase_total = sum(
            self._count_folder_files(os.path.join(path, folder)) for folder in folders
        )
        self._phase_done = 0
        self._dashboard_sync(phase=f"整理文件夹 · {label}", current=0, total=self._phase_total)
        for folder in folders:
            self._process_folder(path, folder)

        self._dashboard_sync(phase=f"清理关键词 · {label}")
        self._clean_keyword_files(path)

        if self.config.check_shortcuts:
            self._dashboard_sync(phase=f"校验快捷方式 · {label}")
            self._clean_invalid_shortcuts(path)

        logger.info(f"{ICONS['ok']} 处理完成: {label}")

    def _count_folder_files(self, folder_path: str) -> int:
        """统计文件夹（含子目录）内的文件数量，用于进度总量估算。"""
        total = 0
        for src_root in [folder_path, *self._subdirs(folder_path)]:
            try:
                total += sum(
                    1 for item in os.listdir(src_root)
                    if os.path.isfile(os.path.join(src_root, item))
                )
            except OSError:
                pass
        return total

    def _generate_dry_run_plan(self, path: str, folders: List[str]) -> None:
        """Generate detailed dry run plan for the given path.

        Args:
            path: Base path being processed.
            folders: List of folders to be processed.
        """
        logger.info("")
        logger.info(f"  {ICONS['info']} 执行计划")
        logger.info(f"  {'─' * 40}")

        plan_entry = {
            "path": path,
            "folders_to_process": [],
            "files_to_move": [],
            "files_to_delete": [],
            "shortcuts_to_validate": [],
            "shortcuts_to_dedupe": [],
        }

        def _record_move(src: str, dst: str) -> None:
            plan_entry["files_to_move"].append({"source": src, "destination": dst})
            self.dry_run_summary["total_files_to_move"] += 1
            logger.info(f"    {ICONS['move']} {shorten_start_menu_path(src)}")
            logger.info(f"      → {shorten_start_menu_path(dst)}")

        for folder in folders:
            folder_path = os.path.join(path, folder)
            plan_entry["folders_to_process"].append(folder)
            self.dry_run_summary["total_folders"] += 1
            logger.info(f"  {ICONS['folder']} {folder}")

            try:
                for src_root in [folder_path, *self._subdirs(folder_path)]:
                    for item in os.listdir(src_root):
                        item_path = os.path.join(src_root, item)
                        if os.path.isfile(item_path):
                            _record_move(item_path, os.path.join(path, item))
            except OSError as e:
                logger.error(f"  扫描文件夹出错: {folder} - {e}")

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
                logger.info(f"  {ICONS['delete']} {short_path}")

            elif item.lower().endswith(".lnk") and self.config.check_shortcuts:
                plan_entry["shortcuts_to_validate"].append(item_path)
                self.dry_run_summary["total_shortcuts_to_clean"] += 1
                # 在预览阶段就验证快捷方式有效性
                try:
                    if not self._is_valid_shortcut(item_path):
                        self.dry_run_summary["total_shortcuts_invalid"] += 1
                        logger.info(f"  {ICONS['invalid']} {item}（无效快捷方式）")
                except Exception:
                    pass  # 验证失败时不计数，执行时再处理

        if self.config.backup_shortcuts:
            backup_count = sum(1 for _ in self._iter_shortcut_files(path))
            self.dry_run_summary["total_shortcuts_to_backup"] += backup_count
            if backup_count:
                logger.info(f"  {ICONS['backup']} {backup_count} 个快捷方式将被备份")

        self.dry_run_plan.append(plan_entry)

    def _update_impact_assessment(self) -> None:
        """更新影响评估等级。"""
        total_operations = (
            self.dry_run_summary["total_files_to_move"] +
            self.dry_run_summary["total_files_to_delete"] +
            self.dry_run_summary["total_shortcuts_to_clean"] +
            self.dry_run_summary["total_shortcuts_invalid"] +
            self.dry_run_summary["total_shortcuts_duplicate"]
        )

        if total_operations > 50:
            self.dry_run_summary["estimated_impact"] = "高"
        elif total_operations > 20:
            self.dry_run_summary["estimated_impact"] = "中"
        else:
            self.dry_run_summary["estimated_impact"] = "低"

    def _print_dry_run_summary(self) -> None:
        """打印干跑模式统计摘要。"""
        summary = self.dry_run_summary
        logger.info("")
        logger.info(f"  {'─' * 40}")
        logger.info(f"  {ICONS['stats']} 摘要")
        logger.info(f"  {ICONS['folder']} 待处理文件夹: {summary['total_folders']}")
        logger.info(f"  {ICONS['move']} 待移动文件: {summary['total_files_to_move']}")
        logger.info(f"  {ICONS['delete']} 待删除文件/文件夹: {summary['total_files_to_delete']}")
        invalid = summary['total_shortcuts_invalid']
        found = summary['total_shortcuts_to_clean']
        if invalid > 0:
            logger.info(f"  {ICONS['validate']} 快捷方式: 共 {found} 个, 其中 {invalid} 个无效")
        else:
            logger.info(f"  {ICONS['validate']} 快捷方式: 共 {found} 个（均有效）")
        logger.info(f"  {ICONS['dedupe']} 重复快捷方式: {summary['total_shortcuts_duplicate']}")
        if self.config.backup_shortcuts:
            logger.info(f"  {ICONS['backup']} 待备份快捷方式: {summary['total_shortcuts_to_backup']}")
        logger.info(f"  {ICONS['warn']} 影响评估: {summary['estimated_impact']}")
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
            logger.error(f"  处理文件夹出错: {folder_name} - {e}")
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
        self._phase_done += 1
        self._dashboard_sync(current=self._phase_done, total=self._phase_total)

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
                        logger.info(f"  {ICONS['delete']} {item} → 回收站（关键词匹配）")
                        self.stats["files_deleted"] += 1
                    elif os.path.isdir(item_path):
                        send2trash.send2trash(item_path)
                        logger.info(f"  {ICONS['delete']} {item} → 回收站（关键词文件夹匹配）")
                        self.stats["files_deleted"] += 1
                except OSError as e:
                    logger.error(f"  删除失败: {item} - {e}")

    def _clean_invalid_shortcuts(self, base_path: str) -> None:
        """Remove invalid .lnk shortcuts.

        Args:
            base_path: Path to clean.
        """
        try:
            from win32com.client import Dispatch  # noqa: F401
        except ImportError:
            logger.warning("未安装 pywin32，跳过快捷方式验证")
            return

        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)

            if not item.lower().endswith(".lnk") or not os.path.isfile(item_path):
                continue

            if not self._is_valid_shortcut(item_path):
                try:
                    send2trash.send2trash(item_path)
                    logger.info(f"  {ICONS['invalid']} {item} → 回收站（无效快捷方式）")
                    self.stats["shortcuts_cleaned"] += 1
                except OSError as e:
                    logger.error(f"  移除失败: {item} - {e}")

    @staticmethod
    def _iter_shortcut_files(base_path: str):
        """递归产出 base_path 下所有快捷方式文件路径（.lnk/.url）。"""
        for root, _dirs, files in os.walk(base_path):
            for name in files:
                if name.lower().endswith(StartMenuOrganizer.SHORTCUT_EXTENSIONS):
                    yield os.path.join(root, name)

    def _get_backup_run_dir(self) -> str:
        """获取（并惰性创建）本次运行的时间戳备份目录。"""
        if self._backup_run_dir is None:
            root = self.config.backup_dir or get_default_backup_dir()
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_dir = os.path.join(root, stamp)
            os.makedirs(run_dir, exist_ok=True)
            self._backup_run_dir = run_dir
            logger.info(f"  {ICONS['backup']} 备份目录: {shorten_start_menu_path(run_dir)}")
        return self._backup_run_dir

    @staticmethod
    def _backup_label(path: str) -> str:
        """为待备份路径生成安全的子目录名。"""
        lower = path.replace("/", "\\").lower()
        start_menu_marker = "microsoft\\windows\\start menu"
        if start_menu_marker in lower and "programdata" in lower:
            return "System"
        if start_menu_marker in lower and "appdata" in lower:
            return "User"
        name = os.path.basename(path.rstrip("\\/")) or "Path"
        return re.sub(r'[<>:"/\\|?*]', "_", name)

    def _backup_shortcuts(self, base_path: str) -> int:
        """将 base_path 下所有快捷方式按原目录结构复制到备份目录。

        Args:
            base_path: 待备份路径。

        Returns:
            成功备份的快捷方式数量。
        """
        run_dir = self._get_backup_run_dir()
        dest_root = os.path.join(run_dir, self._backup_label(base_path))
        count = 0

        backup_root = os.path.abspath(self.config.backup_dir or get_default_backup_dir())
        # 先枚举源文件（并排除备份目录自身），避免备份目录位于待备份路径内时被递归复制
        sources = [
            src for src in self._iter_shortcut_files(base_path)
            if not os.path.abspath(src).startswith(backup_root + os.sep)
        ]

        progress_total = len(sources)
        self._dashboard_sync(phase="备份快捷方式", current=0, total=progress_total)
        for position, src in enumerate(sources, 1):
            rel = os.path.relpath(src, base_path)
            dst = os.path.join(dest_root, rel)
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                count += 1
            except OSError as e:
                logger.error(f"  备份失败: {os.path.basename(src)} - {e}")
            self._dashboard_sync(current=position, total=progress_total)

        if count:
            logger.info(
                f"  {ICONS['backup']} 已备份 {count} 个快捷方式 "
                f"→ {shorten_start_menu_path(dest_root)}"
            )
        self.stats["shortcuts_backed_up"] += count
        return count

    def _dedupe_across_paths(self, preview_only: bool = False) -> int:
        """在所有待处理路径之间比对并清理重复快捷方式。

        Args:
            preview_only: 为 True 或干跑模式时只统计不删除。

        Returns:
            实际移除的快捷方式数量。
        """
        try:
            from win32com.client import Dispatch  # noqa: F401
        except ImportError:
            logger.warning("未安装 pywin32，跳过重复快捷方式清理")
            return 0

        valid_paths = [p for p in self._processed_paths if os.path.isdir(p)]
        if not valid_paths:
            return 0

        if self.config.dry_run or preview_only:
            excluded = self._collect_shortcut_exclusions(valid_paths)
            info_map = {
                p: info for p, info in self._collect_shortcut_info(valid_paths).items()
                if p not in excluded
            }
            entry_by_path = {entry["path"]: entry for entry in self.dry_run_plan}
            for duplicate in self._find_duplicate_shortcuts(info_map):
                self.dry_run_summary["total_shortcuts_duplicate"] += 1
                owner = entry_by_path.get(os.path.dirname(duplicate))
                if owner is not None:
                    owner["shortcuts_to_dedupe"].append(duplicate)
                logger.info(f"  {ICONS['dedupe']} {shorten_start_menu_path(duplicate)}（重复快捷方式）")
            return 0

        self._dashboard_sync(phase="清理重复快捷方式")
        return self._dedupe_shortcuts(valid_paths)

    def _collect_shortcut_exclusions(self, base_paths: List[str]) -> Set[str]:
        """收集会被关键词/无效清理提前移除的根目录快捷方式（供 dry-run 去重比对排除）。"""
        excluded: Set[str] = set()
        for base_path in base_paths:
            for item in os.listdir(base_path):
                item_path = os.path.join(base_path, item)
                if any(keyword in item for keyword in self.config.delete_keywords):
                    excluded.add(item_path)
                elif item.lower().endswith(".lnk") and os.path.isfile(item_path):
                    if not self._is_valid_shortcut(item_path):
                        excluded.add(item_path)
        return excluded

    def _dedupe_shortcuts(self, base_paths: List[str]) -> int:
        """移除跨路径目标与启动参数均相同的重复快捷方式（每组保留一个）。

        Args:
            base_paths: 参与比对的路径列表。

        Returns:
            实际移除的快捷方式数量。
        """
        info_map = self._collect_shortcut_info(base_paths)
        removed = 0
        for duplicate in self._find_duplicate_shortcuts(info_map):
            try:
                send2trash.send2trash(duplicate)
                logger.info(
                    f"  {ICONS['dedupe']} {shorten_start_menu_path(duplicate)} → 回收站（重复快捷方式）"
                )
                self.stats["shortcuts_deduped"] += 1
                removed += 1
                self._dashboard_sync()
            except OSError as e:
                logger.error(f"  移除失败: {os.path.basename(duplicate)} - {e}")
        return removed

    @staticmethod
    def _read_shortcut(shortcut_path: str) -> Dict[str, Any]:
        """读取 .lnk 文件，返回目标信息字典。

        Args:
            shortcut_path: 快捷方式文件路径。

        Returns:
            包含 target_path / arguments / working_dir / icon_location 的字典。
            读取失败时返回包含 error 键的字典。
        """
        try:
            from win32com.client import Dispatch
            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            return {
                "target_path": (shortcut.TargetPath or "").strip(),
                "arguments": (shortcut.Arguments or "").strip(),
                "working_dir": (shortcut.WorkingDirectory or "").strip(),
                "icon_location": (shortcut.IconLocation or "").strip(),
            }
        except ImportError:
            return {"error": "pywin32 not installed"}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def _check_shortcut_target(info: Dict[str, Any]) -> bool:
        """验证快捷方式的目标是否有效。纯逻辑，不依赖 COM，可独立测试。

        验证规则（按优先级）：
          1. 读取失败 → 无效
          2. 无 TargetPath 且无 Arguments 和 IconLocation → 无效
          3. 无 TargetPath 但有 Arguments 或 IconLocation → 有效（UWP/协议快捷方式）
          4. TargetPath 是特殊协议路径 → 有效
          5. TargetPath 包含 AppUserModelID → 有效
          6. TargetPath 是普通文件/目录路径 → 检查是否存在
          7. 路径不存在 → 无效
          8. 其余情况 → 有效（保守兜底）

        Args:
            info: _read_shortcut() 返回的字典。

        Returns:
            True 表示快捷方式有效，False 表示无效。
        """
        # 规则 1：读取失败
        if "error" in info:
            logger.debug(f"快捷方式读取失败: {info['error']}")
            return False

        target = info.get("target_path", "")
        arguments = info.get("arguments", "")
        icon = info.get("icon_location", "")

        # 规则 2：完全无目标信息
        if not target and not arguments and not icon:
            logger.debug("快捷方式无任何目标信息")
            return False

        # 规则 3：无 TargetPath 但有其他信息
        if not target:
            return True

        # 规则 4：特殊协议路径
        special_protocols = ("shell:", "app:", "ms:", "ms-resource:", "://")
        if any(target.lower().startswith(p) for p in special_protocols):
            return True

        # 规则 5：AppUserModelID / 通配符
        if "!" in target or "*" in target:
            return True

        # 规则 6+7：普通文件路径检查
        return StartMenuOrganizer._check_file_target(target)

    @staticmethod
    def _check_file_target(target_path: str) -> bool:
        """检查目标文件路径是否存在。处理 Windows 路径特殊问题。

        Args:
            target_path: 目标路径字符串。

        Returns:
            True 如果路径存在，False 如果路径不存在或无效。
        """
        # 清理路径
        path = target_path.strip().strip('"\'')
        if not path:
            return False

        # 尝试直接检查
        try:
            if os.path.exists(path):
                return True
        except Exception:
            pass

        # 展开环境变量后检查
        try:
            expanded = os.path.expandvars(path)
            if expanded and expanded != path and os.path.exists(expanded):
                return True
        except Exception:
            pass

        # 尝试处理长路径（>260 字符）
        if len(path) > 240 and not path.startswith("\\\\?\\"):
            try:
                long_path = "\\\\?\\" + os.path.abspath(path)
                if os.path.exists(long_path):
                    return True
            except Exception:
                pass

        # 尝试规范化路径
        try:
            normalized = os.path.normpath(path)
            if normalized != path and os.path.exists(normalized):
                return True
        except Exception:
            pass

        # 路径格式检查 — 看起来像有效路径吗？
        # 展开环境变量后再检查格式
        try:
            expanded_for_check = os.path.expandvars(path)
            if expanded_for_check != path:
                # 环境变量展开后是标准磁盘路径 → 路径不存在
                if re.match(r'^[a-zA-Z]:\\', expanded_for_check):
                    return False
                # 展开后是 UNC 路径且不存在
                if expanded_for_check.startswith('\\\\'):
                    return False
                # 展开后仍是未知格式，保守处理
                return True
        except Exception:
            pass

        if not re.match(r'^[a-zA-Z]:\\', path) and not path.startswith('\\'):
            # 不是磁盘路径也不是 UNC 路径，保守处理视为有效
            return True

        # 路径不存在
        return False

    def _is_valid_shortcut(self, shortcut_path: str) -> bool:
        """检查快捷方式是否有效。整合 COM 读取与目标验证。

        Args:
            shortcut_path: 快捷方式文件路径。

        Returns:
            True 表示有效，False 表示无效。
        """
        info = self._read_shortcut(shortcut_path)
        return self._check_shortcut_target(info)

    def _collect_shortcut_info(self, base_paths: List[str]) -> Dict[str, Dict[str, str]]:
        """收集给定路径（根目录）下所有 .lnk 的 {快捷方式路径: 读取信息} 映射。

        读取失败的快捷方式信息记为空字典（后续去重时会被忽略）。

        Args:
            base_paths: 待扫描的路径列表（每个路径只扫描根目录）。

        Returns:
            快捷方式路径到目标信息的字典（含 target_path / arguments）。
        """
        info_map: Dict[str, Dict[str, str]] = {}
        for base_path in base_paths:
            if not os.path.isdir(base_path):
                continue
            for item in os.listdir(base_path):
                item_path = os.path.join(base_path, item)
                if not item.lower().endswith(".lnk") or not os.path.isfile(item_path):
                    continue
                info = self._read_shortcut(item_path)
                info_map[item_path] = {} if "error" in info else {
                    "target_path": info.get("target_path", ""),
                    "arguments": info.get("arguments", ""),
                }
        return info_map

    @staticmethod
    def _normalize_target(target_path: str) -> str:
        """规范化目标路径用于去重比较：去引号/空格、展开环境变量、规范化并小写。

        Args:
            target_path: 原始目标路径字符串。

        Returns:
            用于比较的规范化键；无有效目标时返回空字符串。
        """
        path = (target_path or "").strip().strip('"\'')
        if not path:
            return ""
        expanded = os.path.expandvars(path)
        return os.path.normpath(expanded).lower()

    @staticmethod
    def _shortcut_key(info: Dict[str, str]) -> str:
        """由 TargetPath + Arguments 生成去重比较键。

        仅当 TargetPath 有效时才生成键（空目标不参与去重）；Arguments 保留大小写
        并仅去除首尾空白，因为命令行参数可能是大小写敏感的。

        Args:
            info: 包含 target_path / arguments 的字典。

        Returns:
            比较键；无有效目标时返回空字符串。
        """
        target = StartMenuOrganizer._normalize_target(info.get("target_path", ""))
        if not target:
            return ""
        arguments = (info.get("arguments") or "").strip()
        return f"{target}\x00{arguments}"

    @staticmethod
    def _find_duplicate_shortcuts(shortcut_info: Dict[str, Dict[str, str]]) -> List[str]:
        """按 TargetPath + Arguments 分组，返回每组中除保留项外的重复快捷方式。

        可传入跨多个路径收集的信息，实现跨目录去重。同组内按文件名长度（短者优先）、
        长度相同时按名称、再按完整路径排序，保留第一个，其余视为重复。
        目标路径为空（读取失败 / UWP 等无目标）的快捷方式不参与去重。

        Args:
            shortcut_info: {快捷方式路径: 读取信息} 映射。

        Returns:
            需要移除的重复快捷方式路径列表。
        """
        seen: Dict[str, str] = {}
        duplicates: List[str] = []
        for path in sorted(
            shortcut_info,
            key=lambda p: (len(os.path.basename(p)), os.path.basename(p).lower(), p.lower()),
        ):
            key = StartMenuOrganizer._shortcut_key(shortcut_info[path])
            if not key:
                continue
            if key in seen:
                duplicates.append(path)
            else:
                seen[key] = path
        return duplicates

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
