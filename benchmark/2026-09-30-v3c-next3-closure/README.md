# next3: complete OH dependency namespace coverage

Next2's physical ELF inventory did not become a complete namespace policy.
Unity advanced from missing hitrace to missing libwm, although libwm was already
in the inventory. This change generates shared names and dependency roots from
the entire packaged runtime plus representative app DT_NEEDED graphs.

## Inputs and change

`audit_closure.py` reads all 90 native members in the Android, route and ZigZag
payload directories, retains next2's eight explicit NDK entry points, and walks
native sidecars for Anki, NetGuard, Auxio, VLC, Droid-ify, Wikipedia, Thunderbird,
OONI and LocalSend. Each app resolves its own sibling libraries before the
runtime/platform index, avoiding collisions between app libc++_shared builds.
The fd-noice input has no extracted native sidecars here and contributes zero
seeds; it is not claimed as a native-input test. Inputs were found on Mac first,
then in the local OrbStack input corpus; no upstream source was guessed.

The resulting graph contains 407 distinct ELF files. 292 explicit system names
(including preserved B87 supply) and five roots feed the generated
`bms/src/adapter/framework/app-native-loader/src/oh_system_dependencies.h`:
`/system/lib64`, `platformsdk`, `chipset-sdk`, `chipset-sdk-sp`, and `ndk`.
The existing B87 liblog-sharing branch receives this complete list. Caller
app-path admission remains unchanged; the fixed roots supply dependencies.
The generated name string is 6893 bytes, so the internal joined buffer is sized
for the validated caller string plus the generated constant, not PATH_MAX.
There is no wildcard inheritance or unchecked caller-provided path expansion.

The host mock's old 512-byte observation buffers truncated the enlarged list,
causing an initial test failure. They now hold 16384 bytes; assertions check
C++, libwm, length beyond 4096, the final libzuri entry, and foreign-path rejection.
No failed assertion was removed. The original public input-size limit remains.

`closure.json` records every source SHA, dependency edge, owning app context,
resolved path and unresolved edge. Missing independent filenames are explicitly
`libm.so`, `libdl.so`, and `libjnigraphics.so`. They are not fabricated or counted
as resolved; musl aliases and dynamic loads require device evidence. This task
expands OH namespace supply and does not implement missing Android libraries.

## Host validation and package

- Two strict OH6.1 builds are byte-identical: ANL `7a6683a5`.
- Full SONAME, NEEDED order and imported/exported symbols equal next2.
- Host suite: 145 checks, zero failures; repository known answers: 69, two skips.
- Negative control: next2 misses 276 required names and the complete root list.
- Full package dry-run: 281 files, no device I/O.
- Package: `/Users/zhaoyue/orca/workspaces/westlake-generation-v3c-next3-audio-anl`.
- Manifest SHA: `a0075b0558ccad3f4fcdfe1f33d570c21af5e610d266e01e4972f264f693097a`.
- Only two ANL aliases change from next2; AudioSystem runtime f87dcdf9 remains.

The package uses one `--upgrade` transaction for route/Android aliases, with
rollback to the exact preceding owned package. Keep r17m fixed, exposing r8b
only around the transaction. No installer or foundation change is involved.
Source, generated header, graph, recipe and tests are versioned; compiler and
frozen header/sysroot archive references are in source-provenance.json.

Device prediction: the two known Unity OH lookup failures should disappear;
HelloWorld/Auxio/NetGuard should retain their UI. VLC may remain white at the
known unimplemented AudioSystem.newAudioSessionId call. That existing failure
is reported separately from new regressions. Any control regression rejects
next3 and requires rollback. Device results and screenshots are recorded after
execution; host gates alone do not sign this package.
