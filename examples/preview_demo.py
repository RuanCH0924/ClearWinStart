"""
Preview Feature Demo

This script demonstrates the interactive preview window functionality.
"""

from clear_win_start.preview import (
    PreviewWindow,
    InteractiveConfirm,
    create_preview_from_stats,
    ImpactLevel,
    PreviewReport,
    PreviewSection,
    PreviewItem,
    ActionType
)
from datetime import datetime


def demo_preview_window():
    """Demonstrate the preview window rendering."""
    print("\n" + "="*70)
    print("  预览窗口演示")
    print("="*70 + "\n")

    stats = {
        'folders_processed': 5,
        'files_moved': 12,
        'files_deleted': 3,
        'shortcuts_cleaned': 7,
    }

    paths = [
        r"C:\Users\TestUser\AppData\Roaming\Microsoft\Windows\Start Menu\Programs",
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"
    ]

    user_name = "TestUser"

    preview_report = create_preview_from_stats(stats, paths, user_name)
    preview_output = PreviewWindow.render_preview(preview_report)
    print(preview_output)
    print()


def demo_interactive_confirm():
    """Demonstrate interactive confirmation."""
    print("\n" + "="*70)
    print("  交互式确认演示")
    print("="*70 + "\n")

    print("演示菜单选择：")
    choice = InteractiveConfirm.show_execute_menu()

    print(f"\n您选择了: {choice}")
    print()


def demo_preview_report():
    """Demonstrate creating a detailed preview report."""
    print("\n" + "="*70)
    print("  详细预览报告演示")
    print("="*70 + "\n")

    report = PreviewReport(
        timestamp=datetime.now(),
        paths=[
            r"C:\Users\TestUser\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"
        ],
        user_name="TestUser"
    )

    report.add_item(
        "📂 文件夹处理",
        "📂",
        PreviewItem(
            action=ActionType.SKIP,
            name="将处理 5 个文件夹",
            reason="扁平化嵌套结构"
        ),
        "📂 文件夹整理"
    )

    report.add_item(
        "📦 文件移动",
        "📦",
        PreviewItem(
            action=ActionType.MOVE,
            name="Chrome.lnk",
            source=r"...\Browser\Chrome.lnk",
            destination=r"...\Chrome.lnk"
        ),
        "📦 文件移动"
    )

    report.add_item(
        "🗑️ 删除操作",
        "🗑️",
        PreviewItem(
            action=ActionType.DELETE,
            name="卸载XXX.lnk",
            reason="匹配关键词: 卸载"
        ),
        "🗑️ 删除文件"
    )

    report.add_item(
        "🔍 快捷方式验证",
        "🔍",
        PreviewItem(
            action=ActionType.VALIDATE,
            name="VSCode.lnk"
        ),
        "🔍 快捷方式"
    )

    report.impact_level = ImpactLevel.MEDIUM

    preview_output = PreviewWindow.render_preview(report)
    print(preview_output)
    print()


def demo_color_output():
    """Demonstrate color output."""
    print("\n" + "="*70)
    print("  颜色输出演示")
    print("="*70 + "\n")

    colors = ['header', 'success', 'warning', 'error', 'info', 'dim']

    for color in colors:
        text = PreviewWindow.color(f"这是 {color} 颜色", color)
        print(f"  {text}")

    print()


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "═"*68 + "╗")
    print("║" + " "*20 + "ClearWinStart 预览功能演示" + " "*19 + "║")
    print("╚" + "═"*68 + "╝")

    try:
        demo_preview_window()
        input("按 Enter 键继续演示...")
        print()

        demo_preview_report()
        input("按 Enter 键继续演示...")
        print()

        demo_color_output()

        print("\n提示：在实际使用中，交互式确认会等待用户输入。")
        print("运行以下命令测试预览功能：")
        print("  clear-win-start --preview --user-name 你的用户名")
        print()

    except KeyboardInterrupt:
        print("\n\n演示已取消")
    except Exception as e:
        print(f"\n演示过程中出现错误: {e}")


if __name__ == "__main__":
    main()
