"""
终端渲染工具与预览报告的单元测试。

覆盖 console 的显示宽度对齐、颜色门控、表格宽度自适应、全屏面板、动画开关、
方向键菜单（键盘打桩）、面板感知日志 Handler，以及 create_preview_from_plan。
"""

import io
import logging

from clear_win_start import console, logging_setup
from clear_win_start.cli import ImpactLevel, PreviewWindow, create_preview_from_plan


# =============================================================================
# 显示宽度与对齐
# =============================================================================


class TestDisplayWidth:
    """测试按终端显示宽度计算（CJK 占 2 列）。"""

    def test_ascii(self):
        assert console.display_width("abc") == 3

    def test_chinese(self):
        assert console.display_width("已处理") == 6

    def test_mixed(self):
        assert console.display_width("已处理 a") == 8

    def test_variation_selector_is_zero_width(self):
        """变体选择符不计入宽度"""
        assert console.display_width("⚠\ufe0f") == console.display_width("⚠")

    def test_empty(self):
        assert console.display_width("") == 0


class TestPad:
    """测试填充对齐。"""

    def test_left_align_chinese(self):
        assert console.pad("已处理", 8) == "已处理  "

    def test_right_align_chinese(self):
        assert console.pad("已处理", 8, "right") == "  已处理"

    def test_never_truncates(self):
        assert console.pad("abc", 1) == "abc"


class TestTruncate:
    """测试按显示宽度截断。"""

    def test_short_text_unchanged(self):
        assert PreviewWindow.truncate("abc", 10) == "abc"

    def test_cjk_truncate_within_limit(self):
        result = PreviewWindow.truncate("已处理文件夹", 6)
        assert console.display_width(result) <= 6
        assert result.endswith("...")


# =============================================================================
# 颜色门控
# =============================================================================


