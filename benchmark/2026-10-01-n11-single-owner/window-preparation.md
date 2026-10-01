# N11 window preparation

Outer ACK80 15:04:08 extended the batch window to <=45 minutes. `plan61b.json` uses required offline_precheck, existing U8/N10b maps and source-identity evidence. Acceptance of the public window path finally requires the U9 full sweep (119/168 U8 keys logged unknown sessionId).

Host NEEDED/SONAME/export surface matches U8; runtime surface matches approved N10b. No new ABI drift from N11. The recorded initial strict U8-runtime equality assertion failed because N10b itself adds Skia/Emboss and changes an unconsumed JNIEnv inline export; the correct comparison to N10b passes.
