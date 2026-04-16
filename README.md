# ClearWinStart

**Windows Start Menu Organization Tool**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python versions](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/RuanCH/ClearWinStart)](https://github.com/RuanCH/ClearWinStart/stargazers)

An easy-to-use tool for organizing Windows Start Menu by flattening nested folders and cleaning up invalid shortcuts.

**Original author: © Ruan CH**

---

## ✨ Features

### Core Functionality
- **Flatten Nested Folders**: Automatically extract shortcuts from subfolders to the Start Menu root directory
- **Smart Cleanup**: Automatically delete items containing specified keywords (uninstall, website, update, help, settings, etc.)
- **Invalid Shortcut Detection**: Automatically detect and remove shortcuts pointing to non-existent targets
- **Preserve System Folders**: Smart filtering to keep essential system folders (Accessories, Administrative Tools, Startup, etc.)

### Advanced Features
- **🔍 Interactive Preview Window**: Beautiful GUI-like preview of all operations before execution with impact assessment
- **📋 Dry Run Mode**: Preview changes without making modifications with detailed execution plan
- **📝 Configuration Wizard**: Interactive step-by-step configuration generator
- **📁 File Logging**: Automatic log rotation with sensitive information filtering
- **⚙️ Fully Configurable**: JSON configuration support with sensible defaults

### Developer Experience
- **💻 CLI Interface**: Easy-to-use command-line interface with verbose logging
- **🐍 Python API**: Programmatic access for integration with other tools
- **✅ Type Hints**: Full type annotation support for better IDE integration
- **🧪 Well Tested**: Comprehensive unit test coverage

---

## 📋 Requirements

- Windows 10 or Windows 11
- Python 3.8 or higher
- Administrator privileges (for modifying system Start Menu)

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/RuanCH/ClearWinStart.git
cd ClearWinStart

# Install in development mode
pip install -e ".[dev]"
```

### Basic Usage

```bash
# Interactive preview mode (recommended for first-time users)
clear-win-start --preview --user-name YOUR_USERNAME

# Automatic mode
clear-win-start --auto-confirm --user-name YOUR_USERNAME

# Dry run (preview only)
clear-win-start --dry-run --user-name YOUR_USERNAME

# With configuration file
clear-win-start --config config.json
```

---

## 🎯 Usage Guide

### Interactive Preview Window

The preview window provides a beautiful, interactive interface to review all operations before execution:

```bash
clear-win-start --preview --user-name YOUR_USERNAME
```

**Preview Window Features:**
- 📊 Impact level assessment (Low/Medium/High)
- 📂 Organized by operation type
- ✅ Clear action confirmation
- 🎨 Color-coded information
- ⚠️ Warning for potentially dangerous operations

### Configuration Wizard

Generate configuration files interactively:

```bash
clear-win-start --wizard --save-config my-config.json
```

### CLI Arguments

```
clear-win-start [-h] [--version] [--user-name USER_NAME] [--config CONFIG]
                [--paths PATHS] [--neglect-folders FOLDERS] [--delete-keywords KEYWORDS]
                [--dry-run] [--auto-confirm] [--no-check-shortcuts] [--verbose]
                [--validate-only] [--log-file LOG_FILE] [--wizard] [--save-config SAVE_CONFIG]
                [--preview]
```

| Argument | Description |
|----------|-------------|
| `--preview` | Show interactive preview window with detailed operation plan |
| `--dry-run` | Preview changes without making them |
| `--wizard` | Run interactive configuration wizard |
| `--config` | Path to JSON configuration file |
| `--user-name`, `-u` | Windows username (auto-detected if not provided) |
| `--auto-confirm`, `-y` | Skip all confirmation prompts |
| `--no-check-shortcuts` | Skip shortcut validation |
| `--verbose`, `-v` | Enable verbose (debug) logging |
| `--log-file` | Path to log file (auto-generated in AppData if not specified) |
| `--validate-only` | Only validate configuration, don't modify |

---

## ⚙️ Configuration

### Configuration File Format

Create a `config.json` file:

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

### Default Settings

**Preserved Folders:**
- Accessibility, Accessories, Administrative Tools, Desktop.ini, Maintenance, Startup, System Tools, Windows PowerShell

**Delete Keywords:**
- Chinese: 卸载, 官网, 更新, 帮助, 意见, 设置, 关于
- English: install, Website, Setting, Documentation, Help
- Other: .url

---

## 💻 Python API

```python
from clear_win_start import StartMenuOrganizer, Configuration
from clear_win_start.preview import PreviewWindow, create_preview_from_stats

# Create configuration
config = Configuration(user_name="testuser")

# Create organizer
organizer = StartMenuOrganizer(config)

# Generate preview
stats = organizer.organize(auto_confirm=True, preview_only=True)
preview_report = create_preview_from_stats(stats, config.paths, config.user_name)

# Render preview
preview_output = PreviewWindow.render_preview(preview_report)
print(preview_output)

# Execute operations
stats = organizer.organize(auto_confirm=True)
print(f"Folders processed: {stats['folders_processed']}")
print(f"Files moved: {stats['files_moved']}")
```

---

## 📁 Logging

Logs are automatically saved to:
```
%APPDATA%\ClearWinStart\logs\clear_win_start_YYYYMMDD.log
```

**Features:**
- Automatic log rotation (10MB per file, 5 backups)
- Sensitive information filtering
- Detailed timestamp and module information
- Separate console and file output formats

### Custom Log Path

```bash
clear-win-start --verbose --log-file custom.log
```

---

## 🧪 Development

### Setup Development Environment

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run tests with coverage
pytest --cov=clear_win_start tests/

# Code quality tools
flake8 clear_win_start tests
black --check clear_win_start tests
isort --check-only clear_win_start tests
mypy clear_win_start
```

### Project Structure

```
ClearWinStart/
├── clear_win_start/          # Main package
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # Module entry point
│   ├── cli.py               # CLI interface
│   ├── core.py              # Core functionality
│   ├── preview.py           # Preview window
│   ├── utils.py             # Utilities & config wizard
│   ├── exceptions.py        # Custom exceptions
│   └── py.typed             # Type marker
├── tests/                    # Unit tests
├── examples/                 # Usage examples
└── .github/                 # GitHub configuration
```

---

## 📚 Documentation

- [README.zh-CN.md](README.zh-CN.md) - 中文文档
- Examples in `examples/` directory
- Configuration templates in `examples/sample-config.json`

---

## 🔧 Troubleshooting

### Permission Issues

Before using this tool, ensure you have write permissions for the Start Menu folders:

1. Right-click the folder → Properties → Security
2. Click "Edit" → "Add"
3. Enter your username
4. Grant "Modify" permission
5. Click "OK"

Folders to check:
- `C:\Users\<username>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs`
- `C:\ProgramData\Microsoft\Windows\Start Menu\Programs`

### Preview Window Display Issues

If emoji or box characters don't display correctly:
- Use Windows Terminal (recommended)
- Or run `chcp 65001` in CMD to enable UTF-8

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

**Original author: © Ruan CH**

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## 🙏 Acknowledgments

- Original author: Ruan CH
- Contributors and issue reporters

---

<p align="center">
  <strong>ClearWinStart</strong> - Making Windows Start Menu Management Easy
</p>
