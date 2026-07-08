"""
快捷方式有效性验证的单元测试。

测试 _check_shortcut_target 和 _check_file_target 两个纯逻辑方法，
不依赖 COM / pywin32，可在任何系统上运行。
"""

import os
import sys
import tempfile
import pytest

from clear_win_start.core import StartMenuOrganizer


# =============================================================================
# _check_file_target 测试
# =============================================================================

class TestCheckFileTarget:
    """测试 _check_file_target 静态方法（路径存在性检查）。"""

    def test_empty_path(self):
        """空路径 → False"""
        assert StartMenuOrganizer._check_file_target("") is False

    def test_whitespace_path(self):
        """纯空格路径 → False"""
        assert StartMenuOrganizer._check_file_target("   ") is False

    def test_just_quotes(self):
        """只有引号 → False"""
        assert StartMenuOrganizer._check_file_target('""') is False

    def test_nonexistent_path(self):
        """不存在的文件 → False"""
        assert StartMenuOrganizer._check_file_target(r"C:\ThisPath\ShouldNot\Exist_ABCDE.exe") is False

    def test_nonexistent_drive(self):
        """不存在的盘符 → False"""
        assert StartMenuOrganizer._check_file_target(r"Z:\nonexistent.exe") is False

    def test_existing_file(self):
        """Windows 系统目录下存在的文件 → True"""
        existing = r"C:\Windows\System32\notepad.exe"
        if os.path.exists(existing):
            assert StartMenuOrganizer._check_file_target(existing) is True

    def test_existing_directory(self):
        """存在的目录 → True"""
        existing = r"C:\Windows"
        if os.path.exists(existing):
            assert StartMenuOrganizer._check_file_target(existing) is True

    def test_path_with_quotes(self):
        """带引号的路径 → 能正确去掉引号检查"""
        existing = r"C:\Windows\System32\notepad.exe"
        if os.path.exists(existing):
            assert StartMenuOrganizer._check_file_target(f'"{existing}"') is True
            assert StartMenuOrganizer._check_file_target(f"'{existing}'") is True

    def test_path_envvar(self):
        """包含环境变量的路径 → 展开后检查"""
        assert StartMenuOrganizer._check_file_target(r"%WINDIR%\System32\notepad.exe") is True

    def test_path_envvar_nonexistent(self):
        """包含环境变量但目标不存在 → False"""
        assert StartMenuOrganizer._check_file_target(r"%WINDIR%\NonExistentFile_XYZ.exe") is False

    def test_unknown_path_format(self):
        """非标准磁盘路径格式（如 shell: 等）→ 保守返回 True"""
        assert StartMenuOrganizer._check_file_target("shell:AppsFolder") is True
        assert StartMenuOrganizer._check_file_target("::{CLSID}") is True

    def test_temp_file(self):
        """创建临时文件后检查 → True，删除后再检查 → False"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".test") as f:
            tmp_path = f.name
        try:
            assert StartMenuOrganizer._check_file_target(tmp_path) is True
            os.remove(tmp_path)
            assert StartMenuOrganizer._check_file_target(tmp_path) is False
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_long_path(self):
        """长路径（不需真实存在，但要确保不抛异常）"""
        long_path = "C:\\" + "A" * 300 + "\\file.exe"
        # 不应抛出异常，应返回 False
        result = StartMenuOrganizer._check_file_target(long_path)
        assert result is False


# =============================================================================
# _check_shortcut_target 测试
# =============================================================================

class TestCheckShortcutTarget:
    """测试 _check_shortcut_target 静态方法（快捷方式目标验证）。"""

    # ---- 无效场景 ----

    def test_read_error(self):
        """读取失败 → False"""
        info = {"error": "COM failure"}
        assert StartMenuOrganizer._check_shortcut_target(info) is False

    def test_pywin32_not_installed(self):
        """pywin32 未安装 → False"""
        info = {"error": "pywin32 not installed"}
        assert StartMenuOrganizer._check_shortcut_target(info) is False

    def test_empty_all(self):
        """所有字段为空 → False"""
        info = {"target_path": "", "arguments": "", "working_dir": "", "icon_location": ""}
        assert StartMenuOrganizer._check_shortcut_target(info) is False

    def test_nonexistent_target(self):
        """目标路径不存在 → False"""
        info = {
            "target_path": r"C:\Does\Not\Exist_ABCDE.exe",
            "arguments": "",
            "working_dir": "",
            "icon_location": "",
        }
        assert StartMenuOrganizer._check_shortcut_target(info) is False

    def test_nonexistent_target_with_quotes(self):
        """带引号的无效路径 → False"""
        info = {
            "target_path": r'"C:\Does\Not\Exist_ABCDE.exe"',
            "arguments": "",
            "working_dir": "",
            "icon_location": "",
        }
        assert StartMenuOrganizer._check_shortcut_target(info) is False

    # ---- 有效场景 ----

    def test_existing_exe(self):
        """指向存在的 .exe 文件 → True"""
        existing = r"C:\Windows\System32\notepad.exe"
        if os.path.exists(existing):
            info = {
                "target_path": existing,
                "arguments": "",
                "working_dir": "",
                "icon_location": "",
            }
            assert StartMenuOrganizer._check_shortcut_target(info) is True

    def test_existing_exe_with_quotes(self):
        """带引号的存在的文件路径 → True"""
        existing = r"C:\Windows\System32\notepad.exe"
        if os.path.exists(existing):
            info = {
                "target_path": f'"{existing}"',
                "arguments": "",
                "working_dir": "",
                "icon_location": "",
            }
            assert StartMenuOrganizer._check_shortcut_target(info) is True

    def test_existing_dir(self):
        """指向存在的目录 → True"""
        existing = r"C:\Windows"
        if os.path.exists(existing):
            info = {
                "target_path": existing,
                "arguments": "",
                "working_dir": "",
                "icon_location": "",
            }
            assert StartMenuOrganizer._check_shortcut_target(info) is True

    def test_uwp_app_empty_target_with_arguments(self):
        """UWP 应用：无 TargetPath 但有 Arguments → True"""
        info = {
            "target_path": "",
            "arguments": "-ServerName:App.AppXd39jq...",
            "working_dir": "",
            "icon_location": "",
        }
        assert StartMenuOrganizer._check_shortcut_target(info) is True

    def test_uwp_app_empty_target_with_icon(self):
        """UWP 应用：无 TargetPath 但有 IconLocation → True"""
        info = {
            "target_path": "",
            "arguments": "",
            "working_dir": "",
            "icon_location": r"C:\Windows\System32\shell32.dll,1",
        }
        assert StartMenuOrganizer._check_shortcut_target(info) is True

    def test_shell_protocol(self):
        """Shell 协议路径 → True"""
        info = {
            "target_path": "shell:AppsFolder",
            "arguments": "",
            "working_dir": "",
            "icon_location": "",
        }
        assert StartMenuOrganizer._check_shortcut_target(info) is True

    def test_app_protocol(self):
        """App 协议路径 → True"""
        info = {
            "target_path": "ms-settings:",
            "arguments": "",
            "working_dir": "",
            "icon_location": "",
        }
        assert StartMenuOrganizer._check_shortcut_target(info) is True

    def test_url_shortcut(self):
        """URL 快捷方式 → True"""
        info = {
            "target_path": "https://www.example.com",
            "arguments": "",
            "working_dir": "",
            "icon_location": "",
        }
        assert StartMenuOrganizer._check_shortcut_target(info) is True

    def test_appusermodelid(self):
        """AppUserModelID 格式 → True"""
        info = {
            "target_path": "Microsoft.WindowsStore_8wekyb3d8bbwe!App",
            "arguments": "",
            "working_dir": "",
            "icon_location": "",
        }
        assert StartMenuOrganizer._check_shortcut_target(info) is True

    def test_wildcard_target(self):
        """含通配符的路径 → True"""
        info = {
            "target_path": r"C:\Program Files\*",
            "arguments": "",
            "working_dir": "",
            "icon_location": "",
        }
        assert StartMenuOrganizer._check_shortcut_target(info) is True

    def test_envvar_target_path(self):
        """含环境变量的路径且文件存在 → True"""
        info = {
            "target_path": r"%WINDIR%\System32\notepad.exe",
            "arguments": "",
            "working_dir": "",
            "icon_location": "",
        }
        assert StartMenuOrganizer._check_shortcut_target(info) is True

    def test_system32_notepad(self):
        """指向 C:\Windows\System32\notepad.exe（真实存在的系统文件）"""
        existing = r"C:\Windows\System32\notepad.exe"
        if os.path.exists(existing):
            info = {
                "target_path": existing,
                "arguments": "",
                "working_dir": r"C:\Windows",
                "icon_location": "",
            }
            assert StartMenuOrganizer._check_shortcut_target(info) is True

    def test_normal_app_shortcut(self):
        """模拟微信/滴答清单等正常应用快捷方式"""
        info = {
            "target_path": r"C:\Program Files\Tencent\WeChat\WeChat.exe",
            "arguments": "",
            "working_dir": r"C:\Program Files\Tencent\WeChat",
            "icon_location": "",
        }
        # 路径可能不存在（不同机器），但验证逻辑应正确判断
        expected = os.path.exists(r"C:\Program Files\Tencent\WeChat\WeChat.exe")
        assert StartMenuOrganizer._check_shortcut_target(info) is expected


# =============================================================================
# _check_shortcut_target 边界场景测试
# =============================================================================

class TestCheckShortcutTargetEdgeCases:
    """边界和组合场景。"""

    def test_empty_dict(self):
        """空字典 → False（无任何字段）"""
        assert StartMenuOrganizer._check_shortcut_target({}) is False

    def test_partial_fields(self):
        """部分字段缺失 → 应能容错处理"""
        info = {"target_path": ""}
        # target_path 为空，且 arguments/icon 缺失，视为无目标信息
        assert StartMenuOrganizer._check_shortcut_target(info) is False

    def test_target_with_trailing_spaces(self):
        """目标路径带尾部空格 → 应能清理后检查"""
        existing = r"C:\Windows\System32\notepad.exe"
        if os.path.exists(existing):
            info = {
                "target_path": existing + "   ",
                "arguments": "",
                "working_dir": "",
                "icon_location": "",
            }
            assert StartMenuOrganizer._check_shortcut_target(info) is True

    def test_malformed_target_starts_with_slash(self):
        """路径格式异常但非标准磁盘路径 → 保守返回 True"""
        info = {
            "target_path": "/some/unix/path",
            "arguments": "",
            "working_dir": "",
            "icon_location": "",
        }
        assert StartMenuOrganizer._check_shortcut_target(info) is True

    def test_ms_resource_protocol(self):
        """ms-resource: 协议路径 → True"""
        info = {
            "target_path": "ms-resource:AppName",
            "arguments": "",
            "working_dir": "",
            "icon_location": "",
        }
        assert StartMenuOrganizer._check_shortcut_target(info) is True

    def test_clsid_path(self):
        """CLSID 路径格式 → 非标准磁盘路径，保守返回 True"""
        info = {
            "target_path": "::{26EE0668-A00A-44D7-9371-BEB064C98683}",
            "arguments": "",
            "working_dir": "",
            "icon_location": "",
        }
        assert StartMenuOrganizer._check_shortcut_target(info) is True

    def test_working_dir_only(self):
        """只有 working_dir → 无 target/args/icon → False"""
        info = {
            "target_path": "",
            "arguments": "",
            "working_dir": r"C:\SomeDir",
            "icon_location": "",
        }
        assert StartMenuOrganizer._check_shortcut_target(info) is False
