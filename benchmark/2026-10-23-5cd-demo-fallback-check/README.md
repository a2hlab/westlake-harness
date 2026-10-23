# T73 — 5cd demo fallback: one ordinary desktop Toutiao tap

Board 5cd (boot 89388a7b, no reboot), network connected, lock free; HAP b18978b8, toutiao cfg 19d0201b (differs from 61b), recover-v3 897f9ca0. No Toutiao child and no guardian process were running before the tap.

## Evidence
- After unlock the foreground was a blank white page (not a feed).
- One tap on the layout-located 今日头条 icon (WorkSpace_8, 736,507). t30, t60 (byte-identical to t30) and t120 screenshots are white; no Toutiao child appeared; network stayed connected.
- Returned to the desktop; power restored to the 5cd preimage (10000/10000) and read back; lock released.

## Result
FAIL: 5cd did not show the feed within 120 s of one ordinary tap, so it is not a demo fallback in its current state. The user's revised scope (feed on the next tap after a crash) does not change this run, which never showed a feed. No retry, no diagnosis.

Outer review: [outer-review.json](outer-review.json). 440 private manifest entries, eight cited receipts and five public image hashes checked. Private originals: `$HOME/.local/share/westlake/5cd-demo-fallback-check-20261023/`. This fallback was not accepted, even under the updated feed-only scope.
