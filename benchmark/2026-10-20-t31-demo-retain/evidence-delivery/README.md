# T31 offline evidence supplement

The 45 execution/spec/fixture/card files already collected by outer remain byte-identical. This supplement contains the existing 95 evidence files and delivery metadata only; it does not replace running inputs. No tests were rerun while packaging.

Recorded results: recovery 7 tests (64 known source branches, 6 cutpoints, 5 foreign cases and local bash guards), new helpers 3 tests, Rust 2 tests; all passed. Final spec lint scores are 100%. Lifecycle t1/t3 each has 4 PASS; t2 has 4 human PendingReview and strict rc1. These are offline results, not device recovery or final playback acceptance.

`check03.stdout.txt` contains an obsolete “No shell” limitation. Preserve it and consume `../evidence/limits-correction.json`: local bash guards did run, no HDC ran, full remote transaction remains unknown. Earlier syntax/path failures remain in evidence. Public path-sanitized logs map to original private bytes through `../raw-sanitization-index.json`; private originals are excluded from landing.

The historical derivation script and failed source snapshot in evidence are provenance, not execution entrypoints; do not replay them over the frozen sources.

`landing-paths.txt` is the exact supplemental list. `manifest.json` covers payload bytes; `SHA256SUMS` additionally pins the manifest and landing list. The already-collected 45 files are recorded in `frozen-source-check.json` and are not repeated in this landing list.

Author commit is not claimed: the previously established worktree index-lock sandbox restriction remains; no staging retry was made. Outer may commit this exact list with `evidence: preserve T31 offline checks and human-pending boundary`. No push is authorized.
