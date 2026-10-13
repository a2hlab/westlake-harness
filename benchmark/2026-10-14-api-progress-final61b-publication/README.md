# Physical publication depth

The core build places views under a build child, while its rendered links target the final MAIN package/views depth. Keeping the build child during landing would resolve links at the wrong level. The exact mapping flattens build/views into package/views without changing any core byte or generated view byte; actual binding/request/verification receipts go into this separate publication sibling.

The independent checker reads evidenceLinks from physically landed HTML, resolves each href from the real HTML parent, and verifies the exact evidence target and fullSHA. It never imports core.link or uses a fictional logical origin. Existing MAIN315 views provided a real-path control:142 evidence links per language and535 Markdown links, canonical JSON/CSV/bilingual rows315. This control is explicitly not new61b publication acceptance. Final actual MAIN validation remains null until the real new views are landed; wrong depth is rejected.

See [publication commands and mapping](PUBLICATION.zh.md) and publication.pending.json. Zero device operations, no MAIN writes, no core or current-round changes.
