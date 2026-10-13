# Exact Noice upgrade with preserved private data

The first backup attempt failed before installation: the deployed OH `tar
--selinux` crashed in `getfilecon` with exit139. A separate bounded experiment
using absolute paths failed too. Neither attempt invoked `bm install`; both
finished with unchanged337 runtime identities and released their board locks.
The failure is observed behavior, not a source-level root-cause attribution.

R2 changes only the archive construction. The device creates an ordinary tar
with numeric ownership. Its original bytes are retained privately and verified
by independent remote/local SHA256. For every archive member, original command
receipts record live `stat` and `ls -Zd` results. A local PAX archive encodes those
measured labels after checking content, membership, ownership and mode. The
original strict archive verifier and all18 other original functions remain
unchanged. No archive is extracted onto the device, and no data is removed.

Independent review accepted source `a6fe1a8d…`, replayed10 tests, refused incorrect
content/ownership/labels, and reproduced an identical PAX SHA from the raw tar
plus stored metadata. This establishes offline archive recoverability; it does
not claim a device restore rehearsal.

Actual5ea attempt02 installed the same-signer fixed Noice version72 over66.
All16 pre-existing files retained their SHA and metadata; all four data roots,
UID/GID, both access-token fields and permission states remained equal. The
archive contains40 members with measured labels. Original337 identity checks,
HelloWorld/ZigZag smoke and final identity checks passed, and the window unlocked
at13:27:46. `upgrade-acceptance.json` binds the actual result without exposing
private contents. Noice UI success is a separate full128 result.

Private raw logs, original APK and both archives remain outside this public
repository under `$WORKSPACES/westlake-inputs/private-backups/noice-20261013/`.
Attempt01 and the absolute-path probe are preserved alongside successful
attempt02. Failure never enables uninstall, clear-data or automatic rollback.
