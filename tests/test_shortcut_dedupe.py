"""
重复快捷方式（TargetPath + Arguments 均相同）清理的单元测试。

覆盖 _normalize_target、_shortcut_key、_find_duplicate_shortcuts 三个纯逻辑方法，
以及 _dedupe_shortcuts 的跨路径执行流程（通过桩替 COM 与回收站）。
测试不依赖 pywin32 / COM，但涉及 Windows 路径语义，需在 Windows 上运行。
"""

import os
import sys
import types

import pytest

import send2trash

from clear_win_start.core import StartMenuOrganizer


# =============================================================================
# _normalize_target 测试
# =============================================================================


class TestNormalizeTarget:
    """测试目标路径规范化（去重比较用的键）。"""

    def test_empty(self):
        """空字符串 → 空键"""
        assert StartMenuOrganizer._normalize_target("") == ""

    def test_none(self):
        """None → 空键"""
        assert StartMenuOrganizer._normalize_target(None) == ""

    def test_whitespace(self):
        """纯空格 → 空键"""
        assert StartMenuOrganizer._normalize_target("   ") == ""

    def test_strip_quotes(self):
        """带引号 → 去掉引号"""
        assert StartMenuOrganizer._normalize_target('"C:\\App\\a.exe"') == "c:\\app\\a.exe"

    def test_case_insensitive(self):
        """大小写不同 → 归一化为同一个键"""
        assert StartMenuOrganizer._normalize_target(
            r"C:\App\A.EXE"
        ) == StartMenuOrganizer._normalize_target(r"c:\app\a.exe")

    def test_trailing_slash_normalized(self):
        """尾部分隔符 → 规范化后一致"""
        assert StartMenuOrganizer._normalize_target(
            r"C:\App\\"
        ) == StartMenuOrganizer._normalize_target(r"C:\App")


# =============================================================================
# _find_duplicate_shortcuts 测试
# =============================================================================


