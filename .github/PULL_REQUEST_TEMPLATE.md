# Pull Request

## 变更类型

- [ ] Bug 修复（fix）
- [ ] 新功能（feat）
- [ ] 重构 / 优化（refactor / perf）
- [ ] 文档（docs）
- [ ] 测试 / 工程化（test / chore）

## 变更说明

<!-- 简要描述这个 PR 做了什么、为什么这么做 -->

## 关联 Issue

<!-- 例如：Closes #123 -->

## 自测清单

- [ ] 本地已运行 `pytest tests/ -q` 且全部通过
- [ ] 已运行 `flake8 clear_win_start tests --max-line-length=100 --extend-ignore=E203,W503`
- [ ] 涉及删除 / 移动逻辑时，确认仍走回收站（`send2trash`）且未破坏干跑预览
- [ ] 涉及交互界面时，已确认非交互环境（管道 / CI）仍能正常降级
- [ ] 文档（README / 配置示例）已同步更新

## 补充说明

<!-- 截图、日志、兼容性影响等 -->
