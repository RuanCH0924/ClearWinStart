"""
配置语义测试：区分「未配置」（沿用默认值）与「显式空列表」（确实不启用）。

覆盖 `delete_keywords` / `neglect_folders` 两处此前的静默回退缺陷：
用户写空数组本意是"什么都不删/不豁免"，旧实现会回退成内置默认关键词。
"""

import json

from clear_win_start.config import Configuration, DefaultConfig


class TestExplicitEmptyLists:
    def test_unset_falls_back_to_defaults(self):
        """未指定 → 沿用内置默认值"""
        config = Configuration(user_name="tester")
        assert config.delete_keywords == DefaultConfig.DELETE_KEYWORDS
        assert config.neglect_folders == DefaultConfig.NEGLECT_FOLDERS

    def test_explicit_empty_stays_empty(self):
        """显式空列表 → 保持为空（真的不启用），不回退默认"""
        config = Configuration(user_name="tester", delete_keywords=[], neglect_folders=[])
        assert config.delete_keywords == []
        assert config.neglect_folders == []

    def test_unset_sentinel_is_not_leaked(self):
        """构造后不应残留内部哨兵对象（两个字段是各自独立的列表）"""
        config = Configuration(user_name="tester")
        assert config.delete_keywords is not config.neglect_folders

    def test_from_file_explicit_empty_stays_empty(self, tmp_path):
        """配置文件中显式写空数组 → 保持为空"""
        path = tmp_path / "cfg.json"
        path.write_text(
            json.dumps(
                {"user_name": "tester", "delete_keywords": [], "neglect_folders": []}
            ),
            encoding="utf-8",
        )
        config = Configuration.from_file(str(path))
        assert config.delete_keywords == []
        assert config.neglect_folders == []

    def test_from_file_missing_keys_use_defaults(self, tmp_path):
        """配置文件未写这两个键 → 沿用默认值"""
        path = tmp_path / "cfg.json"
        path.write_text(json.dumps({"user_name": "tester"}), encoding="utf-8")
        config = Configuration.from_file(str(path))
        assert config.delete_keywords == DefaultConfig.DELETE_KEYWORDS
        assert config.neglect_folders == DefaultConfig.NEGLECT_FOLDERS

    def test_roundtrip_preserves_explicit_empty(self, tmp_path):
        """显式空列表经 to_file → from_file 后仍为空"""
        path = tmp_path / "cfg.json"
        Configuration(user_name="tester", delete_keywords=[]).to_file(str(path))
        reloaded = Configuration.from_file(str(path))
        assert reloaded.delete_keywords == []
