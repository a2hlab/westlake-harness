# T104 — 5cd full desktop scan, one ordinary icon tap: feed at t+40 s

## Starting state and lock
At 20:21:59 no Toutiao child, imehost host or appspawn-x process was running. The lock was held from 20:22:08 to 20:25:13.

## Finding the icon
The desktop was scanned page by page (`coverage.tsv`). The exact target, `AppIconCommonView_org.westlake.imehost.EntryAbility`, is on **SwiperPage_Grid_WorkSpace_8**: bounds [600,371][873,644], center (736,507), clickable. T103 had checked only pages 0–2.

## One tap at 20:23:25
| Time after tap | Screen | Processes |
|---|---|---|
| +5 s | white | new host imehost 19801 and appspawn-x 19930 |
| +10 s | white | — |
| +26 s | white | new child `com.ss.android.article.news` 21639 (parent 19930) |
| **+40 s** | **feed**: recommend list with a video card | — |
| +60 s | feed kept | — |
| +90 s | feed kept | network IPv4 and route OK |

The +26 s sample was labelled t20 in the plan but was actually taken late; the actual capture times are in `run/t104-5cd/record.json`.

## Screenshot count
Quoted from `run/facts.txt` (`scripts/lab/run_facts.py` over the script-derived `record.json`): `shots 6/6`.

## Restore
Power was restored and read back as 10000/10000, matching the pre-check. The feed was kept on screen, and the board was unlocked. 61b was not touched.

## Scope
This is a 5cd baseline only. It is not a fix and not a cold power-cut signoff. The content's network origin is unknown.

## Outer review

The outer reviewer independently viewed s90 as a real feed; the sentry independently viewed s40. Facts were regenerated and matched. The +26s process sample establishes first observation, not birth time. Raw receipts are SHA-indexed in `raw-manifest.json` and preserved in its persistent private archive. This is one baseline launch, not a runtime repair or cold-power seal.
