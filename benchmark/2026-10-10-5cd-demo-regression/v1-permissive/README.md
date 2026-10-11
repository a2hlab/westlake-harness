# Pure-v2 U13 v1 preview on 5cd

## Evidence first

**A permissive runtime preview is not a persistent sealing configuration.**
The outer authorized all 128 selected demo keys on healthy pure-v2 5cd, using
the same t4 driver and icon-click path as the 61b sealing round. No Boat, APK
reinstallation, runtime replacement, reboot or persistent configuration change
is performed. Boot is pinned to `a565a760-c10e-4ad4-80cd-23cd98165b28`.

Each <=45-minute window stops opening keys at minute 35. The task-only mode
hook verifies U13, changes runtime enforce 1→0 with readback, then finally
restores 1 with readback and verifies 319 identities and both fingerprints
before unlock. A changed boot or identity/cleanup refusal stops dispatch;
this preview never repairs a device or silently reboots it.

The initial two 64-key plans group the same inputs by root and approved
10/20-second screenshot tier. If a clean cutoff leaves keys unmeasured, the
continuation glue schedules only those keys in smaller bounded windows, via
the unchanged `demo_board_run.py` and master runner. OrganicMaps is isolated
at the continuation tail because its documented child rebirth must never
hide the rest of the set. Nonzero cleanup/interrupted records are not cutoffs.

## Output

- `round-20261010T2135/`: exact prepared inputs, bindings, initial captures.
- `continuation-after-window1-r3/`: cutoff continuation, if needed.
- Each window has mode-apply / mode-finish evidence and raw runner results.
- `readout.py` creates raw `facts.txt`, all-frame contact sheet, t3 comparison
  and a suspect-only review sheet, excluding control captures.
- `suspect` means desktop/blank/unknown evidence for outer review; it is not
  a confirmed regression. `same_class` is equally not an automatic UI signoff.
- `comparator-tests.txt`: 17 existing tests pass, including real t3 all-same,
  changed-two, and known preview-01 7/2 semantic triage.

RUNTIME is `452447a4a0ba`; BOOTIMAGE is `ee927db88a67`. Captured/survival counts
come only from the master run_facts.py output, not hand-maintained counters.
All 128 regular keys have final-frame evidence; no key remains unmeasured. This
is cross-validation only; the outer owns all screenshot verdicts and the 61b
net-boot 128-key run remains authoritative.


## Final readout and safety outcome

The last OrganicMaps record captured both scheduled images, then the regular
cleanup guard refused: `target cleanup could not be verified; stop before next
app`. The coordinator stopped; it did not retry or open another window.
`before_unlock=0` nevertheless restored Enforcing, verified 319 paths with
`diff={}`, and released the lock. `unlocked.json` records `held rc=1`, empty
output. Boot stayed unchanged throughout all seven bounded windows.

Raw master facts (not a UI verdict):

```
TOTAL keys=128 screenshots_captured=256/256 alive_t5=124 alive_t10=119 alive_t20=5
```

- [Combined facts](full128-readout/facts.txt), [128-key contact wall](full128-readout/contact-sheet.jpeg), [tile mapping](full128-readout/contact-mapping.txt).
- [t3 comparison](full128-readout/compare/comparison.json): no missing keys;
  image-byte comparison changes all 128, so use the semantic queue to direct
  human review rather than treating timestamp/image changes as regressions.
- [Suspect queue](full128-readout/compare/suspect.keys) has 16 desktop/blank/unknown
  candidates. This is **not** a confirmed regression count or a lit count.
- [Suspect log readout](full128-readout/suspect-log-readout.json) preserves
  PID-attributed fatal lines and package-attributed WMS conflicts. Missing
  fatal matches remain unknown. NewPipe and AntennaPod have concrete Java NPE
  lines; this alone cannot classify all remaining screenshots.
- [Results](results.json) summarizes per-window safety receipts.
- [Raw evidence SHA index](raw-evidence-index.json) preserves the local large
  capture/log sources; large originals are not copied into git.

No screenshot retries or uncovered-key continuation follow the outer stop
instruction. Only the runtime SELinux mode was intentionally varied; the
existing driver may perform its ordinary sandbox preparation. No manual
sandbox repair, runtime replacement, reinstall, reboot, Boat overlay or
persistent sealing configuration was introduced.
