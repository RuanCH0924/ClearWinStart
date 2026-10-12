"""
统一大屏交互层（ui.Screen / Dashboard 视图）与全流程会话的单元测试。

覆盖：
  - Screen 的静态降级（非交互环境下的菜单 / 文本 / 是-否 / 列表输入）
  - Screen 的交互行为（方向键菜单多选、键位打桩）
  - Dashboard 的自定义视图 / 步骤指示器 / 停留时长 / 面板内输入
  - _run_session 端到端跑通「初始化 → 配置 → 路径选择 → 执行 → 结果」，
    并验证全程只使用同一块全屏面板、只进入/退出备用屏各一次。
"""

import argparse
import io

import pytest

from clear_win_start import cli, console, paths, ui
from clear_win_start.config import Configuration, ConfigurationWizard
from clear_win_start.core import StartMenuOrganizer


# =============================================================================
# 辅助
# =============================================================================


class _FakeOrganizer:
    """替换 StartMenuOrganizer，避免真实扫描 / 回收站操作。"""

    def __init__(self, config):
        self.config = config
        self.organize_calls = []

    def validate_paths(self):
        return []

    def organize(self, auto_confirm=False, preview_only=False, dashboard=None):
        self.organize_calls.append(
            {"auto_confirm": auto_confirm, "preview_only": preview_only, "dashboard": dashboard}
        )
        if dashboard is not None:
            dashboard.log("演示：已移动 3 个文件")
        return dict(StartMenuOrganizer.EMPTY_STATS)

    def get_dry_run_report(self):
        return {"plan": [], "summary": dict(StartMenuOrganizer.EMPTY_SUMMARY)}


class _RecordingPrompter:
    """记录向导提问的假 prompter（用于验证用户名默认值）。"""

    def __init__(self):
        self.text_calls = []

    def header(self, title):
        pass

    def section(self, title):
        pass

    def note(self, text):
        pass

    def text(self, prompt, default=None, required=False):
        self.text_calls.append({"prompt": prompt, "default": default, "required": required})
        return default if default is not None else "fallback"

    def yes_no(self, prompt, default=False):
        return default

    def list_input(self, prompt, allow_empty=True):
        return []


def _make_args(**overrides):
    base = {"validate_only": False, "auto_confirm": False, "preview": False}
    base.update(overrides)
    return argparse.Namespace(**base)


# =============================================================================
# 静态降级（非交互环境）
# =============================================================================


class TestScreenStatic:
    def test_menu_single_select(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda prompt="": "2")
        screen = ui.Screen(stream=io.StringIO(), enabled=False)
        assert screen.menu(["  hdr"], [("A", ""), ("B", "")], single=True) == [1]

    def test_menu_multi_select_all(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda prompt="": "a")
        screen = ui.Screen(stream=io.StringIO(), enabled=False)
        result = screen.menu([], [("A", ""), ("B", ""), ("C", "")], multi=True)
        assert result == [0, 1, 2]

    def test_menu_multi_select_indices(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda prompt="": "1 3")
        screen = ui.Screen(stream=io.StringIO(), enabled=False)
        result = screen.menu([], [("A", ""), ("B", ""), ("C", "")], multi=True)
        assert result == [0, 2]

    def test_yes_no_uses_default_on_empty(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda prompt="": "")
        screen = ui.Screen(stream=io.StringIO(), enabled=False)
        assert screen.yes_no("继续？", default=True) is True
        assert screen.yes_no("继续？", default=False) is False

    def test_text_falls_back_to_default(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda prompt="": "")
        screen = ui.Screen(stream=io.StringIO(), enabled=False)
        assert screen.text([], "姓名", "bob") == "bob"

    def test_list_input_finishes_on_empty(self, monkeypatch):
        responses = iter(["a", "b", ""])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))
        screen = ui.Screen(stream=io.StringIO(), enabled=False)
        assert screen.list_input([], "输入") == ["a", "b"]


# =============================================================================
# 交互行为（键位打桩）
# =============================================================================


