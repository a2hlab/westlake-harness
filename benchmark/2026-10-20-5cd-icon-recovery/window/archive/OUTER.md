# Persistent raw archive handoff

The local archive is verified: 3760 members, 4049128 bytes, SHA `6a127efd203c9162b227e598b479035e07e47d8a4815c8e6b2f719b443d0c6a6`.

Execute the three argv arrays in `../.private/archive-01/remote-commands.private.json` in order, saving each argv/stdout/stderr/rc in a new persistent output directory. Stop on nonzero. Check remote SHA and byte count against receipt.json, then add a separate outer-success sidecar. Do not repack or overwrite this archive. The lane prepared local packing and exact argv only, as requested; remote verification is pending.

The archive includes the full actual window plus T12 identity/power/log-prefix readonly inputs, local packaging source, and committed producer source pins. Existing MAIN producer code is referenced by exact commit/path/SHA rather than copied as another source tree. Lost hilog stdout was never present and is explicitly missing.
