# v3c-next rollout on 5cd and 61b

The host-only ANL checks did not cover Unity's complete dependency closure.
The combined next package passes deployment SHA/maps gates, but ZigZag exits
on both boards because the app namespace cannot resolve `libhitrace_ndk.z.so`
needed by `/system/android/lib64/libandroid.so`. A deployment gate is not a
rendering verdict. Native rollback with the same r17m JAR is the isolation test.

## Inputs and boundaries

- Accepted base: `westlake-generation-v3c-candidate`, manifest `668e4f7c`.
- Candidate: `westlake-generation-v3c-next-audio-anl`, manifest
  `0aa46f8faef4eba9e6f5191ef39835dd83d2b8457a765b590d9734a0ce53015b`.
- Candidate runtime `f87dcdf9`, both ANL aliases `b66f1b60`.
- Java variable: r17m
  `a5cbd8d77ad7cb1592db5d64f9ec1f7ce7da9732fdbe8c4b180c8fa1ea95c2e7`.
- Existing native source, recipes and persistent archives are documented in
  `../2026-09-30-v3c-next-native/`. This rollout rebuilt no native libraries.
- 61b boot `6fd44228-d33e-4f0e-9bf9-9a34842c72bf`; initial Java r17b `8636782c`.
- 5cd boot `a42f2d6c-d29d-40aa-8145-51b4f85d0187`; initial Java r17c `2b201bda`.
- Both board locks were taken before writes. Installer/foundation, 5ea and
  whole-device reboot were outside this rollout. 5cd installer remains deferred
  because its USB connection is through two hubs.

## Procedure and evidence

`jar_transition.py` pins each received boot, overlay source and full SHA; it
exposes package r8b for deployment checks and overlays r17m afterward. 61b was
first upgraded to v3c with the existing alias transaction, then to next. 5cd
was upgraded from its accepted v3c directly to next. Each transaction passed
its live SHA, installer-unchanged, parent, child maps, single ART and bridge
84695d62 gates, and captured a rendered HelloWorld screen under package r8b.

`predictions.csv` was published before the runs. `run_controls.py` calls the
**master** batch driver, with 16M logs, privacy off, 24h timeout and clock
preflight, `--launch-only --hilog 20 --shots 5,20 --focus-check`. Focus parsing
reports unconfirmed; screenshot review is independent. The requested test set
is HW, ZigZag, Auxio, NetGuard and Droid-ify. No reinstall occurred.

The first 5cd app run stopped before NetGuard when the VM/Mac transport lost
the remote status marker. A subsequent read confirmed the original boot; only
NetGuard was rerun under a new run ID. Both the interrupted facts and retry
facts are retained. `facts.txt` files are unedited tool output, not totals inferred
from planned screenshots. Full logs remain in local `runs/`; committed evidence
contains screenshots, records, process tables, fingerprints and selected errors.

## Findings and limits

ZigZag's exact fatal line on 5cd is at hilog line 16891; on 61b, line 17320:

```
JNI FatalError called: Unable to load library: /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so [Error loading shared library libhitrace_ndk.z.so: (needed by /system/android/lib64/libandroid.so)]
```

Droid-ify on 5cd reaches a separate Java provider initialization failure:
`java.lang.RuntimeException: Sun provider not found`, caused by
`ClassNotFoundException: com.android.org.conscrypt.OpenSSLProvider`.
This is not proof of a native regression. HTML load warnings concern a library
explicitly absent from v3c; they are not counted as the fatal failure.

Final screenshot review, native rollback isolation and final state are recorded
in `results.json` and the evidence directories. R2 is **partially**: rollout and rollback are verified, next acceptance is
rejected by regression, and outer screenshot sign-off is pending. VLC/Anki/audio
playback are not tested by this task. Repository known-answer tests: 69 run,
2 skipped, pass; these do not certify app rendering.

## Final state and native A/B

Both boards remain on **v3c 668e4f7c + r17m a5cbd8d7**, with their older
installers unchanged. Both locks were released after final readback. 61b retains
its completed v3c upgrade; only the subsequent next transaction was reversed.
The rollback is exercised on real boards and restores the previous package
ledger, aliases, SHA and child gates. No boot changed.

At t20 under next, both boards show HelloWorld, Auxio's five-tab music UI and
NetGuard's main UI. ZigZag and Droid-ify show the desktop. Keeping Java fixed,
rollback restores ZigZag's `TAP TO PLAY` menu on both boards. The 117-file
fingerprint comparison changes exactly the runtime and the two ANL aliases,
with no JAR change. Thus the native bundle introduced the ZigZag regression;
ANL dependency lookup is implicated by the fatal message, but runtime versus
ANL was not separately switched in this task.

Counts and survival are quoted verbatim in `facts-verbatim.txt`; source files
remain under `evidence/<run>/<serial>/facts.txt`. The fingerprints for the two
next runs match (`682bbecc8adc`). This is a failed candidate rollout with a
verified recovery, not acceptance of v3c-next as a unified baseline.
