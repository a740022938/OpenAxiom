# OpenAxiom Release Notes

## v1.0.2 — Markdown Formatting Fix

- Rewrite README.md with proper multi-line Markdown
- Ensure all code blocks render correctly on GitHub
- Remove all hardcoded local path examples
- Use YOUR_* placeholders consistently
- No source code changes

## v1.0.1 — Documentation Hotfix

- Fix README clone URL to `https://github.com/a740022938/OpenAxiom.git`
- Fix Windows `.venv` activation command format
- Fix Markdown table and code block formatting
- Fix restore guide to use `YOUR_*` placeholders instead of hardcoded paths
- GitHub default branch changed from `master` to `main`
- No source code changes in this release

## v1.0.0 — GitHub 正式封板

### 里程碑
- 首个完整 Annotation MVP 工作流
- 支持单张安全保存/恢复（自动备份 + 二次确认 + 写入校验）
- 支持全数据集分批保存（批大小 5/10/20，多批执行器）
- 支持撤销/重做（Ctrl+Z/Y）、新增框、修改类别、删除框
- 支持低置信度复核队列 + 确认并下一个
- 支持保存前检查、YOLO 预览、MVP 总检查等质量门禁
- 支持批量检查 / 批量 YOLO dry-run
- 治理完成：旧 rc 备份清理、残留文件隔离、备份策略改进

### 先前版本

#### v0.4.5 — 治理收口版
- 治理摸底 → 残留文件隔离 → 旧备份清理 → 清理后复验
- 备份策略改进：source_only 备份，排除 .venv

#### v0.4.4 — 完整回归 + 操作区整理版
- 操作区 QTabWidget 重构
- 右侧 QSplitter + 信息区 QTabWidget
- 2000 label 全量分批保存完成

#### v0.4.3 — 批量保存完成版
- 多批保存执行器
- 审计统计修复
- 全量 2000 label 分批保存

#### v0.4.0 — 标注 MVP 正式版
- 产品正式命名 OpenAxiom
- 标注 MVP 闭环

### 说明
- 本仓库不包含数据集、模型权重或标注文件
- 数据集需单独准备 YOLO 格式数据
- 使用前请通过 `pip install -r requirements.txt` 安装依赖
