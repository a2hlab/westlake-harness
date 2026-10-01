# N11f window observation shard — prediction (written BEFORE the window)

`n11f-window-prediction.csv` — the pre-window prediction for the N11f observation shard (18 keys: 14 U9
alive-white-window + `wikipedia` + 3 already-lit 61b canaries), produced by
`scripts/lab/predict_vs_actual.py predict` against the U9 baseline
(`2026-10-01-u9-sweep/outer-signoff.json`, 166 keys). Per the user rule, a sweep is only informative against a
prediction written first.

## Discriminator (NOT `unknown sessionId`)
`getOhNativeWindow: unknown sessionId` is **100% in the lit group** and 91% in white (`u9-sweep/base-rates.md`) — it is
not a white-window discriminator. The real signal for the N11f (single-copy bridge → single `sessions_` registry)
hypothesis is **whether the content activity's `BBQ.getSurface` returns an EMPTY Surface** in that key's U9 hilog:
- **empty ≥ 1** → a session was not rescued by the last-session `BBQ.update` (the `sessions_`-miss the u8-vs-u7 analysis
  pinned) → N11f's single shared `sessions_` rescues the content → **predict `lit?`** (passes this wall; next wall
  unknown, so a miss here is a wall the scanner didn't see).
- **empty = 0** (content got a non-empty Surface, or no content surface, or a different fatal) → not a `sessions_`-miss
  → N11f does not address it → **predict unchanged** (`alive-white-window`).

`--observed` on each row carries the per-key U9 evidence (the `BBQ.getSurface` empty/returning counts + any Java fatal).

## The 18-key prediction
| prediction | keys | basis |
|---|---|---|
| **`lit?`** (N11f rescues content) | `cv2-org-andresoviedo-dddmodel2`, `fd-noice`, `fd-uhabits`, `noice` | U9 content-session `BBQ.getSurface` **empty** (1 empty / 1 returning = the two-session last-rescue lottery lost the content) |
| **unchanged** (`alive-white-window`) | `x`, `cv2-dev-obfusk-jiten-webview`, `termux`, `cv2-ca-vaults-randomlydie`, `cv2-com-bytehamster-flowitgame`, `cv2-com-degeder-yam`, `cv2-com-paultirk-yatoo`, `fd-AppManager`, `fd-app`, `fd-shatteredpixeldungeon` | content got a **non-empty** Surface (white for app/GL/WebView render reasons) — or a non-surface fatal. Named other-causes: `x` = telephony cast NPE (`null→TelephonyManager`, needs phone fetcher); `jiten-webview` = 2 surfaces served, WebView content render; `termux` = no content `getSurface` at all |
| **`lit`** (must stay lit) | `wikipedia` (baseline lit — content stamped last by luck on U9 per u8-vs-u7; N11f makes it **deterministic**), `fd-k9`, `fd-com-amaze-filemanager`, `fd-libretube` (3 already-lit 61b canary controls — a regression here = N11f took something down) |

## After the window — compare
`predict_vs_actual.py compare --predictions n11f-window-prediction.csv --actual <signed N11f sign-off>`:
- `lit?` → **lit** = hit (N11f rescues the content as predicted); `lit?` → still white = **missed-wall** (the `sessions_`-miss
  wasn't the whole story for that key → feed the scanner: re-check `resolve_oh_wm_funcs` / a second copy outside the two owners).
- unchanged → still white = hit; unchanged → **lit** = `unexpected-lit` (N11f helped a key I predicted it wouldn't → find
  why, e.g. the content *was* a sessions-miss my empty-count missed).
- `wikipedia`/canary → not lit = **regression** (exit 1) — N11f broke a working path; stop and roll back.

Net prediction: **+4 lit** (sessions-miss keys) if N11f lands, wikipedia stays lit deterministically, 10 whites unchanged
(their walls are beyond the surface registry), 0 regressions. Ground truth = t20 screenshots, not `alive`.

Evidence: per-key U9 hilogs under `2026-10-01-u9-native/rollout/approved-j10g/…/<key>/hilog.txt` (`BBQ.getSurface`
empty/returning); `u9-sweep/base-rates.md` (unknown-sessionId non-discriminator); `u8-vs-u7-lit-analysis/README.md`
(the last-session-rescue mechanism); baseline `u9-sweep/outer-signoff.json`.
