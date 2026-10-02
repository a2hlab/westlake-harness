# Installation service split: offline identity, behavior and alignment proposal

**The mistake was treating a shared Android runtime bundle as a shared installation
service state.** 5ea/5cd still use the original `2c9a5294` libinstalls;61b uses the
reviewed `51e1b525`. Moving Toutiao to5ea exposed this pre-existing extraction
difference, not a U10.1/T8 runtime regression. The older alignment draft also
overinterpreted a stripped call-set label and proposed extending a transaction
that already supports a one-library manifest. This report corrects both.

No board access, lock, deployment or restart occurred. The plan is disabled and
requires outer review and a separate user-present service window.

## Identity and lineage

| Role | Full SHA256 | Authoritative local bytes |
|---|---|---|
| Original / rollback | `2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0` | `$WORKSPACES/oh61-bms-kit-b79/board-baseline/libinstalls.z.so` |
| Later reviewed source artifact | `51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5` | `$WORKSPACES/oh61-bms-kit-b79/out/wukong100/bundlemanager/bundle_framework/libinstalls.z.so` |

Both board paths are `/system/lib64/libinstalls.z.so` and
`/system/lib64/platformsdk/libinstalls.z.so`. Existing service identity and
U10.1 recovery reports pin old on5ea/5cd and new on61b; the two aliases agree per
board. Evidence: master `benchmark/2026-10-01-installation-chain-identity/current-u9.json`
and `benchmark/2026-10-02-u10-1-t8-rerun/window/restored-{5ea,5cd,61b}.json`.

`deployed_whois.py libinstalls.z.so` was run first (`evidence/whois.txt`). Its
default native runtime bundle has **no service artifact**, and its169 **app** maps
have no service mapping. That is a scope limitation, not evidence that installd
is absent. The existing #79 `installs-live-r3.txt` includes libinstalls maps and
both `/proc/9037/root` hashes51e1; it is historical, not a new live measurement.
Current actual service-loader proof is explicitly unobserved in this task.

Old2c is the retained original board backup, also the source baseline used for
#77/#79 analysis. Its adjacent frozen `baseline-source/.../installd_operator.cpp`
hash is `dd2ad565fb1eded5c7e7a68a2c16580977d7e667a9856d39c2b53533e5db82de`.
This is **not** a claim that the old full ELF was byte-reproduced from that one file.

New51e1 follows #77 patch commit `22de5ddb52212f3640a7214194472e30991e0c65`
(exception approval digest refresh `e89d1af4fe7a29c4d095d5cebcb6367c3c87474f`),
then #79 source-build/61b validation `70fc62aa7e0369427f4ba22b1d370d2a58496eab`.
The matching candidate operator source SHA is
`7a6b2101c2fcf54a19ac2d1c9879cec144dd25b1d00d4b668b7fa17545b1d607`.
Both source snapshots were checked against #79 `source-toolchain.json`.
The final51e1 was unchanged between #79 rounds2/3; the round3 routing repairs
were in its companion BMS, **not** another libinstalls change. Do not resurrect
the failed initial43bcde50 artifact or deploy historical companion BMS2220df48.

Frozen OH clang SHA: `b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913`.
The final kit archive was independently hashed here:
`$WORKSPACES/oh61-bms-kit-b79-r3-final.tar.gz`,
SHA `61ff2def4508cafa6c1acd30c0c8436a5a760d5869a3520a140a216e39548bb6`.
Its recorded persistent remote copy is
`/home/alvin/westlake-oh6.1-b79-bms-2220df48-installs-51e1b525/oh61-bms-kit-b79-r3-final.tar.gz`.
This task read the local archive only. Full sources, objects, rules, linker/compiler
inputs and artifacts remain archived; no new native build occurred.

## What changed, shown from deployed bytes

`evidence/source.diff` is the complete operator snapshot difference. Old rejects
any selected-ABI nonconforming ELF, including Seal's three ZIP payloads and
Toutiao's ARM32 libcvt packaged under arm64. New keeps default ELF checking, then
allows these **four exact bundle + ABI + filename + payload-SHA tuples**:

| Bundle | arm64-v8a member | Payload SHA256 |
|---|---|---|
| com.junkfood.seal | libaria2c.zip.so | d3c2dc0a6db502aa1820cca94db978e793070bfb16c4fe7edfb72306837697bb |
| com.junkfood.seal | libffmpeg.zip.so | 68359d6cbac6adc021419ee7974f346721e5d8a306729e3e1bd771426375f3c6 |
| com.junkfood.seal | libpython.zip.so | 0210b1223ec8895a0b76679e643e777d37b4c6e4912ea6a95a0759e20bb0ae50 |
| com.ss.android.article.news | libcvt.so | 132e6c2058b9fa58df568a551ceddabef27cf6a03d8be915e464cd32520763af |

