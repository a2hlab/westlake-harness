# Signed lit-app metadata for leadership reporting

## Corrected count and evidence boundary

**129 signed test keys represent 128 distinct Android packages, not 129 different
applications.** `fd-noice` and `noice` are Noice versions 2.5.7 and 2.5.1, with
different APK bytes but the same package. Keep both requested evidence rows;
use one application card with a version note rather than count it twice.

The exact scope is the 126 `verdict=lit` rows in
`benchmark/2026-10-03-u14-stage-b/inputs/reference.json`, plus the three signed
window1 gains in `benchmark/2026-10-03-u14-stage-a-plan/window1-signoff/outer-signoff.json`:
VLC, 3D Model Viewer and Termux. No process-status inference or new screenshot
classification changes that scope. Source file SHAs are in `inputs/provenance.json`.

This is a **historical own-UI light-up inventory**, not proof that all functions
work, that U14 was promoted, or that all applications are currently retained on
all boards. In particular the signed gains include a 3D viewer menu dialog and
a Termux terminal with a bootstrap-install error dialog; VLC shows its welcome
page. Purpose sentences describe the application, not functions verified on OH.
WebView, camera, audio, network and gameplay capabilities must not be inferred
from these descriptions. The outer reviewer owns screenshot selection and layout.

## Deliverables and extraction

- `apps.csv`: UTF-8 with BOM for spreadsheet use; one row per requested key.
- `apps.json`: the same rows, plus count interpretation, duplicate packages and provenance.
- `purposes.tsv`: reviewed category and one Chinese purpose sentence per key,
  with the exact F-Droid evidence field used. No uncertain purpose was needed:
  all 128 packages have local F-Droid summary/description evidence.
- `inputs/apk-metadata.json`: selected run record/installation paths and SHAs,
  actual APK identities, manifest labels, resolved resource variants and source receipts.
- `inputs/fdroid-metadata.json`: selected local index names/summaries/categories
  and bounded description excerpts. These are descriptive metadata, not runtime evidence.
- `validation.json` and `evidence/validation/`: fresh local checks and receipts.

All 129 APKs were present locally. Each APK SHA/package was checked against the
signed reference run's `record.json`; cv2 APKs also matched `apps-v2.json`.
The three gains use their unique signed window1 run. `install.txt` contains the
installation receipt, but package/version/labels come from the verified APK,
not from the generic install-success text. No APK was downloaded or modified.

The requested `westlake-inputs/venv` androguard parses binary AndroidManifest
and resources directly; it does not analyze or execute app DEX. Chinese label
priority is APK `zh-rCN` → generic `zh` → other Chinese locales. English resources
and the default manifest label are preserved separately. Twenty rows have an
APK Chinese locale, fourteen fall back to a F-Droid localized name, and ninety-five
retain the original APK brand/name because a Chinese locale is absent. Some
Chinese locales deliberately retain an English brand. No invented Chinese brand
translation is labeled as an official resource. Every name records its source/locale.

Source counts by key: 38 F-Droid, 90 cv2 corpus (F-Droid), one third-party APK
(VLC via APKPure). The exact frozen index SHA matches 127 APKs. Noice 2.5.1 has a
matching local input receipt citing F-Droid versionCode66; VLC 3.7.1 has a matching
APKPure delivery receipt. Neither is silently declared an exact current index
match. Third-party distribution does not make open-source VLC a commercial app.
Unknown source attribution would remain `uncertain`; none is necessary here.

| Category | Distinct packages | Requested keys |
|---|---:|---:|
| Tools / 工具 | 36 | 36 |
| Productivity / 效率 | 33 | 33 |
| Games / 游戏 | 12 | 12 |
| Health / 健康 | 11 | 11 |
| Media / 影音 | 10 | 11 |
| System / 系统 | 10 | 10 |
| Graphics / 图形 | 5 | 5 |
| Communication / 通讯 | 4 | 4 |
| Education / 教育 | 4 | 4 |
| Reading / 阅读 | 3 | 3 |
| **Total** | **128** | **129** |

Categories are editorial browsing aids, not the F-Droid taxonomy. Separate
generic Notes, Shopping List and Calculator apps using their package/project
subtitle; a repeated title alone is not a duplicate app.

## Recommended leadership presentation

**Use an offline HTML gallery as the complete exhibit, plus a PDF for forwarding;
do not make a 129-slide deck the primary inventory.** HTML supports Chinese/English
name search, category filters, quick scanning and full-size screenshots. It can
use local assets only, without a CDN, remote fonts or internet access. A PDF is
the stable, easy-to-forward snapshot. A short PPT can summarize progress, but
should link to the full exhibit rather than replace the per-app evidence.

Suggested opening headline:

> 128 个不同应用的自有界面已签认上屏（129 个测试 key，含 Noice 两个版本）。
> 本清单反映指定批次的截图签认，不代表所有功能通过或当前三板统一保留状态。

Use a summary cover with the count/scope/date and category totals, followed by
one card per package: **one actual screenshot**, Chinese-priority/English name,
one Chinese purpose sentence, category and version. Keep package/key/evidence
links in the detail view. For Noice use one card with two version tabs/receipts.
Retain original screenshot aspect ratio and visible dialogs; do not crop away
errors or visually manufacture functionality. A menu/onboarding/error-dialog
screen needs that qualification next to the image. Highlight the three signed
gains without calling them three fully functional apps.

For a PDF appendix, use four cards per A4 landscape page (128 apps = 32 gallery
pages plus summary), with readable captions and category dividers. The short
leadership brief can show a few representative categories and refer to the
complete appendix. The outer reviewer selects and verifies every image before
publication; `screenshot_reference` here is only the existing signed run pointer,
not a new preferred screenshot or final selection.

## Reproduce offline

Refresh from original local evidence using the lab venv:

```sh
"$WORKSPACES/westlake-inputs/venv/bin/python" benchmark/2026-10-08-lit-apps-report/collect.py
python3 benchmark/2026-10-08-lit-apps-report/build_report.py
python3 benchmark/2026-10-08-lit-apps-report/test_report.py
```

`build_report.py` and tests use only committed snapshots and `purposes.tsv`;
they also work in a cold copy without `.artifacts`, the lab venv, original APKs
or external worktrees. `collect.py` is the explicit local evidence refresh and
must not be mistaken for an execution/board script. No board, lock, VM, SSH,
network request or screenshot selection is performed by this deliverable.
