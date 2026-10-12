"""
统一的大屏交互外壳（Screen）。

把「启动初始化 → 配置 → 路径选择 → 执行 → 结果」整条流程收敛到同一套视觉语言：
交互式终端全程只进入一次备用屏幕（全屏面板），菜单、表单、进度、结果都在同一块
面板内完成，不再出现「启动静态输出 + 执行时全屏」的割裂。非交互环境（管道 / 重定向
/ CI / NO_COLOR / --no-animation）自动降级为等价的静态文本输出。
"""

import re
import sys
from typing import List, Optional, Sequence, Tuple

from clear_win_start import console

__all__ = ["Screen", "ScreenPrompter"]

_MENU_HINT_SINGLE = "↑/↓ 移动 · Enter 确认 · Esc 取消"
_MENU_HINT_MULTI = "↑/↓ 移动 · 空格 选择 · A 全选 · N 全不选 · Enter 确认 · Esc 取消"


def _clip(text: str, width: int) -> str:
    """按显示宽度截断（超出时以 … 结尾），保证面板内每行不换行。"""
    if console.display_width(text) <= width:
        return text
    limit = max(0, width - 1)
    result = ""
    for char in text:
        if console.display_width(result + char) > limit:
            break
        result += char
    return result + "…"


class Screen:
    """全流程统一的大屏交互外壳（交互式为全屏面板，否则静态文本）。"""

    STEPS: Sequence[str] = ("初始化", "配置", "路径选择", "执行", "结果")

    def __init__(
        self,
        title: str = "ClearWinStart",
        subtitle: str = "Windows 开始菜单整理工具",
        stream=None,
        enabled: Optional[bool] = None,
    ) -> None:
        self.stream = stream if stream is not None else sys.stdout
        self.enabled = console.animation_enabled(self.stream) if enabled is None else enabled
        self._color = console.should_use_color(self.stream)
        self.dashboard = console.Dashboard(
            title=title,
            subtitle=subtitle,
            stream=self.stream,
            enabled=self.enabled,
            steps=self.STEPS,
            min_dwell=0.7,
        )
        self._opened = False

    # ---- 尺寸 / 着色 ----
    @property
    def width(self) -> int:
        """面板可用显示宽度。"""
        return max(40, console.terminal_width() - 1)

    def line(self, text: str = "", *names: str) -> str:
        """构造一行面板文本：先按显示宽度截断，再按需着色。"""
        return console.style(_clip(text, self.width), *names, enabled=self._color)

    # ---- 生命周期 ----
    def open(self, context: str = "") -> "Screen":
        """进入大屏（一次），并定位到第一步。"""
        if context:
            self.dashboard.context = context
        self.dashboard.start()
        self._opened = True
        self.step(0)
        return self

    def close(self) -> None:
        """退出大屏，恢复终端原有内容。"""
        if self._opened:
            self.dashboard.close()
            self._opened = False

    def step(self, index: int) -> None:
        """高亮步骤指示器。"""
        self.dashboard.set_step(index)

    def set_context(self, context: str) -> None:
        """更新顶部配置行。"""
        self.dashboard.set_context(context)

    def ensure_visible(self, seconds: Optional[float] = None) -> None:
        """保证当前内容至少再停留指定秒数，避免一闪而过。"""
        self.dashboard.ensure_visible(seconds)

    def log(self, message: str, level: str = "INFO") -> None:
        """写入执行期活动日志（面板激活时显示在面板内）。"""
        self.dashboard.log(message, level)

    # ---- 展示 ----
    def show(
        self,
        lines: Sequence[str],
        footer: str = "",
        hold: bool = False,
        min_seconds: Optional[float] = None,
    ) -> None:
        """展示一段内容；hold=True 时停留到用户按键。"""
        if self.enabled:
            self.dashboard.set_body(list(lines), footer=footer)
            if hold:
                self.dashboard.hold(footer or "按任意键继续 …")
            else:
                self.dashboard.ensure_visible(min_seconds)
            return
        for line in lines:
            print(line)

    # ---- 交互 ----
    def menu(
        self,
        header: Sequence[str],
        options: Sequence[Tuple[str, str]],
        multi: bool = False,
        selected: Optional[Sequence[int]] = None,
        default_index: int = 0,
        single: bool = False,
        footer: Optional[str] = None,
        allow_empty: bool = False,
    ) -> Optional[List[int]]:
        """展示选择列表。

        Returns:
            选中项索引列表（单选为单元素）；用户取消或环境不可用时返回 None。
        """
        items = [(str(label), str(description or "")) for label, description in options]
        if not items:
            return None
        if not self.enabled:
            return self._static_menu(
                header, items, multi, selected, default_index, single, allow_empty
            )

        checked = set(selected or ())
        if single:
            checked = {default_index}
        cursor = max(0, min(default_index, len(items) - 1))
        hint = footer or (_MENU_HINT_MULTI if (multi and not single) else _MENU_HINT_SINGLE)

        while True:
            body: List[str] = list(header)
            if body:
                body.append("")
            for index, (label, description) in enumerate(items):
                pointer = "❯" if index == cursor else " "
                box = "◉" if index in checked else "○"
                text = f"  {pointer} {box} {label}"
                body.append(
                    self.line(text, "bold", "cyan") if index == cursor else self.line(text)
                )
                if description:
                    body.append(self.line(f"        {description}", "dim"))
            self.dashboard.set_body(body, footer=hint)
            key = console.read_key()
            if key is None:
                return None
            if key == "up":
                cursor = (cursor - 1) % len(items)
            elif key == "down":
                cursor = (cursor + 1) % len(items)
            elif key == "space":
                if single:
                    checked = {cursor}
                elif cursor in checked:
                    if allow_empty or len(checked) > 1:
                        checked.discard(cursor)
                else:
                    checked.add(cursor)
            elif key in ("a", "A") and multi and not single:
                checked = set(range(len(items)))
            elif key in ("n", "N") and multi and not single and allow_empty:
                checked = set()
            elif key == "enter":
                if single:
                    return [cursor]
                if not checked and not allow_empty:
                    continue
                return sorted(checked)
            elif key in ("escape", "q"):
                return None

    def yes_no(self, prompt: str, default: bool = False) -> bool:
        """大屏内 y/n 确认（Esc 采用默认值）。"""
        result = self.menu(
            [self.line("  " + prompt, "bold")],
            [("是", ""), ("否", "")],
            single=True,
            default_index=0 if default else 1,
        )
        if result is None:
            return default
        return result[0] == 0

    def text(self, header: Sequence[str], prompt: str, default: str = "") -> str:
        """大屏内单行文本输入（Esc 采用默认值）。"""
        if self.enabled:
            body = list(header)
            if body:
                body.append("")
            body.append(self.line("  " + prompt, "bold"))
            body.append("")
            self.dashboard.set_body(body, footer="直接输入 · Enter 确认 · Esc 使用默认值")
            value = self.dashboard.read_line(initial=default)
            return default if value is None else value
        for line in header:
            print(line)
        hint = "  " + prompt + (f" [{default}]" if default else "") + ": "
        try:
            raw = input(hint).strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return default
        return raw or default

    def list_input(
        self,
        header: Sequence[str],
        prompt: str,
        allow_empty: bool = True,
        initial: Optional[Sequence[str]] = None,
    ) -> List[str]:
        """大屏内多行列表输入（留空 / Esc 结束）。"""
        items: List[str] = list(initial or ())
        if self.enabled:
            while True:
                body = list(header)
                if body:
                    body.append("")
                body.append(self.line("  " + prompt, "bold"))
                body.append("")
                for item in items:
                    body.append(self.line(f"    • {item}"))
                body.append(self.line("    （留空并回车结束）", "dim"))
                self.dashboard.set_body(body, footer="输入一项后回车；留空结束 · Esc 结束")
                value = self.dashboard.read_line()
                if not value:
                    break
                items.append(value)
            return items
        for line in header:
            print(line)
        print(f"  {prompt}（每行一项，留空结束）")
        while True:
            try:
                raw = input("    - ").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                break
            if not raw:
                break
            items.append(raw)
        return items

    def paths_select(self, options: Sequence[Tuple[str, str]]) -> Optional[List[int]]:
        """面板内多选待处理路径（默认全选）。返回选中索引；取消返回 None。"""
        header = [
            self.line("  请选择要处理的路径", "bold"),
            self.line("  默认全部选中；可用空格逐项取舍", "dim"),
        ]
        return self.menu(
            header,
            options,
            multi=True,
            selected=range(len(options)),
            allow_empty=True,
        )

    # ---- 静态（非交互）降级 ----
    def _static_menu(
        self,
        header: Sequence[str],
        items: Sequence[Tuple[str, str]],
        multi: bool,
        selected: Optional[Sequence[int]],
        default_index: int,
        single: bool,
        allow_empty: bool,
    ) -> Optional[List[int]]:
        for line in header:
            print(line)
        print()
        marked = set(selected) if selected else {default_index}
        for index, (label, description) in enumerate(items, 1):
            mark = "★" if (index - 1) in marked else " "
            print(console.style(f"  {mark} [{index}] {label}", enabled=self._color))
            if description:
                print("        " + description)
        print()
        while True:
            try:
                if single:
                    raw = input("  请选择序号（回车=默认）: ").strip()
                    if not raw:
                        return [default_index]
                    if raw.isdigit() and 1 <= int(raw) <= len(items):
                        return [int(raw) - 1]
                else:
                    raw = input(
                        "  输入序号（空格/逗号分隔，a=全选，回车=默认）: "
                    ).strip().lower()
                    if not raw:
                        if selected:
                            return sorted(selected)
                        return [] if multi else [default_index]
                    if raw in ("a", "all"):
                        return list(range(len(items)))
                    picks = {
                        int(token) - 1
                        for token in re.split(r"[\s,]+", raw)
                        if token.isdigit() and 1 <= int(token) <= len(items)
                    }
                    if picks:
                        return sorted(picks)
                print("  输入无效，请重试")
            except (KeyboardInterrupt, EOFError):
                print()
                return None


class ScreenPrompter:
    """把 ``ConfigurationWizard`` 的逐项问答渲染进全屏面板。"""

    def __init__(self, screen: Screen) -> None:
        self.screen = screen

    def header(self, title: str) -> None:
        self.screen.show(
            ["", self.screen.line("  " + title, "bold", "cyan")], min_seconds=0.0
        )

    def section(self, title: str) -> None:
        self.screen.show([self.screen.line(f"  ── {title} ──", "cyan")], min_seconds=0.0)

    def note(self, text: str) -> None:
        lines = [
            self.screen.line("  " + part)
            for part in text.splitlines()
            if part.strip()
        ]
        if lines:
            self.screen.show(lines, min_seconds=0.0)

    def text(self, prompt: str, default: Optional[str] = None, required: bool = False) -> str:
        return self.screen.text([], prompt, default or "")

    def yes_no(self, prompt: str, default: bool = False) -> bool:
        return self.screen.yes_no(prompt, default)

    def list_input(self, prompt: str, allow_empty: bool = True) -> List[str]:
        return self.screen.list_input([], prompt, allow_empty)
