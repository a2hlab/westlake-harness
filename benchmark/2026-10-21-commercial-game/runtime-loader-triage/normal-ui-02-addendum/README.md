# G16 addendum: attempt2 mapping identity, not call ownership

Transport rc0 is insufficient: round 2's stat-after and all four object reads
contain missing-file errors. They do not close a valid identity/hash observation.
Full private hilog and maps are not copied into this packet.

Round 0 and round 1 each bracket maps with PID10946, PPID6274, starttime **598912**.
`comm` changes across rounds; this is not evidence of PID reuse. Round0 state is
R and round1 S. Object reads occur **after** their round's stat-after; the next
round's stat-before has the same identity and brackets those reads. This temporal
ordering is retained explicitly, rather than claiming stat-after followed hashes.

| Round1 path | maps line(s) | decimal dev / inode | file SHA prefix |
|---|---|---|---|
| system/android/lib64/libapp_native_loader.so | 100–103 | 66352 / 15142 | eebd62f2 |
| route-a/74d1…/libapp_native_loader.so | 1643–1646 | 66352 / 20292 | eebd62f2 |
| system/android/lib64/libnativeloader.so | 96–99 | 66352 / 15157 | b8be63d2 |
| route-a/74d1…/libnativeloader.so | 1551–1554 | 66352 / 26235 | b8be63d2 |

Linux dev_t 66352 decodes to major259/minor48, exactly maps `103:30` (hex).
Each inode matches its `/proc/10946/root/...` stat. Both loader pairs contain
same-SHA bytes at distinct mapped file identities and address ranges. Round0
shows the route objects only in the captured loader rows. The later appearance
of system objects does not select an active API implementation.

Round2's before stat still has birth598912, and maps contains the two sets, but
its after stat is missing. All four object read bodies fail even though command
records say rc0. Treat the maps as an unclosed partial capture; never reuse the
previous hashes as successful round2 measurements. Child log line3979 records
exit1 at 18:47:14.366; after-stat receipt is 18:47:14.489. No signal-crash claim.

The same failure chain remains: errno at lines3380/3406 (execution continues),
GLESv2 dependency failure in `westlake.anl.app.10946.2` at3521–3526, and unbound
Unity JNI at3928 before exit1. Errno remains a deferred, nonterminal gap.

**For G18:** both mapped aliases are established, but the production entry winner
and per-object namespace membership remain **UNKNOWN**. Maps and content hashes
cannot select which OpenNativeLibrary/ANL domain registry instance serviced the
failing request. Do not infer that a runtime-provider pathname selects a loader,
or that equal bytes imply a single instance. No device action or new observation
is requested by this addendum. Source/open-site analysis is a separate next slice.

Limits: path stat followed by SHA is not an atomic hash of mapped memory. The
next stat supplies a process-identity bracket, not a guarantee that no file
mutation occurred. Only a final boot receipt is included here, not a new
before/after boot proof. No environ was read. No screenshots were evaluated and
no UI/game success is claimed.
