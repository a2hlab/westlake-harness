# G34 DFX provenance: exact identity of mapped crash-reporting and sigchain objects

## Question and scope

The G34 post-close plan established that the child maps contain `libdfx_signalhandler`, `libfaultloggerd`
and route-a `libsigchain.so`, but bound none of them to bytes or a build. This task closes that gap where local
records allow. It uses existing text records and locally saved ELF copies only:

- no device, VM, network, debugger, REA or build;
- no game internals;
- no signal-handling design.

A mapping does not show that a handler was registered or ran. A missing crash record is not evidence that any
protection fired.

## Exact matches

The source maps are the G34 child 29761 maps, `9040c304…`. All SHA, size, build-id and SONAME values below were
recomputed by [build_table.py](build_table.py) into [match-table.json](match-table.json)
([stdout](build_table.stdout.txt), rc 0). In revision 3, only the wording of the two route-a `note` fields in
`match-table.json` and its generator template was corrected (package-declared target, no new mount/write in
this window). No SHA or value changed. `build_table.stdout.txt` is the original historical output; it carries
no note field.

| Object (maps dev:inode) | SHA256 | Build ID | Same-boot pre-window path SHA | Other binding |
|---|---|---|---|---|
| platformsdk/libdfx_signalhandler.z.so (103:20:4897) | `2be2b137…` | `0a51f2ca…` | missing | 5ea n5 inventory (boot f828d689); G34 rollout native-gates candidate and baseline; 67904 B = 5ea 2026-09-30 listing |
| chipset-sdk-sp/libdfx_dumpcatcher.z.so (103:20:2591) | `77d9d3e6…` | `f1a15cb5…` | missing | same three, 100824 B |
| chipset-sdk-sp/libfaultloggerd.z.so (client, 103:20:2603) | `57f87325…` | `d16e5f81…` | missing | same three, 25120 B |
| chipset-sdk-sp/libdfx_procinfo.z.so (103:20:2592) | `aea0f002…` | `eb97fd2b…` | missing | same three, 47464 B |
| chipset-sdk-sp/libunwinder.z.so (103:20:2635) | `f71cf42b…` | `d32457da…` | missing | same three, 278976 B |
| chipset-sdk-sp/libbacktrace_local.so (103:20:2582) | `ee6debe4…` | `c2ecf7a4…` | missing | same three, 113496 B |
| route-a/74d1d6…/libsigchain.so (103:30:20250) | `6d5d5538…` | `a05e545b…` | direct = old parent 19168 view = `6d5d5538…` (23:05:56, boot a1d869b4, before apply) | G34 transaction baseline-319; G34 rollout `payload/route` bytes |
| route-a/74d1d6…/libunwindstack.so (103:30:20209) | `d2c1cbc7…` | `085331ff…` | direct = old parent 19168 view = `d2c1cbc7…` (same read) | same |

The route-a objects belong to the pre-existing route-a generation. The G34 package **declares** the same
`payload/route` bytes for the target `/system/android/lib64/libsigchain.so`, a different path. This is a
package declaration, not evidence that this window mounted either library anew. The 36-operation journal did
not write these two route-a targets.

The route-a SHA is a path read in the same boot **before the window**: the direct view plus the view of
**old parent 19168**. The game maps come from **parent 27555 / child 29761**, so the parent had changed.
No stat (dev/inode) of these paths was taken bracketing maps inodes 20250/20209. The read therefore verifies
the same-boot baseline path bytes, **not** the bytes mapped at crash time.

## Minimal missing pieces

See [missing.json](missing.json):

1. **G34-time device SHA of the six stock DFX objects.** The fresh 319-hash read covers Westlake targets
   only, so the newest 5ea SHA is from 2026-10-01. Path, inode and size are consistent with it, but that
   does not bind the bytes at boot a1d869b4.
2. **Source snapshot and build log for the stock DFX objects.** Only build-ids exist locally. They are not
   bound by OH version label.
3. **Crash-time binding of the two route-a objects.** A stat (dev/inode) of the two route-a paths was not
   taken bracketing child 29761's maps inodes 20250/20209, and the pre-window read used old parent 19168, not
   parent 27555.
4. **Source, recipe and build log for route-a libsigchain 6d5d5538 and libunwindstack d2c1cbc7.** Local
   SHA hits are deployment and fingerprint receipts only. The route-A frozen build inputs are recorded on hw248
   (OPS-RUNBOOK) and were not read here.

Conclusion, per object group:

- **The six stock DFX objects.** Only the locally saved ELF bytes have exact identity: SHA, bytes,
  build-id and SONAME. They are **not** bound to the device bytes at the G34 boot (a1d869b4). The newest 5ea
  binding is the 2026-10-01 inventory (boot f828d689) plus the G34 rollout gates.
- **The two route-a objects.** For `libsigchain.so` `6d5d5538…` and `libunwindstack.so` `d2c1cbc7…`, the
  same-boot baseline path SHA before the window is verified. The direct view and the old parent 19168 view
  both equal the local copy and the G34 transaction baseline-319. They are **not** bound to the crash-time
  mapped bytes of child 29761: the parent changed, and the inode binding is missing.

For all eight, reproducibility from source and the build chain are **not established** locally. Nothing here
supports a conclusion about the game crash cause.

No device, VM, network, debugger, REA, build, code or policy change, and no G14/T38.
