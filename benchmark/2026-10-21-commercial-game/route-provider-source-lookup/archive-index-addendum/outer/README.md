# Independent member-list verification

Accepted fixed author revision `42a2026a5d` with these limits. A new independent read used the persistent `read_index.py` with the workspace directory as its sole argument. Exact original argv, timestamps, stdout/stderr and rc0 are retained in the archive. Public receipt paths use aliases; source-index.json binds original and published bytes. This is a new execution, not a reconstruction of the author's missing script or stderr.

All four list hashes, member counts (77329, 6, 363, 6), target-path absence and eight library paths agree. Only absence of the named snapshot paths in these lists is accepted. Compressed archive bodies were not inspected or verified against their lists; no globally missing source or inability to recover source elsewhere is established. No library bytes were extracted or compared.

The author's original .rc files 06/07 contain zero. Outer initially mistook their two-byte size for exit code two; that interpretation is withdrawn. Their incomplete capture remains explicit. This result confirms neither game repair nor a build provenance closure.

The 235544-byte remote archive includes the four original member lists, their stored checksum lists, the author read records and this independent original execution. It excludes archive payloads and missing source snapshots.
