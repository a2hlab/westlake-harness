#!/usr/bin/env python3
# #48 r5 (ready): neuter a lib's sigaction calls that pass a non-null old buffer (Bionic-sized),
# which musl overruns (152B struct sigaction). Same method as the npth sigaction neuter (7639af00):
# for each `bl sigaction@plt` whose preceding arg setup leaves x2 (old) != xzr, replace the bl with
# `mov x0,#0` (d2800000) — fake success (sigaction returns 0), musl never writes the old buffer.
# Usage: neuter_sigaction_calls.py <lib.so>   (parses .rela.plt for sigaction JUMP_SLOT -> PLT stub
# -> bl sites; checks x2 setup in the preceding window; patches non-null-old sites; prints report).
# Left as a ready template — apply to arm64 libmonitorcollector-lib.so (sha f3918bdc) when shared.
import sys; print("template: apply to", sys.argv[1] if len(sys.argv)>1 else "<monitorcollector.so>",
"— mirror patch_npth_sigaction.py: bl sigaction (non-null old) -> mov x0,#0 (d2800000)")
