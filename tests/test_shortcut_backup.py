"""
快捷方式备份功能的单元测试。

覆盖 _iter_shortcut_files、_backup_label、_backup_shortcuts 以及默认备份目录
get_default_backup_dir。测试不依赖 pywin32 / COM，可在任何系统上运行。
"""

import os

from clear_win_start import paths
from clear_win_start.config import Configuration
from clear_win_start.core import StartMenuOrganizer
from clear_win_start.paths import get_default_backup_dir


def _make_organizer(tmp_path, backup_dir=None):
    config = Configuration(
        user_name="tester",
        backup_shortcuts=True,
        backup_dir=str(backup_dir if backup_dir is not None else tmp_path / "backup"),
    )
    return StartMenuOrganizer(config)


# =============================================================================
# _iter_shortcut_files 测试
# =============================================================================


class TestIterShortcutFiles:
    """测试快捷方式文件递归收集。"""

    def test_collects_lnk_and_url_recursively(self, tmp_path):
        """递归收集 .lnk / .url，忽略其他文件"""
        (tmp_path / "Chrome.lnk").write_bytes(b"x")
        (tmp_path / "Site.url").write_bytes(b"x")
        (tmp_path / "readme.txt").write_bytes(b"x")
        sub = tmp_path / "Google Chrome"
        sub.mkdir()
        (sub / "Chrome.lnk").write_bytes(b"x")

        found = set(StartMenuOrganizer._iter_shortcut_files(str(tmp_path)))
        assert found == {
            str(tmp_path / "Chrome.lnk"),
            str(tmp_path / "Site.url"),
            str(sub / "Chrome.lnk"),
        }

    def test_empty_dir(self, tmp_path):
        """空目录 → 无结果"""
        assert list(StartMenuOrganizer._iter_shortcut_files(str(tmp_path))) == []


# =============================================================================
# _backup_label 测试
# =============================================================================


class TestBackupLabel:
    """测试备份子目录命名。"""

    def test_programdata_is_system(self):
        """系统开始菜单 → System"""
        path = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"
        assert StartMenuOrganizer._backup_label(path) == "System"

    def test_appdata_is_user(self):
        """用户开始菜单 → User"""
        path = r"C:\Users\me\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"
        assert StartMenuOrganizer._backup_label(path) == "User"

    def test_other_path_uses_sanitized_basename(self):
        """其他路径 → 使用目录名并清理非法字符"""
        assert StartMenuOrganizer._backup_label(r"D:\My:Menu\Programs") == "Programs"


# =============================================================================
# _backup_shortcuts 测试
# =============================================================================


class TestBackupShortcuts:
    """测试快捷方式备份执行流程。"""

    @staticmethod
    def _build_menu(tmp_path):
        menu = tmp_path / "menu"
        menu.mkdir()
        (menu / "Chrome.lnk").write_bytes(b"chrome")
        (menu / "Site.url").write_bytes(b"url")
        (menu / "readme.txt").write_bytes(b"text")
        sub = menu / "Google Chrome"
        sub.mkdir()
        (sub / "Chrome.lnk").write_bytes(b"chrome-nested")
        return menu

    def test_backs_up_all_shortcuts_preserving_structure(self, tmp_path):
        """所有快捷方式按原目录结构复制，普通文件不备份"""
        menu = self._build_menu(tmp_path)
        organizer = _make_organizer(tmp_path)

        count = organizer._backup_shortcuts(str(menu))

        assert count == 3
        assert organizer.stats["shortcuts_backed_up"] == 3

        dest_root = os.path.join(organizer._backup_run_dir, "menu")
        assert os.path.isfile(os.path.join(dest_root, "Chrome.lnk"))
        assert os.path.isfile(os.path.join(dest_root, "Site.url"))
        assert os.path.isfile(os.path.join(dest_root, "Google Chrome", "Chrome.lnk"))
        assert not os.path.exists(os.path.join(dest_root, "readme.txt"))

    def test_backup_uses_configured_dir(self, tmp_path):
        """备份目录位于配置指定的目录下"""
        menu = self._build_menu(tmp_path)
        organizer = _make_organizer(tmp_path)

        organizer._backup_shortcuts(str(menu))

        assert organizer._backup_run_dir.startswith(str(tmp_path / "backup"))

    def test_backup_content_matches_source(self, tmp_path):
        """备份文件内容与源文件一致"""
        menu = self._build_menu(tmp_path)
        organizer = _make_organizer(tmp_path)

        organizer._backup_shortcuts(str(menu))

        dest = os.path.join(organizer._backup_run_dir, "menu", "Chrome.lnk")
        with open(dest, "rb") as f:
            assert f.read() == b"chrome"

    def test_same_run_reuses_single_backup_dir(self, tmp_path):
        """同一组织器多次备份复用同一个时间戳目录"""
        first = tmp_path / "root1"
        first.mkdir()
        (first / "A.lnk").write_bytes(b"a")
        second = tmp_path / "root2"
        second.mkdir()
        (second / "B.lnk").write_bytes(b"b")

        organizer = _make_organizer(tmp_path)
        organizer._backup_shortcuts(str(first))
        run_dir = organizer._backup_run_dir
        organizer._backup_shortcuts(str(second))

        assert organizer._backup_run_dir == run_dir
        assert os.path.isfile(os.path.join(run_dir, "root2", "B.lnk"))

    def test_no_shortcuts_returns_zero(self, tmp_path):
        """无快捷方式 → 返回 0"""
        menu = tmp_path / "menu"
        menu.mkdir()
        (menu / "readme.txt").write_bytes(b"text")
        organizer = _make_organizer(tmp_path)

        assert organizer._backup_shortcuts(str(menu)) == 0
        assert organizer.stats["shortcuts_backed_up"] == 0

    def test_backup_dir_inside_menu_not_recursively_copied(self, tmp_path):
        """备份目录位于待备份路径内时，不会递归复制备份内容"""
        menu = tmp_path / "menu"
        menu.mkdir()
        (menu / "A.lnk").write_bytes(b"a")
        backup_dir = menu / "backup"  # 故意放在菜单目录内

        organizer = _make_organizer(tmp_path, backup_dir=backup_dir)
        count = organizer._backup_shortcuts(str(menu))

        assert count == 1
        assert organizer.stats["shortcuts_backed_up"] == 1