class TestFindDuplicateShortcuts:
    """测试按 TargetPath + Arguments 分组的重复检测。"""

    @staticmethod
    def _info(target: str, arguments: str = "") -> dict:
        return {"target_path": target, "arguments": arguments}

    def test_no_duplicates(self):
        """目标各不相同 → 无重复"""
        mapping = {
            r"C:\Menu\chrome.lnk": self._info(r"C:\App\chrome.exe"),
            r"C:\Menu\notepad.lnk": self._info(r"C:\Windows\notepad.exe"),
        }
        assert StartMenuOrganizer._find_duplicate_shortcuts(mapping) == []

    def test_simple_duplicate(self):
        """目标与参数均相同 → 保留一个，另一个为重复"""
        mapping = {
            r"C:\Menu\chrome.lnk": self._info(r"C:\App\chrome.exe"),
            r"C:\Menu\chrome - 副本.lnk": self._info(r"C:\App\chrome.exe"),
        }
        duplicates = StartMenuOrganizer._find_duplicate_shortcuts(mapping)
        assert duplicates == [r"C:\Menu\chrome - 副本.lnk"]

    def test_relative_target_resolved_by_working_dir(self):
        """相对目标按 WorkingDirectory 解析：不同工作目录下同名相对目标不算重复"""
        mapping = {
            r"C:\Menu\a.lnk": {
                "target_path": "app.exe", "arguments": "", "working_dir": r"C:\A",
            },
            r"C:\Menu\b.lnk": {
                "target_path": "app.exe", "arguments": "", "working_dir": r"C:\B",
            },
        }
        assert StartMenuOrganizer._find_duplicate_shortcuts(mapping) == []

    def test_relative_target_same_working_dir_is_duplicate(self):
        """相对目标 + 相同工作目录 → 解析后与绝对目标一致，视为重复"""
        mapping = {
            r"C:\Menu\a.lnk": {
                "target_path": "app.exe", "arguments": "", "working_dir": r"C:\A",
            },
            r"C:\Menu\b.lnk": {
                "target_path": r"C:\A\app.exe", "arguments": "", "working_dir": r"C:\A",
            },
        }
        assert StartMenuOrganizer._find_duplicate_shortcuts(mapping) == [r"C:\Menu\b.lnk"]

    def test_keeps_first_alphabetically(self):
        """同组内文件名长度相同 → 保留名称排序最靠前者"""
        mapping = {
            r"C:\Menu\b_chrome.lnk": self._info(r"C:\App\chrome.exe"),
            r"C:\Menu\a_chrome.lnk": self._info(r"C:\App\chrome.exe"),
        }
        # 两者长度相同，a_chrome 排序在前，被保留；b_chrome 为重复
        assert StartMenuOrganizer._find_duplicate_shortcuts(mapping) == [r"C:\Menu\b_chrome.lnk"]

    def test_case_and_quote_insensitive(self):
        """目标大小写与引号差异不构成新目标 → 视为重复"""
        mapping = {
            r"C:\Menu\chrome.lnk": self._info(r"C:\App\chrome.exe"),
            r"C:\Menu\chrome2.lnk": self._info(r'"C:\APP\CHROME.EXE"'),
        }
        assert StartMenuOrganizer._find_duplicate_shortcuts(mapping) == [r"C:\Menu\chrome2.lnk"]

    def test_different_arguments_not_duplicate(self):
        """目标相同但启动参数不同 → 不视为重复"""
        mapping = {
            r"C:\Menu\chrome_work.lnk": self._info(
                r"C:\App\chrome.exe", '--profile-directory="Work"'
            ),
            r"C:\Menu\chrome_personal.lnk": self._info(
                r"C:\App\chrome.exe", '--profile-directory="Personal"'
            ),
        }
        assert StartMenuOrganizer._find_duplicate_shortcuts(mapping) == []

    def test_same_target_and_arguments_duplicate(self):
        """目标与启动参数均相同 → 视为重复"""
        mapping = {
            r"C:\Menu\chrome.lnk": self._info(r"C:\App\chrome.exe", "--incognito"),
            r"C:\Menu\chrome_copy.lnk": self._info(r"C:\App\chrome.exe", "--incognito"),
        }
        assert StartMenuOrganizer._find_duplicate_shortcuts(mapping) == [r"C:\Menu\chrome_copy.lnk"]

    def test_arguments_whitespace_ignored(self):
        """参数首尾空白差异 → 视为相同"""
        mapping = {
            r"C:\Menu\a.lnk": self._info(r"C:\App\chrome.exe", "--incognito"),
            r"C:\Menu\b.lnk": self._info(r"C:\App\chrome.exe", "  --incognito  "),
        }
        assert StartMenuOrganizer._find_duplicate_shortcuts(mapping) == [r"C:\Menu\b.lnk"]

    def test_empty_targets_ignored(self):
        """目标为空（读取失败/UWP）→ 不参与去重"""
        mapping = {
            r"C:\Menu\uwp1.lnk": self._info(""),
            r"C:\Menu\uwp2.lnk": self._info("", ""),
            r"C:\Menu\uwp3.lnk": self._info("   "),
        }
        assert StartMenuOrganizer._find_duplicate_shortcuts(mapping) == []

    def test_empty_info_dict_ignored(self):
        """空信息字典（读取失败）→ 不参与去重"""
        mapping = {
            r"C:\Menu\broken1.lnk": {},
            r"C:\Menu\broken2.lnk": {},
        }
        assert StartMenuOrganizer._find_duplicate_shortcuts(mapping) == []

    def test_three_way_duplicate(self):
        """三个目标与参数均相同 → 只保留一个，另两个为重复"""
        mapping = {
            r"C:\Menu\a.lnk": self._info(r"C:\App\chrome.exe"),
            r"C:\Menu\b.lnk": self._info(r"C:\App\chrome.exe"),
            r"C:\Menu\c.lnk": self._info(r"C:\App\chrome.exe"),
        }
        assert StartMenuOrganizer._find_duplicate_shortcuts(mapping) == [
            r"C:\Menu\b.lnk",
            r"C:\Menu\c.lnk",
        ]


# =============================================================================
# _dedupe_shortcuts 流程测试
# =============================================================================


@pytest.fixture
def fake_pywin32(monkeypatch):
    """注入假的 win32com.client 模块，绕过 pywin32 依赖。"""
    module = types.ModuleType("win32com.client")
    module.Dispatch = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    package = types.ModuleType("win32com")
    package.client = module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "win32com", package)
    monkeypatch.setitem(sys.modules, "win32com.client", module)


