# Ordinary recents close and later desktop reopen

The observations must not be merged into one continuous window. A new host process does not prove a new article child or a successful feed. This report records an observed white-screen reopen; its cause remains unknown. No application/runtime source change, repair, deployment or seal occurred. This author only reviewed existing private evidence offline.

All private roots below are under `$HOME/.local/share/westlake/`. Exact selected paths, byte counts and SHA256 are in [raw-manifest.json](raw-manifest.json); personal raw logs remain private. [results.json](results.json) contains sanitized identities, command timing, screenshot pins and cleanup. [facts.txt](facts.txt) is computed from received image receipts, process roles and successful UI command receipts, not planned counts.

| Separate window | Original evidence and outcome |
| --- | --- |
| `recents-close-reopen-20261024` | `raw/04/vswipe.*`: ordinary card-close swipe at 12:23:51–52 +08. `raw/00/pre.ident.json` → `raw/04/post.ident.json`: host 4958/birth10879 no longer present in the post-sample; parent5129/birth11126 and child22035/birth6535369 remain. `raw/05/wait.start` 12:24:05 → `wait.timeout` 12:24:35: GO wait expired, no reopen/click. `DONE`: cleanup completed 12:24:42. |
| `desktop-reopen-20261024` | `raw/06/home.*`: Home at 12:27:56; no target found per operator report, no click receipt. This was an intermediate non-click window, not a failed target launch. `DONE`: cleanup 12:28:12. |
| `desktop-reopen-02-20261024` | `raw/06/click.stdout:1–3`: one target click bracketed by device uptime **70394.33 → 70394.69**, local 12:31:27–28. Four white samples; `raw/07/home.*`: return Home at 12:33:37–38. `DONE`: cleanup 12:33:40. |

The boot remains `61aa5791-fd69-4bbb-a7b5-333b5d913c81`. Final `raw/06/t{10,30,60,90}.ident.json` all bind **new host10486/birth7039472**, **old child22035/birth6535369**, and **parent5129/birth11126**. The child is present in each sample, not proven continuously executing or attached to the new host. Transient recorder shell rows are excluded from role counts.

| Sample | Identity sample device uptime | Original visual review | Public image |
| --- | ---: | --- | --- |
| t10 | 70405.63 | Outer: white | [t10](screenshots/t10.jpeg) |
| t30 | 70425.57 | Author: white; not claimed outer-reviewed | [t30](screenshots/t30.jpeg) |
| t60 | 70455.59 | Outer: white | [t60](screenshots/t60.jpeg) |
| t90 | 70485.39 | Outer: white | [t90](screenshots/t90.jpeg) |

Original review attribution comes from the outer closeout instruction; this report's author also inspected all four existing images offline. Sample labels are nominal: image capture command intervals are separately recorded in results, not equated to identity-sample uptimes. `raw/08/wms.stdout:15,29` records host10486/window62 and focus62 at local 12:33:30, **after t90 and before the final Home**, not at click time.

`desktop-reopen-02-observer-20261024` has **52 accepted samples**, `sample-0000.json` through `sample-0051.json`, spanning device uptime **70405.67–70494.12**. The first sample begins **10.98 seconds after click end**. All sampled parent ranges remain **281883→281883** bytes and event ranges **5744→5744** bytes; sampled child identity is unchanged. The 53rd command (`command-0052/receipt.json`) stopped on the configured **90-second total timeout** (`local_rc=-9`), not an observed application failure. There is no pre-click continuous coverage, nor proof of no activity during gaps, buffering, or truncate/regrow. These offsets cannot establish request absence or a white-screen cause.

All three windows record power **30000/10000 before and after**, `raw/09/unlock.rc=0`, `held.rc=1`, empty `held.stdout`. UI counts include unlock/navigation swipes; final Home count is **2**, target click **1**. Complete per-window counts and sampled process identities are in facts. Only four approved white screenshots are copied; all other UI images/layouts/logs stay private. Recompute offline with `python3 benchmark/2026-10-24-recents-close-desktop-reopen/check_evidence.py`; it never invokes device commands. [landing-paths.txt](landing-paths.txt) is the exact public delivery list; [manifest.json](manifest.json) pins public files except itself.
