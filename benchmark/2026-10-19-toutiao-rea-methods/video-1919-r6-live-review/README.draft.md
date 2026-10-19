# r6 native-log observation — in progress

This draft is not a frozen packet and makes no API change. The approved r4 four-file tuple was reused without a new repair. Candidate boot df563b46 reached a real feed with child7085/b11201 and parent5130/b9571. One video tap produced three byte-identical cover screenshots; playback is NOT_PASSED and audio unknown.

The child bridge logged `property debug.ttplayer.log.enable=true` after player-load messages. This establishes an actual child property read, consistent with the static consumer path, without a runtime return-PC/call stack tying that individual line to JNI_OnLoad. Explicit all-level, same-PID hilog and stderr were retained. Exact setDataSource/prepareAsync labels were absent, not evidence those methods did not execute. The original GOT status remains unknown.

Four-file rollback used the original apply-plan. Restored boot66dbabb7 has raw parameter errNum106 and COMPLETE same-plan snapshot. baseline-final checks original run/media/player bytes and physical/private inode identity, with compat absent. Its actual screenshot is still IMEhost. The first baseline child7578 exited; a second icon click has not established a new child/feed in reviewed evidence. Do not call first-icon or second-icon restoration successful. Parent maps were not included in baseline-final's command. Final closure/unlock and any later feed remain pending.

Raw evidence stays under the portable private root `$HOME/.local/share/westlake/toutiao-resume-20261019`; individual file hashes are in the checkpoint JSONs. Large stderr/hilog/process dumps are not copied into the public draft. No device calls, old test reruns, deployment gates or API edits were made by this lane.
