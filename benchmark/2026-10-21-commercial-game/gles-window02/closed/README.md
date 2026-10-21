# G24 window02: observed loader progress, game still failed

The previous trial never launched the game. This trial completed the original apply (rc=0, active_verified), verified the Hello World control visually, and clicked the installed Genshin desktop icon once. The first image was white; the later image was the launcher. Child 31523 exited with code 1. No game frame or playable state is claimed.

Compared with baseline child 10946, the observed libGLESv2 dependency failure disappeared and libyuanshen reached a missing __register_atfork relocation. Earlier __errno and the final Unity JNI exception remain. This establishes progress to a later loader check, not working GLES. The game child maps were not captured. See the [independent launch review](../launch-review-01/README.md) for exact raw-log excerpts, hashes and limitations.

Original rollback returned rc=0. Outer independently rechecked all 319 baseline hashes, the full relevant mount stack, and three BoatAttack private-library hashes. The restored Hello World image was visually accepted. Test children were absent, original SLEEP/30000/10000 power settings restored, and the lock released at 20:43:19.590276 +08:00: 1007.590276 seconds after lock acquisition. The 318 window-only native exceptions were retired after recovery.

The existing [candidate source and build recipe](../../gles-loader-candidate/README.md) are unchanged. No runtime-success API or freeze is added. Full original execution logs remain under $HOME/.local/share/westlake/commercial-game-20261021/g24-window02; [remote-archive.json](remote-archive.json) records the SHA-verified 67,886,623-byte durable backup on hw248.

- [Candidate control](candidate-control.jpeg)
- [Game first image](game-first.jpeg)
- [Game later image](game-later.jpeg)
- [Restored control](restored-control.jpeg)

The closure-final power command without -s returned help; only the subsequent closure-power/power.txt is accepted as power-state evidence.
