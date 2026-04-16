# ClearWinStart - Windows Start Menu Organization Tool

**Original author: © Ruan CH**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python versions](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)

A powerful and easy-to-use tool for organizing Windows Start Menu by flattening nested folders and cleaning up invalid shortcuts.

## Features

- **Flatten Nested Folders**: Automatically extract shortcuts from subfolders to the Start Menu root directory
- **Smart Cleanup**: Automatically delete items containing specified keywords (uninstall, website, update, help, settings, etc.)
- **Invalid Shortcut Detection**: Automatically detect and remove shortcuts pointing to non-existent targets
- **Preserve System Folders**: Smart filtering to keep essential system folders (Accessories, Administrative Tools, Startup, etc.)
- **Dry Run Mode**: Preview changes without making modifications
- **CLI Interface**: Easy-to-use command-line interface with verbose logging
- **Configurable**: Fully customizable via JSON configuration files
- **Type Hints**: Full type annotation support for better IDE integration

## Requirements

- Windows 10 or Windows 11
- Python 3.8 or higher
- Administrator privileges (for modifying system Start Menu)

## Installation

### From Source

```bash
git clone https://github.com/RuanCH/ClearWinStart.git
cd ClearWinStart
pip install -e .
```

### Dependencies

- `winshell`: For parsing Windows shortcuts
- `pywin32`: For Windows COM interface access

These dependencies are automatically installed with the package.

## Quick Start

### Basic Usage

```bash
clear-win-start
```

### Automatic Mode

```bash
clear-win-start --auto-confirm
```

### Dry Run (Preview)

```bash
clear-win-start --dry-run
```

### Verbose Mode

```bash
clear-win-start --verbose
```

## CLI Usage

```
clear-win-start [-h] [--version] [--user-name USER_NAME] [--config CONFIG]
                [--paths PATHS [PATHS ...]] [--neglect-folders FOLDERS [FOLDERS ...]]
                [--delete-keywords KEYWORDS [KEYWORDS ...]] [--dry-run]
                [--auto-confirm] [--no-check-shortcuts] [--verbose]
                [--validate-only]
```

### Command-line Arguments

| Argument | Description |
|----------|-------------|
| `--version` | Show program version |
| `--user-name`, `-u` | Windows username (auto-detected if not provided) |
| `--config`, `-c` | Path to JSON configuration file |
| `--paths`, `-p` | Additional paths to process |
| `--neglect-folders`, `-n` | Folders to skip during organization |
| `--delete-keywords`, `-d` | Keywords for files/folders to delete |
| `--dry-run` | Preview changes without making them |
| `--auto-confirm`, `-y` | Skip all confirmation prompts |
| `--no-check-shortcuts` | Skip shortcut validation |
| `--verbose`, `-v` | Enable verbose logging |
| `--validate-only` | Only validate configuration, don't modify |

## Configuration

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
        "帮助",
        "install"
    ],
    "check_shortcuts": true,
    "dry_run": false
}
```

### Using Configuration File

```bash
clear-win-start --config config.json
```

## Prerequisites

### Folder Permissions

Before using this tool, ensure you have write permissions for the Start Menu folders:

1. Right-click the folder → Properties → Security
2. Click "Edit" → "Add"
3. Enter your username
4. Grant "Modify" permission
5. Click "OK"

Folders to check:
- `C:\Users\<username>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs`
- `C:\ProgramData\Microsoft\Windows\Start Menu\Programs`

## Project Structure

```
ClearWinStart/
├── clear_win_start/               # Main package
│   ├── __init__.py              # Package initialization
│   ├── __main__.py              # Module entry point
│   ├── cli.py                   # CLI interface
│   ├── core.py                  # Core functionality
│   ├── exceptions.py            # Custom exceptions
│   ├── utils.py                 # Utility functions
│   └── py.typed                 # Type marker
├── tests/                        # Unit tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_cli.py
│   ├── test_core.py
│   ├── test_exceptions.py
│   └── test_utils.py
├── docs/                         # Documentation
│   └── README.zh-CN.md          # Chinese documentation
├── examples/                      # Usage examples
│   ├── example-usage.py
│   └── sample-config.json
├── .github/                      # GitHub configuration
│   ├── workflows/
│   │   └── ci.yml              # CI/CD pipeline
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── PULL_REQUEST_TEMPLATE.md
├── .gitignore
├── LICENSE                       # MIT License
├── README.md                     # This file
├── pyproject.toml               # Project configuration
├── requirements.txt             # Development dependencies
└── tox.ini                      # Tox configuration
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/RuanCH/ClearWinStart.git
cd ClearWinStart
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/
```

### Run Tests with Coverage

```bash
pytest --cov=clear_win_start tests/
```

### Code Quality Tools

```bash
# Lint with flake8
flake8 clear_win_start tests

# Format with black
black clear_win_start tests

# Sort imports with isort
isort clear_win_start tests

# Type check with mypy
mypy clear_win_start
```

### Local Testing with tox

```bash
pip install tox
tox
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Original author: © Ruan CH**

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
