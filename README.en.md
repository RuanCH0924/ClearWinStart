# ClearWinStart

**A Windows Start Menu organizer** — flatten nested folders and clean up invalid shortcuts.

[中文](README.md) | **English**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python versions](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![GitHub release](https://img.shields.io/github/v/release/RuanCH0924/ClearWinStart)](https://github.com/RuanCH0924/ClearWinStart/releases)

---

## What it does

Every Windows installation slowly accumulates clutter in
`%APPDATA%\Microsoft\Windows\Start Menu\Programs`: orphaned shortcuts left behind by
uninstalled apps, useless entries such as "Uninstall" / "Help" / "Website", and
multi-level folders created by installers. ClearWinStart cleans this up.

| Feature | Description |
|---------|-------------|
| **Flatten folders** | Move shortcuts from sub-folders up to the Programs root, then remove the empty folders |
| **Keyword cleanup** | Move shortcuts whose names contain configured keywords (e.g. "Uninstall", "Help") to the Recycle Bin |
| **Invalid shortcut detection** | Read each `.lnk` target and move shortcuts pointing at missing files to the Recycle Bin. Shortcuts that **cannot be read are skipped and reported, never treated as invalid** (`.url` is INI text and cannot be read via COM, so it is only backed up) |
| **Duplicate cleanup** | Compare across **all** scanned directories by `TargetPath + Arguments`; keep one copy of each, recycle the rest (relative targets are resolved against `WorkingDirectory`) |
| **Backup before changes** | Copy every shortcut (`.lnk` / `.url`) to the desktop first, preserving the original folder structure (OneDrive redirection is detected automatically) |
| **Dry-run preview** | Generate the full operation plan before touching anything |
| **Unified full-screen TUI** | One single alt-screen from start to finish: init, config wizard, path selection, execution and results all render in the same panel, in place — no scrolling logs. Degrades to static text on non-interactive terminals |

### Safety principles

- **Trash first** — every delete goes through [`send2trash`](https://github.com/arsenetar/send2trash); nothing is permanently removed.
- **Conservative validation** — a shortcut is only deleted when it is *definitely* invalid; if it cannot be read, it is skipped.
- **Previewable** — every change can be reviewed before execution.

---

## Requirements

- Windows 10 / 11
- Python 3.8 – 3.12
- Read/write access to the Start Menu folders

> The project is **Windows-only by design**: it relies on Windows path semantics, the
> Recycle Bin and Shell Link (COM). The test suite and CI therefore target Windows only.

| Dependency | Notes |
|------------|-------|
| [`send2trash`](https://github.com/arsenetar/send2trash) >= 1.8 | Required — moves files to the Recycle Bin |
| [`pywin32`](https://github.com/mhammond/pywin32) >= 228 | Optional — needed to read `.lnk` files (shortcut validation / dedupe) |

The core modules (`config.py`, `core.py`, `paths.py`) use only the Python standard library.

---

## Install

```bash
git clone https://github.com/RuanCH0924/ClearWinStart.git
cd ClearWinStart

python -m venv venv
.\venv\Scripts\activate

pip install -e ".[windows]"   # runtime, including pywin32
pip install -e ".[dev]"       # development (tests + linters)
```

## Usage

```bash
# Preview only — changes nothing (recommended first run)
clear-win-start --preview

# Execute
clear-win-start --auto-confirm

# Use a config file
clear-win-start --config config.json
```

The Windows username is auto-detected (`USERNAME` → `%USERPROFILE%` → `getpass`);
pass `--user-name` to override it.

### Options

```text
--version                Show version
--user-name, -u          Windows username (auto-detected by default)
--config, -c             JSON config file
--paths, -p              Extra paths to process
--neglect-folders, -n    Folder names to skip
--delete-keywords, -d    Keywords whose matching files/folders are removed
--dry-run                Preview only, change nothing
--auto-confirm, -y       Skip confirmation prompts (including the path picker)
--no-check-shortcuts     Skip shortcut validation
--no-dedupe-shortcuts    Skip duplicate-shortcut cleanup
--no-backup-shortcuts    Skip the pre-run backup
--backup-dir             Backup directory (default: ClearWinStart_Backup on the desktop)
--no-animation           Disable the terminal UI (panel / progress / menus)
--verbose, -v            Verbose (debug) logging
--validate-only          Validate configuration and paths only
--log-file               Log file path
--wizard                 Run the configuration wizard
--save-config            Save the generated config to a file
--preview                Show the plan and ask for confirmation before executing
```

### The unified full-screen panel

The terminal itself becomes the interface — one alt-screen for the whole session:

```text
╔════════════════════════════════════════════════════════════╗
║                 C L E A R W I N S T A R T                  ║
║                  Windows 开始菜单整理工具                   ║
╚════════════════════════════════════════════════════════════╝

  ✓ 初始化 › ✓ 配置 › ● 路径选择 › ○ 执行 › ○ 结果

  请选择要处理的路径
  默认全部选中；可用空格逐项取舍

  ❯ ◉ [USER] C:\Users\me\AppData\Roaming\Microsoft\Windows\Start Menu\Programs
    ◉ [SYS]  C:\ProgramData\Microsoft\Windows\Start Menu\Programs

  ↑/↓ 移动 · 空格 选择 · A 全选 · N 全不选 · Enter 确认 · Esc 取消
```

Panel strings are Chinese by default (the mockup above is the real output).

Progress, counters and the "recent activity" log refresh in place; the results screen
stays until a key is pressed. Piped / redirected / CI environments automatically fall
back to plain static output (`NO_COLOR`, `--no-animation` also disable it).

> 📸 **Demo media welcome.** The terminal UI is the differentiator — a ~30s recording
> (`docs/demo.gif`) would help a lot. PRs welcome.

---

## Configuration

Configuration is a JSON file; see [`default-config.json`](default-config.json).

```json
{
    "user_name": "",
    "paths": {
        "user_start_menu": "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs",
        "system_start_menu": "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs"
    },
    "neglect_folders": ["System Tools", "Windows PowerShell", "Startup"],
    "delete_keywords": ["卸载", "官网", "更新", "帮助"],
    "check_shortcuts": true,
    "dedupe_shortcuts": true,
    "backup_shortcuts": true,
    "backup_dir": "",
    "animation": true,
    "dry_run": false
}
```

- `user_name` — leave empty to auto-detect at runtime.
- `paths` — supports environment variables such as `%APPDATA%`.
- `delete_keywords` / `neglect_folders` — **omitting** the key keeps the built-in
  defaults; writing an **empty list** (`[]`) means "really nothing" (no deletion / no
  folder is exempt).

---

## Project structure

```text
ClearWinStart/
├── clear_win_start/
│   ├── cli.py             # CLI parsing + session orchestration + preview rendering
│   ├── ui.py              # Unified full-screen shell (Screen / ScreenPrompter)
│   ├── config.py          # Configuration + JSON serialization + wizard
│   ├── console.py         # Terminal rendering (colors, alignment, table, Dashboard)
│   ├── core.py            # StartMenuOrganizer: flatten / clean / dedupe / backup
│   ├── logging_setup.py   # Logging (panel-aware console handler + rotating file)
│   └── paths.py           # Env-var expansion, path shortening, desktop detection
├── tests/                 # pytest suite
├── default-config.json
├── pyproject.toml
├── README.md              # 中文
└── README.en.md           # this file
```

---

## License

[MIT](LICENSE)
