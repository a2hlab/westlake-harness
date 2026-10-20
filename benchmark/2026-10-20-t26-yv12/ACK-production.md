ACK t26-t27-joint-production-ready

OFFLINE_CANDIDATE_NOT_DEPLOYMENT_AUTHORIZED. Candidate fc58cec5c7a445a28ed0c0e3ec44d486f16f0921afe8ef4b6974bd96ca9574e9 / 96680 bytes. Lock 0x6ec8, unlockAndPost 0x6edc, geometry 0xe3c0. Exact T25 baseline reproduced; 78 exports unchanged, sole libc dependency, no TEXTREL; exact HWUI/player ABI consumer check rc0.

Current source: 34 actual core C cases, 15 full route scenarios, final-observer 5 getter cases + 10 joint routes; peer 14 actual R23 entries pinned (original receipt 9af7eae53a0d7327b7f741f34310fd7ed4bf0b479da5462aacf3f96fe908afff). Seven Rust selectors, eight receipt negatives, spec parse/lint and explicit path gate passed. Production-01 parser failure preserved; production-02 uses explicit GNU format and nonempty ABI assertions. No device operations; playback and actual getter binding remain UNKNOWN.

Minimal landing: production-landing-paths.txt; exact payload SHA: production-landing-manifest.json. Public production references are under production-02/, not the historical draft results.json. Original build and test bytes remain under .private/ and the peer's pinned persistent directory. Remote archive is separate and pending.