class TestColorGating:
    """测试 NO_COLOR / FORCE_COLOR / 非 TTY 的颜色降级。"""

    def test_no_color_env_disables(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        assert console.should_use_color(io.StringIO()) is False
        assert console.style("x", "red", enabled=False) == "x"

    def test_force_color_enables(self, monkeypatch):
        monkeypatch.setenv("FORCE_COLOR", "1")
        monkeypatch.delenv("NO_COLOR", raising=False)
        assert console.should_use_color(io.StringIO()) is True
        assert "\033[" in console.style("x", "red", enabled=True)

    def test_non_tty_disables(self, monkeypatch):
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("TERM", raising=False)
        assert console.should_use_color(io.StringIO()) is False

    def test_style_without_style_names(self):
        assert console.style("plain") == "plain"


# =============================================================================
# 表格
# =============================================================================


class TestTable:
    """测试表格渲染。"""

    def test_lines_share_same_display_width(self):
        rendered = console.table(
            ["项目", "数量"],
            [("已处理文件夹", 0), ("已移动文件", 12)],
            aligns=["left", "right"],
            enabled=False,
        )
        widths = {console.display_width(line) for line in rendered.splitlines()}
        assert len(widths) == 1

    def test_content_present(self):
        rendered = console.table(["A", "B"], [("1", "2")], enabled=False)
        assert "A" in rendered
        assert "─" in rendered
        assert "1" in rendered

    def test_max_width_fits_terminal(self):
        """超过 max_width 时压缩并截断，不再溢出。"""
        rendered = console.table(
            ["项目", "值"],
            [("a", "x" * 100)],
            aligns=["left", "left"],
            max_width=40,
            enabled=False,
        )
        assert all(console.display_width(line) <= 40 for line in rendered.splitlines())


class TestTerminalWidth:
    def test_positive(self):
        assert console.terminal_width() > 0


# =============================================================================
# 动画开关
# =============================================================================


class TestAnimationSwitch:
    """测试动态效果的启用条件。"""

    def test_disabled_flag_wins(self):
        console.set_animation_enabled(False)
        try:
            assert console.animation_enabled(io.StringIO()) is False
        finally:
            console.set_animation_enabled(True)

    def test_non_tty_disabled(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("TERM", raising=False)
        console.set_animation_enabled(True)
        assert console.animation_enabled(io.StringIO()) is False

    def test_no_color_env_disables(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        console.set_animation_enabled(True)
        assert console.animation_enabled(io.StringIO()) is False


# =============================================================================
# 全屏面板
# =============================================================================


class TestDashboard:
    """测试全屏面板（非交互时静默）。"""

    def test_disabled_is_noop(self):
        stream = io.StringIO()
        dashboard = console.Dashboard(stream=stream, enabled=False)
        dashboard.start()
        dashboard.update(phase="整理文件", current=1, total=2, counters={"移动": 1})
        dashboard.log("hello")
        dashboard.close()
        assert stream.getvalue() == ""

    def test_enabled_renders_phase_progress_counters(self):
        stream = io.StringIO()
        dashboard = console.Dashboard(stream=stream, enabled=True)
        try:
            dashboard.start()
            dashboard.update(phase="整理文件", current=1, total=2, counters={"移动": 1})
        finally:
            dashboard.close()
        output = stream.getvalue()
        assert "整理文件" in output
        assert "1/2" in output
        assert "移动 1" in output

    def test_title_is_spaced_heading(self):
        """项目名渲染为顶部大标题（字符间加空格）。"""
        dashboard = console.Dashboard(stream=io.StringIO(), enabled=True)
        lines = dashboard._title_lines(80)
        assert any("C L E A R W I N S T A R T" in line for line in lines)

    def test_log_is_shown_in_panel(self):
        stream = io.StringIO()
        dashboard = console.Dashboard(stream=stream, enabled=True)
        try:
            dashboard.start()
            dashboard.log("已备份 3 个快捷方式", "INFO")
        finally:
            dashboard.close()
        assert "已备份 3 个快捷方式" in stream.getvalue()

    def test_phase_change_resets_progress(self):
        stream = io.StringIO()
        dashboard = console.Dashboard(stream=stream, enabled=True)
        try:
            dashboard.start()
            dashboard.update(phase="A", current=5, total=10)
            dashboard.update(phase="B")
            assert dashboard._total is None
        finally:
            dashboard.close()

    def test_start_registers_active_dashboard(self):
        stream = io.StringIO()
        dashboard = console.Dashboard(stream=stream, enabled=True)
        try:
            dashboard.start()
            assert console.get_active_dashboard() is dashboard
        finally:
            dashboard.close()
        assert console.get_active_dashboard() is None

    def test_pause_resume_toggles_active(self):
        stream = io.StringIO()
        dashboard = console.Dashboard(stream=stream, enabled=True)
        try:
            dashboard.start()
            assert dashboard.active is True
            dashboard.pause()
            assert dashboard.active is False
            dashboard.resume()
            assert dashboard.active is True
        finally:
            dashboard.close()


# =============================================================================
# 方向键菜单（键盘打桩）
# =============================================================================


class TestMenuSelect:
    """测试菜单选择逻辑（不依赖真实终端）。"""

    def test_returns_none_for_empty_options(self):
        assert console.menu_select([], enabled=True) is None

    def test_returns_none_when_unavailable(self, monkeypatch):
        """read_key 不可用（非 TTY）时返回 None，供调用方退化。"""
        monkeypatch.setattr(console, "read_key", lambda: None)
        assert (
            console.menu_select([("A", ""), ("B", "")], stream=io.StringIO(), enabled=True) is None
        )

    def test_moves_and_confirms(self, monkeypatch):
        keys = iter(["down", "enter"])
        monkeypatch.setattr(console, "read_key", lambda: next(keys))
        stream = io.StringIO()
        result = console.menu_select([("A", "第一项"), ("B", "第二项")], stream=stream, enabled=True)
        assert result == 1
        assert "已选择: B" in stream.getvalue()

    def test_wraps_around(self, monkeypatch):
        keys = iter(["up", "enter"])
        monkeypatch.setattr(console, "read_key", lambda: next(keys))
        stream = io.StringIO()
        result = console.menu_select([("A", ""), ("B", ""), ("C", "")], stream=stream, enabled=True)
        assert result == 2

    def test_escape_cancels(self, monkeypatch):
        monkeypatch.setattr(console, "read_key", lambda: "escape")
        stream = io.StringIO()
        assert console.menu_select([("A", "")], stream=stream, enabled=True) is None


# =============================================================================
# 面板感知日志 Handler
# =============================================================================


class _DummyDashboard:
    """记录写入日志的假面板。"""

    def __init__(self, active=True):
        self._active = active
        self.logged = []

    @property
    def active(self):
        return self._active

    def log(self, message, level="INFO"):
        self.logged.append((message, level))


class TestDashboardAwareHandler:
    """测试日志输出与全屏面板的协调。"""

    @staticmethod
    def _logger(name, handler):
        test_logger = logging.getLogger(name)
        test_logger.handlers = []
        test_logger.propagate = False
        test_logger.setLevel(logging.INFO)
        test_logger.addHandler(handler)
        return test_logger

    def test_routes_to_active_dashboard(self, monkeypatch):
        """面板激活时日志写入面板，不再滚动到流。"""
        dummy = _DummyDashboard(active=True)
        monkeypatch.setattr(console, "_active_dashboard", dummy)
        stream = io.StringIO()
        handler = logging_setup.DashboardAwareHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        test_logger = self._logger("cws.test.panel", handler)
        try:
            test_logger.info("hello")
        finally:
            test_logger.removeHandler(handler)

        assert dummy.logged == [("hello", "INFO")]
        assert "hello" not in stream.getvalue()

    def test_emits_directly_without_dashboard(self, monkeypatch):
        monkeypatch.setattr(console, "_active_dashboard", None)
        stream = io.StringIO()
        handler = logging_setup.DashboardAwareHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        test_logger = self._logger("cws.test.panel2", handler)
        try:
            test_logger.info("world")
        finally:
            test_logger.removeHandler(handler)

        assert "world" in stream.getvalue()

    def test_emits_directly_while_paused(self, monkeypatch):
        """面板暂停（等待用户输入）时日志回退到流输出。"""
        dummy = _DummyDashboard(active=False)
        monkeypatch.setattr(console, "_active_dashboard", dummy)
        stream = io.StringIO()
        handler = logging_setup.DashboardAwareHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        test_logger = self._logger("cws.test.panel3", handler)
        try:
            test_logger.info("paused")
        finally:
            test_logger.removeHandler(handler)

        assert dummy.logged == []
        assert "paused" in stream.getvalue()


# =============================================================================
# 预览报告（由 dry-run 计划生成）
# =============================================================================


class TestPreviewFromPlan:
    """测试 create_preview_from_plan（修复 --preview 空白）。"""

    @staticmethod
    def _sample_plan():
        return [
            {
                "path": r"C:\Menu",
                "folders_to_process": ["Google Chrome"],
                "files_to_move": [
                    {
                        "source": r"C:\Menu\Google Chrome\Chrome.lnk",
                        "destination": r"C:\Menu\Chrome.lnk",
                    }
                ],
                "files_to_delete": [
                    {
                        "path": r"C:\Menu\卸载微信.lnk",
                        "type": "file",
                        "reason": "包含关键词: ['卸载']",
                    }
                ],
                "shortcuts_to_validate": [],
                "shortcuts_to_dedupe": [r"C:\Menu\Chrome 副本.lnk"],
            }
        ]

    @staticmethod
    def _sample_summary():
        return {
            "total_folders": 1,
            "total_files_to_move": 1,
            "total_files_to_delete": 1,
            "total_shortcuts_to_clean": 1,
            "total_shortcuts_invalid": 1,
            "total_shortcuts_duplicate": 1,
            "total_shortcuts_to_backup": 3,
            "estimated_impact": "中",
        }

    def test_builds_sections_and_impact(self):
        report = create_preview_from_plan(
            self._sample_plan(), self._sample_summary(), [r"C:\Menu"], "tester"
        )
        assert report.impact_level is ImpactLevel.MEDIUM
        assert report.total_operations > 0
        assert "backup" in report.sections

    def test_render_is_not_empty(self):
        report = create_preview_from_plan(
            self._sample_plan(), self._sample_summary(), [r"C:\Menu"], "tester"
        )
        rendered = PreviewWindow.render_preview(report)
        assert "开始菜单整理预览" in rendered
        assert "没有检测到任何操作" not in rendered
        assert "Chrome.lnk" in rendered

    def test_empty_plan_reports_no_operations(self):
        report = create_preview_from_plan([], {}, [r"C:\Menu"], "tester")
        rendered = PreviewWindow.render_preview(report)
        assert "没有检测到任何操作" in rendered
