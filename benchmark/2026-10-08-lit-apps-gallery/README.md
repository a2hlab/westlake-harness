# Leader gallery of signed-lit apps: 128 apps, 94 shown with one historical t20 each

**What was wrong first.** The first cut of the gallery picked, for each key, the first signed screenshot it found.
That put white, empty-list and splash screens at the front, because "signed lit" only means the app drew its own
UI at t20. It does not mean the first screen has anything worth showing. The candidate list also started at
142 keys, because it included keys that had appeared only in a window and never entered the signed scope. A
mechanical audit by cx-bms (`../2026-10-08-lit-apps-gallery-check/`) then found three more errors:

- Package dedupe silently dropped the key `noice` (Noice 2.5.1, same package as `fd-noice` 2.5.7), so the
  129-key partition did not close.
- The source line said "128 from F-Droid". That counts APKs (129), but it sat under a 128-app headline.
- The PPT shortened two long app names without saying so.

**Scope (unchanged from the metadata package).** 129 signed-lit keys = the U14 stage-B reference (126 lit, i.e.
the promoted U13 unified state) + the 3 U14 window-1 gains (vlc, termux, cv2-org-andresoviedo-dddmodel2). That
is 128 distinct packages. No new screenshots were taken: every image is a t20 (or the signed eyeball shot) from a
signed run.

| tier | keys | meaning | in the gallery |
|---|---:|---|---|
| A | 95 (94 packages) | the app's own first screen with content and no error | one card each; `noice` is covered by the `fd-noice` card (`also_keys`) |
| B | 32 | lit, but the first screen is an empty list, a loader or an almost flat page (empty notebook, empty shopping list) | appendix A table, no image |
| X | 2 | lit, but the first screen carries an error dialog: fd-stk (SDL `dlopen_ns failed libSDL2.so`), termux (`Unable to install bootstrap`) | appendix B table, not counted as shown |

Partition check: shown keys + `also_keys` + B + X = **129/129 unique keys** (`report-data.json`, `partition_note`).
The cards are grouped into 10 categories: 效率 17 · 工具 27 · 影音 8 · 健康 10 · 游戏 10 · 系统 9 · 图形 4 · 教育 4 · 通讯 2 · 阅读 3 (= 94).

**Where the shown images come from.** Each image is the richest signed shot of that key, judged by the outer
loop's eyeball and not by tooling:

| source (tier-A keys, incl. `noice`) | images |
|---|---:|
| U14 windows 1–5 signed runs | 76 |
| U14 window 1/2 eyeball or gain shots | 6 |
| stage-B reference (U10.1T8 / U13 stage A) | 13 |
| total | 95 |

The pair-sheet sign-offs bind every path. cx-bms verified that 128/128 screenshot paths belong to their key's
signed run (wrong-object 0) and that 512/512 metadata fields match `apps.json` exactly.

## Rules this sets

1. **"Lit" and "presentable" are different claims.** A leader report counts signed-lit keys, but it shows only
   tier A. B and X are listed by name with their purpose, so the count stays honest and nothing is hidden.
2. **Report in one unit per sentence.** The headline uses packages (128). The APK count (129, Noice ×2) and the
   source breakdown each state their unit. Deduplicating never drops a key; the key moves to `also_keys`.
3. **Display aliases are declared.** PPT cards use the text before `・`/`：` (e.g. Organic Maps). The cover says so,
   and `index.html` keeps the full names.

## Files

- `curation.json`: per key, its tier, the reason, the chosen shot (`$WORKSPACES`-relative) and its source.
- `build_gallery.py`: writes `index.html`, `report-data.json` and `img/` to
  `$WORKSPACES/westlake-inputs/reports/2026-10-08-lit-apps/`. The HTML has search, category filter and
  click-to-zoom. Its print CSS gives A4 landscape with 16 cards per page; the PDF is rendered by
  `chrome --headless --print-to-pdf`.
- `build_pptx.py`: an 11-slide 16:9 deck. Cover with counts and 14 representative shots, 7 gallery slides of
  7×2 cards, 2 appendix slides.
- `results.json`: the counts above.

The binary outputs (HTML with embedded images 3.1 MB, PDF 13 pages, PPTX 11 slides) live in westlake-inputs and
are not committed. A rebuild from this directory reproduces `report-data.json` key for key.
