"""
路径处理工具：环境变量展开、起始菜单路径缩短、用户名检测、桌面/备份目录定位。
"""

import os
from typing import List, Optional

__all__ = [
    "DEFAULT_USER_START_MENU",
    "DEFAULT_SYSTEM_START_MENU",
    "build_default_paths",
    "expand_env_vars",
    "get_default_backup_dir",
    "get_desktop_dir",
    "shorten_start_menu_path",
    "get_windows_username",
    "get_default_log_path",
]


# 系统默认起始菜单路径（用于未指定时的回退）
DEFAULT_USER_START_MENU = (
    r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"
)
DEFAULT_SYSTEM_START_MENU = (
    r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"
)


def build_default_paths(user_name: str) -> List[str]:
    """根据用户名构造默认的用户/系统起始菜单路径列表。"""
    user = fr"C:\Users\{user_name}\AppData\Roaming"
    user = user + r"\Microsoft\Windows\Start Menu\Programs"
    return [user, DEFAULT_SYSTEM_START_MENU]


def expand_env_vars(path: str) -> str:
    """展开路径中的环境变量（%APPDATA% / %USERPROFILE% 等）。"""
    if not path:
        return path

    result = os.path.expandvars(path)
    for var in (
        "APPDATA",
        "USERPROFILE",
        "LOCALAPPDATA",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
    ):
        result = result.replace(f"%{var}%", os.environ.get(var, ""))
    return result


def get_windows_username() -> Optional[str]:
    """获取当前 Windows 用户名（无法确定时返回 None）。

    依次尝试环境变量 USERNAME / USER、%USERPROFILE% 的末段、getpass.getuser()。
    """
    for var in ("USERNAME", "USER"):
        name = os.environ.get(var)
        if name:
            return name
    profile = os.environ.get("USERPROFILE")
    if profile:
        name = os.path.basename(profile.rstrip("\\/"))
        if name:
            return name
    try:
        import getpass

        return getpass.getuser() or None
    except Exception:
        return None


def get_desktop_dir() -> str:
    """获取当前用户实际使用的桌面目录（兼容 OneDrive / 自定义重定向）。

    依次尝试：
      1. SHGetKnownFolderPath(FOLDERID_Desktop) —— 最权威，反映重定向
      2. 注册表 HKCU\\...\\User Shell Folders 的 Desktop 项
      3. 回退到 %USERPROFILE%\\Desktop

    Returns:
        桌面目录路径。
    """
    for resolver in (_desktop_from_known_folder, _desktop_from_registry):
        path = resolver()
        if path and os.path.isdir(path):
            return path
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    return os.path.join(home, "Desktop")


def _desktop_from_known_folder() -> Optional[str]:
    """通过 SHGetKnownFolderPath(FOLDERID_Desktop) 读取桌面目录。"""
    if os.name != "nt":
        return None
    try:
        import ctypes

        class _GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", ctypes.c_uint32),
                ("Data2", ctypes.c_uint16),
                ("Data3", ctypes.c_uint16),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        # FOLDERID_Desktop = {B4BFCC3A-DB2C-424C-B029-7FE99A87C641}
        folder_id = _GUID()
        folder_id.Data1 = 0xB4BFCC3A
        folder_id.Data2 = 0xDB2C
        folder_id.Data3 = 0x424C
        for index, byte in enumerate((0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41)):
            folder_id.Data4[index] = byte

        path_ptr = ctypes.c_void_p()
        hresult = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(folder_id), 0, None, ctypes.byref(path_ptr)
        )
        if hresult != 0 or not path_ptr.value:
            return None
        resolved = ctypes.cast(path_ptr, ctypes.c_wchar_p).value
        ctypes.windll.ole32.CoTaskMemFree(path_ptr)
        return resolved
    except Exception:
        return None


def _desktop_from_registry() -> Optional[str]:
    """通过注册表 User Shell Folders 读取桌面目录（支持 %USERPROFILE% 等变量）。"""
    try:
        import winreg
    except ImportError:
        return None
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        )
        try:
            value, _ = winreg.QueryValueEx(key, "Desktop")
        finally:
            winreg.CloseKey(key)
        return os.path.expandvars(value) if value else None
    except OSError:
        return None


def get_default_backup_dir() -> str:
    """默认快捷方式备份目录：当前用户桌面下的 ClearWinStart_Backup 文件夹。"""
    return os.path.join(get_desktop_dir(), "ClearWinStart_Backup")


def get_default_log_path() -> str:
    """获取默认日志文件路径（%APPDATA%\\ClearWinStart\\logs\\clear_win_start_YYYYMMDD.log）。"""
    from datetime import datetime  # 局部导入避免顶层依赖

    log_dir = os.path.join(os.environ.get("APPDATA", ""), "ClearWinStart", "logs")
    os.makedirs(log_dir, exist_ok=True)

    filename = f"clear_win_start_{datetime.now().strftime('%Y%m%d')}.log"
    return os.path.join(log_dir, filename)


def shorten_start_menu_path(
    full_path: str,
    user_start_menu: Optional[str] = None,
    system_start_menu: Optional[str] = None,
) -> str:
    """把完整起始菜单路径缩短为 `[USER]` / `[SYS]` / `~/...` 形式。"""
    if user_start_menu is None:
        user_start_menu = os.path.join(
            os.environ.get("APPDATA", ""),
            "Microsoft", "Windows", "Start Menu", "Programs",
        )
    if system_start_menu is None:
        system_start_menu = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"

    if full_path.startswith(user_start_menu):
        return f"[USER] {full_path[len(user_start_menu):].lstrip(os.sep)}"
    if full_path.startswith(system_start_menu):
        return f"[SYS] {full_path[len(system_start_menu):].lstrip(os.sep)}"

    user_profile = os.environ.get("USERPROFILE", "")
    if user_profile and full_path.startswith(user_profile):
        return f"~/{full_path[len(user_profile):].lstrip(os.sep)}"
    return full_path
