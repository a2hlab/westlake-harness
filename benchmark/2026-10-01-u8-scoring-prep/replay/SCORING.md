# Three-freeze scoring

Mode: **cv2-structure-replay-not-U8**; observed 100/166 keys.

cv2 unknown is abstention; ActionBar tiers are risks, not a t20 binary prediction. WebView fallback is not functional lit.

## cv2 confusion

| Prediction | lit | lit-webview-fallback | alive-launcher-foreground | alive-blank-window | dead | app_failed |
|---|---|---|---|---|---|---|
| own-ui | 54 | 2 | 3 | 0 | 14 | 0 |
| unknown | 11 | 0 | 0 | 2 | 13 | 1 |

## ActionBar tiers

| Tier | Keys | Observed visual classes |
|---|---:|---|
| startup-or-calibrated-first-content | 21 | {"alive-launcher-foreground": 2, "dead": 8, "lit": 4, "unobserved": 7} |
| later-activity-only | 28 | {"lit": 19, "unobserved": 9} |

WebView exact t20: 5/7.

U7→current app-owned-UI changes: {"unchanged": 100, "unobserved": 66}.

All historical late/retrospective labels remain. First wall and checkpoints are not supplied by visual signoff.
Optional diagnostic roots are terminal-first/PID-bound and must match runtime/image facts; duplicate attempts are refused.
