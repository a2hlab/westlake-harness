# Tools

开发、生成、验证和诊断工具。

- `migrate_fn_atoms.py`：按历史文件名和相对子目录增量迁移；同内容文件不重复复制，
  并逐文件校验。
- `review_fn_migration_with_kimi.py`：每个 Fn 启动一次独立、只读的 Kimi 迁移挑刺；
  结果沿用 `veration-reviews/kimi-fn-migration-review.md`，已有结果默认跳过。
- `validate_fn_migration.py`：核对四域 ID、L→Fn 语义映射、依赖、全部历史文件哈希、
  生成文档链接和独立审查覆盖率；加 `--require-reviews` 可把 143 份审查设为硬门。
- `build-strategy-review-html.py`：根据 `docs/spec/concept-graph.yaml` 和
  `docs/concepts/Fnxx/` 生成自包含的 HTML 版 strategy review 控制台
  `docs/decisions/strategy-review-console.html`。
- `strategy-review-console.py`：CLI 版交互式 strategy review 控制台。
  保存 owner 选择到 `docs/decisions/records/`，并生成
  `docs/decisions/strategy-review-latest-report.md`。
- `build-concept-authority-pages.py`：为每个 Concept Domain 生成自包含的权威 HTML 页面
  `docs/authority/Fnxx.html` 及索引 `docs/authority/index.html`。聚合 `docs/spec/`、`docs/`、
  `var/evidence/`、`src/` 与独立评审（IEEE 编辑 + 大一学生各 2 轮）来源；输出术语表、周边关系、
  状态机、数据结构、历史案例、技术路线、工程轨迹、评审批注，以及本地 SVG/Mermaid 图和
  Gemini 图形 prompt。

使用说明见 `docs/decisions/strategy-review-console-usage.md`。
