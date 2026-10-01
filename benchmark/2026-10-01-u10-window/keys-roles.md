# U10 window — per-board keys (carry-forward) + roles

finalize-checklist item 7, native-independent part. The three `keys-<board>.txt` are the **full 166-key
unified-state sweep, carried forward from the U9 sign-off board assignment** (`outer-signoff.json` `keys[].shard`
→ board = first token). A key stays on its U9 board so each key is compared against its own prior round on the
same board. **This supersedes the plan-draft §3 proposed beneficiary redistribution** — per outer ACK(90), keys
follow the U9 assignment, not a re-spread.

| board | keys | U10 beneficiaries (carry-forward board) | canaries (lit, non-flaky) | FZ controls on this board |
|---|---|---|---|---|
| `5ea34a45…` | 55 | `fd-meet` (abort-owner visibility / U10ShareResidentCompat) | `aegis`, `fd-feeder`, `ooniprobe` | FZ-005 aegis/ooniprobe, FZ-006 fd-feeder |
| `5cd1e3dd…` | 55 | `fd-fennec_fdroid` (strerror_r) | `fd-droidify`, `markor`, `newpipe` | FZ-004 fd-droidify, FZ-002 markor, FZ-003 newpipe |
| `61b0657200…` | 56 | `firefox` (strerror_r), `cv2-com-nbossard-packlist` (Predicate), `fd-tutanota` (J10f → white) | `fd-k9`, `fd-com-amaze-filemanager`, `fd-libretube` | FZ-001 fd-k9, FZ-004 amaze, FZ-007 fd-libretube |

Carry-forward naturally distributes the native fixes across boards: `abort-owner visibility` observed on 5ea
(fd-meet); `strerror_r` observed on **two** boards (fd-fennec_fdroid 5cd, firefox 61b); `Predicate` (jar) on 61b
(packlist). 

**Carry-forward `dead` keys (not beneficiaries, verified by first-wall move only):**
- `toutiao` (61b) — libstdc++ first wall clears, libjnigraphics → U11; expect first-wall move, not lit (v4).
- `mindustry` (5ea) — OpenSLES → U11; stays `dead` (v4).

**Smoke marker (every board):** `[U10-COMPAT-VISIBLE] inherit_requested` (APPSPAWN_LOGI, host
`resident-compat.h:39`), keyed to `helloworld` — the host prints it for every bridged app at namespace build, so
the always-launched control is the right marker key. fd-meet is **not** the marker key (the smoke does not launch
it); fd-meet's benefit is judged from its first wall in the full sweep.

**Deferred to window finalize (needs cx-bms U10 native合包):** combined jar+native `runtime_fp` in `u10.json`
(current `1833eb39872f` is jar-only), native `probe.files` (policy json + `libnativeloader.so` sha),
`after_lock`/`before_unlock` argv (deploy + rollback to U9 `565fc6fdc116`/`a2919b793eb6` + boot `4db882a81732`
+ 318 assertions).