# =============================================================================
# get_default_backup_dir 测试
# =============================================================================


class TestDesktopDir:
    """测试用户实际桌面目录的探测与回退。"""

    def test_prefers_resolved_desktop(self, monkeypatch, tmp_path):
        """优先使用 SHGetKnownFolderPath 解析出的桌面（如 OneDrive 重定向）"""
        redirected = tmp_path / "OneDrive" / "Desktop"
        redirected.mkdir(parents=True)
        monkeypatch.setattr(paths, "_desktop_from_known_folder", lambda: str(redirected))
        monkeypatch.setattr(paths, "_desktop_from_registry", lambda: r"C:\Other\Desktop")
        assert paths.get_desktop_dir() == str(redirected)

    def test_falls_back_to_registry(self, monkeypatch, tmp_path):
        """已知文件夹不可用时回退注册表值"""
        registry_desktop = tmp_path / "RegDesktop"
        registry_desktop.mkdir()
        monkeypatch.setattr(paths, "_desktop_from_known_folder", lambda: None)
        monkeypatch.setattr(paths, "_desktop_from_registry", lambda: str(registry_desktop))
        assert paths.get_desktop_dir() == str(registry_desktop)

    def test_ignores_nonexistent_resolved_path(self, monkeypatch, tmp_path):
        """解析出的目录不存在 → 继续回退到 USERPROFILE\\Desktop"""
        monkeypatch.setattr(paths, "_desktop_from_known_folder", lambda: str(tmp_path / "nope"))
        monkeypatch.setattr(paths, "_desktop_from_registry", lambda: None)
        monkeypatch.setenv("USERPROFILE", r"C:\Users\somebody")
        assert paths.get_desktop_dir() == r"C:\Users\somebody\Desktop"

    def test_known_folder_resolver_returns_existing_dir_on_windows(self):
        """Windows 上 SHGetKnownFolderPath 应返回一个存在的目录"""
        if os.name != "nt":
            return
        resolved = paths._desktop_from_known_folder()
        assert resolved and os.path.isdir(resolved)


class TestDefaultBackupDir:
    """测试默认备份目录（桌面文件夹）。"""

    def test_backup_dir_is_under_desktop(self):
        """默认目录位于当前桌面目录下的 ClearWinStart_Backup"""
        backup_dir = get_default_backup_dir()
        assert os.path.basename(backup_dir) == "ClearWinStart_Backup"
        assert os.path.dirname(backup_dir) == paths.get_desktop_dir()

    def test_backup_dir_follows_userprofile_fallback(self, monkeypatch):
        """无重定向时，备份目录位于 %USERPROFILE%\\Desktop"""
        monkeypatch.setattr(paths, "_desktop_from_known_folder", lambda: None)
        monkeypatch.setattr(paths, "_desktop_from_registry", lambda: None)
        monkeypatch.setenv("USERPROFILE", r"C:\Users\somebody")
        assert get_default_backup_dir() == os.path.join(
            r"C:\Users\somebody", "Desktop", "ClearWinStart_Backup"
        )
