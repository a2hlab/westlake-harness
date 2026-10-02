# U10.1T8 unbound-key long-wait baseline

The earlier t20-only `unbound_at_capture` classification did not establish process termination. This capture-only window records bind failures separately from native fatal events and leaves UI verdicts to the outer reviewer.

No runtime member, JAR, JIT setting or configuration was changed. Five requested keys were attempted once with reinstall, 95-second wait/hilog and t20/t45/t90 shots; frequent-habits could not be launched because the exact desktop icon was absent. The first mcdonalds input-root attempt failed its APK pin before install; its corrected attempt uses the original Mac input with the same SHA as the prior U12 record. The failed input attempt remains archived.

All windows completed within 20 minutes, with 318 before/after assertions, empty diff/absent, unchanged boot ID and dual fingerprints. Locks were released. Runtime: 5ea/5cd f3b604c94df4, 61b d6848fa2c989; boot e3806b65a079.

| Key | Bind observation | First exception cause |
| --- | --- | --- |
| cv2-com-frequent-habits | Not launched, unknown | exact desktop icon absent across searched pages |
| fd-im-vector-app | ensureBindApplication FAILED | Realm JNI cannot resolve libz.so |
| fd-plus | ensureBindApplication FAILED | android.bluetooth.le.ScanCallback missing |
| fd-libretube | ensureBindApplication FAILED | Application.onCreate cache size must be > 0 |
| mcdonalds | ensureBindApplication FAILED | Realm native cannot resolve libz.so |

None of the four launched-key logs contains a bind-returned-OK marker or the requested DfxFaultLogger/JniAbort/exit line. These are bind-failure observations, not proof of native termination. The LibreTube UI was separately signed by the outer reviewer as its own home page; the Application exception did not prevent that screen.

`results.json` lists exact lines, line numbers, all screenshot paths and hashes. `evidence/` contains portable copies of records, raw facts, bind excerpts, screenshots and before/final identity receipts. Original full logs and command records are preserved under `$WORKSPACES/westlake-inputs/generations/u101t8-unbound-longwait-20261003/`. Source is copied from `benchmark/2026-10-02-toutiao-longwait-cxt0/window.py` via import; no loader/runner criteria were weakened.
