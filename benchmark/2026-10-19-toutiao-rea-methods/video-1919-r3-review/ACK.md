# video-1919-r3-review

**Checklist ready; candidate/executor admission pending.** Read-only source inputs and full hashes are in checks.json.

Actual mffmpeg preimage: fecf91e1fcda600661f501ce76a97456ad7e330b584013f2b742afb680b337c9, 4,870,376 bytes, 644:20011206:20011206, u:object_r:appdat:s0. Physical RT/lib/arm64-v8a and parent5279 view both identify 66352:371892, boot da213fc2, parent birth11376. These are evidence, not future execution authorization.

Extend the existing executor by one member only. Before first target write validate all three preimages and both original backups. Apply compat → mffmpeg → run, with immediate preimage CAS and sibling-temp rename; never truncate a mapped file. Roll back against the original apply-plan in reverse order, preserving actual original bytes/metadata and independently derived current WID. No generic transaction framework is requested.

After fresh boot, verify the exact transformed mffmpeg is the canonical file in physical/parent/child views, then correlate maps device/inode and load bias with the actual player load. Path replacement alone, segment count, or maps alone cannot prove successful player linkage. Preserve P0 cfg and all existing recovery checks. No device calls, builds, or executor invocation.
