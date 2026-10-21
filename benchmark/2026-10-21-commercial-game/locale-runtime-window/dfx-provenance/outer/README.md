# Independent review and exact local ELF retention

Accepted author revision: `d74db75731`, following `01fb36cb2a`, `9f6efd697a` and `34b187ff22`. All eight local ELF SHA/size/build-id/SONAME values were independently checked. Subsequent reviews checked only the changed wording, counts and checksums; no repeated metadata execution is claimed. The original command streams and fixed snapshots are retained in the remote archive.

The final table distinguishes local ELF identity, same-boot pre-window path hashes, and unproven crash-time mapped-inode identity. Six stock objects have no G34-time device hash; both route objects lack the latter mapping binding. Source/build closure and the crash cause remain unknown. No device or debugger action was performed.

`archive-receipt.json` verifies the 512,076-byte archive (`a57287f0161e85ccf33702a0e1c826507e2fa5a873e00f23889e809ef762513f`). It contains all eight exact saved ELF copies, independent metadata command receipts and the table. It does not contain missing source/build logs or a recovered fault stack. Public peer reports replace personal filesystem prefixes with aliases; `source-index.json` retains both original and published hashes.
