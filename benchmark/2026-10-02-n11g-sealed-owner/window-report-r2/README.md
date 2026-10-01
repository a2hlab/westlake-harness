# N11g 61b observation: callback active, duplicate owners remain

The prior assumption was that the plain default `dlopen` fallback in `WLSCPL_OpenPreparedNamespace` was sufficient to explain both extra owners. Replacing it with the explicitly prepared closure namespace and returning exact resident owner handles did execute, but did **not** meet the single-copy gate. Do not interpret live callback logging as proof of owner convergence.

- Approved child: `85ef355c`; manifest: `6d46334d`. All other U9 payload bytes remained unchanged.
- Production N1: 52 excepted / 0 rejected. N2: 103 excepted / 0 rejected. G1/G2 and frozen checks passed before apply.
- Live evidence: `done stage=8 branch=0 index=0`; `[N11g-SEALED-OPEN] route=sealed` for ICU/javacore/openjdk and `route=resident` for the bridge.
- HelloWorld probe PID 6873: ART and openjdkjvm each one load base; bridge at `7ef6080000` and `7efddc0000`; runtime at `7ee0700000` and `7ef6240000`. Identical pathname does not collapse the two load bases into one owner.
- Activation smoke failed only the two single-copy checks. The runner did not start either observation shard: all 18 target keys are unknown/not-run. `predict_vs_actual` therefore reports `missing: 18`; no screenshot verdict or lit count was supplied by this lane.
- The runner executed unconditional finish: rollback, 318 U9 identity assertions with empty diff/absent, HW/ZZ recovery smoke PASS, then final 318 verification. Runtime `a2919b793eb6`; BOOT `4db882a81732`. Boot ID unchanged. Lock empty afterward.

The first attempt failed before any device transaction because OrbStack could not connect the VM. Its separate `../window-report-r1/` retains the failure and recovery. RUNBOOK recovery used quit/TERM/KILL of stalled vmgr and reopen, followed by bind verification; no board or foundation reboot occurred. The second attempt used a fresh directory and completed within the approved 30-minute window.

`candidate-*-facts.txt` and `recovery-*-facts.txt` are unedited `run_facts.py` output. Contact sheets were generated with `contact_sheet.sh` from snapshot_display t20 originals. `live-markers.json` preserves source line numbers; `candidate-four-libraries-maps.txt` preserves the four libraries' mapping rows. Full capture remains in the durable workspace, not this public repository. Outer-loop screenshot review determines UI verdicts. No follow-up build or board experiment was started.
