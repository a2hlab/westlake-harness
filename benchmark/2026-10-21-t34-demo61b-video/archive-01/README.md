# T34 window archive receipt

The archive and its actual remote verification agree: **20,366,770 bytes**, SHA256 `ec5cb95d5f28a82edee9c963afd10240372384cca84a8ca072b0d686e3df5365`, and **3,828 payload files** (3,829 tar entries including `MEMBERS.json`). Remote alias: `HW248_ARTIFACT_ROOT/t34-demo61b-video-20261021/window.tar.gz`.

`command-2` returned 0. Its recorded verifier checks the compressed archive hash and size, exact manifest/member set and count, then each payload size and SHA before printing success. Independent local replay verified the actual archive bytes and all 3,828 payloads; the embedded manifest equals the separate member manifest. Original receipt and command evidence hashes are in `results.json`; accounts, host paths and original logs are not published. No re-upload was performed.

The snapshot covers W01/W02 through W02 after-close13, candidate inputs, transport/UI peers, Git integration and capability evidence. Later task changes are excluded. Archive integrity does not upgrade W02: the candidate failed visual acceptance and was rolled back; the restored homepage showed a network error, not healthy feed. This receipt is neither video/audio acceptance nor remote Git publication evidence.
