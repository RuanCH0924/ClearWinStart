"""
Command-line interface for ClearWinStart.
"""

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from clear_win_start import __version__
from clear_win_start.core import StartMenuOrganizer, StartMenuOrganizerError
from clear_win_start.config import Configuration, ConfigurationWizard
from clear_win_start.logging_setup import setup_logging
from clear_win_start.paths import get_default_log_path, get_windows_username

logger = logging.getLogger(__name__)


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

    return config


def print_stats(stats: dict) -> None:
    """Print operation statistics.

    Args:
        stats: Statistics dictionary.
    """
    print("\n" + "=" * 50)
    print("操作统计")
    print("=" * 50)
    print(f"  已处理文件夹:     {stats.get('folders_processed', 0)}")
    print(f"  已移动文件:       {stats.get('files_moved', 0)}")
    print(f"  已删除文件/文件夹: {stats.get('files_deleted', 0)}")
    print(f"  已清理无效快捷方式: {stats.get('shortcuts_cleaned', 0)}")
    print("=" * 50)


def run_wizard(args: argparse.Namespace) -> int:
    """Run the configuration wizard.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    setup_logging(verbose=args.verbose)

    try:
        wizard = ConfigurationWizard()
        config = wizard.run()

        save_config = args.save_config or input(
            "\n是否保存配置文件？（回车保存到 'config.json' 或输入路径）："
        ).strip()

        if not save_config:
            save_config = "config.json"

        output_path = wizard.save_config(config, save_config if save_config else None)

        print(f"\n配置已保存到: {output_path}")
        print("\n现在可以运行工具了：")
        print(f"  clear-win-start --config {output_path}")

        return 0

    except KeyboardInterrupt:
        print("\n\n配置向导已取消。")
        return 130
    except Exception as e:
        logger.error(f"Wizard error: {e}")
        print(f"错误: {e}", file=sys.stderr)
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv).

    Returns:
        Exit code (0 for success, 1 for error).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.wizard:
        return run_wizard(args)

    log_file = args.log_file if args.log_file else get_default_log_path()
    setup_logging(verbose=args.verbose, log_file=log_file)

    try:
        config = build_config(args)
        config.validate()

        if args.validate_only:
            print("正在验证配置和路径...")
            organizer = StartMenuOrganizer(config)
            errors = organizer.validate_paths()
            if errors:
                print("\n验证发现以下错误：")
                for error in errors:
                    print(f"  - {error}")
                return 1
            print("所有路径和配置均有效。")
            return 0

        print("=" * 50)
        print("ClearWinStart")
        print("=" * 50)
        print(f"\n用户: {config.user_name}")
        print("\n待处理路径：")
        user_profile = os.environ.get("USERPROFILE", "").lower()
        system_marker = os.path.join("programdata", "microsoft").lower()
        for path in config.paths:
            lower = path.lower()
            if system_marker in lower:
                print(f"  [SYS]  {path}")
            elif user_profile and user_profile in lower:
                print(f"  [USER] {path}")
            else:
                print(f"  {path}")
        print(f"\n干跑模式: {'是' if config.dry_run else '否'}")
        print(f"校验快捷方式: {'是' if config.check_shortcuts else '否'}")
        
        if args.dry_run:
            print("\n" + "⚠️  " + "=" * 46)
            print("⚠️  干跑模式 - 不会对系统进行任何更改  ⚠️")
            print("⚠️  " + "=" * 46 + "\n")
        
        print("=" * 50 + "\n")

        organizer = StartMenuOrganizer(config)

        if args.preview:
            print(PreviewWindow.color("\n正在扫描并生成预览...\n", 'info'))
            stats = organizer.organize(auto_confirm=True, preview_only=True)

            preview_report = create_preview_from_stats(
                stats,
                config.paths,
                config.user_name
            )

            preview_output = PreviewWindow.render_preview(preview_report)
            print(preview_output)

            print("\n")
            action = InteractiveConfirm.show_execute_menu()

            if action == 'cancel':
                print(PreviewWindow.color("\n操作已取消", 'warning'))
                return 0
            if action == 'rescan':
                print(PreviewWindow.color("\n正在重新扫描...\n", 'info'))
                return main(argv)
            print(PreviewWindow.color("\n正在执行操作...\n", 'info'))
            stats = organizer.organize(auto_confirm=True, preview_only=False)
            print_stats(stats)
        else:
            stats = organizer.organize(auto_confirm=args.auto_confirm)
            print_stats(stats)

        if args.dry_run:
            print("\n本次为干跑模式。如需实际执行，请去掉 --dry-run 参数。")

        return 0

    except StartMenuOrganizerError as e:
        logger.error(str(e))
        print(f"错误: {e}", file=sys.stderr)
        return 1

    except ValueError as e:
        logger.error(str(e))
        print(f"配置错误: {e}", file=sys.stderr)
        return 1

    except KeyboardInterrupt:
        print("\n操作已取消。")
        return 130


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

    BOX_WIDTH = 70
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
        """Check if terminal supports colors."""
        if sys.platform == 'win32':
            return os.environ.get('TERM') or True
        return sys.stdout.isatty()

    @staticmethod
    def color(text: str, color_name: str) -> str:
        """Apply color to text."""
        if not PreviewWindow.supports_color():
            return text
        color = PreviewWindow.COLORS.get(color_name, '')
        return f"{color}{text}{PreviewWindow.COLORS['end']}"

    @staticmethod
    def center_text(text: str, width: int) -> str:
        """Center text within specified width."""
        return text.center(width)

    @staticmethod
    def truncate(text: str, max_length: int, suffix: str = "...") -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix

    @staticmethod
    def draw_box(content: List[str], title: Optional[str] = None,
                 border_color: str = 'info') -> str:
        """Draw a box around content."""
        lines = []
        width = PreviewWindow.BOX_WIDTH

        top_border = "┌" + "─" * (width - 2) + "┐"
        bottom_border = "└" + "─" * (width - 2) + "┘"
        side_border = "│"

        lines.append(PreviewWindow.color(top_border, border_color))

        if title:
            title_line = f"│{PreviewWindow.center_text(title, width - 2)}│"
            lines.append(PreviewWindow.color(title_line, border_color))
            lines.append(PreviewWindow.color("├" + "─" * (width - 2) + "┤", border_color))

        for line in content:
            if isinstance(line, tuple):
                text, color = line
                lines.append(f"{side_border} {PreviewWindow.color(text.ljust(width - 2), color)} │")
            else:
                lines.append(f"{side_border} {line.ljust(width - 2)} │")

        lines.append(PreviewWindow.color(bottom_border, border_color))
        return "\n".join(lines)

    @staticmethod
    def format_preview_item(item: PreviewItem, index: int, max_len: int = 50) -> List[str]:
        """Format a single preview item."""
        lines = []

        if item.action == ActionType.MOVE:
            icon = "→"
            source_name = PreviewWindow.truncate(os.path.basename(item.source or ""), max_len // 2)
            dest_name = PreviewWindow.truncate(os.path.basename(item.destination or ""), max_len // 2)
            line = f"  {icon} {source_name} → {dest_name}"
            lines.append((line, 'info'))

        elif item.action == ActionType.DELETE:
            icon = "✓"
            name = PreviewWindow.truncate(item.name, max_len)
            reason = f" ({item.reason})" if item.reason else ""
            line = f"  {icon} {name}{reason}"
            lines.append((line, 'warning'))

        elif item.action == ActionType.VALIDATE:
            icon = "🔍"
            name = PreviewWindow.truncate(item.name, max_len)
            line = f"  {icon} {name}"
            lines.append((line, 'dim'))

        elif item.action == ActionType.SKIP:
            icon = "⚠"
            name = PreviewWindow.truncate(item.name, max_len)
            line = f"  {icon} {name}（将跳过）"
            lines.append((line, 'dim'))

        return lines

    @staticmethod
    def render_preview(report: PreviewReport) -> str:
        """Render the complete preview window."""
        lines = []

        header = [
            "╔══════════════════════════════════════════════════════════════════╗",
            "║                    开始菜单整理预览                               ║",
            "╚══════════════════════════════════════════════════════════════════╝",
        ]

        info_section = [
            f"  📅 时间: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"  👤 用户: {report.user_name}",
            f"  📁 路径: {PreviewWindow.truncate(', '.join(report.paths), 50)}",
            "",
        ]

        if report.backup_id:
            info_section.append(f"  📦 备份: {report.backup_id}")

        impact_colors = {
            '低': 'success',
            '中': 'warning',
            '高': 'error'
        }
        impact = report.impact_level.label
        info_section.append(f"  ⚠️  影响级别: {PreviewWindow.color(impact, impact_colors.get(impact, 'info'))}")

        lines.extend(header)
        lines.append("")
        lines.extend(info_section)

        if not report.sections:
            lines.append("")
            lines.append(PreviewWindow.color("  ⚠️  没有检测到任何操作", 'dim'))
            return "\n".join(lines)

        for section_name, section in report.sections.items():
            if not section.items:
                continue

            lines.append("")
            lines.append(f"  {section.icon} {section.title} ({len(section.items)} 项)")

            for idx, item in enumerate(section.items[:20], 1):
                item_lines = PreviewWindow.format_preview_item(item, idx)
                for line in item_lines:
                    if isinstance(line, tuple):
                        lines.append(line[0])
                    else:
                        lines.append(line)

            if len(section.items) > 20:
                lines.append(f"  ... 还有 {len(section.items) - 20} 项未显示")

        lines.append("")
        lines.append("  " + "─" * 66)
        lines.append(f"  📊 总计: {report.total_operations} 个操作")
        lines.append("  " + "─" * 66)

        return "\n".join(lines)


class InteractiveConfirm:
    """Interactive confirmation interface."""

    @staticmethod
    def confirm(message: str, default: Optional[bool] = None) -> bool:
        """Ask for user confirmation."""
        if default is None:
            prompt = f"{message} [y/n]: "
        elif default:
            prompt = f"{message} [Y/n]: "
        else:
            prompt = f"{message} [y/N]: "

        while True:
            try:
                response = input(PreviewWindow.color(prompt, 'info')).strip().lower()
                if not response:
                    if default is not None:
                        return default
                elif response in ['y', 'yes', '是', '确认']:
                    return True
                elif response in ['n', 'no', '否', '取消']:
                    return False
                else:
                    print(PreviewWindow.color("  请输入 y 或 n", 'warning'))
            except (KeyboardInterrupt, EOFError):
                print()
                return False

    @staticmethod
    def show_menu(options: List[Dict[str, Any]]) -> Optional[int]:
        """Show interactive menu and return selected option index."""
        if not options:
            return None

        print()
        for idx, option in enumerate(options, 1):
            key = option.get('key', str(idx))
            label = option.get('label', '')
            description = option.get('description', '')
            default = option.get('default', False)

            default_marker = " ★" if default else ""
            print(f"  [{key}] {label}{default_marker}")
            if description:
                print(f"      {PreviewWindow.color(description, 'dim')}")

        print()
        while True:
            try:
                response = input(PreviewWindow.color("  请选择 [1]: ", 'info')).strip()
                if not response:
                    for idx, option in enumerate(options):
                        if option.get('default', False):
                            return idx
                    return 0 if options else None
                elif response.isdigit():
                    idx = int(response) - 1
                    if 0 <= idx < len(options):
                        return idx
                else:
                    for idx, option in enumerate(options):
                        if option.get('key') == response:
                            return idx
                print(PreviewWindow.color(f"  请输入 1-{len(options)} 之间的数字", 'warning'))
            except (KeyboardInterrupt, EOFError):
                print()
                return None

    @staticmethod
    def show_execute_menu() -> str:
        """Show execution options menu."""
        options = [
            {'key': '1', 'label': '确认执行', 'description': '执行所有列出的操作', 'default': True},
            {'key': '2', 'label': '重新扫描', 'description': '重新扫描并生成新的预览'},
            {'key': '3', 'label': '取消', 'description': '取消操作，返回命令行'},
        ]

        idx = InteractiveConfirm.show_menu(options)
        if idx is None:
            return 'cancel'

        actions = ['execute', 'rescan', 'cancel']
        return actions[idx]


def create_preview_from_stats(stats: dict, paths: List[str],
                              user_name: str) -> PreviewReport:
    """Create a preview report from operation statistics."""
    report = PreviewReport(
        timestamp=datetime.now(),
        paths=paths,
        user_name=user_name
    )

    folders_processed = stats.get('folders_processed', 0)
    if folders_processed > 0:
        report.add_item(
            "📂 文件夹处理",
            "📂",
            PreviewItem(
                action=ActionType.SKIP,
                name=f"将处理 {folders_processed} 个文件夹",
                reason="扁平化嵌套结构"
            ),
            "📂 文件夹整理"
        )

    files_moved = stats.get('files_moved', 0)
    if files_moved > 0:
        report.add_item(
            "📦 文件移动",
            "📦",
            PreviewItem(
                action=ActionType.MOVE,
                name=f"将移动 {files_moved} 个文件",
                reason="扁平化到根目录"
            ),
            "📦 文件移动"
        )

    files_deleted = stats.get('files_deleted', 0)
    if files_deleted > 0:
        report.add_item(
            "🗑️ 删除操作",
            "🗑️",
            PreviewItem(
                action=ActionType.DELETE,
                name=f"将删除 {files_deleted} 个文件/文件夹",
                reason="匹配关键词"
            ),
            "🗑️ 删除文件"
        )

    shortcuts_cleaned = stats.get('shortcuts_cleaned', 0)
    if shortcuts_cleaned > 0:
        report.add_item(
            "🔍 快捷方式验证",
            "🔍",
            PreviewItem(
                action=ActionType.VALIDATE,
                name=f"将验证 {shortcuts_cleaned} 个快捷方式",
                reason="清理无效快捷方式"
            ),
            "🔍 快捷方式"
        )

    total_ops = files_moved + files_deleted + shortcuts_cleaned
    if total_ops > 50:
        report.impact_level = ImpactLevel.HIGH
    elif total_ops > 20:
        report.impact_level = ImpactLevel.MEDIUM
    else:
        report.impact_level = ImpactLevel.LOW

    return report