These are decoded **directly from new deployed ELF `.data.rel.ro` at131ad0**,
four32-byte rows, in `artifacts.json`. No directory-name or extension-wide bypass.
CRC, ZIP length, regular-file, UID/GID0, mode0755, destination/entry-set and SELinux
checks stay in place. Source witnesses include candidate operator3264–3280,
3287–3290,3302 and3348; the actual frozen table has **no whole-APK-SHA field**.
APK SHAs/byte counts in the approval JSON are provenance, not an additional CPP
predicate. Exact payload SHA still fixes its bytes/length. This preserves data
only; it does not make ARM32 code executable as ARM64.

Disassembly evidence (`entry-*.txt`, `extractor-*.txt`, `validator-new.txt`):

- Old CFI export117ba0 tail-branches to actual extractorc7a14.
- New CFI export118eac tail-branches toc8a14; supplemental unstripped symbols
  identify its12f0-byte body, table131ad0 and validatorcacac–cb450.
- The supplemental file's `.text`, `.rodata`, `.data.rel.ro` are byte-identical to
  the deployed51e1 sections before using those labels. Disassembly itself uses
  the **deployed stripped ELF**, not the supplemental file.
- New validator calls lstat@cad18, crc32@cae18/cae78, compares entry CRC atcaeac–caeb4,
  then tests ELF; on invalid ELF, bundle/ABI/name comparisons iterate32-byte rows
  atcaf60/cafb4/cb010, call Sha256File@cb070, compare hash@cb0c4, and log acceptance
  atcb2c0. The rejected default branch remains.

### String/call evidence: preserve the raw failures

Raw `deployed_strings_diff`: **29 dropped /41 added, rc1** (`evidence/strings.txt`).
Raw pointer/readelf-format fragments are included; they were not allowed or
silently stripped from the gate. A separate direct `.rodata` extraction has
**1 dropped /12 added** (`evidence/rodata-delta.json`): replace the generic
CRC/ELF error with a payload+filename diagnostic, add acceptance logging, and add
the four payload hashes, four names and two bundle names. This explanatory
normalization is not a waiver of raw diff review or all readonly data changes.

ABI:1096 exports→1096,0 removal/addition/signature drift. The raw call report
labels a single `strlen` addition as an `OnLoadSystemAbilityFail` nonvirtual
thunk. **Do not conclude that only that callback changed.** In stripped CFI ELF,
the label spans unlabeled internal functions; validator caf6c/cafc4/cb01c/cb080
actually calls strlen for the new tuple comparisons. Supplemental same-byte
symbols resolve that attribution. No consumers were supplied to this ABI command;
its0 consumer-break field is not a sampled consumer test. Final service-client
consumer/closure checks remain a required window gate.

B10 open-site scan: **2→2 sites,0→0 namespace edges**, same paths/flags:
libapk_installer via default NOW|GLOBAL atc7834→c8834, and the existing driver
installer at11284c→113b58. Both original **DEFAULT-NS** findings remain verbatim;
no new namespace edge or new open path, and no claim of dynamic owner safety.

## Existing install observations, not a paired experiment

`installations.json` selects each of166 signed U9 keys from its exact signoff
shard, including the61b Seal retest. Every install receipt/file SHA and every
exception/rejection/completion log line is recorded. All selected166 terminal
bm receipts say success. **Other165 excludes Toutiao**, not Seal.

| Signed selection | Version | Accepted / rejected / unknown | Native extracted lines | Exception lines |
|---|---|---|---|---|
| 5ea55 | old2c | 55 /0 /0 |147|0|
| 5cd55 | old2c | 55 /0 /0 |83|0|
| 61b56 | new51e1 |56 /0 /0|265|4|
| 61b other55, excluding Toutiao | new51e1 |55 /0 /0|127|3|

Thus the **other165** selected attempts are165 accepted /0 rejected /0 unknown.
This is a disjoint shard selection, **not165 paired installs under both binaries**
and not a proof of zero regression. Native extracted lines are not app counts.

Retain **three additional failed observations**, separate from the signed
successful selection:5ea Seal original and retry (Oct1),5ea Toutiao r2 (Oct2).
All have terminal `code:9568260` and operator3222 extraction rejection. The bm
shell command can return0 while printing failure; return0 alone must not count
as acceptance. Pooled available raw attempts:5ea55 accepted/3 rejected,5cd55/0,
61b56/0 (169 attempts,166 unique apps). Two failures are the same Seal APK;
do not treat them as two affected apps or discard them after61b success.

Representative original log witnesses (paths and complete SHA in JSON):

- Seal old5ea original `install-hilog.txt:123`, retry`:120`: operator3222 rejection;
  new61b`:260/:277/:291` accepts the three exact payloads and`:295` completes9 entries.
- Toutiao old5ea r2`:287`: operator3222 rejection; new61b U9`:280` accepts libcvt,
  `:404` completes138 ZIP entries. Same APK SHAa1112a0c. The physical sidecar list
  of137 is not the APK's138 selected-ABI extraction entries.
- Existing master `.../approved-j10g/evidence/seal-install-cross-board.json` also
  records5cd rejection; it is a **summary**, not an extra raw attempt in our counts.

Direct exception-table impact among the other165 is **Seal only**. The other164
packages are not tuple targets and stay on the strict default path by source
analysis. Existing new51e1 installs cover55 of the other165 (including Seal),
not all165 under the new binary. There is no reason to roll61b back to old2c and
lose reviewed acceptance; propose source51e1 for both old boards, subject to
gates. Benefits are installation acceptance, **not predicted extra lit apps**.

