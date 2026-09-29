# 5cd graphics 32dfac83 device verification

The JNI registration fix works, but it does not establish that the white-screen family is fixed. K9, Tusky and Termux remain white. AppManager renders its validation page; HelloWorld, Auxio and Droid-ify retain visible UI. Screenshots, not `foreground_unconfirmed` or process liveness, support those observations. Outer visual acceptance remains pending.

A separate control corrected a test-input error: reinstalling ZigZag removes five generation-owned native bind mounts. With the raw APK libraries it aborts on missing `libmediandk.so`; restoring the same ledger's five original files, with the same runtime and Java, restores the game menu. This does not explain all historical ZigZag crashes.

## Deployment and scope

- User explicitly released 5cd and authorized this device follow-up after the original offline B12 delivery. B12 itself was not edited to broaden acceptance.
- Serial `5cd1e3dd00000000000000000923012c`; boot `a42f2d6c-d29d-40aa-8145-51b4f85d0187`; cx-t0 lock held during all mutations, released after final readback. No foundation restart or reboot.
- Native package `/Users/zhaoyue/orca/workspaces/westlake-runtime-graphics-session-sync-32dfac83-5cd`, manifest `30f63ef76b14a8ba2c1334940c66f5cc0e98aa4862152b81e6379f35d0b62c12`; only runtime `9e14bf20` → `32dfac83` replaced. Deployment evidence: `/Users/zhaoyue/orca/workspaces/westlake-generation-state/5cd1e3dd00000000000000000923012c/attempt-1790720205814298968`.
- At lock acquisition the actual JAR stack was r17m → r17q, not the earlier advertised r17m. Both layers were captured in [jar/original.json](jar/original.json), retired to package r8b for replacement, then restored bottom-up. Top SHA `94424d60b64468b494a9c1f7e0be0fb2bb763585d13cdcb795659089a044bac1` is the experiment's Java variable.
- First expose attempt retired r17q and stopped safely on the unexpected r17m layer. The stack-aware retry exposed r8b. Deployer then rejected missing original ZigZag mounts. Restoring those exact ledger mounts allowed normal deployment checks; no identity check was bypassed.
- Final [receipt](final/receipt.json): 117 live paths match declared hashes with the explicit Java overlay, installer unchanged, ledger `active_verified`. Deployer had already checked child maps, single ART and bridge identity. Graphics remains resident.

## Main batch, exact facts

Master `bms_batch.py`, nine keys in [controls.json](controls.json), `--execute --reinstall --hilog 20 --shots 5,20 --focus-check`. Preflight recorded all buffers 16.0M, private=false, screen timeout 86400000 ms and clock skew 2 s. [Predictions](predictions.csv) were recorded before launch. Raw runs remain under `runs/`; versioned records, process tables (trailing spaces trimmed only), JPEGs and log excerpts are in [evidence/graphics-32df-r17q-5cd](evidence/graphics-32df-r17q-5cd/).

```text
RUNTIME fingerprint=4b2e19554149 files=117 (runtime-fingerprint.txt; compare before blaming the JAR across boards)
fd-AppManager        shots 2/2  alive t5=yes t20=yes  child_hilog=24665  foreground_unconfirmed
fd-auxio             shots 2/2  alive t5=yes t20=yes  child_hilog=40873  foreground_unconfirmed
fd-droidify          shots 2/2  alive t5=yes t20=yes  child_hilog=33079  foreground_unconfirmed
fd-k9                shots 2/2  alive t5=yes t20=yes  child_hilog=36664  foreground_unconfirmed
fd-mobile            shots 2/2  alive t5=yes t20=yes  child_hilog=30318  foreground_unconfirmed
fd-tusky             shots 2/2  alive t5=yes t20=yes  child_hilog=29769  foreground_unconfirmed
helloworld           shots 2/2  alive t5=yes t20=yes  child_hilog=5707  foreground_unconfirmed
termux               shots 2/2  alive t5=yes t20=yes  child_hilog=7294  foreground_unconfirmed
zigzag               shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
TOTAL keys=9 screenshots_captured=18/18 alive_t5=8 alive_t20=8
```

