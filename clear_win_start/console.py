"""
终端渲染工具：颜色控制、宽字符对齐、表格、全屏实时面板与交互选择。

仅使用标准库，供 CLI 与核心日志共享统一的视觉语言：
  - 颜色按 NO_COLOR / FORCE_COLOR / TTY 自动启用或降级
  - 按「显示宽度」对齐，正确处理中文（CJK）与 emoji 的占位宽度
  - 全屏面板仅在交互式终端启用，非 TTY / CI / NO_COLOR 自动静默
"""

import os
import shutil
import sys
import threading
import time
import unicodedata
from collections import deque
from typing import Deque, Dict, Iterable, List, Optional, Sequence, Tuple

__all__ = [
    "ICONS",
    "Dashboard",
    "animation_enabled",
    "display_width",
    "enable_windows_ansi",
    "get_active_dashboard",
    "kv",
    "menu_select",
    "pad",
    "read_key",
    "rule",
    "set_animation_enabled",
    "should_use_color",
    "style",
    "table",
    "terminal_height",
    "terminal_width",
]


# ---- 图标语义（全局统一，避免各处各写一套） ----
ICONS = {
    "path": "▶",
    "folder": "▾",
    "move": "▸",
    "delete": "✗",
    "invalid": "!",
    "dedupe": "⇋",
    "backup": "⤓",
    "validate": "🔍",
    "ok": "✔",
    "warn": "⚠",
    "error": "✘",
    "info": "ℹ",
    "stats": "📊",
}


# ---- 颜色 ----
_CODES = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "gray": "\033[90m",
}

# 零宽字符：变体选择符 / 零宽连接符，不应计入显示宽度
_ZERO_WIDTH = ("\ufe0e", "\ufe0f", "\u200b", "\u200d")

_ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
_ansi_ready = False


def _is_tty(stream) -> bool:
    """安全判断流是否为交互式终端。"""
    try:
        return bool(stream is not None and stream.isatty())
    except Exception:
        return False


def terminal_width(default: int = 80) -> int:
    """当前终端宽度（列数），无法获取时返回 default。"""
    try:
        return shutil.get_terminal_size((default, 24)).columns
    except Exception:
        return default


def terminal_height(default: int = 24) -> int:
    """当前终端高度（行数），无法获取时返回 default。"""
    try:
        return shutil.get_terminal_size((80, default)).lines
    except Exception:
        return default


def enable_windows_ansi() -> None:
    """在 Windows 控制台启用 ANSI（VT）转义支持，仅执行一次。"""
    global _ansi_ready
    if _ansi_ready or os.name != "nt":
        return
    _ansi_ready = True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        for std_handle in (-11, -12):  # STD_OUTPUT_HANDLE / STD_ERROR_HANDLE
            handle = kernel32.GetStdHandle(std_handle)
            mode = ctypes.c_uint32()
            if handle and kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(
                    handle, mode.value | _ENABLE_VIRTUAL_TERMINAL_PROCESSING
                )
    except Exception:
        pass


def should_use_color(stream=None) -> bool:
    """判断是否应输出 ANSI 颜色。

    规则：FORCE_COLOR 强制开启；NO_COLOR / TERM=dumb / 非 TTY 一律关闭。
    """
    stream = stream if stream is not None else sys.stdout
    if os.environ.get("FORCE_COLOR"):
        return True
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    if not _is_tty(stream):
        return False
    if os.name == "nt":
        enable_windows_ansi()
    return True


def style(text: str, *names: str, enabled: Optional[bool] = None) -> str:
    """为文本着色/加粗；未启用颜色时原样返回。"""
    if not names:
        return text
    if enabled is None:
        enabled = should_use_color()
    if not enabled:
        return text
    codes = "".join(_CODES.get(name, "") for name in names)
    return f"{codes}{text}{_CODES['reset']}"


