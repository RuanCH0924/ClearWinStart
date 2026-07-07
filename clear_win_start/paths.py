"""
路径处理工具：环境变量展开、起始菜单路径缩短、用户名检测。
"""

import os
from typing import List, Optional

__all__ = [
    "DEFAULT_USER_START_MENU",
    "DEFAULT_SYSTEM_START_MENU",
    "build_default_paths",
    "expand_env_vars",
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
    """获取当前 Windows 用户名（无法确定时返回 None）。"""
    return os.environ.get("USERNAME") or os.environ.get("USER")


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