| App | t5 / t20 visual observation | Interpretation |
|---|---|---|
| HelloWorld | Full Hello World lifecycle/actions UI | Control retained |
| AppManager | App Manager “正在验证…” 4.1.1 | Validation frame present; not main list; no same-run old-runtime A/B |
| Auxio | Five music tabs + music-source button | Control retained |
| Droid-ify | Explore / Installed / Updates, empty app list | Control retained; content loading not established |
| K9 | White | Prediction not met; BMS launcher was `net.thunderbird.app.common.MainActivity`, not expected UpgradeDatabaseActivity |
| Tusky | White | Prediction not met |
| Termux | White | Terminal not visible |
| fd-mobile | Black app content with system bars | Not visible app UI |
| ZigZag (reinstalled) | OH desktop | Input changed: five original native mounts absent |

All nine children log BLAST `registered 13/13`. The observed SC names match their own session IDs: HW492, AppManager495, Droidify498, Auxio500 and mobile504/505. K9/Tusky/Termux have no target `SC.create` or `oh_rs_flush_transaction` invocation in the captured interval, despite JNI registration. Do not count registration-table or ART method-list text as a function call. The remaining white-screen cause is not located by this sweep.

The first explicit process-fatal marker is in the reinstalled ZigZag log, line 16901:

```text
JNI FatalError called: Unable to load library: /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so [Error loading shared library libmediandk.so: (needed by /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so)]
```

No explicit target process-fatal marker was found in the other eight captured logs. Their records/process tables remain the liveness evidence. Several log `[B8-UEH] ... uncaught, thread ended (process kept alive)` exceptions; these are recorded separately in [results.json](results.json), not relabeled as process crashes.

## ZigZag input control

The missing mount state existed before graphics deployment and recurred after the requested reinstall. Raw APK `libil2cpp=74825000` / `libtuanjie=c5b4a64c` differ from generation `3bea2f16` / `eb9d8c6d`; `libmediandk` and `libwestlake_bionic_signal_box` are absent in the raw APK layout. `restore_control_mounts.py` only restores current-boot ledger-owned `payload/zigzag/` entries after source SHA checks, rejects foreign mounts and verifies targets. The post-reinstall restoration has its own [receipt](restore-after-reinstall/receipt.json); pre-deploy evidence is retained separately.

Then the same master runner used `--keys zigzag --launch-only` (no reinstall), same 32df runtime and r17q Java:

```text
RUNTIME fingerprint=4b2e19554149 files=117 (runtime-fingerprint.txt; compare before blaming the JAR across boards)
zigzag               shots 2/2  alive t5=yes t20=yes  child_hilog=12481  foreground_unconfirmed
TOTAL keys=1 screenshots_captured=2/2 alive_t5=1 alive_t20=1
```

Both [t5](evidence/graphics-32df-r17q-5cd-sealed-zz/zigzag/t5.jpeg) and [t20](evidence/graphics-32df-r17q-5cd-sealed-zz/zigzag/t20.jpeg) show “ZIGZAG / TAP TO PLAY / BEST SCORE: 0”. Keep this control separate from the requested nine-app facts. All five original mounts were retained at release.

## Verification limits

R2 verified: deployment SHA/maps/single ART, actual JNI registration, observed session-name binding and captured screenshots. Partially verified: graphics behavior (controls retain UI; target white screens remain). Unverified here: Wikipedia's two-window causal fix, to be checked independently by the 5ea owner. Screenshots are offered to outer review, not self-signed as final acceptance. No native code changed during this device follow-up; helper scripts were syntax-checked; the known-answer suite ran 69 tests successfully (2 skipped). Previous offline B12 lifecycle remains 5/5 from the accepted build report.