def display_width(text: str) -> int:
    """计算字符串在终端的显示宽度（CJK / 全角字符占 2 列）。"""
    width = 0
    for char in text:
        if char in _ZERO_WIDTH or unicodedata.combining(char):
            continue
        if ord(char) < 32:  # 控制字符
            continue
        width += 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
    return width


def _fit(text: str, width: int, suffix: str = "…") -> str:
    """按显示宽度截断文本，超长时以 suffix 结尾。"""
    if display_width(text) <= width:
        return text
    limit = max(0, width - display_width(suffix))
    result = ""
    for char in text:
        if display_width(result + char) > limit:
            break
        result += char
    return result + suffix


def pad(text: str, width: int, align: str = "left") -> str:
    """按显示宽度填充到指定宽度。"""
    gap = max(0, width - display_width(text))
    if align == "right":
        return " " * gap + text
    if align == "center":
        left = gap // 2
        return " " * left + text + " " * (gap - left)
    return text + " " * gap


def rule(width: int = 52, char: str = "─") -> str:
    """返回一条分隔线。"""
    return char * max(1, width)


def kv(label: str, value: str, label_width: int = 20, indent: int = 4) -> str:
    """对齐的「标签: 值」行（中文按显示宽度对齐）。"""
    return " " * indent + pad(label, label_width) + value


def table(
    headers: Sequence[str],
    rows: Iterable[Sequence[object]],
    aligns: Optional[Sequence[str]] = None,
    indent: int = 4,
    enabled: Optional[bool] = None,
    max_width: Optional[int] = None,
) -> str:
    """渲染对齐表格（中文按显示宽度对齐），返回多行字符串。

    max_width 给定时，若整体超出则压缩最后一列并截断单元格内容（宽度自适应）。
    """
    header_list = [str(header) for header in headers]
    row_list = [[str(cell) for cell in row] for row in rows]
    columns = len(header_list)
    if columns == 0:
        return ""
    if aligns is None:
        aligns = ["left"] * columns

    widths = [display_width(header) for header in header_list]
    for row in row_list:
        for index in range(columns):
            cell = row[index] if index < len(row) else ""
            widths[index] = max(widths[index], display_width(cell))

    truncate = False
    if max_width:
        total = indent + sum(widths) + 2 * (columns - 1)
        if total > max_width:
            widths[-1] = max(4, widths[-1] - (total - max_width))
            truncate = True

    def _cell(text: str, index: int) -> str:
        value = _fit(text, widths[index]) if truncate else text
        return pad(value, widths[index], aligns[index])

    prefix = " " * indent
    lines = [(prefix + "  ".join(_cell(header_list[i], i) for i in range(columns))).rstrip()]
    lines.append(prefix + "  ".join("─" * widths[i] for i in range(columns)))
    for row in row_list:
        lines.append(
            (
                prefix
                + "  ".join(_cell(row[i] if i < len(row) else "", i) for i in range(columns))
            ).rstrip()
        )
    return "\n".join(lines)


# =============================================================================
# 动画开关
# =============================================================================

_animation_enabled = True


def set_animation_enabled(enabled: bool) -> None:
    """设置是否允许动态效果（由 CLI / 配置调用）。"""
    global _animation_enabled
    _animation_enabled = enabled


def animation_enabled(stream=None) -> bool:
    """当前是否应启用动态效果（全屏面板 / 方向键菜单）。"""
    if not _animation_enabled:
        return False
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return _is_tty(stream if stream is not None else sys.stdout)


# =============================================================================
# 全屏实时面板
# =============================================================================

_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

_ENTER_ALT_SCREEN = "\033[?1049h"
_EXIT_ALT_SCREEN = "\033[?1049l"
_HIDE_CURSOR = "\033[?25l"
_SHOW_CURSOR = "\033[?25h"
_CURSOR_HOME = "\033[H"
_CLEAR_TO_EOL = "\033[K"
_CLEAR_BELOW = "\033[0J"

_active_dashboard: Optional["Dashboard"] = None


def get_active_dashboard() -> Optional["Dashboard"]:
    """返回当前处于活动状态的全屏面板（供日志 Handler 协调输出）。"""
    return _active_dashboard


