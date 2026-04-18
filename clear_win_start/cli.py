"""
Command-line interface for ClearWinStart.
"""

import argparse
import logging
import sys
from typing import List, Optional

from clear_win_start import __version__
from clear_win_start.core import StartMenuOrganizer
from clear_win_start.exceptions import StartMenuOrganizerError
from clear_win_start.utils import (
    Configuration,
    ConfigurationWizard,
    get_windows_username,
    get_default_log_path,
    setup_logging
)
from clear_win_start.preview import (
    PreviewWindow,
    InteractiveConfirm,
    create_preview_from_stats,
    ImpactLevel
)

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="clear-win-start",
        description="Organize Windows Start Menu by flattening nested folders and cleaning invalid shortcuts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  clear-win-start
  clear-win-start --user-name john --verbose
  clear-win-start --config config.json --dry-run
  clear-win-start --auto-confirm --no-check-shortcuts
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--user-name",
        "-u",
        type=str,
        default=None,
        help="Windows username (default: auto-detect from environment)",
    )

    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="Path to JSON configuration file",
    )

    parser.add_argument(
        "--paths",
        "-p",
        type=str,
        nargs="+",
        default=None,
        help="Additional paths to process",
    )

    parser.add_argument(
        "--neglect-folders",
        "-n",
        type=str,
        nargs="+",
        default=None,
        help="Folders to skip during organization",
    )

    parser.add_argument(
        "--delete-keywords",
        "-d",
        type=str,
        nargs="+",
        default=None,
        help="Keywords for files/folders to delete",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    parser.add_argument(
        "--auto-confirm",
        "-y",
        action="store_true",
        help="Automatically confirm all prompts",
    )

    parser.add_argument(
        "--no-check-shortcuts",
        action="store_true",
        help="Skip validation of shortcut targets",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (debug) logging",
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate paths and configuration, do not make changes",
    )

    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Path to log file (default: auto-generated in AppData)",
    )

    parser.add_argument(
        "--wizard",
        action="store_true",
        help="Run interactive configuration wizard",
    )

    parser.add_argument(
        "--save-config",
        type=str,
        default=None,
        help="Save generated config to specified path",
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="Show preview window with detailed operation plan",
    )

    return parser


def build_config(args: argparse.Namespace) -> Configuration:
    """Build Configuration from command-line arguments.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Configuration instance.

    Raises:
        ValueError: If required configuration is missing.
    """
    user_name = args.user_name or get_windows_username()

    if not user_name:
        raise ValueError(
            "Windows username not provided and could not be auto-detected. "
            "Please specify --user-name."
        )

    if args.config:
        config = Configuration.from_file(args.config)
        config.user_name = user_name
    else:
        config = Configuration(user_name=user_name)

    if args.paths:
        config.paths = args.paths

    if args.neglect_folders:
        config.neglect_folders = args.neglect_folders

    if args.delete_keywords:
        config.delete_keywords = args.delete_keywords

    config.dry_run = args.dry_run
    config.check_shortcuts = not args.no_check_shortcuts

    return config


def print_stats(stats: dict) -> None:
    """Print operation statistics.

    Args:
        stats: Statistics dictionary.
    """
    print("\n" + "=" * 50)
    print("Operation Statistics:")
    print("=" * 50)
    print(f"  Folders processed:     {stats.get('folders_processed', 0)}")
    print(f"  Files moved:           {stats.get('files_moved', 0)}")
    print(f"  Files/folders deleted: {stats.get('files_deleted', 0)}")
    print(f"  Invalid shortcuts:     {stats.get('shortcuts_cleaned', 0)}")
    print("=" * 50)


def run_wizard(args: argparse.Namespace) -> int:
    """Run the configuration wizard.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    setup_logging(verbose=args.verbose)

    try:
        wizard = ConfigurationWizard()
        config = wizard.run()

        save_config = args.save_config or input(
            "\nSave configuration to file? (press Enter for 'config.json' or enter path): "
        ).strip()

        if not save_config:
            save_config = "config.json"

        output_path = wizard.save_config(config, save_config if save_config else None)

        print(f"\nConfiguration saved to: {output_path}")
        print("\nYou can now run the tool with:")
        print(f"  clear-win-start --config {output_path}")

        return 0

    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled by user.")
        return 130
    except Exception as e:
        logger.error(f"Wizard error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv).

    Returns:
        Exit code (0 for success, 1 for error).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.wizard:
        return run_wizard(args)

    log_file = args.log_file if args.log_file else get_default_log_path()
    setup_logging(verbose=args.verbose, log_file=log_file)

    try:
        config = build_config(args)
        config.validate()

        if args.validate_only:
            print("Validating configuration and paths...")
            errors = []
            try:
                config.validate()
            except StartMenuOrganizerError as e:
                errors.append(str(e))

            organizer = StartMenuOrganizer(config)
            path_errors = organizer.validate_paths()
            errors.extend(path_errors)

            if errors:
                print("\nValidation errors:")
                for error in errors:
                    print(f"  - {error}")
                return 1
            else:
                print("All paths and configuration are valid.")
                return 0

        print("=" * 50)
        print("ClearWinStart")
        print("=" * 50)
        print(f"\nUser: {config.user_name}")
        print("\nPaths:")
        for path in config.paths:
            if "ruanc" in path.lower():
                print(f"  [USER] {path}")
            elif "programdata" in path.lower():
                print(f"  [SYS]  {path}")
            else:
                print(f"  {path}")
        print(f"\nDry run: {config.dry_run}")
        print(f"Check shortcuts: {config.check_shortcuts}")
        
        if args.dry_run:
            print("\n" + "⚠️  " + "=" * 46)
            print("⚠️  DRY RUN MODE - No changes will be made  ⚠️")
            print("⚠️  " + "=" * 46 + "\n")
        
        print("=" * 50 + "\n")

        organizer = StartMenuOrganizer(config)

        if args.preview:
            print(PreviewWindow.color("\n正在扫描并生成预览...\n", 'info'))
            stats = organizer.organize(auto_confirm=True, preview_only=True)

            preview_report = create_preview_from_stats(
                stats,
                config.paths,
                config.user_name
            )

            preview_output = PreviewWindow.render_preview(preview_report)
            print(preview_output)

            print("\n")
            action = InteractiveConfirm.show_execute_menu()

            if action == 'cancel':
                print(PreviewWindow.color("\n操作已取消", 'warning'))
                return 0
            elif action == 'backup_only':
                print(PreviewWindow.color("\n✓ 备份功能开发中（建议使用 --dry-run 预览）", 'info'))
                return 0
            elif action == 'rescan':
                print(PreviewWindow.color("\n正在重新扫描...\n", 'info'))
                return main(argv)
            else:
                print(PreviewWindow.color("\n正在执行操作...\n", 'info'))
                stats = organizer.organize(auto_confirm=True, preview_only=False)
                print_stats(stats)
        else:
            stats = organizer.organize(auto_confirm=args.auto_confirm)
            print_stats(stats)

        if args.dry_run:
            print("\nThis was a dry run. To apply changes, run without --dry-run.")

        return 0

    except StartMenuOrganizerError as e:
        logger.error(str(e))
        print(f"Error: {e}", file=sys.stderr)
        return 1

    except ValueError as e:
        logger.error(str(e))
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
