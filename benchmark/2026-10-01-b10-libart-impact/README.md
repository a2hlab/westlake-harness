# B10: exact U8 missing-class exposure and BitVector impact

## What was wrong; what this report establishes

An absent class reference does **not** prove eager parsing, a startup crash, or an unlock count. Packlist can run on Android without the hidden `com.android.internal.util.Predicate` class. Adding that class to satisfy an inventory would hide the ART behavior under investigation. Likewise, `garbageSetBits=0`, another app's PID, or a positive line alone does not identify a BitVector crash victim.

The earlier U8 package `reference/{runtime,boot-image}.txt` files describe its **U7 baseline**, not the new target. Before opening DEX, `scan_classes.py` derives the U8 expected map from the frozen baseline plus the bundle's target members, binds the deployed 5cd final receipt, and runs `artifact_identity`: **11 DEPLOYED, exit 0**. See `identity.json`: nine boot jars, the separate 168-class runtime jar, and ART `59e1bb45294b9dd587dc9b81bad719b60675aa98c9c6cfced426449bcad0fe5f`. The runtime jar is not silently counted as a tenth boot jar.

## Complete static inventory

- **166 SHA/package-pinned APKs, 350 DEX, 38,099 boot classes**, plus 168 separately indexed auxiliary runtime classes.
- **2,563 distinct boot-plus-all-app-DEX-absent classes; 80,826 sites**. This includes invoke owners and signature types, fields, type instructions, superclass/interfaces, and declarations. Cross-DEX app definitions are resolved before calculating absence.
- Sites: **10,164 startup-chain candidates / 1,313 transition-timing unknown / 456 later-component candidates / 68,893 unanchored**. Key groups overlap: **73 / 23 / 5 / 133** respectively. `MISSING-CLASSES.csv` has one row per key; `CLASS-CLUSTERS.json.gz.b64` ranks classes by referenced-key count, not predicted deaths.
- Application/factory/main-process providers and selected launcher are startup roots. Literal Activity routing is stage 2; other declared Activities are stage 3. These are conditional static paths, not proof of execution, first-frame order, or t20 timing. Unreached sites and type-pool-only types stay unknown rather than becoming late-only.
- All references and sites were scanned without a count cap. The **60-second per-app staged-RTA budget** truncated only `toutiao` and `x`; their unanchored paths remain unknown. An earlier unbounded RTA run was stopped and is not the published result. The successful three-worker rescan completed all 166 APKs.
- Computed reflection, dynamic loaders/modules, framework-driven layout inflation, branch guards and unknown callbacks are incomplete. An absent type can be intentionally optional or resolve lazily. No binary repair or hidden-class addition is proposed here.

## Evidence and negative controls

`PACKLIST.json` identifies the sole Predicate key, `cv2-com-nbossard-packlist`: Application `PackListApp.attachBaseContext` → ACRA initialization/error-reporting callbacks → `LogCatCollector$1`'s implemented interface; `IOUtils.streamToString` also declares Predicate in its signature. The callback path is conditional and does not prove it ran during startup. Complete instruction coordinates and all paths are retained in the compressed full facts, not reduced to these illustrative examples.

The common absent `BluetoothManager` occurs in **86 keys, 57 previously signed lit**; `NsdManager` and `WifiP2pManager` each occur in **82 keys, 55 previously signed lit**. Those previously lit labels are the frozen B10 baseline labels, not a new U8 screenshot claim. `ooniprobe`, `noice`, and `fd-catima` are explicit lit negative controls with startup-candidate missing references. Their existence rules out turning this inventory into a hard missing-class startup gate.

## Selected U8 log evidence

The only admitted attempts are the outer-selected `5ea/5cd/61b-seq-{v1,cv2}` six roots plus `5cd-seq-v1-rest`. The latter supplies `fd-plus`, `fd-reader`, `fd-saber`, and `fd-mobile`. **Never use** the invalid concurrent `5ea-v1`, `5ea-cv2`, `61b-v1`, or `61b-cv2` runs. Every selected plan, receipt, APK/package and runtime/image fingerprint is checked before analyzing logs. The final cohort must contain exactly 166 unique keys; duplicate attempts, incomplete receipts or wrong state refuse with exit 2.

