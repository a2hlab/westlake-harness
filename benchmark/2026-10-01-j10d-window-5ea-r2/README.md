# J10d window result (5ea, 2026-10-01) — theme-restore fix lights 10/12 of the appcompat-actionbar + getActivityInfo cluster

**Result:** the J10d jar (`57d62183`, overlaid on U8 via `sweep_bind_deploy --bind`) makes **all 12**
appcompat-actionbar / getActivityInfo apps reach **alive_t20** (previously 0/0 for the two probed in
J10c — all died on the first-frame action-bar ISE). Smoke PASS; rollback to U8 byte-identical.
**Outer-loop screenshot read (ground truth): 10/12 lit** — dice, advancedpassgen, deadhash, knot,
diaspora, textpad, photophase, timerdroid, woefe-shoppinglist, privacyfriendlymemory. Two residual:
**itsdicey** (action-bar body still black — partial) and **yahtzeedicer** (still desktop) are alive at
t20 but not lit, i.e. the theme restore cleared the launch-fatal ISE but each has a second wall.

## Numbers (evidence first)

Shard `v1` (12 keys, `--reinstall --hilog --shots 5,20`):
```
TOTAL keys=12 screenshots_captured=24/24 alive_t5=12 alive_t20=12
```
Every key `alive t5=yes t20=yes` (`foreground_unconfirmed` — the 24 screenshots are the ground truth;
the outer loop reads them):

| key | t5 | t20 |
|---|---|---|
| cv2-com-aptasystems-dicewarepasswordgenerator | yes | yes |
| cv2-com-codedead-advancedpassgen | yes | yes |
| cv2-com-codedead-deadhash | yes | yes |
| cv2-com-deva-knot | yes | yes |
| cv2-com-emmanuelmess-itsdicey | yes | yes |
| cv2-com-github-dfa-diaspora-android | yes | yes |
| cv2-com-maxistar-textpad | yes | yes |
| cv2-com-ruesga-android-wallpapers-photophase | yes | yes |
| cv2-com-tomatodev-timerdroid | yes | yes |
| cv2-com-woefe-shoppinglist | yes | yes |
| cv2-org-secuso-privacyfriendlymemory | yes | yes |
| cv2-org-secuso-privacyfriendlyyahtzeedicer | yes | yes |

## The fix firing (smoke group-1, decisive marker reads)

```
[J10d-THEME] com.deva.knot.MainActivity theme=0x7f11019e (manifest 0x7f11019e; was 0x7f11019c)
[J10d-THEME] com.aptasystems.dicewarepasswordgenerator.MainActivity theme=0x7f0f0008 (manifest 0x7f0f0008; was 0x7f0f0006)
[J10-ACTINFO] synthesized self getActivityInfo com.aptasystems.dicewarepasswordgenerator/.MainActivity ...
```
`was 0x7f11019c` is the PARENT theme `Theme.Knot` (the value J10c read as `app windowActionBar=true`);
J10d restores the activity's own `Theme.Knot.NoActionBar` (`0x7f11019e`). The action-bar
`IllegalStateException` count dropped to **0** for both knot and dice. Note the two apps carry
*different* theme-resource pairs (knot `...019c→019e`, dice `...0006→0008`) — the fix is generic
(restore `activityInfo.theme` from the manifest), not hard-coded to one app, which is why it clears
the whole cluster rather than a single key.

## Smoke gate (14/14 PASS)

fingerprint `runtime_fp=f7fa0244c5a0` / `boot_fp=4db882a81732` (both groups) · controls helloworld/zigzag
alive_t20 · markers `[J10d-THEME]` (knot) + `[J10-ACTINFO]` (dice) · single-copy libart/libopenjdkjvm=1 ·
expected-copies bridge/runtime=2 · child-view jar `57d62183` + stubs `f3bcc9d7`. See `smoke/smoke-result.json`.

## Rollback (U8 restored, no stuck board)

```
ROLLBACK OK: RUNTIME=e953c0921536 BOOT=4db882a81732 byte_identical=True residual_mounts=0
```

## Note on the first attempt

The first window (`2026-10-01-j10d-window-5ea`) smoke-PASSed identically but the 12-key shard failed
with `unknown or duplicate requested key`: `board_run` passed the newline-delimited keys file as one
`--keys` string. Tool fixed (master `4644823af`: `raw.replace(',', ' ').split()`), re-run here.

## Ground-truth (outer-loop screenshot read, ACK j10d)

Per DIGEST B.7 **lit** is decided by the 24 screenshots, read by the outer loop. Read: **10/12 lit** —
dice, advancedpassgen, deadhash, knot, diaspora, textpad, photophase, timerdroid, woefe-shoppinglist,
privacyfriendlymemory. **itsdicey**: action-bar body still black (partial render — a second wall after
the ISE is gone). **yahtzeedicer**: still desktop. Both are alive_t20 with `[J10d-THEME]` applied, so
the theme restore removed the launch-fatal action-bar ISE for the whole cluster; the two residuals are
app-specific second walls, not a theme-restore miss. Screenshots: `v1/.../<key>/{t5,t20}.jpeg`.
