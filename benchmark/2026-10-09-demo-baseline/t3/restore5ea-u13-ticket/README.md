# 5ea signed U13 recovery

The first replay was correctly refused before any bind: `begetctl stop_service appspawn-x` returned zero, but a Route B orphan (PID 24657, PPID 1, deleted executable under `/data/local/tmp/asx/`) remained. The first replay journal has zero operations. No root-parent signal, reboot, forced bind or weakened guard was used by this lane.

Outer delegated removal to the original owner cc-t3 under the existing cx-t0 lock (master 0f01ed6a18). Read-only confirmation then showed no appspawn-x and the same boot ID. The fresh `retry-r2` journal preserves the original failed journal and replays only the already-signed U13 baseline, using a freshly authorized baseline-only native ticket. All 319 baseline hashes match the independently signed recovery inventory; the original source journal remains unchanged.

The executor restored 56 layers. The original restored smoke passed: runtime 821de739cf81, boot ee927db88a67, ART/JVM one load each and the accepted baseline bridge/runtime counts. HelloWorld and ZigZag t20 captures are retained without modification for outer review. Final parent/child verification passed (parent 30436, child 6251); 319 paths have empty diff/absence. The lock was released and rc1/empty holder confirmed. Verification and unlock receipts are included; raw command receipts and journals remain in retry-r2.

Screenshot/liveness counts in facts.txt are generated directly by run_facts.py. foreground_unconfirmed is preserved; UI signoff belongs to the outer reviewer.
