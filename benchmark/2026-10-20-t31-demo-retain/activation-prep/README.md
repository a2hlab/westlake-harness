# Unsigned activation evidence preparation

Local-only producer; never calls HDC, a remote shell, REA, or a signer. It preserves old replay/T31 files. `template-01/unsigned-retain-evidence.json` has actual static source/production/recovery/reuse references; all signature/time/retention fields and new evidence verdicts are null. Window start is origin provenance, not signing time.

Run from any local directory; `MAIN` is the landed repository and `W` is the **current activation** window. Do not pass replay IDs. Explicit new boot, parent PID/birth, host PID/birth and parent namespace must come from root's fresh reads. `render` rejects an old experiment window (age >=1200), a context/plan/admission mismatch, or source drift. It reuses the frozen recovery policy to validate the exact origin. No unsigned template constitutes a device verdict.

```sh
PREP="$MAIN/benchmark/2026-10-20-t31-demo-retain/activation-prep"
python3 "$PREP/prepare.py" render --repo "$MAIN" --window "$W" --boot "$BNEW" --parent "$PNEW" --parent-birth "$PBNEW" --host "$HNEW" --host-birth "$HBNEW" --parent-mnt "$PMNT" --out "$W/retain-prep"
```

Output: `unsigned-retain-evidence.json`, `candidate-six-read.sh`, `render.json` (all exclusive creation). Root executes the generated shell only through the existing T31 held/boot/time-checked serial channel and preserves argv/stdout/stderr/rc. This producer does not execute it. The rendered script contains only reads/tests: bookended boot/parent+host birth/UID/tracer/exe checks; exact parent namespace; all six physical/private SHA, mode/UID/GID/label and dev:inode comparisons before/after; cfg SHA, WMS and power/param raw readouts. A missing final marker or nonzero rc is not successful evidence. Host executable identity is recorded and required stable across the read; its prior admission provenance is still reviewed by root. WMS29 and power/param interpretation remain explicit root review, not hidden behind the completion marker. External holder/time guards remain mandatory for execution and each later action.

`origin_backups` lists the exact five expected origin-boot paths and ABSENT marker from this apply plan. It says EXPECTED_PATHS_ONLY_NOT_REREAD; `actual_backup_receipt` stays null. Root adds actual backup verification, six-state receipt, five-slot result, fresh child/birth, normal icon/final feed, original/restored power and debug evidence, and then signs separately if complete before the deadline. The generator never reads or patches an existing unsigned file and cannot overwrite old evidence. Reusing prior video/audio evidence does not fill any current identity or imply a new signature.

Seven local checks passed: null signature; synthetic current origin; expiry refusal; context/plan drift refusal; six-state shell parse/read-only form; missing birth refusal; namespace injection refusal. `bash -n` parsed generated shell only. No shell commands from it ran, and synthetic values are not board evidence. Tests use temporary local fixtures, not MAIN writes. No runtime sources, T31 frozen helpers, spec or executable gates changed.