## Disabled alignment proposal and rollback

`alignment-plan.json`: **execution_enabled=false**,5ea first,5cd second,61b
read-only identity/owner confirmation. Each old board replaces exactly the two
libinstalls aliases above with source51e1. Preserve current BMS6aadb8b4 and
libapk_installer7048c7c5, runtime/JAR/native bundle and data. Any changed precondition
requires re-review; do not overlay an old #79 BMS pair.

`swap_installer.py` already derives its library list from
`manifest['candidate']` (lines47–48). A one-lib manifest suffices; no `--libs`
extension is needed. Actual **dry-run only**, with a local identical51e1 copy,
produced two paths per old board and `device_io=false`; it returns before `Board`
construction (line60). `evidence/transaction-dry-run-*.txt` are the real outputs.
No apply/restart/rollback command was run. Do not use `--accept-baseline`, which
overrides only BMS/APK pairs. Choose a fresh, per-board transaction name at the
eventual authorized window, not this diagnostic's name.

Before any swap: outer approval of this plan/string delta, original/source SHA
and archived inputs, ABI/client closure, B10 sites/namespace delta plus final
N1/N2 bindings, exact-payload positive/mutation/CRC/owner/mode tests, actual
installd maps/process-root identity, both aliases/backups and full current
runtime/boot/service snapshots. Our8 tests verify **offline evidence/policy
membership/counting/plan**, not native execution or a board's acceptance.

At a separately authorized **daytime, user-present** window, wait until all
promotion windows release their leases; use one idle board at a time and announce
foundation restart risk. It can reboot/drop USB and bind mounts. Snapshot the
actual currently signed generation, not the obsolete v3a/v4 recipe in the older
draft. Hash-verify each original2c backup, stage atomic replacements, restart via
the reviewed service mechanism, and inspect the new **installd** owner/maps;
foundation-only file-root reads do not prove the newly loaded service DSO.

Post-swap canary: fresh pinned Toutiao/Seal/X installs, exact payload readback,
HelloWorld/Zigzag install/control screenshots and retained companions. Then
other165 fresh-install regression coverage, with terminal accepted/rejected/unknown
receipts; APK/input identities pinned. UI remains separate outer screenshot
review. Check both aliases and actual loader, full identity and controls before
continuing to5cd. Any failure: stop, restore **both original2c aliases** from the
verified backup, restart/recover the exact current signed generation, re-verify
services/runtime/boot/controls and release only after evidence. If physical
reconnection is needed, wait for the user; no unreviewed parent kills or restarts.

Installation fingerprints already include both aliases since master8859d87899;
the current123-file fp split is565fc6fdc116 vs a2919b793eb6 on U9. Do **not**
re-add the old119-file gate or update runtime_fp by guess. Recompute the final
composition, unified service pins/318 assertions and final smoke expectations
after alignment; current per-board split must not remain an approved final state.
`expect.confirm/refute` in the JSON tells the future coordinator when to accept
the hypothesis or stop/roll back. This report does not authorize that window.

## Reproduce offline

```sh
python3 benchmark/2026-10-02-libinstalls-unification/audit.py
python3 benchmark/2026-10-02-libinstalls-unification/stats.py
python3 benchmark/2026-10-02-libinstalls-unification/dry_run.py
python3 benchmark/2026-10-02-libinstalls-unification/test_audit.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test libinstalls_unification
```

Raw tool stdout is retained under `.artifacts/`; public evidence changes only
exact workspace prefixes (and the documented nm symbol excerpt). Archive/input
SHAs and raw/published hashes are in `artifacts.json`. `landing-paths.txt` lists
only this deliverable; `documentation.json` supplies additive shared-doc lines.

## Portable-path regression (2026-10-02)

The original eight-test lane run missed a master-only failure: plain string
replacement of REPO treated `westlake-harness` as the prefix of the sibling
`westlake-harness-u7-executor`. It produced `$REPO-u7-executor`, which cannot be
expanded by the stats evidence checker. The fix matches the exact root or a
root followed by `/`, retaining sibling paths under `$WORKSPACES/`.

The same fix covers five helpers: this audit, toutiao-bionic-scope, SIGABRT,
disappeared and upstream-audio collection. Ten current Python tests include
both master/lane roots for every helper, embedded strings, the exact root, and
the actual 166 selected plus three diagnostic records with master REPO.
`path_prefix_replay.py` first reproduces the old FileNotFoundError and then
checks the corrected real records. The four Rust selectors remain green.

The real master and its index are outside this lane's writable roots. Instead,
the actual `land.py --no-commit` ran against a disposable clone of master,
with read-only sibling-worktree symlinks and a matching WORKSPACES layout.
`evidence/master-clone-land.txt` preserves its result: user-path and frozen
gates, admitted Python tests and Rust selector all pass. This is not a claim
that the real master was modified or committed. The outer loop can now run the
original landing command. The combined listing includes four helper updates
in addition to this not-yet-landed installation report; no board access.
