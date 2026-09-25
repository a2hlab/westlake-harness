# #48 route C: core libandroid sensor exports

Board 61b0657200000000000000000324012c only. Independent harness branch
`test/libandroid-sensor-48`; VM source worktree `westlake-operator-sensor48`,
branch `test/operator-sensor-48`, source 72ed855566c530c46cdd5ec3f378b1b979f8bbda.
All VM commands run through `orb -m a2hlab bash -lc '<command>'`. Commit only.

`build_sensor.py` reproduced the stock core libandroid SHA
dc5eb800eb5626f41f72cb9ed8fe59f2c35151b0e8f2ee3b49cd9779886a47b4 from its
recorded link inputs. Five existing source object hashes match their manifest.
It compiled only android_sensor_noop.c and relinked only libandroid.so.
New SHA: 14fe6c92f6f034b109e5ada98a79be25df9d36efedf1024fc393fa592c67e0ee.
The exact seven new ASensor dynamic exports are present, all original exports
remain, and DT_NEEDED is unchanged. The supplied assert_libandroid_sensor.sh
passes 7/7; an independent dynamic-table comparison prevents its static-symbol
fallback from masking a missing dynamic export. Build commands and input hashes
are preserved. No full native-runtime build or downstream rebuild.

Deployment backs up core `runtime/libandroid.so` by SHA and preserves its file
label. It does not target `webview-t-lib/libandroid.so`. The same ability38-v7
operator stage, A1 ART ae2cb182, shim85c789f4 (GLES + npth refusal), mc46 bridge
d4fae8e5, npth8b8d559c, and run.sh17781b81 (four tt targets + libttcrypto-first
LD_PRELOAD) remain. Seven component hashes are checked before and after each
round. vm.max_map_count=1048576 is asserted before startup and reapplied by the
existing guardian. No system-partition or policy changes.

Five fresh starts use the exercised #49 runner with separate data/evidence.
Each round stops the guardian, kills prior app PIDs/parent, preserves all three
old profile trees, creates empty ones and launches a new parent/child. Consent
and article clicks use real uinput after visual confirmation. Original PID and
birth are bound; guardian replacement never counts as survival. Each successful
round requires a real NewDetailActivity lifecycle record, at least 180s after
detail RESUMED, readable article screenshots, no metasec ULE/exit and no original
process terminal record. Raw stderr, parent log, samples and matching faultlogs
are retained. The old #49 group is not mixed in: it ended 3/5 body survival,
2/5 metasec main exit and was ACK(blocked), commit1c5dad5.

Results pending. This is a finite reliability window, not a guarantee of
unlimited uptime or of full metasec native functionality. Exports alone do not
prove successful relocation/initialization; runtime exceptions are reported.

Live pointers remain `/data/local/tmp/operator45/{child.pid,parent.pid,guard.pid,child.stderr.path}`.
Stop guardian without killing app: board shell
`touch /data/local/tmp/operator45/stop; kill $(cat /data/local/tmp/operator45/guard.pid)`.
Archive root `/data/local/tmp/operator45-crashes`; old core backup subdirectory
`sensor48-original`. No automatic rollback to the old candidate is planned.
