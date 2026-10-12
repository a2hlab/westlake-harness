# T5 parser advice: use the corrected board-side strings evidence

## Evidence correction, not a candidate edit

Receiver cx-t0 / outer(codex). No t0 file, prior52-file R2 artifact or immutable
T4 snapshot was modified. `evidence/t5-parser-sources.json` independently pins9
source/index files and verifies each selected stdout against its index SHA.

`followup-1913/environ-nul-tools.stdout.txt` actually contains
WL_PARENT_ID=33, ASX_RUNTIME_OWNER_UID=20011206 and **REMOTE_RC=0**, SHA2ef85aca.
The prior1910 host filter of an HDC NUL-containing cat stream is not evidence
that the board's parent environment lacked these values. This advice therefore
does not ask to manufacture an environment value or copy a stale WID33.
Read the current field again and compare to the current foreground WMS row.

`followup-1913/toybox-tr-help.stdout.txt` says Unknown command tr,
REMOTE_RC=127 (even though the transport host_rc is0).1910 shows strings/od
are available;1913 proves strings successfully retrieved the two fields.
Never grade host_rc0 alone as a successful remote parser/tool invocation.

`followup-1910/parent-jit.stdout.txt` proves the captured parent9529 JIT view
SHAaa1234d2 and device:inode66352:437034. This closes the corresponding captured
same-file evidence request, not future PID/birth/boot authority or JIT execution.

Version distinction: immutable e576's launch-common.sh:35 uses `grep -ao`
directly on environ, **not tr**. The80a helper uses tr in rb_script_signal only.
Do not incorrectly label that immutable launch function as tr-dependent; any
new T5 variant that adds a tr parser really must refuse until replaced/reviewed.
The tr-based rollback/supervisor-signal helper remains unusable on this board.
No name-based signal or permissive fallback is acceptable.

## Minimal useful parsing change for a separately reviewed T5 candidate

1. Keep existing exact parent birth/UID/executableSHA/private-root/mount namespace
   guards. Save birth before the read, and repeat exact identity after it.
2. Perform `strings /proc/$verified_parent/environ` **on the board**, preserving
   its command failure status. Do not cat the NUL stream through HDC into a
   host text filter; do not place raw NUL bytes in a shell variable.
3. Filter complete lines with exactly
   `^WL_PARENT_ID=[0-9]+$` and `^ASX_RUNTIME_OWNER_UID=[0-9]+$` using grep -E.
   Require exactly one line for each (wc -l; numeric -eq1). Missing, duplicate,
   malformed or command-error output refuses. Do not head-1 away duplicates.
4. Strip only the known prefix with POSIX `${line#WL_PARENT_ID=}` /
   `${line#ASX_RUNTIME_OWNER_UID=}`. Compare WID to a freshly verified numeric
   foreground imehost0 fourth token, and runtime-owner UID to the installed
   host/current approved UID and the existing child/parent role rules.
5. Treat result33/20011206 as this captured reading only. A newly changed WID
   or reused PID requires fresh matching evidence; do not rewrite a live parent's
   environment/run.sh merely to make a check pass.

This needs only the proven strings plus existing grep/wc/printf/sh primitives,
not tr/awk/a new native build. Bind the actual binaries/tool availability and
scope in the new T5 package. Existing synthetic fields do not establish these
real-domain prerequisites. A raw remote stdout wrapper must verify its own
REMOTE_RC marker; a pipeline's final grep rc0 alone can mask failed collection.

Read-only collector shape, **not run by BMS**, after exact owner selection:

```sh
# Do not substitute historical9529 without fresh owner/boot/birth checks.
strings "/proc/$verified_parent/environ"  # board side; check this command's rc
# Then exact-line validation of only the two allowed fields, with counts.
```

Do not print or archive an entire environment unnecessarily; export only the
allowed fields, raw read rc and identity bindings to host evidence. Local known
answers for the future T5 candidate: the1913 two-field fixture succeeds; missing
either field/duplicate/malformed numeric/read failure refuses; current-WID
mismatch/PID reuse refuses; tr unavailable does not prevent this strings path.
These are recommended tests, not tests executed by this advice report.

The helper's **cmdline** kill guard is a different interface: strings extraction
does not prove exact NUL-delimited argv boundaries. Keep that signal path
disabled/pending, or separately review an exact binary NUL parser/collector
(for example board base64 plus strict host binary parsing) with its own identity
and authorization. No signal/stop clearing is part of this advice.

JPEG compatibility, empty-preimage enforcement and17s/15s budget remain separate
T4 findings in `T4-E576-FINAL.md`. Environment/JIT evidence does not resolve them.