class TestDedupeShortcuts:
    """测试 _dedupe_shortcuts 的完整执行流程。"""

    def test_removes_duplicates_to_trash(self, tmp_path, monkeypatch, fake_pywin32):
        """目标与参数一致的重复快捷方式被移入回收站，保留项不受影响。"""
        infos = {
            "chrome.lnk": {"target_path": r"C:\App\chrome.exe", "arguments": ""},
            "chrome_copy.lnk": {"target_path": r"C:\App\chrome.exe", "arguments": ""},
            "chrome_dup.lnk": {"target_path": r'"C:\APP\CHROME.EXE"', "arguments": ""},
            "notepad.lnk": {"target_path": r"C:\Windows\notepad.exe", "arguments": ""},
        }
        for name in infos:
            (tmp_path / name).write_bytes(b"fake")

        monkeypatch.setattr(
            StartMenuOrganizer,
            "_read_shortcut",
            staticmethod(lambda p, _i=infos: _i[os.path.basename(p)]),
        )

        trashed = []
        monkeypatch.setattr(send2trash, "send2trash", lambda p: trashed.append(p))

        organizer = StartMenuOrganizer()
        organizer._dedupe_shortcuts([str(tmp_path)])

        assert {os.path.basename(p) for p in trashed} == {"chrome_copy.lnk", "chrome_dup.lnk"}
        assert organizer.stats["shortcuts_deduped"] == 2

    def test_different_arguments_kept(self, tmp_path, monkeypatch, fake_pywin32):
        """目标相同但启动参数不同 → 两者都保留。"""
        infos = {
            "chrome_work.lnk": {
                "target_path": r"C:\App\chrome.exe",
                "arguments": '--profile-directory="Work"',
            },
            "chrome_personal.lnk": {
                "target_path": r"C:\App\chrome.exe",
                "arguments": '--profile-directory="Personal"',
            },
        }
        for name in infos:
            (tmp_path / name).write_bytes(b"fake")

        monkeypatch.setattr(
            StartMenuOrganizer,
            "_read_shortcut",
            staticmethod(lambda p, _i=infos: _i[os.path.basename(p)]),
        )

        trashed = []
        monkeypatch.setattr(send2trash, "send2trash", lambda p: trashed.append(p))

        organizer = StartMenuOrganizer()
        organizer._dedupe_shortcuts([str(tmp_path)])

        assert trashed == []
        assert organizer.stats["shortcuts_deduped"] == 0

    def test_dedupes_across_paths(self, tmp_path, monkeypatch, fake_pywin32):
        """跨目录：不同路径下指向同一目标+参数的快捷方式视为重复。"""
        user_dir = tmp_path / "User"
        system_dir = tmp_path / "System"
        user_dir.mkdir()
        system_dir.mkdir()
        user_link = user_dir / "Chrome.lnk"
        system_link = system_dir / "Chrome.lnk"
        user_link.write_bytes(b"fake")
        system_link.write_bytes(b"fake")

        infos = {
            str(user_link): {"target_path": r"C:\App\chrome.exe", "arguments": ""},
            str(system_link): {"target_path": r"C:\App\chrome.exe", "arguments": ""},
        }
        monkeypatch.setattr(
            StartMenuOrganizer, "_read_shortcut", staticmethod(lambda p, _i=infos: _i[p])
        )

        trashed = []
        monkeypatch.setattr(send2trash, "send2trash", lambda p: trashed.append(p))

        organizer = StartMenuOrganizer()
        removed = organizer._dedupe_shortcuts([str(user_dir), str(system_dir)])

        assert removed == 1
        assert len(trashed) == 1

    def test_no_duplicates_no_action(self, tmp_path, monkeypatch, fake_pywin32):
        """无重复时不触发任何删除。"""
        infos = {
            "chrome.lnk": {"target_path": r"C:\App\chrome.exe", "arguments": ""},
            "notepad.lnk": {"target_path": r"C:\Windows\notepad.exe", "arguments": ""},
        }
        for name in infos:
            (tmp_path / name).write_bytes(b"fake")

        monkeypatch.setattr(
            StartMenuOrganizer,
            "_read_shortcut",
            staticmethod(lambda p, _i=infos: _i[os.path.basename(p)]),
        )

        trashed = []
        monkeypatch.setattr(send2trash, "send2trash", lambda p: trashed.append(p))

        organizer = StartMenuOrganizer()
        organizer._dedupe_shortcuts([str(tmp_path)])

        assert trashed == []
        assert organizer.stats["shortcuts_deduped"] == 0

    def test_read_error_ignored(self, tmp_path, monkeypatch, fake_pywin32):
        """读取失败的快捷方式被忽略，不参与去重。"""
        names = ["broken1.lnk", "broken2.lnk"]
        for name in names:
            (tmp_path / name).write_bytes(b"fake")

        monkeypatch.setattr(
            StartMenuOrganizer,
            "_read_shortcut",
            staticmethod(lambda p: {"error": "COM failure"}),
        )

        trashed = []
        monkeypatch.setattr(send2trash, "send2trash", lambda p: trashed.append(p))

        organizer = StartMenuOrganizer()
        organizer._dedupe_shortcuts([str(tmp_path)])

        assert trashed == []