def _set_active_dashboard(dashboard: Optional["Dashboard"]) -> None:
    global _active_dashboard
    _active_dashboard = dashboard


def _progress_bar(current: int, total: int, width: int) -> str:
    ratio = 0.0 if not total else max(0.0, min(1.0, current / total))
    filled = int(width * ratio)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {current}/{total} ({int(ratio * 100)}%)"


class Dashboard:
    """全屏实时面板：独占备用屏幕，原地刷新标题 / 阶段 / 进度 / 统计 / 最近日志。

    仅在动画启用（交互式终端）时生效；否则所有方法为 no-op。
    执行期间的日志由 logging Handler 写入本面板（见 log()），不再滚动输出。
    """

    def __init__(
        self,
        title: str = "ClearWinStart",
        subtitle: str = "Windows 开始菜单整理工具",
        context: str = "",
        stream=None,
        enabled: Optional[bool] = None,
        max_activity: int = 500,
        steps: Optional[Sequence[str]] = None,
        min_dwell: float = 0.7,
    ) -> None:
        self.title = title
        self.subtitle = subtitle
        self.context = context
        self.stream = stream if stream is not None else sys.stdout
        self.enabled = animation_enabled(self.stream) if enabled is None else enabled
        self._color = should_use_color(self.stream)
        self.min_dwell = min_dwell

        self._phase = ""
        self._current = 0
        self._total: Optional[int] = None
        self._counters: Dict[str, int] = {}
        self._activity: Deque[Tuple[str, str]] = deque(maxlen=max_activity)

        self._steps: List[str] = list(steps or [])
        self._step = -1
        self._body: Optional[List[str]] = None
        self._footer = ""

        self._frame = 0
        self._active = False
        self._paused = False
        self._lock = threading.RLock()
        self._ticker: Optional[threading.Thread] = None
        self._last_content_change = 0.0

    # ---- 生命周期 ----
    @property
    def active(self) -> bool:
        """面板是否正在占用屏幕。"""
        return self._active and not self._paused

    def start(self) -> None:
        """进入备用屏幕并开始刷新。"""
        if not self.enabled:
            return
        with self._lock:
            if self._active:
                return
            self._active = True
            self._paused = False
            _set_active_dashboard(self)
            self._touch()
            self.stream.write(_ENTER_ALT_SCREEN + _HIDE_CURSOR)
            self._draw()
        self._ticker = threading.Thread(target=self._tick, daemon=True)
        self._ticker.start()

    def close(self) -> None:
        """退出备用屏幕、恢复光标并归还屏幕。"""
        if not self.enabled:
            return
        self._active = False
        if _active_dashboard is self:
            _set_active_dashboard(None)
        with self._lock:
            self.stream.write(_SHOW_CURSOR + _EXIT_ALT_SCREEN)
            self.stream.flush()

    def pause(self) -> None:
        """临时退出面板（用于显示交互式提示，如确认输入）。"""
        if not (self.enabled and self._active) or self._paused:
            return
        with self._lock:
            self._paused = True
            self.stream.write(_SHOW_CURSOR + _EXIT_ALT_SCREEN)
            self.stream.flush()

    def resume(self) -> None:
        """从 pause 恢复面板。"""
        if not (self.enabled and self._active) or not self._paused:
            return
        with self._lock:
            self._paused = False
            self.stream.write(_ENTER_ALT_SCREEN + _HIDE_CURSOR)
            self._draw()

    # ---- 更新 ----
    def update(
        self,
        phase: Optional[str] = None,
        current: Optional[int] = None,
        total: Optional[int] = None,
        counters: Optional[Dict[str, int]] = None,
    ) -> None:
        """更新面板内容并重绘一次。阶段变化时自动重置进度。"""
        with self._lock:
            if phase is not None and phase != self._phase:
                self._phase = phase
                self._current = current if current is not None else 0
                self._total = total if total is not None else None
            else:
                if phase is not None:
                    self._phase = phase
                if current is not None:
                    self._current = current
                if total is not None:
                    self._total = total
            if counters is not None:
                self._counters = dict(counters)
            self._body = None
            self._footer = ""
            self._touch()
        self._redraw_now()

    def log(self, message: str, level: str = "INFO") -> None:
        """追加一条活动日志并在面板内显示（不再滚动到屏幕）。"""
        with self._lock:
            self._activity.append((message, level))
            self._touch()
        self._redraw_now()

    def _redraw_now(self) -> None:
        if not self.active:
            return
        with self._lock:
            self._draw()

    def _tick(self) -> None:
        """后台定时刷新，使 spinner 持续转动。"""
        while self._active:
            time.sleep(0.12)
            if not self.active:
                continue
            try:
                with self._lock:
                    self._draw()
            except Exception:
                return

    # ---- 视图与交互 ----
    def set_body(self, lines: Optional[Sequence[str]], footer: Optional[str] = None) -> None:
        """切换到自定义视图（菜单 / 表单 / 结果）；传 None 回到默认进度视图。"""
        with self._lock:
            self._body = None if lines is None else [str(line) for line in lines]
            if footer is not None:
                self._footer = footer
            self._touch()
        self._redraw_now()

    def set_footer(self, text: str) -> None:
        """设置 / 清除底部提示行。"""
        with self._lock:
            self._footer = text
            self._touch()
        self._redraw_now()

    def set_step(self, step: int) -> None:
        """高亮步骤指示器中的某一步（负数表示不显示）。"""
        with self._lock:
            self._step = step
            self._touch()
        self._redraw_now()

    def set_context(self, context: str) -> None:
        """更新顶部「配置」行内容。"""
        with self._lock:
            self.context = context
            self._touch()
        self._redraw_now()

    def ensure_visible(self, seconds: Optional[float] = None) -> None:
        """确保当前内容至少再停留指定秒数（默认 min_dwell），避免界面一闪而过。"""
        if not self.enabled:
            return
        dwell = self.min_dwell if seconds is None else seconds
        remaining = dwell - (time.monotonic() - self._last_content_change)
        if remaining > 0:
            time.sleep(remaining)

    def hold(self, hint: str = "按任意键继续 …") -> Optional[str]:
        """原地停留并等待任意按键，使界面稳定展示（非交互环境立即返回 None）。"""
        if not self.active:
            return None
        with self._lock:
            self._footer = hint
            self._draw()
        return read_key()

    def read_line(self, prompt: str = "  ❯ ", initial: str = "",
                  allow_empty: bool = True) -> Optional[str]:
        """在面板内读取一行文本（Esc 或环境不可用时返回 None）。"""
        if not self.active:
            return None
        buffer: List[str] = list(initial)
        while True:
            with self._lock:
                self._footer = f"{prompt}{''.join(buffer)}"
                self._draw()
            key = read_key()
            if key is None:
                return None
            if key == "enter":
                value = "".join(buffer).strip()
                if value or allow_empty:
                    return value
            elif key == "escape":
                return None
            elif key == "backspace":
                if buffer:
                    buffer.pop()
            elif key == "space":
                buffer.append(" ")
            elif len(key) == 1 and key.isprintable():
                buffer.append(key)

    def _touch(self) -> None:
        self._last_content_change = time.monotonic()

    @property
    def activity(self) -> List[Tuple[str, str]]:
        """本次运行记录的活动日志（消息, 级别），供结果视图复用。"""
        with self._lock:
            return list(self._activity)

    def _step_line(self, cols: int) -> str:
        steps = self._steps
        if not steps:
            return ""
        plain = "  " + " › ".join(steps)
        if display_width(plain) > cols:
            current = steps[self._step] if 0 <= self._step < len(steps) else ""
            return "  " + style(
                f"步骤 {self._step + 1}/{len(steps)}: {current}", "cyan", enabled=self._color
            )
        parts: List[str] = []
        for index, name in enumerate(steps):
            if index == self._step:
                parts.append(style(f"● {name}", "bold", "cyan", enabled=self._color))
            elif 0 <= index < self._step:
                parts.append(style(f"✓ {name}", "green", enabled=self._color))
            else:
                parts.append(style(f"○ {name}", "dim", enabled=self._color))
        return "  " + style(" › ", "dim", enabled=self._color).join(parts)

    # ---- 渲染 ----
    def _title_lines(self, cols: int) -> List[str]:
        box_width = min(cols - 1, 62)
        inner = box_width - 2
        spaced = " ".join(self.title.upper())
        lines = [style("╔" + "═" * inner + "╗", "cyan", enabled=self._color)]
        lines.append(
            style("║" + pad(spaced, inner, "center") + "║", "bold", "cyan", enabled=self._color)
        )
        if self.subtitle:
            lines.append(
                style("║" + pad(self.subtitle, inner, "center") + "║", "cyan", enabled=self._color)
            )
        lines.append(style("╚" + "═" * inner + "╝", "cyan", enabled=self._color))
        return lines

    def _field(self, label: str, value: str, cols: int) -> str:
        prefix = "  " + pad(label, 6)
        return prefix + _fit(value, max(10, cols - display_width(prefix) - 1))

    def _activity_line(self, text: str, level: str, cols: int) -> str:
        body = _fit(text, max(4, cols - 6))
        if level in ("ERROR", "CRITICAL"):
            return style(f"    {ICONS['error']} {body}", "red", enabled=self._color)
        if level == "WARNING":
            return style(f"    {ICONS['warn']} {body}", "yellow", enabled=self._color)
        if level == "DEBUG":
            return style(f"    {body}", "dim", enabled=self._color)
        return f"    {ICONS['move']} {body}"

    def _render(self) -> List[str]:
        cols = max(40, terminal_width())
        rows = max(10, terminal_height() - 1)
        self._frame += 1
        spin = _SPINNER[(self._frame - 1) % len(_SPINNER)]

        lines: List[str] = []
        if rows >= 16:
            lines.extend(self._title_lines(cols))
            lines.append("")

        if self._steps:
            lines.append(self._step_line(cols))
            lines.append("")

        if self._body is not None:
            lines.extend(self._body)
        else:
            phase = self._phase or "准备中"
            lines.append(self._field("阶段", f"{spin} {phase}", cols))
            if self._total:
                bar = _progress_bar(self._current, self._total, max(10, cols - 24))
            else:
                bar = "—"
            lines.append(self._field("进度", bar, cols))
            counters = "   ".join(f"{key} {value}" for key, value in self._counters.items())
            lines.append(self._field("统计", counters or "—", cols))
            if self.context:
                lines.append(self._field("配置", self.context, cols))
            lines.append("")

            header = f"{ICONS['info']} 最近操作 "
            tail = max(0, cols - display_width(header) - 3)
            lines.append("  " + style(header + "─" * tail, "gray", enabled=self._color))

            remaining = rows - len(lines) - (2 if self._footer else 0)
            if remaining > 0:
                for text, level in list(self._activity)[-remaining:]:
                    lines.append(self._activity_line(text, level, cols))
            elif remaining <= 0:
                lines.append(style("    （窗口过小，已省略日志区）", "dim", enabled=self._color))

        if self._footer:
            lines.append("")
            lines.append(
                "  " + style(_fit(self._footer, max(4, cols - 2)), "dim", enabled=self._color)
            )
        return lines[:rows]

    def _draw(self) -> None:
        """原地重绘整屏（需持有锁）。"""
        out = [_CURSOR_HOME]
        for line in self._render():
            out.append(line + _CLEAR_TO_EOL + "\r\n")
        out.append(_CLEAR_BELOW)
        self.stream.write("".join(out))
        self.stream.flush()


