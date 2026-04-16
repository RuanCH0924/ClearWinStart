"""
Example usage of ClearWinStart as a Python module.

This script demonstrates various ways to use the ClearWinStart package
programmatically.
"""

from clear_win_start.core import StartMenuOrganizer
from clear_win_start.utils import Configuration


def example_basic_usage():
    """Basic usage with auto-detected username."""
    config = Configuration(user_name="your_username")
    organizer = StartMenuOrganizer(config)
    stats = organizer.organize(auto_confirm=True)
    print(f"Operation completed: {stats}")


def example_with_custom_config():
    """Custom configuration with specific settings."""
    config = Configuration(
        user_name="your_username",
        neglect_folders=["Accessories", "Startup", "System Tools"],
        delete_keywords=["卸载", "官网", "更新"],
        check_shortcuts=True,
        dry_run=True,
    )
    organizer = StartMenuOrganizer(config)
    stats = organizer.organize(auto_confirm=True)
    print(f"Operation completed (dry run): {stats}")


def example_validation_only():
    """Only validate paths without making changes."""
    config = Configuration(user_name="your_username")
    organizer = StartMenuOrganizer(config)
    errors = organizer.validate_paths()
    if errors:
        print("Validation errors found:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("All paths are valid!")


def example_custom_paths():
    """Process custom paths instead of default Start Menu locations."""
    config = Configuration(
        user_name="your_username",
        paths=[
            "C:\\Users\\your_username\\Custom\\Programs",
            "D:\\Apps\\Shortcuts",
        ],
        delete_keywords=["temp", "test"],
    )
    organizer = StartMenuOrganizer(config)
    stats = organizer.organize(auto_confirm=True)
    print(f"Operation completed: {stats}")


if __name__ == "__main__":
    print("Example 1: Basic Usage")
    print("-" * 50)
    # Uncomment to run:
    # example_basic_usage()

    print("\nExample 2: Custom Configuration")
    print("-" * 50)
    # Uncomment to run:
    # example_with_custom_config()

    print("\nExample 3: Validation Only")
    print("-" * 50)
    # Uncomment to run:
    # example_validation_only()

    print("\nExample 4: Custom Paths")
    print("-" * 50)
    # Uncomment to run:
    # example_custom_paths()
