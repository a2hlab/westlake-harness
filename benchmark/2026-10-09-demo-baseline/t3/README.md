# Demo t3: selected 61b, unchanged U13

Fresh input resolution: 128/128 pinned package and APK identities passed in the
VM and Mac production view. APK bytes are 1,756,238,122; ×3 estimate is
5,268,714,366 bytes. The fresh 61b check reports all 319 unique U13 identity
paths equal (`diff={}`), runtime `452447a4a0ba`, boot `ee927db88a67`, and stable
boot `131b8ff9-2ead-4ee0-afe4-8700433d8bec`. Evidence:
`input-resolution-v1.{json,txt}`, `input-resolution-mac.json`, and
`prelock-v3/identity.json`. Frozen source check: 30 checked, zero violations.

The initial adapter mistake was treating the fingerprint API return as a dict
(it returns a string); the next attempt also counted child `appspawn-x` names
as parents. Both pre-lock attempts made zero board writes. The working hook
selects only name=appspawn-x, UID=0, PPID=1 and checks full expected SHA values;
it does not relax the identity comparison. Failed receipts remain preserved.

## Authorization and changes in procedure

Master manifest SHA: `7a2627326cb536bc8b0ee35587827999f448f827a91e22bdc663809767d82933`.
Outer ACK(91), 2026-10-09 21:35, authorizes installation and capture on 61b only.
The first window uses the unchanged master `board_run.py --detach`, 12 singleton
shards, 45-minute maximum, 35-minute new-key cutoff, current U13 activation smoke,
and read-only identity hooks before and after. No runtime, jar, installer,
service, ROM or other board is changed.

The user's 21:55 decision supersedes the first-tap procedure: the 94 historical
content packages are counted by the outer reviewer; the 32 empty first screens
are captured without tree reads or taps, recorded as `no_tap_map`. Window 1
finishes unchanged. Subsequent windows first install the remaining packages
once (`bm install -r`, preserving existing app data), then use the master
collector's `--launch-only` path. Between launches, only the existing targeted
cold-stop is used. No `bm uninstall` appears in the adapter.

`demo_board_run.py` reuses the master runner's lock, activation, observation,
cutoff and finally/unlock logic; only its batch executable is the scoped
`batch_adapter.py`. Its own `--detach` must re-enter this adapter, otherwise
master's re-exec would lose the launch-only mode. The plan fixes serial=61b.
No consumer or generic runner source is changed.

The original APK directories were copied unchanged from VM HOME to a persistent
shared WORKSPACES input directory so Mac supervision cannot expand `$HOME` to
the wrong machine. See `original-inputs-mirror.json`; all mirrored APK hashes
were resolved again on Mac. Corpus-v2 inputs keep their canonical shared root.

All current capture plans use t20. Once the mechanical stability groups arrive,
only subsequently dispatched stable captures may switch to t10. Edge cases,
games and empty first screens remain t20. Actual capture times are recorded;
missing capture remains unknown. No machine count is presented as a new lit
count. The outer loop signs screenshots/contact sheets.

## Tests and evidence

`test_adapters.py` runs without HDC: launch-only removes reinstall; a future t10
plan selects actual shots5,10; install uses replacement and targeted stop,
never uninstall. Six known answers pass on Mac and VM.

Every batch has a fresh output root, `board-run-result.json`, after-lock and
before-unlock identity receipts, and raw facts. The latter is printed unchanged
with its shard directory in PROGRESS(91). Artifacts and screenshots are retained;
large raw command logs remain on disk and are referenced, not removed.

The disabled supervisor dry run also caught a 29-character serial literal in
the new adapter before it was enabled. It was corrected to the exact 32-character
selected key. Known answers now require the full-key disabled plan to refuse
before spawning and the shortened key to refuse immediately, without HDC.

Window 1 has completed and unlocked. `window1-facts.txt` is the unchanged
run_facts output over a symlink-only index of the 12 regular shards (controls
excluded). Its aggregate fingerprint/tool fields are unknown because the index
has no shared baseline files; the exact per-shard identities remain in
`window1-all-shard-facts.txt`, and the final check is in
`window1-final-identity.json`. No image lit count is claimed.

Raw record.json and runner receipts include the original VM HOME paths. The
first landing preflight rejected these as data paths. They are actual recorded
evidence, not scripted path constants; the final preflight uses land.py's
documented `--allow-home-paths` option and preserves the records unchanged.
There are zero script user-path hits and zero oversized files. The outer land
command for this evidence must use the same recorded-evidence flag.