# =============================================================================
# 键盘输入与方向键菜单
# =============================================================================


def read_key() -> Optional[str]:
    """读取单个按键。

    Returns:
        'up' / 'down' / 'left' / 'right' / 'enter' / 'escape'，或普通字符；
        非交互式终端或无法读取时返回 None。
    """
    if not _is_tty(sys.stdin):
        return None

    if os.name == "nt":
        try:
            import msvcrt
        except ImportError:
            return None
        try:
            char = msvcrt.getwch()
        except Exception:
            return None
        if char in ("\x00", "\xe0"):  # 功能键前缀
            return {"H": "up", "P": "down", "K": "left", "M": "right"}.get(msvcrt.getwch())
        if char in ("\r", "\n"):
            return "enter"
        if char in ("\x08", "\x7f"):
            return "backspace"
        if char == " ":
            return "space"
        if char == "\x1b":
            return "escape"
        if char == "\x03":
            raise KeyboardInterrupt
        return char

    try:
        import select as _select
        import termios
        import tty
    except ImportError:
        return None
    try:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)  # type: ignore[attr-defined]
    except Exception:
        return None
    try:
        tty.setraw(fd)  # type: ignore[attr-defined]
        char = sys.stdin.read(1)
        if char == "\x1b":
            ready, _, _ = _select.select([fd], [], [], 0.05)
            if not ready:
                return "escape"
            if sys.stdin.read(1) == "[":
                return {"A": "up", "B": "down", "C": "right", "D": "left"}.get(sys.stdin.read(1))
            return "escape"
        if char in ("\r", "\n"):
            return "enter"
        if char in ("\x08", "\x7f"):
            return "backspace"
        if char == " ":
            return "space"
        if char == "\x03":
            raise KeyboardInterrupt
        return char
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)  # type: ignore[attr-defined]


