# ClearWinStart

**Windows 开始菜单整理工具**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python versions](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/RuanCH/ClearWinStart)](https://github.com/RuanCH/ClearWinStart/stargazers)

一个易于使用的 Windows 开始菜单整理工具，可以扁平化嵌套文件夹并清理无效的快捷方式。

**原作者: © Ruan CH**

---

## ✨ 功能特点

### 核心功能
- **📂 扁平化嵌套文件夹**: 自动将子文件夹中的快捷方式提取到开始菜单根目录
- **🧹 智能清理**: 自动删除包含指定关键词的项目（卸载、官网、更新、帮助、设置等）
- **🔍 无效快捷方式检测**: 自动检测并删除指向不存在目标路径的快捷方式
- **🛡️ 保留系统文件夹**: 智能过滤，保留必要的系统文件夹（附件、管理工具、启动、系统工具等）

### 高级功能
- **🔍 交互式预览窗口**: 执行前以美观的 GUI 风格预览所有操作，附带影响评估
- **📋 Dry Run 模式**: 详细预览执行计划，不实际修改系统
- **📝 配置文件向导**: 交互式分步配置生成器
- **📁 文件日志**: 自动日志轮转，敏感信息过滤
- **⚙️ 完全可配置**: JSON 配置文件支持，开箱即用的默认设置

### 开发者体验
- **💻 CLI 界面**: 易于使用的命令行界面，支持详细日志
- **🐍 Python API**: 程序化访问，便于集成到其他工具
- **✅ 类型提示**: 完整的类型注解支持，提升 IDE 体验
- **🧪 完善测试**: 全面的单元测试覆盖

---

## 📋 系统要求

- Windows 10 或 Windows 11
- Python 3.8 或更高版本
- 管理员权限（用于修改系统开始菜单）

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/RuanCH/ClearWinStart.git
cd ClearWinStart

# 开发模式安装
pip install -e ".[dev]"
```

### 基本用法

```bash
# 交互式预览模式（推荐首次使用）
clear-win-start --preview --user-name 你的用户名

# 自动模式
clear-win-start --auto-confirm --user-name 你的用户名

# 预览模式（仅预览，不执行）
clear-win-start --dry-run --user-name 你的用户名

# 使用配置文件
clear-win-start --config config.json
```

---

## 🎯 使用指南

### 交互式预览窗口

预览窗口提供美观的交互式界面，在执行操作前预览所有变更：

```bash
clear-win-start --preview --user-name 你的用户名
```

**预览窗口功能：**
- 📊 影响级别评估（低/中/高）
- 📂 按操作类型分类展示
- ✅ 清晰的操作确认
- 🎨 颜色编码信息
- ⚠️ 危险操作警告

### 配置文件向导

交互式生成配置文件：

```bash
clear-win-start --wizard --save-config 我的配置.json
```

### 命令行参数

```
clear-win-start [-h] [--version] [--user-name USER_NAME] [--config CONFIG]
               [--paths PATHS] [--neglect-folders FOLDERS] [--delete-keywords KEYWORDS]
               [--dry-run] [--auto-confirm] [--no-check-shortcuts] [--verbose]
               [--validate-only] [--log-file LOG_FILE] [--wizard] [--save-config SAVE_CONFIG]
               [--preview]
```

| 参数 | 说明 |
|------|------|
| `--preview` | 显示交互式预览窗口，包含详细操作计划 |
| `--dry-run` | 预览更改，不实际执行 |
| `--wizard` | 运行交互式配置向导 |
| `--config` | JSON 配置文件路径 |
| `--user-name`, `-u` | Windows 用户名（未提供时自动检测） |
| `--auto-confirm`, `-y` | 跳过所有确认提示 |
| `--no-check-shortcuts` | 跳过快捷方式验证 |
| `--verbose`, `-v` | 启用详细（调试）日志 |
| `--log-file` | 日志文件路径（未指定时自动生成到 AppData） |
| `--validate-only` | 仅验证配置，不进行任何修改 |

---

## ⚙️ 配置

### 配置文件类型

项目使用两种配置文件：

1. **`default-config.json`** - 默认配置文件（定义全局默认行为）
2. **`config.json`** - 用户配置文件（自定义运行时配置）

### 默认配置文件（default-config.json）

此文件定义所有默认行为，包括：
- 删除关键词
- 保留文件夹
- 日志设置
- 备份设置
- 预览设置

**创建或编辑 `default-config.json`：**

```json
{
    "version": "1.0.0",
    "description": "ClearWinStart 默认配置文件",

    "user_name": "",

    "paths": {
        "user_start_menu": "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs",
        "system_start_menu": "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs"
    },

    "neglect_folders": [
        "Accessibility",
        "Accessories",
        "Administrative Tools",
        "Startup",
        "System Tools"
    ],

    "delete_keywords": {
        "chinese": ["卸载", "官网", "更新", "帮助", "意见", "设置", "关于"],
        "english": ["install", "Website", "Setting", "Documentation", "Help"],
        "other": [".url"]
    },

    "check_shortcuts": true,
    "dry_run": false
}
```

### 用户配置文件（config.json）

用于运行时配置，可完全覆盖默认值：

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
        "help",
        "install"
    ],
    "check_shortcuts": true,
    "dry_run": false
}
```

### 配置文件查找顺序

程序按以下顺序查找配置文件：

1. 当前目录下的 `default-config.json`
2. 项目根目录下的 `default-config.json`
3. `%APPDATA%\ClearWinStart\default-config.json`
4. 使用内置默认值

### 环境变量支持

配置文件中支持环境变量：

- `%APPDATA%` - 用户应用数据目录
- `%USERPROFILE%` - 用户主目录
- `%LOCALAPPDATA%` - 本地应用数据目录
- `%PROGRAMFILES%` - 程序文件目录

### 默认设置

**保留的文件夹：**
- Accessibility（轻松访问）、Accessories（附件）、Administrative Tools（管理工具）、Desktop.ini、维护、Startup（启动）、System Tools（系统工具）、Windows PowerShell

**删除关键词：**
- 中文：卸载、官网、更新、帮助、意见、设置、关于
- 英文：install、Website、Setting、Documentation、Help
- 其他：.url

---

## 💻 Python API

```python
from clear_win_start import StartMenuOrganizer, Configuration
from clear_win_start.preview import PreviewWindow, create_preview_from_stats

# 创建配置
config = Configuration(user_name="testuser")

# 创建组织器
organizer = StartMenuOrganizer(config)

# 生成预览
stats = organizer.organize(auto_confirm=True, preview_only=True)
preview_report = create_preview_from_stats(stats, config.paths, config.user_name)

# 渲染预览
preview_output = PreviewWindow.render_preview(preview_report)
print(preview_output)

# 执行操作
stats = organizer.organize(auto_confirm=True)
print(f"处理的文件夹: {stats['folders_processed']}")
print(f"移动的文件: {stats['files_moved']}")
```

---

## 📁 日志

日志自动保存到：
```
%APPDATA%\ClearWinStart\logs\clear_win_start_YYYYMMDD.log
```

**功能特点：**
- 自动日志轮转（每个文件 10MB，保留 5 个备份）
- 敏感信息过滤
- 详细的时间戳和模块信息
- 独立的控制台和文件输出格式

### 自定义日志路径

```bash
clear-win-start --verbose --log-file custom.log
```

---

## 🧪 开发

### 设置开发环境

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/

# 运行带覆盖率的测试
pytest --cov=clear_win_start tests/

# 代码质量工具
flake8 clear_win_start tests
black --check clear_win_start tests
isort --check-only clear_win_start tests
mypy clear_win_start
```

### 项目结构

```
ClearWinStart/
├── clear_win_start/          # 主包
│   ├── __init__.py          # 包初始化
│   ├── __main__.py          # 模块入口
│   ├── cli.py               # CLI 接口
│   ├── core.py              # 核心功能
│   ├── preview.py           # 预览窗口
│   ├── utils.py             # 工具函数和配置向导
│   ├── exceptions.py        # 自定义异常
│   └── py.typed             # 类型标记
├── tests/                    # 单元测试
├── examples/                 # 使用示例
└── .github/                 # GitHub 配置
```

---

## 📚 文档

- [README.md](README.md) - 英文文档
- `examples/` 目录中的示例
- `examples/sample-config.json` 中的配置模板

---

## 🔧 故障排除

### 权限问题

使用此工具前，请确保您对开始菜单文件夹具有写权限：

1. 右键点击文件夹 → 属性 → 安全
2. 点击"编辑" → "添加"
3. 输入您的用户名
4. 授予"修改"权限
5. 点击"确定"

需要检查的文件夹：
- `C:\Users\<用户名>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs`
- `C:\ProgramData\Microsoft\Windows\Start Menu\Programs`

### 预览窗口显示问题

如果 Emoji 或框线字符显示不正确：
- 使用 Windows Terminal（推荐）
- 或在 CMD 中运行 `chcp 65001` 启用 UTF-8 编码

---

## 🤝 贡献

欢迎贡献！请随时提交 Pull Request。

1. Fork 本仓库
2. 创建您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

---

## 📄 许可证

本项目根据 MIT 许可证授权。

**原作者: © Ruan CH**

特此免费授予获得本软件及相关文档文件（"软件"）副本的任何人不受限制地处理本软件的权利，包括但不限于使用、复制、修改、合并、发布、分发、再许可和/或销售软件副本的权利，并允许获得软件的人员在满足以下条件的情况下这样做：

上述版权声明和本许可声明应包含在软件的所有副本或重要部分中。

本软件按"原样"提供，不提供任何明示或暗示的保证，包括但不限于对适销性、特定用途适用性和非侵权性的保证。在任何情况下，作者或版权持有人均不对因软件或使用或其他与软件相关的交易而产生的任何索赔、损害或其他责任负责，无论是在合同诉讼、侵权诉讼或其他诉讼中。

---

## 🙏 致谢

- 原作者：Ruan CH
- 贡献者和问题报告者

---

<p align="center">
  <strong>ClearWinStart</strong> - 让 Windows 开始菜单管理变得简单
</p>