class TestScreenInteractive:
    def test_menu_multi_select_toggles_with_space(self, monkeypatch):
        screen = ui.Screen(stream=io.StringIO(), enabled=True)
        screen.open()
        keys = iter(["down", "space", "enter"])
        monkeypatch.setattr(console, "read_key", lambda: next(keys))
        try:
            result = screen.menu(
                ["hdr"], [("A", ""), ("B", ""), ("C", "")], multi=True, selected=range(3)
            )
        finally:
            screen.close()
        assert result == [0, 2]

    def test_menu_escape_cancels(self, monkeypatch):
        screen = ui.Screen(stream=io.StringIO(), enabled=True)
        screen.open()
        monkeypatch.setattr(console, "read_key", lambda: "escape")
        try:
            assert screen.menu([], [("A", ""), ("B", "")], multi=True) is None
        finally:
            screen.close()

    def test_text_reads_line(self, monkeypatch):
        screen = ui.Screen(stream=io.StringIO(), enabled=True)
        screen.open()
        keys = iter(["h", "i", "enter"])
        monkeypatch.setattr(console, "read_key", lambda: next(keys))
        try:
            assert screen.text([], "输入", "") == "hi"
        finally:
            screen.close()

    def test_single_alt_screen_entry_and_exit(self):
        stream = io.StringIO()
        screen = ui.Screen(stream=stream, enabled=True)
        screen.open()
        screen.show(["内容"], min_seconds=0.0)
        screen.close()
        output = stream.getvalue()
        assert output.count("\033[?1049h") == 1
        assert output.count("\033[?1049l") == 1


# =============================================================================
# Dashboard 视图 / 步骤 / 停留 / 面板内输入
# =============================================================================


class TestDashboardViews:
    def test_step_line_marks_current_only(self):
        dashboard = console.Dashboard(stream=io.StringIO(), enabled=True, steps=("A", "B", "C"))
        dashboard._step = 1
        line = dashboard._step_line(80)
        assert line.count("●") == 1
        assert "B" in line

    def test_custom_view_and_footer_rendered(self):
        stream = io.StringIO()
        dashboard = console.Dashboard(stream=stream, enabled=True)
        dashboard.start()
        try:
            dashboard.set_body(["  自定义内容一", "  自定义内容二"], footer="底部提示")
        finally:
            dashboard.close()
        output = stream.getvalue()
        assert "自定义内容一" in output
        assert "自定义内容二" in output
        assert "底部提示" in output

    def test_progress_view_resumes_after_custom_view(self):
        stream = io.StringIO()
        dashboard = console.Dashboard(stream=stream, enabled=True)
        dashboard.start()
        try:
            dashboard.set_body(["  临时视图"])
            assert dashboard._body is not None
            dashboard.update(phase="执行中", current=1, total=2)
            assert dashboard._body is None
        finally:
            dashboard.close()
        assert "执行中" in stream.getvalue()

    def test_hold_returns_none_when_disabled(self):
        dashboard = console.Dashboard(stream=io.StringIO(), enabled=False)
        assert dashboard.hold() is None

    def test_ensure_visible_sleeps_for_remaining_dwell(self, monkeypatch):
        slept = []
        monkeypatch.setattr(console.time, "sleep", lambda seconds: slept.append(seconds))
        dashboard = console.Dashboard(stream=io.StringIO(), enabled=True, min_dwell=1.0)
        dashboard._touch()
        dashboard.ensure_visible()
        assert slept and slept[0] > 0

    def test_read_line_handles_backspace(self, monkeypatch):
        dashboard = console.Dashboard(stream=io.StringIO(), enabled=True)
        dashboard.start()
        keys = iter(["a", "b", "backspace", "c", "enter"])
        monkeypatch.setattr(console, "read_key", lambda: next(keys))
        try:
            assert dashboard.read_line(initial="") == "ac"
        finally:
            dashboard.close()


# =============================================================================
# 全流程会话
# =============================================================================