def menu_select(
    options: Sequence[Tuple[str, str]],
    default_index: int = 0,
    stream=None,
    enabled: Optional[bool] = None,
) -> Optional[int]:
    """方向键选择菜单（↑/↓ 移动、Enter 确认、Esc 取消）。

    Args:
        options: (label, description) 列表。
        default_index: 默认高亮项索引。

    Returns:
        选中索引；用户取消或环境不支持交互时返回 None（调用方应退化到数字输入）。
    """
    stream = stream if stream is not None else sys.stdout
    if enabled is None:
        enabled = animation_enabled(stream) and _is_tty(sys.stdin)
    if not enabled or not options:
        return None

    index = max(0, min(default_index, len(options) - 1))
    color = should_use_color(stream)
    height = 0

    def render_lines() -> List[str]:
        lines: List[str] = []
        for position, (label, description) in enumerate(options):
            marker = "❯" if position == index else " "
            text = f"  {marker} {label}"
            lines.append(
                style(text, "bold", "cyan", enabled=color) if position == index else text
            )
            if description:
                lines.append("     " + style(description, "dim", enabled=color))
        return lines

    def draw() -> None:
        nonlocal height
        lines = render_lines()
        out: List[str] = []
        if height:
            out.append(f"\033[{height}A")
        for offset in range(max(height, len(lines))):
            out.append("\r\033[2K")
            if offset < len(lines):
                out.append(lines[offset])
            out.append("\n")
        if height > len(lines):
            out.append(f"\033[{height - len(lines)}A")
        height = len(lines)
        stream.write("".join(out))
        stream.flush()

    def clear() -> None:
        nonlocal height
        if not height:
            return
        stream.write(f"\033[{height}A" + "\r\033[2K\n" * height + f"\033[{height}A")
        stream.flush()
        height = 0

    try:
        draw()
        while True:
            key = read_key()
            if key in ("up", "k"):
                index = (index - 1) % len(options)
                draw()
            elif key in ("down", "j"):
                index = (index + 1) % len(options)
                draw()
            elif key == "enter":
                break
            elif key in ("escape", "q", None):
                clear()
                return None
    except (KeyboardInterrupt, EOFError):
        clear()
        return None

    clear()
    stream.write("  " + style(f"已选择: {options[index][0]}", "cyan", enabled=color) + "\n")
    stream.flush()
    return index
