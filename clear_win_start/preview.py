"""
Interactive preview window for ClearWinStart operations.
"""

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from shutil import get_terminal_size


class ActionType(Enum):
    """Types of actions that can be performed."""
    MOVE = "move"
    DELETE = "delete"
    SKIP = "skip"
    VALIDATE = "validate"


class ImpactLevel(Enum):
    """Impact level of operations."""
    LOW = ("Low", "green")
    MEDIUM = ("Medium", "yellow")
    HIGH = ("High", "red")

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
            line = f"  {icon} {name} (will skip)"
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
            'Low': 'success',
            'Medium': 'warning',
            'High': 'error'
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
            {
                'key': '1',
                'label': '确认执行',
                'description': '执行所有列出的操作',
                'default': True
            },
            {
                'key': '2',
                'label': '仅创建备份',
                'description': '仅创建备份，不执行任何操作'
            },
            {
                'key': '3',
                'label': '修改预览',
                'description': '重新扫描并生成新的预览'
            },
            {
                'key': '4',
                'label': '取消',
                'description': '取消操作，返回命令行'
            }
        ]

        idx = InteractiveConfirm.show_menu(options)
        if idx is None:
            return 'cancel'

        actions = ['execute', 'backup_only', 'rescan', 'cancel']
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
