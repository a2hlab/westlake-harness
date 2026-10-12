# R5 independent binary-collector narrow review

The original `HDC shell cat /proc/PID/cmdline` lost NUL bytes; accepting that lossy text would weaken the frozen identity validator. R5 repairs only the transport. This independent review accepts collector `64421012ff2bc905970a5d2d0dd72073755b81b6f42f8c182680fc91ef95ef34` and entry `a5eb301d77f92c1755c53c93e9d59ca60d5da5030b77f495d5859b2cf68012d8` for the narrow offline seam. **No new device command or live selfcheck was executed by this reviewer.**

Eight independent incremental tests passed in 0.036 seconds. No old recovery matrix was rerun. `test.stderr.txt` is the verbatim unittest receipt; `results.json` pins subjects and dependencies. The historical outer probe reconstructs exactly 275 bytes, including NUL padding, with on-board SHA `02d57f611f6aeb98c4c796a5925fff85f8907113ab924b42c66f5aa0d6ddbf5c`.

## Actual and logical commands remain distinguishable

The caller's logical read is exactly `cat /proc/4344/cmdline`. R5 accepts only canonical decimal PID >1; command suffixes, alternate programs, newline and leading-zero PID are rejected before transport. Actual shell content is:

```
set -eu; set -o pipefail; cat /proc/4344/cmdline | od -An -v -tx1; printf '\nR5_CMDLINE_SHA256='; sha256sum /proc/4344/cmdline
```

The unchanged superclass wraps that content in explicit `/system/bin/sh -c` and checks independent host rc and a unique terminal remote-rc marker. Actual argv/encoded shell command remain in the original transport JSON. The returned validator reading names the logical cat and the separately SHA-pinned decoded bytes. `.binary.json` connects both, pins the adapter and records the board checksum. It is not a claim that the actual argv was plain cat.

`evidence/isolated-transport/` was generated using the real collector with only `subprocess.run` replaced. Its original encoded stdout, transport stdout, stderr, JSON, binary audit and decoded output are mutually hash-consistent. `adapted-existing-probe.hex.txt` inserts the R5 delimiter into the already captured root probe; this is labelled isolated replay, not a second board read. The full probe source JSON/argv and source SHA are pinned separately in results.

## Refusal checks

- Ten invalid encoded variants (odd-width/nonhex/repetition-marker hex, wrong proc path, missing/duplicate SHA delimiter, wrong SHA, prefix garbage, trailing garbage, empty bytes) reject and retain encoded/transport/audit originals. None produces a successful decoded artifact.
- Nonzero transport rc, nonzero remote rc and missing remote marker reject before decoding.
- A preexisting decoded output is not overwritten; failure is recorded as not accepted.
- A changed frozen selfcheck is rejected by `install`.
- Logical-command injection is rejected with zero transport calls.

The checksum comes from a separate read of the same proc path; if the underlying cmdline changes between cat and checksum, mismatching bytes reject. Existing independent boot/WMS/PID/birth/UID checks remain authoritative. A bytes-only transport correction does not itself prove live process ownership or UI.

## R3 loading is actually tested

The activation entry loads the exact R3 checker, installs the collector, then wraps its real `select_frozen`. The independent test invokes the genuine pinned `select_frozen/dependencies` using a pinned generator-selection document. R3 does reload `original_check`; the wrapper installs BinarySafeCollector again into that newly loaded module. A subsequent read through its `ReadOnlyCollector` retains NUL and passes the strict byte/SHA transport. The test replaces only R3 `main` to reach this seam without admitting a fake history or issuing HDC. It does **not** report a full activation comparison PASS.

Only the collector subclass and the explicit selector entry are new. Frozen observations, realization, selfcheck/compare, seal checks, R3 checker and their source pins are unchanged and independently rehashed. Non-host_cmdline reads continue through the unchanged superclass. BMS's own tests separately cover the original strict NUL validator.

## Scope of acceptance

No blocking defect was found in this narrow offline review. Outer must still perform a fresh complete source WMS sample and each target board's actual selfcheck using the landed adapter. Keep the old failed lossy sample; bind the new encoded/decoded audit to the new observation. Neither the historical probe nor this isolated replay is a fresh live selfcheck, device restoration or seal signature.

Run locally:

```
python3 benchmark/2026-10-13-r5-binary-collector-review/test_r5_review.py
```

The tests first pin the exact two reviewed BMS files and refuse drift. No BMS tree, original payload, validator, compiler, board, VM or remote system was modified.
