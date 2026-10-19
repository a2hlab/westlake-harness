# APK demonstration materials — 2026-10-19

The earlier gallery's broader historical counts must not be presented as the final61b functional acceptance count. This delivery uses the October 14 root decision: **128 baseline keys = 115 startup-only + 13 excluded**, plus **two separately scoped demonstrations** (Toutiao and BoatAttack). All 130 selected original images match their recorded delivery SHA256. No device was accessed.

## Delivery

All persistent products are in `delivery/`:

| File | Contents |
|---|---|
| `Westlake-精选演示-17页.pptx` | Cover, Toutiao, BoatAttack, 14 substantive startup interfaces; no welcome pages |
| `Westlake-全量分类-128加2.pptx` | 50 slides: two specials, 115 categorized startup entries, 13 excluded entries in an honest appendix |
| `全量图文清单-128加2.xlsx` | 130 rows and 130 embedded proportional screenshots; filters, scope, limitations, original paths and SHA256 |
| `全量清单-128加2.csv` | UTF-8 BOM, same 130-key inventory |
| `全量图文清单.html` | Offline searchable/category/status-filterable illustrated catalog; embedded thumbnails, links to originals |
| `raw-baseline-screenshots/` + `raw-baseline-index.json` | All 256 captured screenshots from 128 authoritative records, exact bytes and SHA/source index |
| `Westlake-完整离线包.zip` | Two PPTX + two PDF decks, XLSX/CSV/HTML, manifest, 130 selected originals, all 256 captured baseline originals and index; unpack together |
| `manifest.json` | Shared authoritative delivery rows with source bindings |
| `READY.json` | Current availability and verification state |

Application purpose is distinct from demonstrated functionality. Empty states, welcome screens and errors remain visible in the comprehensive inventory. The excluded entries are not counted as successful demonstrations. The curated deck deliberately chooses substantive controls, lists, grids and content instead of welcome screens.

The OneTwo purpose was narrowed from broad inherited metadata to “记录桌面游戏中的玩家生命值与分数”, supported by the visible four-player life-counter UI. Original metadata is retained in the manifest.

## Evidence and provenance

- Root acceptance: sibling `westlake-harness/benchmark/2026-10-14-final61b-full128-outer/{demo-list,results}.json`.
- Exact selected baseline images: root-reviewed recommendation `actual_image` and `actual_image_sha256` fields, copied from sibling `westlake-harness-t0/benchmark/2026-10-14-final61b-next-binding/actual-running-086db6c7/identity128/round/`.
- Names, categories and product purposes: that round's `batch-apps.json`, bound by key and `record.json`.
- BoatAttack: original `step-5-after.jpeg` in `2026-10-09-demo-boatattack/v2-20261013/outer/final61b-game-resume-086d/run/`, matching the SHA in `2026-10-14-final61b-game-resume-review/review.json`. This is a real water/boat/course image after reset, not a montage or host view.
- Toutiao: `$HOME/.local/share/westlake/toutiao-resume-20261019/video-live-r1/before-video-tap/screen.jpeg`; real feed content was visually inspected. This image does not prove video playback or network freshness.
- Package identity for the two additional keys: desktop inventory `manifest.json`; neither key belongs to the baseline 128.
- Layout conventions and proportional image technique reused from `benchmark/2026-10-08-lit-apps-gallery/build_pptx.py` at commit `b31b8b2d9a378feff2c45eac71aee4e78707b033`. The new deck uses one large application per curated slide and three per classified slide.

Original source-run facts, preserved verbatim in `evidence/facts.txt`:

```text
TOTAL keys=128 screenshots_captured=256/256 alive_t5=125 alive_t10=120 alive_t20=5
```

The 130 selected evidence images include 128 baseline selections and two specials. The additional `raw-baseline-screenshots/` contains all 256 baseline captured images (two per key), copied only from `captured=true` record entries and checked against recorded SHA256. Thus 128 selected image files overlap the raw set; these duplicates are not new measurements. Montages, smoke images and private logs are excluded. There are 386 image file placements across these two directories, representing 258 source screenshot selections (256 baseline captures plus two specials), not a new device run.

## Generation and checks

Use the persistent `.venv` with versions in `requirements.txt`:

```sh
M=benchmark/2026-10-19-apk-demo-materials
python3 -m venv "$M/.venv"
"$M/.venv/bin/pip" install -r "$M/requirements.txt"
"$M/.venv/bin/python" "$M/prepare.py"
"$M/.venv/bin/python" "$M/build.py"
"$M/.venv/bin/python" "$M/build.py" --full
"$M/.venv/bin/python" "$M/inventory.py"
"$M/.venv/bin/python" "$M/collect_raw.py"
"$M/.venv/bin/python" "$M/package.py"
"$M/.venv/bin/python" "$M/check_artifacts.py"
cargo test --manifest-path tools/spec-checks/Cargo.toml --test apk_demo_materials
```

`WORKSPACES` may override the sibling workspace root. Original source path tokens remain portable (`$WORKSPACES`, `$HOME`); no user-specific absolute path is hardcoded into scripts. Once originals and manifest exist, deck and inventory generation is independent of the source worktrees.

The Rust selector only calls the actual delivery checker. It validates the 115/13/2 partition against the root source, all original image hashes, ZIP relationships, exact per-key PPT image coverage, picture aspect ratio and zero crop, slide bounds, XLSX embedded image count, CSV/HTML coverage, all 256 captured baseline image hashes and source bindings, native PDF page counts and current OneTwo wording, and ZIP contents. Machine integrity checks do not replace native rendering and visual review.

## Compatibility observation

The first deck parsed successfully but failed import in Keynote Creator Studio. The outer operator then opened a minimal deck and the 17-slide `compat-no-notes-ea.pptx` in `/Applications/Keynote.app` 14.5 and visually inspected the cover, Toutiao and BoatAttack. The final generator adopts that compatible structure: public python-pptx APIs, no custom East Asian font XML, and external manifest instead of large JSON notes. Two variables changed, and the application also changed; **this does not establish that either XML feature caused the first failure**. The failed original and compatibility probes are retained in `evidence/` locally.

The installed `soffice` wrapper initially pointed at an absent application. Native rendering receipts and any remaining review limits are recorded separately from integrity in `delivery/READY.json` and `evidence/`.

No shared README/DIGEST, runtime or device state was changed. Main-tree board append was denied by the sandbox at lock creation; `delivery/PROGRESS.md` supplies updates for the outer operator to relay. No push is authorized or performed.

Final layout review: the inner agent inspected all 50 classified PDF pages using six contact sheets and enlarged pages 26, 40 and 46; no title, purpose or footer overflow was observed. The outer operator visually inspected all 17 curated pages. The corrected OneTwo page is re-exported from the canonical final PPTX before bundling.

## Rebuild from this checkout

The committed manifest and original images are sufficient to regenerate the decks and inventories. After creating the venv above, run `build.py`, `build.py --full`, and `inventory.py`; do **not** rerun `prepare.py` or `collect_raw.py` unless importing the original lab run again. Export the two PPTX files to same-name PDFs with LibreOffice, then run `package.py` and `check_artifacts.py`. Large office/PDF/ZIP delivery files are persistent local artifacts; raw images, generators, manifest and source indexes are retained in Git. No remote push has been performed.
