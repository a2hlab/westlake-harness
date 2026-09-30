# T5 attribution progress

- #91 21:27 dispatch: one hour, offline. No device access.
- Remote SSH denied by session sandbox; VM lookup pending. Requested Mac copy of T5 inputs through board progress; continue on SHA-matched local R155 reference.
- Reference boot.oat SHA 25d92cf7df9c86ca4bbc81c1e2f44a5c6c64798506247239e07a30f651b9e78c matches board manifest. OAT at 0x1000, checksum d369f830, KV size 2259: 8 keys, neither bootclasspath-checksums nor compilation-reason. Reported premise correction immediately.
- Outer supplied `_hw248-t5/arm64`; all 27 hashes verified against parent SHA256SUMS. This is checksum 0424c4ee, not the earlier reported 31a3e81e artifact. Actual candidate has no compilation-reason either.
- Compared 9 OAT headers/13 dex records/ELF sections: all 9 VDEX equal; all 9 .text differ, even empty-KV secondary files. Candidate concurrent-copying=true vs reference false; both sets have 9/9 consistent ART-to-OAT checksums.
- Posted early read-barrier compatibility risk and native CMS-default finding to board for T3b/T6 owners. No device or remote build was touched.
- Extended scope per 21:38 dispatch: native flag matrix and T4 recommendation, retaining the approved T4 spec unchanged. Native branch evidence verifies RB-off, default CMS, generational default off, heap poisoning off and release build. TLAB/C++ interpreter/sanitizer-gap/optimization remain unknown, rather than invented upstream defaults.
- Nine tests and 3/3 contract selectors passed (lint100%); repository known-answer run69/skipped2/failed0; path gate36/violations0; git diff --check passed. Four unresolved original build options are observation boundaries, not blockers to this scoped offline handoff.
- Local git add succeeded. Commit failed creating the shared worktree index.lock: Operation not permitted. No new commit or push; branch analysis/bms-route-study, base 2ea129754. The staged delivery is available for outer-loop commit; pre-existing specs/unified-replay remains untouched.
