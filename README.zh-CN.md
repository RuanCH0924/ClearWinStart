# ClearWinStart - Windows 开始菜单整理工具

**原作者: © Ruan CH**

[![许可证: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python版本](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)

一个功能强大且易于使用的 Windows 开始菜单整理工具，可以扁平化嵌套文件夹并清理无效的快捷方式。

## 功能特点

- **扁平化嵌套文件夹**：自动将子文件夹中的快捷方式提取到开始菜单根目录
- **智能清理**：自动删除包含指定关键词的项目：
  - 卸载相关（卸载、Uninstall、Remove）
  - 官网相关（官网、Website）
  - 更新相关（更新、Update）
  - 帮助和文档（帮助、Help、Documentation）
  - 设置和关于（设置、Setting、关于）
  - URL 文件（.url）
- **无效快捷方式检测**：自动检测并删除指向不存在目标路径的快捷方式
- **保留系统文件夹**：智能过滤，保留必要的系统文件夹（附件、管理工具、启动、系统工具等）
- **预览模式**：在不进行修改的情况下预览更改
- **命令行界面**：易于使用的命令行界面，支持详细日志
- **可配置**：完全支持通过 JSON 配置文件自定义

## 系统要求

- Windows 10 或 Windows 11
- Python 3.8 或更高版本
- 管理员权限（用于修改系统开始菜单）

## 安装

### 从源码安装

```bash
git clone https://github.com/RuanCH/ClearWinStart.git
cd ClearWinStart
pip install -e .
```

### 依赖项

- `winshell`：用于解析 Windows 快捷方式
- `pywin32`：用于访问 Windows COM 接口

这些依赖会在安装时自动安装。

## 快速开始

### 基本用法

```bash
clear-win-start
```

工具会在处理每个路径前提示确认。

### 自动模式

```bash
clear-win-start --auto-confirm
```

处理所有路径，无需确认提示。

### 预览模式（Dry Run）

```bash
clear-win-start --dry-run
```

在不进行任何修改的情况下预览将要执行的操作。

### 详细日志模式

```bash
clear-win-start --verbose
```

启用详细的调试日志。

## 命令行用法

```
clear-win-start [-h] [--version] [--user-name USER_NAME] [--config CONFIG]
                [--paths PATHS [PATHS ...]] [--neglect-folders FOLDERS [FOLDERS ...]]
                [--delete-keywords KEYWORDS [KEYWORDS ...]] [--dry-run]
                [--auto-confirm] [--no-check-shortcuts] [--verbose]
                [--validate-only]
```

### 命令行参数说明

| 参数 | 说明 |
|------|------|
| `--version` | 显示程序版本 |
| `--user-name`, `-u` | Windows 用户名（未提供时自动检测） |
| `--config`, `-c` | JSON 配置文件路径 |
| `--paths`, `-p` | 要处理的额外路径 |
| `--neglect-folders`, `-n` | 整理时跳过的文件夹 |
| `--delete-keywords`, `-d` | 要删除的文件/文件夹关键词 |
| `--dry-run` | 预览更改，不实际修改 |
| `--auto-confirm`, `-y` | 跳过所有确认提示 |
| `--no-check-shortcuts` | 跳过快捷方式验证 |
| `--verbose`, `-v` | 启用详细日志 |
| `--validate-only` | 仅验证配置，不进行任何修改 |

## 配置

### 配置文件格式

创建 `config.json` 文件：

```json
{
    "user_name": "your_username",
    "paths": [
        "C:\\Users\\your_username\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs",
        "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs"
    ],
    "neglect_folders": [
        "Accessories",
        "Administrative Tools",
        "Startup",
        "System Tools"
    ],
    "delete_keywords": [
        "卸载",
        "官网",
        "更新",
        "帮助",
        "install"
    ],
    "check_shortcuts": true,
    "dry_run": false
}
```

### 使用配置文件

```bash
clear-win-start --config config.json
```

## 使用前提

### 文件夹权限

使用此工具前，请确保您对开始菜单文件夹具有写权限：

1. 右键点击文件夹 → 属性 → 安全
2. 点击"编辑" → "添加"
3. 输入您的用户名
4. 授予"修改"权限
5. 点击"确定"

需要检查的文件夹：
- `C:\Users\<用户名>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs`
- `C:\ProgramData\Microsoft\Windows\Start Menu\Programs`

## 项目结构

```
ClearWinStart/
├── clear_win_start/               # 主包
│   ├── __init__.py              # 包初始化
│   ├── __main__.py              # 模块入口
│   ├── cli.py                   # CLI接口
│   ├── core.py                  # 核心功能
│   ├── exceptions.py            # 自定义异常
│   ├── utils.py                 # 工具函数
│   └── py.typed                 # 类型标记
├── tests/                        # 单元测试
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_cli.py
│   ├── test_core.py
│   ├── test_exceptions.py
│   └── test_utils.py
├── docs/                         # 文档
│   └── README.zh-CN.md          # 中文文档
├── examples/                      # 示例
│   ├── example-usage.py
│   └── sample-config.json
├── .github/                      # GitHub配置
│   ├── workflows/
│   │   └── ci.yml              # CI/CD流水线
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── PULL_REQUEST_TEMPLATE.md
├── .gitignore
├── LICENSE                       # MIT许可证
├── README.md                     # 英文文档
├── pyproject.toml               # 项目配置
├── requirements.txt             # 开发依赖
└── tox.ini                      # Tox配置
```

## 开发

### 设置开发环境

```bash
git clone https://github.com/RuanCH/ClearWinStart.git
cd ClearWinStart
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest tests/
```

### 运行带覆盖率的测试

```bash
pytest --cov=clear_win_start tests/
```

### 代码质量检查

```bash
flake8 clear_win_start tests
black clear_win_start tests
isort clear_win_start tests
mypy clear_win_start
```

### 使用 tox 进行本地多版本测试

```bash
pip install tox
tox
```

## 贡献

欢迎贡献！请随时提交 Pull Request。对于重大更改，请先打开 Issue 讨论您想要更改的内容。

1. Fork 本仓库
2. 创建您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目根据 MIT 许可证授权 - 请参阅 [LICENSE](LICENSE) 文件了解详情。

---

**原作者: © Ruan CH**
