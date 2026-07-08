# ClearWinStart

**Windows 开始菜单整理工具** — 扁平化嵌套文件夹、清理无效快捷方式。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python versions](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![GitHub release](https://img.shields.io/github/v/release/RuanCH/ClearWinStart)](https://github.com/RuanCH/ClearWinStart/releases)

---

## 目录

- [项目概述](#项目概述)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
- [配置说明](#配置说明)
- [项目结构](#项目结构)
- [功能模块](#功能模块)
- [Python API](#python-api)
- [开发指南](#开发指南)
- [部署指南](#部署指南)
- [贡献规范](#贡献规范)
- [常见问题排查](#常见问题排查)
- [维护与版权](#维护与版权)

---

## 项目概述

### 定位

ClearWinStart 是一个 Windows 命令行工具，用于自动整理「开始菜单」的 Programs 目录。它解决的是 Windows 开始菜单随着软件安装卸载而日益杂乱的问题。

### 背景

Windows 开始菜单的 `%APPDATA%\Microsoft\Windows\Start Menu\Programs` 目录随着软件安装会积累大量子文件夹和冗余快捷方式。软件卸载后，其快捷方式常常残留；安装程序也会创建"卸载""帮助"等无实际用途的快捷方式。手动整理费时费力。

### 核心功能

| 功能 | 说明 |
|------|------|
| **扁平化文件夹** | 将子文件夹中的快捷方式提取到 Programs 根目录，删除空文件夹 |
| **关键词清理** | 删除文件名中包含指定关键词（如"卸载""帮助"）的快捷方式 |
| **无效快捷方式检测** | 读取 `.lnk` 文件的 TargetPath，验证目标文件是否存在，不存在则移入回收站 |
| **干跑预览模式** | 执行前生成完整的操作计划，评估影响等级，不实际修改文件 |
| **配置文件向导** | 交互式引导生成 JSON 配置文件 |

### 设计原则

- **安全优先**：所有删除操作先移入回收站（通过 `send2trash`），而非永久删除
- **保守验证**：快捷方式有效性判断以"宁可放过、不可误删"为原则
- **操作可预览**：所有变更在执行前均可在预览模式中查看

---

## 技术栈

### 运行环境

| 依赖 | 版本要求 | 用途 |
|------|---------|------|
| Python | >= 3.8 | 运行时 |
| [send2trash](https://github.com/arsenetar/send2trash) | >= 1.8 | 文件移入回收站 |
| [pywin32](https://github.com/mhammond/pywin32) | >= 228（可选） | 读取 `.lnk` 快捷方式文件 |

### 开发工具

| 工具 | 用途 |
|------|------|
| [pytest](https://docs.pytest.org/) >= 7.0 | 单元测试 |
| [pytest-cov](https://pytest-cov.readthedocs.io/) >= 4.0 | 测试覆盖率 |
| [flake8](https://flake8.pycqa.org/) >= 6.0 | 代码风格检查 |
| [black](https://black.readthedocs.io/) >= 23.0 | 代码格式化 |
| [isort](https://pycqa.github.io/isort/) >= 5.12 | import 排序 |
| [mypy](https://mypy-lang.org/) >= 1.0 | 类型检查 |
| [tox](https://tox.wiki/) >= 4.0 | 多环境自动化测试 |

### 无外部依赖的核心逻辑

`clear_win_start/config.py`、`clear_win_start/core.py`、`clear_win_start/paths.py` 等核心模块**不依赖任何第三方库**，仅使用 Python 标准库。`send2trash` 和 `pywin32` 仅在执行文件操作和读取快捷方式时使用。

---

## 快速开始

### 系统要求

- Windows 10 或 Windows 11
- Python 3.8 ~ 3.12
- 对开始菜单目录的读写权限

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/RuanCH/ClearWinStart.git
cd ClearWinStart

# 2. （推荐）创建虚拟环境
python -m venv venv
.\venv\Scripts\activate

# 3. 安装
pip install -e ".[windows]"    # 生产环境（含快捷方式读取支持）
pip install -e ".[dev]"        # 开发环境（含测试/代码质量工具）
```

### 快速上手

```bash
# 查看帮助
clear-win-start --help

# 步骤 1：以预览模式扫描（推荐首次使用，不修改文件）
clear-win-start --preview --user-name 你的用户名

# 步骤 2：确认无误后执行整理
clear-win-start --auto-confirm --user-name 你的用户名

# 使用配置文件
clear-win-start --config config.json
```

### 环境变量说明

本项目**无需配置环境变量文件**（无 `.env`）。所有配置通过 JSON 文件或命令行参数传入。

| 环境变量 | 用途 | 默认值 |
|---------|------|--------|
| `USERNAME` | 当前 Windows 用户名（`--user-name` 未指定时自动检测） | 系统环境变量 |
| `APPDATA` | 用户 AppData 路径 | 系统环境变量 |

---

## 使用指南

### 命令参考

```text
clear-win-start [选项]

选项：
  --version               显示版本号
  --user-name, -u         用户名（默认自动检测）
  --config, -c            JSON 配置文件路径
  --paths, -p             额外要处理的路径
  --neglect-folders, -n   跳过的文件夹名称
  --delete-keywords, -d   删除关键词列表
  --dry-run               仅预览，不实际修改
  --auto-confirm, -y      跳过所有确认提示
  --no-check-shortcuts    跳过快捷方式有效性验证
  --verbose, -v           启用调试日志
  --validate-only         仅验证配置和路径
  --log-file              日志文件路径
  --wizard                运行配置向导
  --save-config           保存配置到文件
  --preview               显示详细操作计划
```

### 典型使用流程

```
┌─────────────────────────────────────────────────┐
│  1. clear-win-start --wizard                    │
│     运行配置向导 → 生成 config.json              │
└─────────────────────┬───────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│  2. clear-win-start --preview --config config   │
│     预览操作计划 → 确认影响范围                  │
└─────────────────────┬───────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│  3. clear-win-start --config config.json        │
│     实际执行整理                                │
└─────────────────────────────────────────────────┘
```

### 预览模式输出示例

```text
══════════════════════════════════════════════════
  ClearWinStart
══════════════════════════════════════════════════

  ─── 配置信息 ───
    用户: ruanc
    待处理路径：
      · [USER] C:\Users\ruanc\...\Start Menu\Programs
      · [SYS]  C:\ProgramData\...\Programs
    干跑模式: 否
    校验快捷方式: 是

  ─── 执行计划 ───
    ▾ Google Chrome
    ▾ 7-Zip
    !  百度网盘.lnk（无效快捷方式）
    ✗  卸载微信.lnk

  ─── 摘要 ───
    待处理文件夹:          2
    待移动文件:            5
    快捷方式: 共 23 个, 其中 1 个无效
    影响评估: 低
```

---

## 配置说明

### 配置文件查找顺序

1. 命令行 `--config config.json`
2. 当前目录 `default-config.json`
3. 项目根目录 `default-config.json`
4. `%APPDATA%\ClearWinStart\default-config.json`
5. 代码内置默认值

### 默认配置 (`default-config.json`)

```json
{
    "_comment_user_name": "Windows 用户名，留空则在运行时自动检测",
    "user_name": "",

    "_comment_paths": "要处理的开始菜单路径，支持 %APPDATA% 等环境变量",
    "paths": {
        "user_start_menu": "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs",
        "system_start_menu": "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs"
    },

    "_comment_neglect_folders": "保留的文件夹列表，这些文件夹不会被扁平化处理",
    "neglect_folders": [
        "Accessibility", "Accessories", "Administrative",
        "Administrative Tools", "Startup", "System Tools",
        "Windows PowerShell", "desktop.ini", "Maintenance",
        "StartUp", "Tools"
    ],

    "_comment_delete_keywords": "文件名包含这些关键词时会被移至回收站，留空则不删除",
    "delete_keywords": ["卸载", "官网", "更新", "帮助", "意见", "设置", "关于"],

    "_comment_check_shortcuts": "是否校验快捷方式有效性",
    "check_shortcuts": true,

    "_comment_dry_run": "干跑模式，true 时只预览不修改",
    "dry_run": false
}
```

### 支持的环境变量

在路径配置中可以使用 `%APPDATA%`、`%USERPROFILE%`、`%LOCALAPPDATA%`、`%PROGRAMFILES%` 等 Windows 标准环境变量。

---

## 项目结构

```
ClearWinStart/
├── clear_win_start/              # 主包（Python 模块）
│   ├── __init__.py              # 包初始化，导出公共 API
│   ├── __main__.py              # python -m clear_win_start 入口
│   ├── cli.py                   # CLI 参数解析 + 主流程控制
│   ├── config.py                # 配置管理（Configuration 数据类 + DefaultConfig + ConfigurationWizard）
│   ├── core.py                  # 核心业务逻辑（StartMenuOrganizer + 快捷方式验证）
│   ├── logging_setup.py         # 日志系统（彩色控制台 + 滚动文件）
│   ├── paths.py                 # 路径工具（环境变量展开、路径缩短、默认路径构建）
│   └── py.typed                 # PEP 561 类型标记
├── tests/                        # 单元测试
│   └── test_shortcut_validation.py  # 快捷方式验证逻辑测试（38 个用例）
├── default-config.json           # 默认配置文件
├── pyproject.toml                # 项目元数据 + 构建配置 + 工具配置
├── tox.ini                       # tox 自动化测试配置
├── README.md                     # 本文件
└── LICENSE                       # MIT 许可证
```

### 关键文件说明

| 文件 | 职责 | 关键类/函数 |
|------|------|-------------|
| `__init__.py` | 公共 API 导出 | `Configuration`, `StartMenuOrganizer`, `PreviewWindow` |
| `cli.py` | 命令行入口、参数解析、预览渲染 | `main()`, `PreviewWindow`, `InteractiveConfirm` |
| `config.py` | 配置模型、JSON 序列化、交互式向导 | `Configuration`, `ConfigurationWizard`, `DefaultConfig` |
| `core.py` | 核心整理逻辑、快捷方式验证 | `StartMenuOrganizer`, `_is_valid_shortcut`, `_check_shortcut_target` |
| `paths.py` | Windows 路径处理 | `expand_env_vars()`, `shorten_start_menu_path()` |
| `logging_setup.py` | 日志初始化 | `setup_logging()`, `ColoredFormatter` |

---

## 功能模块

### 模块一：配置管理 (`config.py`)

```
Configuration (数据类)
  ├── user_name         用户名
  ├── paths             待处理路径列表
  ├── neglect_folders   保留文件夹（不处理）
  ├── delete_keywords   删除关键词
  ├── check_shortcuts   是否校验快捷方式
  └── dry_run           干跑模式

ConfigurationWizard (交互式向导)
  └── run() → Configuration  逐步骤引导用户创建配置

DefaultConfig (默认配置加载)
  ├── load_from_file()       加载 default-config.json
  └── reset()                恢复内置默认值
```

### 模块二：核心整理 (`core.py`)

```
StartMenuOrganizer
  ├── organize()              主入口
  │   └── _process_path()     处理单个路径
  │       ├── _process_folder()        扁平化子文件夹
  │       │   └── _move_file()         移动文件（干跑时只打印）
  │       ├── _clean_keyword_files()   删除匹配关键词的文件
  │       └── _clean_invalid_shortcuts() 清理无效快捷方式
  │           └── _is_valid_shortcut() 快捷方式验证总入口
  │               ├── _read_shortcut()           COM 读取 .lnk
  │               └── _check_shortcut_target()   纯逻辑验证（8 条规则）
  │                   └── _check_file_target()   Windows 路径存在性检查
  ├── _generate_dry_run_plan()  生成执行计划
  └── _print_dry_run_summary()  打印摘要
```

### 模块三：快捷方式验证逻辑

验证流程（8 条规则，按优先级）：

```
_read_shortcut(.lnk)
    ↓
_check_shortcut_target(dict)
    │
    ├─ 规则 1：读取失败 → 无效
    ├─ 规则 2：无 TargetPath + 无 Arguments + 无 IconLocation → 无效（空壳快捷方式）
    ├─ 规则 3：无 TargetPath + 有 Arguments 或 IconLocation → 有效（UWP 应用）
    ├─ 规则 4：TargetPath 是 shell:/app:/ms: 协议 → 有效
    ├─ 规则 5：TargetPath 含 ! 或 * → 有效（AppUserModelID）
    ├─ 规则 6：TargetPath 是文件/目录路径 → _check_file_target()
    │   ├─ os.path.exists() 检查
    │   ├─ 环境变量展开后检查
    │   ├─ 长路径 (\\?\ 前缀) 检查
    │   ├─ os.path.normpath() 规范化后检查
    │   └─ 路径格式判断（磁盘路径/UNC/其他）
    ├─ 规则 7：路径不存在 → 无效
    └─ 规则 8：未知格式 → 有效（保守兜底）
```

### 模块四：CLI 界面 (`cli.py`)

```
main()
  ├── --wizard           → run_wizard()
  ├── --validate-only    → validate_paths()
  ├── --preview          → 扫描 → render_preview() → InteractiveConfirm
  │                        → 确认后执行 / 取消 / 重新扫描
  └── 默认               → organize() → print_stats()
```

---

## Python API

ClearWinStart 的核心类和方法也可作为 Python 库调用：

```python
from clear_win_start import StartMenuOrganizer, Configuration
from clear_win_start.cli import PreviewWindow, create_preview_from_stats

# 创建配置
config = Configuration(user_name="testuser")

# 创建组织器
organizer = StartMenuOrganizer(config)

# 生成预览（不修改文件）
stats = organizer.organize(auto_confirm=True, preview_only=True)
preview_report = create_preview_from_stats(stats, config.paths, config.user_name)
preview_output = PreviewWindow.render_preview(preview_report)
print(preview_output)

# 执行操作
stats = organizer.organize(auto_confirm=True)
print(f"已处理文件夹: {stats['folders_processed']}")
print(f"已移动文件: {stats['files_moved']}")
```

---

## 开发指南

### 搭建开发环境

```bash
# 克隆并安装开发依赖
git clone https://github.com/RuanCH/ClearWinStart.git
cd ClearWinStart
python -m venv venv
.\venv\Scripts\activate
pip install -e ".[dev]"
```

### 运行测试

```bash
# 运行全部测试
pytest tests/

# 运行带覆盖率报告
pytest --cov=clear_win_start tests/

# 运行特定测试文件
pytest tests/test_shortcut_validation.py -v

# 运行特定测试类
pytest tests/test_shortcut_validation.py::TestCheckShortcutTarget -v
```

### 代码质量检查

```bash
flake8 clear_win_start tests
black --check clear_win_start tests
isort --check-only clear_win_start tests
mypy clear_win_start
```

### 一键格式化

```bash
black clear_win_start tests
isort clear_win_start tests
```

### tox 自动化

```bash
tox                    # 运行所有环境的测试
tox -e lint            # 代码风格检查
tox -e type            # 类型检查
tox -e format          # 自动格式化
```

### 测试覆盖场景

快捷方式验证测试涵盖 38 个用例：

| 分类 | 用例数 | 关键验证点 |
|------|--------|-----------|
| 无效路径 | 8 | 空路径、不存在文件、盘符不存在、带引号不存在、文件删除后 |
| 有效路径 | 6 | 存在的 exe/目录、环境变量路径、带引号存在 |
| 特殊快捷方式 | 8 | UWP 应用、Shell/App/MS 协议、URL、AppUserModelID、通配符 |
| 边界场景 | 7 | 空字典、字段缺失、尾部空格、Unix 路径、CLSID、ms-resource: |

---

## 部署指南

### 生产环境部署

```bash
# 方式一：从 PyPI 安装（待发布）
pip install clear-win-start

# 方式二：从源码安装
git clone https://github.com/RuanCH/ClearWinStart.git
cd ClearWinStart
pip install -e ".[windows]"

# 验证安装
clear-win-start --version
```

### CI/CD 流水线

项目使用 GitHub Actions（配置文件位于 `.github/workflows/ci.yml`），自动执行：

| 阶段 | 操作 |
|------|------|
| 代码检查 | flake8 + black --check + isort --check-only |
| 类型检查 | mypy |
| 单元测试 | pytest --cov=clear_win_start |
| Python 版本 | 3.8 / 3.9 / 3.10 / 3.11 / 3.12 |

---

## 贡献规范

### Pull Request 流程

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/xxx`
3. 提交代码：`git commit -m "feat: 添加 xxx 功能"`
4. 推送到分支：`git push origin feature/xxx`
5. 创建 Pull Request

### Commit 格式

```
<type>: <简短描述>

<可选详细描述>
```

| Type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 Bug |
| `refactor` | 重构 |
| `test` | 测试 |
| `docs` | 文档 |
| `style` | 代码格式（不影响功能） |
| `chore` | 构建/配置 |

### 分支管理

| 分支 | 用途 |
|------|------|
| `main` | 稳定版本，仅接受 PR 合并 |
| `develop` | 开发主线 |
| `feature/*` | 功能开发 |
| `fix/*` | Bug 修复 |

### 代码要求

- 新增代码需包含类型注解
- 新功能需添加对应测试用例
- 所有测试通过后才能合并

### 问题反馈

- GitHub Issues：https://github.com/RuanCH/ClearWinStart/issues

---

## 常见问题排查

### 安装问题

**Q: `pip install -e ".[windows]"` 报错**

确保使用支持的命令行（PowerShell 或 CMD）。在 PowerShell 中，点号后的参数需要用反引号转义或使用引号：

```powershell
pip install -e '.[windows]'
```

**Q: 安装后 `clear-win-start` 命令找不到**

确认 Python Scripts 目录在 PATH 中：

```powershell
python -m clear_win_start --help   # 用 python -m 方式运行
```

### 运行问题

**Q: `pywin32` 未安装，快捷方式验证被跳过**

`pywin32` 是可选依赖，用于读取 `.lnk` 文件。使用 `pip install pywin32` 安装即可启用快捷方式验证功能。

**Q: 预览显示"路径不存在"**

默认路径中的用户名与实际用户名不匹配。使用 `--user-name` 参数指定正确的用户名，或通过 `--config` 指定自定义配置文件。

**Q: 控制台输出乱码或方框字符**

确保终端使用 UTF-8 编码：

```powershell
chcp 65001
```

推荐使用 Windows Terminal。

**Q: 快捷方式验证结果显示均为有效，但我确认有无效快捷方式**

在文件目录中手动检查：删除一个 `test_invalid.lnk` 快捷方式后运行 `clear-win-start --preview --user-name 用户名 --verbose`，查看调试日志输出。如果问题持续，请在 GitHub Issues 提交报告。

**Q: 运行时报 `PermissionError`**

对开始菜单目录没有写权限。右键目录 → 属性 → 安全 → 编辑，为当前用户添加"修改"权限。

### 文件恢复

**Q: 执行整理后快捷方式不见了**

从回收站还原。所有删除操作均使用 `send2trash` 移入回收站，不会永久删除。

**Q: 被移动的快捷方式在哪里**

在开始菜单 Programs 根目录：`%APPDATA%\Microsoft\Windows\Start Menu\Programs`。原先在子文件夹中的文件已被提取到根目录。

---

## 维护与版权

### 项目维护

- 作者：Ruan CH
- 仓库：https://github.com/RuanCH0924/ClearWinStart
- Issue：https://github.com/RuanCH0924/ClearWinStart/issues

### 开源协议

本项目基于 **MIT License** 授权。完整许可内容见 `LICENSE` 文件。

```
MIT License

Copyright (c) 2024 Ruan CH

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

### 免责声明

本工具会修改开始菜单目录中的文件。虽然所有删除操作均移至回收站，但建议在首次使用前手动备份开始菜单目录。作者不对因使用本工具导致的任何数据丢失或系统问题承担责任。
