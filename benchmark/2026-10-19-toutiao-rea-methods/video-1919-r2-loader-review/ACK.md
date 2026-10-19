# video-1919-r2-final — loader-path verdict

**REJECT the 79275cf9 run-only candidate.** This is a static admission decision, not a newly observed device crash.

The exact ART source chooses namespace from the original basename before sanitizing. Therefore the temporary-name TARGETS hypothesis is cleared. The remaining problem is dependency reuse: Java loads a sanitized sibling inode and unlinks it, while TTPlayer DT_NEEDED opens canonical libmffmpeg.so through musl without ART sanitization. The supplied musl source matches shortname or inode, not merely ELF SONAME; the transient mapping has neither the canonical shortname nor original inode. The original fecf91e1 object contains one unrelocated null init slot. If relocation succeeds, its constructor dispatch calls null.

Smallest correction to assess: derive a fixed canonical libmffmpeg artifact with the existing bionic null-skip semantics (for this exact object, DT_INIT_ARRAYSZ 8→0 only), so Java and dependency loading see the same safe file/inode. Pin exact input/output and byte delta; extend the narrow deployment/rollback allowlist by that object, retaining original bytes. Actual namespace/provider closure still applies. Do not introduce anti-emulation policies or modify valid constructors. Simply keeping the temporary file, adding SONAME or RTLD_GLOBAL, or changing load order is not enough.

Caveat: supplied OH ldso source is release-matched rather than byte-rebuilt against the board binary. Earlier relocation failure can occur before constructor dispatch. Zero device calls, builds or test reruns. Full pins and source lines: results.json.
