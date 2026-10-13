"""
Command-line interface for ClearWinStart.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from clear_win_start import __version__, console
from clear_win_start.console import ICONS
from clear_win_start.core import StartMenuOrganizer, StartMenuOrganizerError
from clear_win_start.config import Configuration, ConfigurationError, ConfigurationWizard
from clear_win_start.logging_setup import setup_logging
from clear_win_start.paths import get_default_backup_dir, get_default_log_path, get_windows_username
from clear_win_start.ui import Screen, ScreenPrompter

logger = logging.getLogger(__name__)


def _path_label(path: str) -> str:
    """为开始菜单路径加上 [USER] / [SYS] / [PATH] 标签（纯文本，颜色交给 Screen）。"""
    user_profile = os.environ.get("USERPROFILE", "").lower()
    system_marker = os.path.join("programdata", "microsoft").lower()
    lower = path.lower()
    if system_marker in lower:
        tag = "[SYS] "
    elif user_profile and user_profile in lower:
        tag = "[USER]"
    else:
        tag = "[PATH]"
    return f"{tag} {path}"


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="clear-win-start",
        description="Windows 开始菜单整理工具 —— 扁平化嵌套文件夹、清理无效快捷方式。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用方法：
  clear-win-start
  clear-win-start --user-name john --verbose
  clear-win-start --config config.json --dry-run
  clear-win-start --auto-confirm --no-check-shortcuts
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--user-name",
        "-u",
        type=str,
        default=None,
        help="Windows 用户名（默认：自动检测）",
    )

    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="JSON 配置文件路径",
    )

    parser.add_argument(
        "--paths",
        "-p",
        type=str,
        nargs="+",
        default=None,
        help="额外要处理的路径",
    )

    parser.add_argument(
        "--neglect-folders",
        "-n",
        type=str,
        nargs="+",
        default=None,
        help="跳过这些文件夹（不处理）",
    )

    parser.add_argument(
        "--delete-keywords",
        "-d",
        type=str,
        nargs="+",
        default=None,
        help="匹配关键词的文件/文件夹将被删除",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅预览，不实际修改",
    )

    parser.add_argument(
        "--auto-confirm",
        "-y",
        action="store_true",
        help="跳过所有确认提示",
    )

    parser.add_argument(
        "--no-check-shortcuts",
        action="store_true",
        help="跳过快捷方式有效性验证",
    )

    parser.add_argument(
        "--no-dedupe-shortcuts",
        action="store_true",
        help="跳过重复快捷方式清理（目标路径与启动参数均相同的快捷方式）",
    )

    parser.add_argument(
        "--no-backup-shortcuts",
        action="store_true",
        help="跳过执行前的快捷方式备份",
    )

    parser.add_argument(
        "--no-animation",
        action="store_true",
        help="关闭终端动态效果（全屏面板 / 进度 / 方向键菜单）",
    )

    parser.add_argument(
        "--backup-dir",
        type=str,
        default=None,
        help="快捷方式备份目录（默认：桌面的 ClearWinStart_Backup 文件夹）",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="启用详细（调试）日志",
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="仅验证配置和路径，不执行操作",
    )

    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="日志文件路径（默认：自动生成到 AppData）",
    )

    parser.add_argument(
        "--wizard",
        action="store_true",
        help="运行交互式配置向导",
    )

    parser.add_argument(
        "--save-config",
        type=str,
        default=None,
        help="将生成的配置保存到指定路径",
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="显示详细操作计划的预览界面",
    )

    return parser


def build_config(args: argparse.Namespace) -> Configuration:
    """Build Configuration from command-line arguments.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Configuration instance.

    Raises:
        ValueError: If required configuration is missing.
    """
    user_name = args.user_name or get_windows_username()

    if not user_name:
        raise ValueError(
            "无法自动检测 Windows 用户名，请使用 --user-name 指定。"
        )

    if args.config:
        config = Configuration.from_file(args.config)
        config.user_name = user_name
    else:
        config = Configuration(user_name=user_name)

    if args.paths:
        config.paths = args.paths

    if args.neglect_folders:
        config.neglect_folders = args.neglect_folders

    if args.delete_keywords:
        config.delete_keywords = args.delete_keywords

    config.dry_run = args.dry_run
    config.check_shortcuts = not args.no_check_shortcuts
    config.dedupe_shortcuts = not args.no_dedupe_shortcuts
    config.backup_shortcuts = not args.no_backup_shortcuts
    config.animation = not args.no_animation

    if args.backup_dir:
        config.backup_dir = args.backup_dir

    return config


def _overview_lines(screen: Screen, config: Configuration) -> List[str]:
    """配置总览视图（面板内）。"""
    backup_value = (
        config.backup_dir or get_default_backup_dir()
    ) if config.backup_shortcuts else "否"
    rows = [
        ("用户", config.user_name),
        ("待处理路径", f"{len(config.paths)} 个"),
        ("干跑模式", "是" if config.dry_run else "否"),
        ("校验快捷方式", "是" if config.check_shortcuts else "否"),
        ("去重快捷方式", "是" if config.dedupe_shortcuts else "否"),
        ("备份快捷方式", backup_value),
    ]
    lines = [screen.line("  配置信息", "bold")]
    for label, value in rows:
        lines.append(screen.line(f"    {console.pad(label, 16)} {value}"))
    lines.append("")
    lines.append(screen.line("  待处理路径", "bold"))
    for path in config.paths:
        lines.append(screen.line("    " + _path_label(path), "dim"))
    return lines


def _activity_line(screen: Screen, message: str, level: str) -> str:
    """把一条活动日志渲染为一行（含级别图标与着色）。"""
    if level in ("ERROR", "CRITICAL"):
        return screen.line(f"    {ICONS['error']} {message}", "red")
    if level == "WARNING":
        return screen.line(f"    {ICONS['warn']} {message}", "yellow")
    if level == "DEBUG":
        return screen.line(f"    {message}", "dim")
    return screen.line(f"    {ICONS['move']} {message}")


def _stats_lines(screen: Screen, stats: dict,
                 activity: Optional[List[tuple]] = None) -> List[str]:
    """结果视图（面板内）：操作统计 + 保留本次执行的操作记录。"""
    rows = [
        ("已处理文件夹", stats.get("folders_processed", 0)),
        ("已移动文件", stats.get("files_moved", 0)),
        ("覆盖同名文件", stats.get("files_overwritten", 0)),
        ("已删除文件/文件夹", stats.get("files_deleted", 0)),
        ("已清理无效快捷方式", stats.get("shortcuts_cleaned", 0)),
        ("已去重快捷方式", stats.get("shortcuts_deduped", 0)),
        ("已备份快捷方式", stats.get("shortcuts_backed_up", 0)),
    ]
    lines = [screen.line(f"  {ICONS['stats']} 操作统计", "bold", "cyan"), ""]
    for label, value in rows:
        lines.append(screen.line(f"    {console.pad(label, 20)} {value}"))

    entries = list(activity or [])
    if entries:
        lines.append("")
        lines.append(
            screen.line(f"  {ICONS['info']} 本次操作记录  {len(entries)} 条", "gray")
        )
        budget = max(2, console.terminal_height() - 11 - len(lines))
        shown = entries[-budget:]
        for message, level in shown:
            lines.append(_activity_line(screen, message, level))
        if len(entries) > len(shown):
            lines.append(screen.line(f"    … 另有 {len(entries) - len(shown)} 条更早记录", "dim"))
    return lines


def _plan_item_text(item: PreviewItem) -> str:
    """把预览项渲染为一行纯文本（颜色与宽度由 Screen 统一处理）。"""
    if item.action == ActionType.MOVE:
        source = os.path.basename(item.source or "")
        destination = os.path.basename(item.destination or "")
        return f"{ICONS['move']} {source} → {destination}"
    if item.action == ActionType.FOLDER:
        reason = f"（{item.reason}）" if item.reason else ""
        return f"{ICONS['folder']} {item.name}{reason}"
    if item.action == ActionType.DELETE:
        reason = f"（{item.reason}）" if item.reason else ""
        return f"{ICONS['delete']} {item.name}{reason}"
    if item.action == ActionType.VALIDATE:
        return f"{ICONS['validate']} {item.name}"
    return f"{ICONS['info']} {item.name}"


def _plan_lines(screen: Screen, report: PreviewReport) -> List[str]:
    """操作计划视图（面板内，按可用高度自动精简明细，保证信息区不被截断）。"""
    impact_style = {"低": "green", "中": "yellow", "高": "red"}.get(
        report.impact_level.label, "cyan"
    )
    lines = [
        screen.line("  操作计划预览", "bold", "cyan"),
        screen.line(f"    时间      {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"),
        screen.line(f"    用户      {report.user_name}"),
        screen.line(f"    影响级别  {report.impact_level.label}", impact_style),
    ]
    sections = [section for section in report.sections.values() if section.items]
    if not sections:
        lines.append("")
        lines.append(screen.line(f"  {ICONS['warn']} 没有检测到任何操作", "dim"))
        return lines

    budget = max(8, console.terminal_height() - 11)
    detail_budget = max(0, budget - len(lines) - 2 * len(sections) - 2)
    per_section = max(1, detail_budget // len(sections))
    hidden = 0
    for section in sections:
        lines.append("")
        lines.append(
            screen.line(f"  {section.icon} {section.title}  {len(section.items)} 项", "bold")
        )
        for item in section.items[:per_section]:
            lines.append(screen.line("    " + _plan_item_text(item)))
        hidden += max(0, len(section.items) - per_section)

    if hidden:
        lines.append("")
        lines.append(screen.line(f"  … 另有 {hidden} 个明细未显示", "dim"))
    lines.append("")
    lines.append(
        screen.line(f"  {ICONS['stats']} 总计 {report.total_operations} 个操作", "bold", "cyan")
    )
    return lines


def _run_wizard_session(screen: Screen, args: argparse.Namespace) -> int:
    """在全屏面板内运行配置向导。"""
    screen.step(1)
    try:
        wizard = ConfigurationWizard(
            prompter=ScreenPrompter(screen),
            default_user_name=get_windows_username() or "",
        )
        config = wizard.run()
        save_path = args.save_config or screen.text(
            [], "是否保存配置文件？（回车保存到 config.json）", "config.json"
        )
        output_path = wizard.save_config(config, save_path or None)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        logger.error(f"Wizard error: {e}")
        screen.show(
            [screen.line(f"  {ICONS['error']} 错误: {e}", "red")],
            footer="按任意键退出 …",
            hold=True,
        )
        return 1

    screen.step(4)
    screen.show(
        [
            screen.line(f"  {ICONS['ok']} 配置已保存到: {output_path}", "green"),
            "",
            screen.line("  现在可以运行工具了：", "dim"),
            screen.line(f"      clear-win-start --config {output_path}", "cyan"),
        ],
        footer="按任意键退出 …",
        hold=True,
    )
    return 0


def _run_session(screen: Screen, args: argparse.Namespace, config: Configuration) -> int:
    """在统一大屏内跑完「初始化 → 配置 → 路径选择 → 执行 → 结果」。"""
    # ---- 步骤 0：启动初始化 ----
    screen.step(0)
    screen.show(
        [
            "",
            screen.line("  正在初始化 …", "cyan"),
            screen.line(f"  {ICONS['path']} 本机用户: {config.user_name}", "dim"),
        ],
        min_seconds=0.8,
    )

    organizer = StartMenuOrganizer(config)
    errors = organizer.validate_paths()
    if errors:
        lines = [screen.line(f"  {ICONS['error']} 配置验证未通过：", "red", "bold")]
        lines += [screen.line(f"      {ICONS['delete']} {msg}", "red") for msg in errors]
        screen.show(lines, footer="按任意键退出 …", hold=True)
        return 1
    screen.log("配置校验通过")

    # ---- 步骤 1：配置总览 ----
    screen.step(1)
    screen.show(_overview_lines(screen, config), footer="按任意键继续 …", hold=True)

    if args.validate_only:
        screen.step(4)
        screen.show(
            [screen.line(f"  {ICONS['ok']} 所有路径和配置均有效。", "green")],
            footer="按任意键退出 …",
            hold=True,
        )
        return 0

    # ---- 步骤 2：路径选择 ----
    screen.step(2)
    if screen.enabled and not args.auto_confirm:
        picked = screen.paths_select([(_path_label(path), "") for path in config.paths])
        if not picked:
            screen.show(
                [screen.line(f"  {ICONS['warn']} 未选择任何路径，操作已取消。", "yellow")],
                footer="按任意键退出 …",
                hold=True,
            )
            return 0
        config.paths = [config.paths[index] for index in picked]
        screen.set_context(f"用户 {config.user_name} · {len(config.paths)} 个路径")
    screen.ensure_visible(0.4)

    # ---- 干跑：仅展示计划 ----
    if config.dry_run:
        screen.step(3)
        screen.show([screen.line("  正在扫描并生成计划 …", "cyan")], min_seconds=0.5)
        organizer.organize(auto_confirm=True, preview_only=True)
        report = organizer.get_dry_run_report()
        preview = create_preview_from_plan(
            report["plan"], report["summary"], config.paths, config.user_name
        )
        screen.show(_plan_lines(screen, preview), footer="按任意键继续 …", hold=True)
        screen.step(4)
        screen.show(
            [
                screen.line(f"  {ICONS['warn']} 干跑模式：未对系统做任何更改。", "yellow"),
                screen.line("  如需实际执行，请去掉 --dry-run 参数。", "dim"),
            ],
            footer="按任意键退出 …",
            hold=True,
        )
        return 0

    # ---- 预览：展示计划，确认后执行 ----
    if args.preview:
        screen.step(3)
        screen.show([screen.line("  正在扫描并生成计划 …", "cyan")], min_seconds=0.5)
        organizer.organize(auto_confirm=True, preview_only=True)
        report = organizer.get_dry_run_report()
        preview = create_preview_from_plan(
            report["plan"], report["summary"], config.paths, config.user_name
        )
        screen.show(_plan_lines(screen, preview), footer="按任意键继续 …", hold=True)
        picked = screen.menu(
            [screen.line("  确认执行以上操作？", "bold")],
            [("确认执行", "执行所有列出的操作"), ("取消", "放弃本次操作")],
            single=True,
            default_index=0,
        )
        if not picked or picked[0] != 0:
            screen.show(
                [screen.line("  操作已取消。", "yellow")], footer="按任意键退出 …", hold=True
            )
            return 0

    # ---- 步骤 3：执行 ----
    screen.step(3)
    auto_confirm = True if screen.enabled else args.auto_confirm
    stats = organizer.organize(auto_confirm=auto_confirm, dashboard=screen.dashboard)

    # ---- 步骤 4：结果（统计 + 保留执行记录，停留到用户按键） ----
    screen.step(4)
    screen.show(
        _stats_lines(screen, stats, screen.dashboard.activity),
        footer="按任意键退出 …",
        hold=True,
    )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv).

    Returns:
        Exit code (0 for success, 1 for error).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    log_file = args.log_file if args.log_file else get_default_log_path()
    setup_logging(verbose=args.verbose, log_file=log_file)

    # 配置向导同样在全屏面板内完成
    if args.wizard:
        console.set_animation_enabled(not args.no_animation)
        screen = Screen()
        screen.open(context="配置向导")
        try:
            return _run_wizard_session(screen, args)
        except KeyboardInterrupt:
            screen.close()
            print("\n  " + console.style(f"{ICONS['info']} 配置向导已取消。", "dim"))
            return 130
        finally:
            screen.close()

    try:
        config = build_config(args)
        config.validate()
    except (StartMenuOrganizerError, ConfigurationError, ValueError) as e:
        logger.error(str(e))
        print(f"{ICONS['error']} 配置错误: {e}", file=sys.stderr)
        return 1

    console.set_animation_enabled(config.animation)
    screen = Screen()
    screen.open(context=f"用户 {config.user_name} · {len(config.paths)} 个路径")
    try:
        return _run_session(screen, args, config)
    except KeyboardInterrupt:
        screen.close()
        print("\n  " + console.style(f"{ICONS['info']} 操作已取消。", "dim"))
        return 130
    except StartMenuOrganizerError as e:
        logger.error(str(e))
        screen.close()
        print(f"{ICONS['error']} 错误: {e}", file=sys.stderr)
        return 1
    finally:
        screen.close()


if __name__ == "__main__":
    sys.exit(main())


# =============================================================================
# Preview classes (migrated from preview.py)
# =============================================================================


class ActionType(Enum):
    """Types of actions that can be performed."""
    MOVE = "move"
    DELETE = "delete"
    SKIP = "skip"
    VALIDATE = "validate"
    FOLDER = "folder"


class ImpactLevel(Enum):
    """Impact level of operations."""
    LOW = ("低", "green")
    MEDIUM = ("中", "yellow")
    HIGH = ("高", "red")

    def __init__(self, label: str, color: str):
        self.label = label
        self.color = color


@dataclass
class PreviewItem:
    """Single item in the preview."""
    action: ActionType
    name: str
    source: Optional[str] = None
    destination: Optional[str] = None
    reason: Optional[str] = None
    size: Optional[str] = None


@dataclass
class PreviewSection:
    """Section in the preview window."""
    title: str
    icon: str
    items: List[PreviewItem] = field(default_factory=list)
    collapsible: bool = True
    collapsed: bool = False


@dataclass
class PreviewReport:
    """Complete preview report."""
    timestamp: datetime
    paths: List[str]
    user_name: str
    sections: Dict[str, PreviewSection] = field(default_factory=dict)
    impact_level: ImpactLevel = ImpactLevel.LOW
    backup_id: Optional[str] = None
    total_operations: int = 0

    def add_item(self, section_name: str, section_icon: str, item: PreviewItem,
                 title: Optional[str] = None) -> None:
        """Add an item to a section, creating the section if needed."""
        if section_name not in self.sections:
            self.sections[section_name] = PreviewSection(
                title=title or section_name,
                icon=section_icon
            )
        self.sections[section_name].items.append(item)
        self.total_operations += 1


class PreviewWindow:
    """Interactive preview window renderer."""

    COLORS = {
        'header': '\033[95m',      # Purple
        'success': '\033[92m',     # Green
        'warning': '\033[93m',      # Yellow
        'error': '\033[91m',       # Red
        'info': '\033[96m',        # Cyan
        'dim': '\033[90m',         # Gray
        'bold': '\033[1m',
        'underline': '\033[4m',
        'end': '\033[0m',
    }

    @staticmethod
    def supports_color() -> bool:
        """是否应输出颜色（委托 console，尊重 NO_COLOR / TTY 探测）。"""
        return console.should_use_color()

    @staticmethod
    def color(text: str, color_name: str) -> str:
        """Apply color to text（未启用颜色时原样返回）。"""
        if not PreviewWindow.supports_color():
            return text
        color = PreviewWindow.COLORS.get(color_name, '')
        return f"{color}{text}{PreviewWindow.COLORS['end']}"

    @staticmethod
    def truncate(text: str, max_length: int, suffix: str = "...") -> str:
        """按显示宽度截断文本（中文按 2 列计算）。"""
        if console.display_width(text) <= max_length:
            return text
        keep = max_length - console.display_width(suffix)
        result = ""
        for char in text:
            if console.display_width(result + char) > keep:
                break
            result += char
        return result + suffix

    @staticmethod
    def format_preview_item(item: PreviewItem, index: int, max_len: int = 56) -> str:
        """把单个预览项格式化为一行（含着色）。"""
        if item.action == ActionType.MOVE:
            source_path = item.source or ""
            parent = os.path.basename(os.path.dirname(source_path))
            if parent:
                source_label = os.path.join(parent, os.path.basename(source_path))
            else:
                source_label = source_path
            source_name = PreviewWindow.truncate(source_label, max_len)
            dest_name = PreviewWindow.truncate(
                os.path.basename(item.destination or ""), max_len // 2
            )
            return console.style(f"    {ICONS['move']} {source_name} → {dest_name}", "cyan")
        if item.action == ActionType.FOLDER:
            name = PreviewWindow.truncate(item.name, max_len)
            reason = console.style(f"（{item.reason}）", "dim") if item.reason else ""
            return console.style(f"    {ICONS['folder']} {name}", "yellow") + reason
        if item.action == ActionType.DELETE:
            name = PreviewWindow.truncate(item.name, max_len)
            reason = console.style(f"（{item.reason}）", "dim") if item.reason else ""
            return f"    {console.style(ICONS['delete'], 'red')} {name}{reason}"
        if item.action == ActionType.VALIDATE:
            name = PreviewWindow.truncate(item.name, max_len)
            return console.style(f"    {ICONS['validate']} {name}", "dim")
        if item.action == ActionType.SKIP:
            name = PreviewWindow.truncate(item.name, max_len)
            reason = console.style(f"（{item.reason}）", "dim") if item.reason else ""
            return f"    {ICONS['info']} {name}{reason}"
        return f"    {item.name}"

    @staticmethod
    def render_preview(report: PreviewReport) -> str:
        """渲染完整的预览面板（尺寸/对齐按显示宽度计算）。"""
        lines: List[str] = []
        width = 60

        lines.append(console.style(console.rule(width, "═"), "cyan"))
        lines.append("  " + console.style("开始菜单整理预览", "bold", "cyan"))
        lines.append(console.style(console.rule(width, "═"), "cyan"))
        lines.append("")

        paths_text = PreviewWindow.truncate(", ".join(report.paths), 44)
        lines.append(console.kv("时间", report.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 10, 2))
        lines.append(console.kv("用户", report.user_name, 10, 2))
        lines.append(console.kv("路径", paths_text, 10, 2))
        if report.backup_id:
            lines.append(console.kv("备份", report.backup_id, 10, 2))

        impact_style = {"低": "green", "中": "yellow", "高": "red"}.get(
            report.impact_level.label, "cyan"
        )
        lines.append(
            console.kv(
                "影响级别",
                console.style(report.impact_level.label, impact_style, "bold"),
                10,
                2,
            )
        )

        if not report.sections:
            lines.append("")
            lines.append("  " + console.style(f"{ICONS['warn']} 没有检测到任何操作", "dim"))
            return "\n".join(lines)

        for section in report.sections.values():
            if not section.items:
                continue
            lines.append("")
            lines.append(
                "  "
                + console.style(f"{section.icon} {section.title}", "bold")
                + console.style(f"  {len(section.items)} 项", "dim")
            )
            for index, item in enumerate(section.items[:20], 1):
                lines.append(PreviewWindow.format_preview_item(item, index))
            if len(section.items) > 20:
                lines.append(
                    console.style(f"    ... 还有 {len(section.items) - 20} 项未显示", "dim")
                )

        lines.append("")
        lines.append(console.style(console.rule(width), "gray"))
        lines.append(
            "  "
            + console.style(f"{ICONS['stats']} 总计 ", "bold")
            + console.style(f"{report.total_operations} 个操作", "bold", "cyan")
        )
        lines.append(console.style(console.rule(width), "gray"))
        return "\n".join(lines)


def create_preview_from_plan(plan: List[dict], summary: dict, paths: List[str],
                             user_name: str) -> PreviewReport:
    """由 dry-run 的计划与摘要构建预览报告（含真实条目明细）。

    Args:
        plan: StartMenuOrganizer.get_dry_run_report() 的 plan 部分。
        summary: 同一报告的 summary 部分。
        paths: 待处理路径列表。
        user_name: 用户名。

    Returns:
        填充好的 PreviewReport。
    """
    report = PreviewReport(
        timestamp=datetime.now(),
        paths=paths,
        user_name=user_name,
    )

    for entry in plan:
        for folder in entry.get("folders_to_process", []):
            report.add_item(
                "folders",
                ICONS["folder"],
                PreviewItem(action=ActionType.FOLDER, name=folder, reason="扁平化后移除空文件夹"),
                "文件夹整理",
            )
        for move in entry.get("files_to_move", []):
            report.add_item(
                "moves",
                ICONS["move"],
                PreviewItem(
                    action=ActionType.MOVE,
                    name=os.path.basename(move.get("source", "")),
                    source=move.get("source"),
                    destination=move.get("destination"),
                ),
                "文件移动",
            )
        for item in entry.get("files_to_delete", []):
            report.add_item(
                "deletes",
                ICONS["delete"],
                PreviewItem(
                    action=ActionType.DELETE,
                    name=os.path.basename(item.get("path", "")),
                    reason=item.get("reason", ""),
                ),
                "关键词删除",
            )
        for duplicate in entry.get("shortcuts_to_dedupe", []):
            report.add_item(
                "dedupe",
                ICONS["dedupe"],
                PreviewItem(
                    action=ActionType.DELETE,
                    name=os.path.basename(duplicate),
                    reason="目标路径与启动参数相同",
                ),
                "快捷方式去重",
            )

    invalid = summary.get("total_shortcuts_invalid", 0)
    if invalid > 0:
        report.add_item(
            "invalid",
            ICONS["validate"],
            PreviewItem(
                action=ActionType.VALIDATE,
                name=f"共 {invalid} 个将移入回收站",
                reason="目标不存在",
            ),
            "无效快捷方式",
        )

    unreadable = summary.get("total_shortcuts_unreadable", 0)
    if unreadable > 0:
        report.add_item(
            "unreadable",
            ICONS["warn"],
            PreviewItem(
                action=ActionType.SKIP,
                name=f"共 {unreadable} 个快捷方式无法读取",
                reason="已跳过校验，不会删除",
            ),
            "无法读取",
        )

    overwritten = summary.get("total_files_overwritten", 0)
    if overwritten > 0:
        report.add_item(
            "overwrite",
            ICONS["warn"],
            PreviewItem(
                action=ActionType.SKIP,
                name=f"共 {overwritten} 个同名文件将被覆盖",
                reason="原文件移入回收站",
            ),
            "同名覆盖",
        )

    backup = summary.get("total_shortcuts_to_backup", 0)
    if backup > 0:
        report.add_item(
            "backup",
            ICONS["backup"],
            PreviewItem(
                action=ActionType.SKIP,
                name=f"共 {backup} 个快捷方式将被备份",
                reason="保存到备份目录",
            ),
            "快捷方式备份",
        )

    impact_map = {"低": ImpactLevel.LOW, "中": ImpactLevel.MEDIUM, "高": ImpactLevel.HIGH}
    report.impact_level = impact_map.get(summary.get("estimated_impact", "低"), ImpactLevel.LOW)
    return report
