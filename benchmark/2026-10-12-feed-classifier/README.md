# T11: observed feed layout classification

The original classifier returned unknown for all three visually confirmed r3 feed
captures. Its legacy feed branch required white(100,1800), which is inside changing
article imagery; its later branch fixed the selected-home red pixel at x150,
while the new layout puts that icon at x120. This was a deterministic classifier
miss, separate from the t10 screenshot-path fix and from runtime crash causality.

## Measured cause and narrow repair

The original source is main-tree `benchmark/2026-10-12-recovery-executor/src/screen_gate_feed.c`,
SHA `94a4a099241e62114f69e77d03473a182103acda889294fcace8d810f05cd6b7`,
landed in main commit `133cdc9c1162a8bbb4e7b8e223fd10674dd13e8d` from t0 `9436ed64b6`.
Original ARM SHA is `a0f5f55472e93338b490b89226aaf0436ee65b45191ce6f9f54be869781867fb`.
The existing r3 package and raw `r3-classifier-real/results.json` bind that original
classifier to the reported unknown/rc0 results.

`evidence/pixel-audit.json` records the measured points and region fractions.
Analysis uses macOS sips for pixel inspection; actual classification uses the
unchanged stb_image decoder, with both original and candidate results recorded.
For before/returned, (100,1800) is RGB(83,91,172); for refresh it is (145,153,166).
All fail white>240. In all three, (150,1840) is (255,255,255), while (120,1840)
is (250,67,51), a valid red icon pixel. Other original fallback chrome checks pass.
The archived accepted feed has the opposite x120/x150 behavior. Thus neither
original feed branch admits the new images. This does not establish anything
about the historical random SIG11 cause.

The new candidate appends one unknown-only branch. Six bounded regions must all
match, followed by the original dark-content count >180:

| Region, half-open coordinates | Colour | Required fraction | New feed observed |
| --- | --- | --- | --- |
| x5:55,y20:60,step2 | red header left | 80% | 92.0% |
| x1160:1190,y110:150,step2 | red header right | 75% | 83.7% |
| x350:950,y70:80,step3 | white search pill | 60% | 75.0% |
| x45:85,y245:251,step1 | red recommendation underline | 25% | 33.3% |
| x95:170,y1830:1875,step2 | selected-home icon | 25% | 40.2% |
| x950:1040,y1830:1880,step3 | white navigation background | 85% | 100% |

The dark article region remains x35:750,y275:660,step3. This is a conjunction of
independent chrome and content evidence; a red point, process lifetime or an
arbitrary picture cannot independently trigger it. All historical colour tests,
privacy/login priority and both old feed branches remain byte-for-byte unchanged.
`verify.py` removes only the new helper/call and compares the remainder exactly
with the frozen baseline. Unsupported size and decoder error behavior is retained.

The old `62-toutiao-after-pull-refresh.jpeg` is visibly **Westlake IME host**,
not feed; its unknown label is unchanged. The actual login sample is the historical
`2026-10-10-u13-autostart/evidence/61b-toutiao/61b-toutiao-cold3.png` (SHA6f555a6a…):
red top area, white X, login form and keyboard. It is not described as an entirely
red screen. Every full input SHA and original expected label is in `samples.json`.

## Build and verification

Candidate ARM `payload/screen-gate-feed` SHA:
`0bf966d76e038379af1fa2542746572a2c76a9bf88e17a97869682debfc36eaf`.
Candidate source SHA:
`54e73e9d20b2005d4b75b5dd1d639d24f54e8b6697c169f4d4d59a217aed0775`.
The original stb_image header is pinned at
`e4b91dc70192b9d998b0103c5e7e2abf531329a27309d239bee9057c519c4b24`.

`build.py` reuses the local DevEco clang15 OH recipe and rejects original compiler,
linker or libc pin drift. Build03 and build04 independently produced identical
ARM, host and baseline-host bytes. Each directory retains input SHA, complete argv,
raw stdout/stderr and actual exit codes. Build01/02 ARM compilation succeeded but
host compilation lacked a default system-header search path; those failed receipts
are retained. Build03/04 explicitly specify the existing macOS SDK sysroot.
No VM, remote build or download occurred. Rebuild to a **new** directory:

```sh
python3 benchmark/2026-10-12-feed-classifier/build.py --out /private/tmp/t11-new-build
python3 benchmark/2026-10-12-feed-classifier/verify.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test recovery_feed_classifier
```

Local results: **17/17**, comprising 12 captured screenshots and five explicitly
synthetic/error fixtures; all three Rust selectors pass. New r3 feed samples move
from baseline unknown to feed. Article, IMEhost, desktop, HelloWorld, ZigZag and
blank remain unknown; actual privacy/login remain exact; missing rc5 and truncated
rc7 are preserved. The synthetic login-anchor case supplements the actual login
sample; it is never reported as captured evidence. `evidence/clean-landing-*`
repeats the suite in a copied tree with private t4 Python reads forbidden. All small
binaries needed by tests are in the landing. Real screenshot inputs are external,
independently pinned local evidence, not regenerated substitutes.

Outer independently ran **10/10** exact-image cases on spare5ea, classifier SHA
0bf966…, boot `aa8245a6-dd86-4666-9706-2e36e86afdad`, Enforcing. It confirmed historical
feed, three new feeds, privacy/login, IMEhost/article rejection and corrupt/missing
rc5, then removed the SHA-checked probe files. Exact raw evidence references and
hashes are in `evidence/outer-arm-references.json`, pointing to main-tree
`benchmark/2026-10-12-v1-seal-execution/feed-classifier-arm/`.
This is outer's ARM ABI/fixed-image result; t4 performed zero board calls.

## Handoff boundary

`candidate-pin.json` and `arm-samples.json` were issued before outer's probe and
remain that immutable early handoff; the final ARM status is in `results.json`.
The source/package freeze does not sign a seal, activate a service, approve privacy,
or establish live recovery UI success. Integration belongs to the separate t0
composer together with t10. No guardian, t10 file, old freeze or native runtime was
modified. `landing-paths.txt` includes all candidate code, small test/build binaries,
raw receipts and the exact Rust selector; larger source screenshots stay at their
pinned local locations. New package pins must be derived from this final candidate.
