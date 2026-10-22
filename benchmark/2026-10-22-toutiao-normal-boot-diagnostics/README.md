# T48 — normal-boot diagnostic window on 5cd (executed, restored)

Plan 53951267, signed `outer(codex)`. LOCK 17:57:29 → UNLOCK 18:10:50 (800 s; limits 1800 s / restore by 1200 s).
Four normal `target boot` reboots, each new boot after 26 s. Six ROOT control files only; no init cfg edit, no stop
cleared, no manual guardian start, no third-party kill, no T38/REA/debugger.

| phase | boot | result |
|---|---|---|
| preflight | 8b64b087 | all pass: ctrl9 and members9 = T46-P2 exact; runtime124/boot36 = T44; HAP b189 and bundle identity; stops absent; power 10000/10000; stage/backup absent |
| M1 | — | backup of six originals SHA-verified; env → maint-forward d1452d77, expected d764a774 |
| R1 | 84a34d9e | ready=true; boots list unchanged (36); no `boots/84a34d9e`; no ROOT process → maintenance isolation |
| C1/C2 | — | candidate watchdog bcae2c69, owner fc63dae9, entry 1f16bc6b, members 04aa24cf; env 465f5fbe; expected 49424def written last |
| R2 | bd406082 | candidate boot dir created with candidate copies; desktop WorkSpace_0 → WorkSpace_8, **one** icon tap |
| observe | bd406082 | SUPERVISOR_STARTING → child 7781 UI_UNVERIFIED → `snapshot_error_rc=126 child_identity_during_capture` → process_exit → RECOVERING; **`guardian-refusal-1.jsonl` at t+41 s: phase=strict, pid 7781, field=birth, actual=`<read-error-or-exited>`, expected 22688**; screenshot white host page |
| M2 | — | env → maint-reverse 8e60a99d, expected b43d886b |
| R3 | b93cae50 | ready=true; boots unchanged (37, incl. R2 dir); no new dir; no ROOT process → isolation |
| B1/B2 | — | six originals restored (2b635ef1, 6bce7c3c, 81dd0557, 328f0af2, 44993dbc, then expected 05c12ce3 last) |
| R4 | 1b1febea | baseline boot dir with baseline copies; desktop → WorkSpace_8, one icon tap → SUPERVISOR_STARTING: the original guardian actually started; screenshot white host page |
| final | 1b1febea | six files SHA/mode/owner/label = T46-P2 (new inodes); members9 exact; runtime124/boot36, HAP, bundle, datadir unchanged; stops absent; `.new` absent; stage/backup retained with bound identity; power restored 10000/10000 |

The refusal record only says that the strict identity check got `actual=<read-error-or-exited>` for the child's birth.
That value cannot tell apart a process that vanished at that instant, a zombie, or an unreadable entry. The
`process_exit` line that follows in `events.log` was observed afterwards and cannot be used to infer what happened at
the moment of failure. The cause is not diagnosed here.

The R2 state when collected (about t+45 s) was `RECOVERING`, not a terminal `OWNER_REFUSED`. Both the R2 and the R4
screenshots are white host pages.

Corrections and deviations (raw under `raw/*/NOTE-*`):
- **M1 guard**: the two M1 writes ran with the old `put` **before** the outer-requested per-write guard (lock
  holder, phase boot, budget, parent identity and labels) was added. M1 relied on the preflight one minute earlier and
  per-file readback.
- **R2 pipefail**: the R2 guard ran as `guard | tail -1 && rboot` without pipefail, so a nonzero guard rc could have
  been hidden. The raw `05-R2/g_r2_*` output shows `GUARD_OK`, and the outer independently re-checked
  holder/boot/7 parents/labels. Pipefail and explicit rc checks were used from then on.
- **Events before click**: after R2 I polled for `events.log` before any click. The outer corrected this: entry waits
  for the host foreground, so events start only after the normal icon tap.
- **Checker**: a label-count bug was fixed and the same raw was re-judged.
- **Local redirect**: one local redirect failed before any device command; the device was verified unchanged.
- **Wi-Fi**: the screenshots show no Wi-Fi icon; Wi-Fi state at those moments is **unknown**. A read-only check after
  UNLOCK (`raw/14-wifi`) showed wlan0 UP with an IPv4 address and WifiDevice "connected". No link to the white screen
  is claimed.

Not claimed: white-screen fix, retained/permanent deployment (the candidate was deployed temporarily in this window and
restored), a complete spec PASS (the Rust receipt validation is not implemented), seal,
human origin.

Public reproduction sources: `tools/` holds the historical helper source actually executed in this window. Reuse needs a
fresh plan; do not replay the old boot or signature. The files are (`rec.py`, `env.sh`, `admit.py`, `ui.py`);
`raw-index.sha256` is the full private raw file index.

Private raw (per-command argv/start/end/stdout/stderr/rc, layouts, screenshots):
`$HOME/.local/share/westlake/t48-normal-boot-diagnostics-20261022/`, MANIFEST in `results.json`.
