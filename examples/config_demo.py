"""
配置管理演示脚本

这个脚本演示如何使用配置文件来管理删除关键词和其他设置。
"""

from clear_win_start.utils import Configuration, DefaultConfig, expand_env_vars
import json
import os


def demo_default_config():
    """演示默认配置加载"""
    print("\n" + "="*70)
    print("  演示1: 加载默认配置")
    print("="*70)

    DefaultConfig.load_from_file()

    print(f"\n✓ 配置文件已加载")
    print(f"\n删除关键词数量: {len(DefaultConfig.DELETE_KEYWORDS)}")
    print(f"保留文件夹数量: {len(DefaultConfig.NEGLECT_FOLDERS)}")

    print("\n删除关键词:")
    for i, keyword in enumerate(DefaultConfig.DELETE_KEYWORDS[:10], 1):
        print(f"  {i}. {keyword}")
    if len(DefaultConfig.DELETE_KEYWORDS) > 10:
        print(f"  ... 还有 {len(DefaultConfig.DELETE_KEYWORDS) - 10} 个")


def demo_path_expansion():
    """演示路径环境变量展开"""
    print("\n" + "="*70)
    print("  演示2: 路径环境变量展开")
    print("="*70)

    test_paths = [
        "%APPDATA%\\Microsoft\\Windows\\Start Menu",
        "%USERPROFILE%\\Desktop",
        "%LOCALAPPDATA%\\Temp",
    ]

    for path in test_paths:
        expanded = expand_env_vars(path)
        print(f"\n原始: {path}")
        print(f"展开: {expanded}")


def demo_create_config():
    """演示创建配置文件"""
    print("\n" + "="*70)
    print("  演示3: 创建自定义配置")
    print("="*70)

    config = Configuration(user_name="testuser")

    print("\n当前配置:")
    print(f"  用户名: {config.user_name}")
    print(f"  路径数量: {len(config.paths)}")
    print(f"  保留文件夹数量: {len(config.neglect_folders)}")
    print(f"  删除关键词数量: {len(config.delete_keywords)}")
    print(f"  检查快捷方式: {config.check_shortcuts}")
    print(f"  预览模式: {config.dry_run}")

    output_path = "my-custom-config.json"
    config.to_file(output_path)

    print(f"\n✓ 配置已保存到: {output_path}")

    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            print("\n配置文件内容预览:")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:500] + "...")

        os.remove(output_path)
        print(f"\n✓ 测试文件已清理: {output_path}")


def demo_load_config():
    """演示加载配置文件"""
    print("\n" + "="*70)
    print("  演示4: 从文件加载配置")
    print("="*70)

    config = Configuration(
        user_name="customuser",
        paths=["%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs"],
        delete_keywords=["卸载", "官网"],
    )

    print("\n自定义配置:")
    print(f"  用户名: {config.user_name}")
    print(f"  路径: {config.paths[0]}")
    print(f"  删除关键词: {config.delete_keywords}")


def main():
    """运行所有演示"""
    print("\n")
    print("╔" + "═"*68 + "╗")
    print("║" + " "*20 + "ClearWinStart 配置管理演示" + " "*13 + "║")
    print("╚" + "═"*68 + "╝")

    try:
        demo_default_config()
        input("\n按 Enter 键继续演示...")

        demo_path_expansion()
        input("\n按 Enter 键继续演示...")

        demo_create_config()
        input("\n按 Enter 键继续演示...")

        demo_load_config()

        print("\n" + "="*70)
        print("  演示完成！")
        print("="*70)
        print("\n提示:")
        print("  1. 编辑 default-config.json 来自定义默认配置")
        print("  2. 使用 --wizard 参数生成交互式配置")
        print("  3. 查看 README 了解配置文件的完整格式")

    except KeyboardInterrupt:
        print("\n\n演示已取消")
    except Exception as e:
        print(f"\n演示过程中出现错误: {e}")


if __name__ == "__main__":
    main()
