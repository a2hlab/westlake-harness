# Window 15 (5ea, legacy entry, MODES="0 64 32"): mode 0 PASS and legacy-ns VALIDATED; modes 64/32 did not run (process reuse) -> run_a0.sh kill_app fix for window 16.

## mode 0 (legacy entry 61e57956) — PASS, legacy namespace validated
    [A0] entry ns nweb_ns_legacy (lib_paths=/data/local/tmp): dlns_get=-1 create=0 dlns_get(default)=0 inherit=0
    [A0] S5 producer surface 0x7f2675f1f0 ; S5 CreateNWeb -> 0x7f215f0c28
    [A0] RESULT PASS stage=S8 surface_frames=5 surface_js=4 console_js=1 load_end=1
The entry created nweb_ns_legacy and NEVER touched nweb_ns; the engine loaded and rendered (#12ab34). Clean rollback +
UNLOCK, fingerprint 821de739cf81.

## errno=17: OH's OWN second create, not ours (ArkWebBridgeHelperLoadLibFile call sequence)
    15:52:12.803 C04500/webview ArkWebBridgeHelperLoadLibFile: succeed to load lib file .../libarkweb_engine.so   <- Init: FIRST create, NO "dlns_create failed" before it = OH created nweb_ns CLEANLY
    15:52:12.921 C04500/webview ArkWebBridgeHelperLoadLibFile: dlns_create failed ... (errno=17) ; succeed to load  <- InitAndRun: SECOND create EEXISTs on OH's own nweb_ns, then reuses
    15:52:13.642 C04501/webview (render pid 29418) dlns_create failed ... (errno=17) ; succeed to load             <- render process: its own repeat
Contrast window 13 (default/co-own entry): the FIRST call ALSO had errno=17 because WE pre-created nweb_ns. With the
legacy entry there is NO first-call EEXIST -> OH owns nweb_ns cleanly. The 2 remaining errno=17 are OH's idempotent
repeats (Init vs InitAndRun, + the render process), which OH handles by reusing its own ns. Legacy criterion MET.

## modes 64/32 did not run: mode-0 process reuse
mode 0's app process (pid 29318) was not killed between modes: `aa force-stop` reports 10106401 on the appspawn-x child,
so the mode-64 `aa start` only foregrounded the existing process (callerPid 29318) instead of binding a fresh one -> the
runtime entry/worker's a0_probe_start never re-ran -> the mode-64/32 segments have ZERO [A0] lines. Not a mode-64 code
problem; the modes never executed.

## Fix (run_a0.sh): kill_app() by pid between modes + at rollback
kill_app(): resolve the bundle install uid (bm dump), `aa force-stop` best-effort, then `kill -9` every ps process whose
USER == that uid (the appspawn-x child + its render procs; uid != 0 only, NEVER the appspawn-x main process -- RUNBOOK 12;
refuses uid 0), polling up to 12x1s until the uid has no processes. Called in the mode loop before each `aa start` (so the
launch re-binds fresh) and in rollback. Syntax-checked.

## Next: window 16 = ENTRY=legacy MODES="64 32" (mode 0 already PASS); 5ea/5cd whichever free (cx-t0 window 4 opens 5cd first).
