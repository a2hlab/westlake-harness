# ACK(95): U6-T7c/J7b prospective freeze

**Verified offline.** No device operations, no push. Own branch `analysis/bms-route-study`, base `5a9984c8e`. Staging still fails with shared `index.lock: Operation not permitted`, exit **128**; outer-loop adoption is required.

## Freeze registration

- Version: **u6-t7c-j7b-v1**.
- Freeze time: **2026-10-01 03:13:07 +0800** (`FREEZE.json` records `2026-09-30T19:13:07.280966+00:00`).
- Board registration: **ACK(95) PROGRESS, 03:13:28 +0800**, before the combined U6 sweep; only prior U5/T7c-only/J7b-only evidence was consumed.
- CSV SHA256: **`b9a414ed0b70134e2b9dbd54be91dd843e130c5d3020acf905577e17ef419746`**.
- Old CSVs `bae8fd74` and `97014f71` are unchanged. Frozen files must not be regenerated in place. `forecast.py --verify` checks file hashes and independent output regeneration.

## Bound candidate and decisions

**T7c**, not T7d: 27 image files plus stubs `366acc27`; **J7b** `381110a6`; **U5 native**, not N5/N6. `expected-run.json` pins all 119 runtime paths, 36 boot paths and 66 APK/native inventories. The API catalog lists **5 T7c groups + 6 J7b groups + 3 input operations**, including each deliberate limitation.

66 predictions: **22 retain UI / 17 retain wall / 16 expected crossing / 9 uncertain or flaky / 2 input-blocked**. There are 24 own-UI forecasts (22 controls plus catima/opencamera), not 24 newly lit apps. Four registered flaky keys stay uncertain. Per-key first-wall hypotheses, log signatures, repair IDs and independent t20 criteria are in the CSV/JSON/Markdown table. The scorer keeps first-wall accuracy, checkpoint accuracy and t20 separate; absence of an error is not a crossing.

Five signed merged APKs were rescanned: **65 DEX / 115 native members**. Native counts burgerking/firefox/mcdonalds/subwaysurfers/x = **34/18/10/20/33**, all DEX hashes unchanged from base. Split/pin flags clear in the explicitly normalized target input set; Firefox mozglue and McDonald's Realm dependencies remain. The 59 unchanged keys are rehashed, and Seal/Toutiao are rescanned separately.

**Seal/Toutiao are not repaired in this freeze**, per the outer loop's direct reply. Metadata lists 6/137, physical directories still contain 9/138 libraries. The actual batch's first rejection is inventory disagreement, before bad ELF headers. The removed metadata entries still have physical ZIP/32-bit files; they must be quarantined outside the scanned native directory, originals retained. This forecast does not silently omit them. After cleanup/resolve, **make a new input-bound forecast version**, not a post-hoc edit of this one.

**Important distinctions:** reader is expected through vibrator/wallpaper/TagSoup but the next fatal remains unknown; Unciv/SPD are expected through vibrator without inventing an EGL result; WiFiAnalyzer's observed next fault is CountryPreference/wb0.H null, not a proven missing WifiManager method. Feeder's CoroutineStart hypothesis still needs causal first-blocker review; LibreTube remains unknown after TagSoup. T7d's planned extra methods are not counted as present.

## Landing list

Take only:

1. `benchmark/2026-10-01-u6-prospective/` (exclude `__pycache__`; exact file list in `landing-paths.txt`).
2. `specs/u6-prospective/`.
3. `tools/spec-checks/tests/u6_prospective.rs` (four **new** integration selectors; existing selectors unchanged).
4. The single new U6-prospective line in root `README.md` and `.octos/KNOWLEDGE-DIGEST.md`.

Do not take the other dirty/untracked branch files or old exception registries: they belong to earlier, already adopted deliveries. Do not overwrite master README/DIGEST with the stale branch versions. No commercial APK/JAR/ELF binary is included.

## Verification receipts

Fixed master **67065c88e40e4bb72649eba21003622ba0e71004** archive, only this delivery overlaid. Exact overlay identities and independent exits: `validation/gates.json`.

- `check_user_paths.py`: **exit 0**, initially 9562 files / 25 original exception entries / 0 violations; final all-delivery path sweep in `validation/final-paths.json`.
- `spec_checks.py`: **exit 0**, `GATE PASS: cargo_exit=101 passed=72 failed=9 excepted=9 unexpected=0`. Existing nine approved exceptions unchanged; **not zero cargo failures**.
- New Python tests: **9 pass**. New Rust selectors: **4 pass**. Known answers: **69 run / 2 skip / 0 fail**.
- Both contracts: lifecycle/explain **2 pass / 0 skip / 0 fail** each. Rustfmt, `git diff --check`, frozen-byte verification pass.

The archive test requires the normal lab environment, `WORKSPACES` pointing to the workspace parent and `CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc` on this Mac. The path gate receives all baseline paths plus new untracked paths explicitly, because the archive has no Git metadata. Post-freeze docs and validation receipts do not alter the CSV, evidence or scoring code. Deploy/run eligibility and all device-side gates remain the outer loop's responsibility.
