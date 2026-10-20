# Same-generation runtime read: prepared only

This is an offline command generator, not a deployment or repair. It reuses the boot/stat/private-root bracket from T34 `after-close/13-real-read-only` and the reviewed T34 executor. The exact nine BCP paths come from W03-b `parent.log:30`; boot and mapped runtime paths are also present in the T31 actual maps. Expected first-fatal-point removal is **unknown**; this collection changes no behavior.

Existing `specs/demo61b-video-delivery/t1-migrate-and-verify.spec.md` covers the preflight/read-only difference evidence; its project permits 5cd read-only, confines device execution to the assigned lane and forbids 5ea. No new spec, acceptance change or runtime modification is introduced. The peer only generates and syntax-checks commands. CC must wait for recovery/unlock and root scheduling before executing either command.

Create two private fresh profiles, each with exactly the current `serial`, `boot`, `parent_pid`, `parent_birth`, `parent_mnt`. Serial allowlist is 5cd/61b only. Never fill these from the historical T31/T32/T34 examples. The live parent must match original executable SHA a7a358c6… and root UID; a missing parent is a blocked collection, not permission to launch one.

```sh
python3 benchmark/2026-10-21-t34-demo61b-video/environment-collect-01/prepare.py \
  --profile-5cd "$PRIVATE/fresh-5cd.json" \
  --profile-61b "$PRIVATE/fresh-61b.json" \
  --hdc "$HDC" --out "$PRIVATE/environment-argv-01"
```

Output is one exact argv array and its readable shell for each board: `5cd.argv.json`, `61b.argv.json`. No transport is invoked by this command. The designated device lane executes each JSON array once via the existing receipt collector with **90-second host timeout**, persisting exact argv/stdout/stderr/rc, including timeout partial output. No retry, launch, screenshot, install, signal or remote file write is included. Stop on identity rejection (81), missing tools/maps (82), timeout or absent final identity marker; do not call these complete.

Each read checks boot, parent birth/state/PPID/root UID, mount namespace and executable before and after. It emits parent stat, selected startup environment, nine expected BCP JAR SHA/size/dev:inode, private boot ART/OAT/VDEX files, and original maps before/after. Shared-library hashes are restricted to actual mapped private-asx/system64 `.so` paths in that parent's namespace. No filesystem-wide search occurs. Missing files or failed reads are UNKNOWN. Metadata changes around hashing invalidate that file.

Read scope and limits:

- These are **parent** observations. Child-specific modules and child loader winners remain unknown without a matching existing child receipt; never substitute physical stage files for them.
- Fixed BCP entries are the recorded expected paths. Missing `BOOTCLASSPATH` in `/proc/environ` does not prove absence: appspawn sets VM options internally. Pair with the matching-generation parent log before claiming actual BCP order/content.
- Compare original maps device/inode/path with each returned stat and SHA; multiple mappings/namespaces remain separate. A live pathname hash does not alone identify an already loaded or replaced mapping. Changed maps require scoped interpretation, not automatic equivalence PASS.
- Original parent-log evidence and 5cd video-generation receipts remain historical. A fresh post-close baseline read cannot reconstruct the failed candidate's earlier loaded generation.
- All raw output remains private: selected environment and maps may contain sensitive paths. Publish only hashes and necessary redacted comparisons. No API or video acceptance changes follow from service/runtime equality alone.