class TestSessionFlow:
    def test_interactive_session_reuses_single_screen(self, monkeypatch, tmp_path):
        created = []
        real_dashboard = console.Dashboard

        class SpyDashboard(real_dashboard):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                created.append(self)

        monkeypatch.setattr(console, "Dashboard", SpyDashboard)
        fake = _FakeOrganizer(None)
        monkeypatch.setattr(cli, "StartMenuOrganizer", lambda config: fake)
        monkeypatch.setattr(console, "read_key", lambda: "enter")

        stream = io.StringIO()
        screen = ui.Screen(stream=stream, enabled=True)
        screen.open(context="测试")
        config = Configuration(user_name="tester", paths=[str(tmp_path)])
        try:
            code = cli._run_session(screen, _make_args(), config)
        finally:
            screen.close()

        assert code == 0
        assert created == [screen.dashboard]
        assert list(screen.dashboard._steps) == list(ui.Screen.STEPS)
        assert fake.organize_calls[0]["dashboard"] is screen.dashboard
        assert fake.organize_calls[0]["preview_only"] is False
        # 执行结果（含操作记录）保留在结果步骤中
        assert "操作统计" in stream.getvalue()
        assert "演示：已移动 3 个文件" in stream.getvalue()

    def test_dry_run_shows_plan_without_executing(self, monkeypatch, tmp_path):
        fake = _FakeOrganizer(None)
        monkeypatch.setattr(cli, "StartMenuOrganizer", lambda config: fake)
        monkeypatch.setattr(console, "read_key", lambda: "enter")

        screen = ui.Screen(stream=io.StringIO(), enabled=True)
        screen.open()
        config = Configuration(user_name="tester", paths=[str(tmp_path)], dry_run=True)
        try:
            code = cli._run_session(screen, _make_args(), config)
        finally:
            screen.close()

        assert code == 0
        assert [call["preview_only"] for call in fake.organize_calls] == [True]

    def test_static_session_degrades_gracefully(self, monkeypatch, tmp_path, capsys):
        fake = _FakeOrganizer(None)
        monkeypatch.setattr(cli, "StartMenuOrganizer", lambda config: fake)

        screen = ui.Screen(stream=io.StringIO(), enabled=False)
        config = Configuration(user_name="tester", paths=[str(tmp_path)])
        code = cli._run_session(screen, _make_args(auto_confirm=True), config)

        assert code == 0
        output = capsys.readouterr().out
        assert "正在初始化" in output
        assert "配置信息" in output
        assert "操作统计" in output


# =============================================================================
# 结果保留 / 用户名自动检测
# =============================================================================


class TestResultRetention:
    def test_stats_lines_include_activity_log(self):
        screen = ui.Screen(stream=io.StringIO(), enabled=False)
        lines = cli._stats_lines(
            screen,
            dict(StartMenuOrganizer.EMPTY_STATS),
            [("已移动 a.lnk", "INFO"), ("删除失败: b", "ERROR")],
        )
        text = "\n".join(lines)
        assert "操作统计" in text
        assert "本次操作记录" in text
        assert "2 条" in text
        assert "已移动 a.lnk" in text
        assert "删除失败: b" in text


class TestUsernameDetection:
    def test_username_from_profile(self, monkeypatch):
        monkeypatch.delenv("USERNAME", raising=False)
        monkeypatch.delenv("USER", raising=False)
        monkeypatch.setenv("USERPROFILE", r"C:\Users\alice")
        assert paths.get_windows_username() == "alice"

    def test_username_from_env(self, monkeypatch):
        monkeypatch.setenv("USERNAME", "bob")
        assert paths.get_windows_username() == "bob"

    def test_wizard_uses_detected_username_as_default(self):
        prompter = _RecordingPrompter()
        config = ConfigurationWizard(prompter=prompter, default_user_name="auto_user").run()
        assert config.user_name == "auto_user"
        assert prompter.text_calls[0]["default"] == "auto_user"
        assert prompter.text_calls[0]["required"] is True


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__]))