The original `fd-organicmaps` receipt records a *later cleanup interruption*, but its diagnostics completed and scheduled t20 was captured. The selected observation is retained, with `probe_status=batch_interrupted`, rather than discarding completed measurements. Incomplete interrupted probes are rejected. Captured screenshots do not imply lit: signed U8 t20 is a separate outer review.

`first_fatal.py` independently finds the first app-PID termination and its exception/crash root. Only target-PID `[IFACE-RAW]`/`[IFACE-BITS]` positive `garbageSetBits` observations enter the exposure table; zero and foreign-PID lines remain separate. Same-PID positives before the first terminal are **suspects**, with class/root co-occurrence separately marked, never asserted causal. Raw log SHA, PID/TID/time/line and cppcrash evidence are preserved. A positive process without a terminal is exposure only; a log without positives is not proof of clean ART.

## Reproduction and files

### Completed U8 BitVector observations

The selected 166-key sweep completed; the outer's 13:03:17 signoff (corrected state spelling at 13:03:28) hashes to `852488d17a5571b8bf931c0ea09a98b13a2a728216c8ff015c18330c3a905524`.

- **163 positive keys; 181,943 positive observations and 86,320 zero observations.** Three installer `app_failed` keys have no bound app PID and remain unverified, not clean.
- **53 temporal suspects**: 37 have class/root-text co-occurrence, 16 do not. These are deliberately broad investigation candidates, **zero established causal victims**. Generic framework/proxy classes can co-occur in an unrelated exception chain; this is not a validated method-slot linkage.
- **107 positive keys have no observed terminal**; three more (`cv2-com-bytehamster-flowitgame`, `fd-fennec_fdroid`, `firefox`) have process disappearance without an ordered terminal log event.
- **All 99 signed lit keys also contain positive bits**, as do 64 unlit keys. `ooniprobe`, `fd-stk`, and `aegis` are signed lit, positive, no-terminal controls. A blanket positive-bit death rule would falsely flag every lit app.
- `BITVECTOR.csv` has all 166 keys, exact signed white/black/launcher/dead labels, terminal/root coordinates and suspect status. `BITVECTOR-CLUSTERS.json.gz.b64` ranks all 67,014 observed positive class names. The eight names in each CSV row are explicitly examples, not the complete inventory.
- The compact full facts retain **every positive and zero observation** as `[line,time,pid,tid,class-index,bits]`, a class dictionary, full first-fatal roots and binding hashes. Original diagnostic message text is recoverable from SHA-pinned raw hilog at `source:line`; first examples are included. Correlation coordinates reference the same observations rather than duplicating them. No observations are capped.

```sh
source "$WORKSPACES/westlake-inputs/env-mac.sh"
python3 benchmark/2026-10-01-b10-libart-impact/scan_classes.py --workers 3 --output /tmp/libart-166-facts.json
python3 benchmark/2026-10-01-b10-libart-impact/report.py --facts /tmp/libart-166-facts.json --output /tmp/libart-report
python3 benchmark/2026-10-01-b10-libart-impact/scan_bitvector.py --output /tmp/libart-bitvector.json
python3 benchmark/2026-10-01-b10-libart-impact/report_bits.py --facts /tmp/libart-bitvector.json --output /tmp/libart-report --signoff "$WORKSPACES/westlake-harness/benchmark/2026-10-01-u8-sweep/outer-signoff.json"
python3 benchmark/2026-10-01-b10-libart-impact/test_impact.py
```

SDK 37 `aapt2`/`dexdump` and scanner dependency hashes are pinned in the output. Decode each `*.json.gz.b64` with base64 then gzip; decoded SHA is in the corresponding summary. The full class facts retain all 80,826 witness sites and paths while avoiding a 97 MB uncompressed checkout artifact. `results.json` provides the joint summary; `validation.json` records the two gates and lifecycle results. This is post-run descriptive B10 evidence, not a pre-run held-out prediction or an U8 UI scoring replacement.

`landing-paths.txt` lists only this task's new files. Apply `documentation.json`'s exact additions to master README/DIGEST; do not copy the whole shared files from this old worktree. Existing freezes/selectors and other lanes' work are unchanged. No device writes, push, or libart repair occurred.
