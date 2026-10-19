# Toutiao r4: slot bindings observed; playback not passed; rollback verified

Three independently reviewed screenshot groups do not demonstrate dynamic video. The exact fault-associated cache GOT read now matches the expected player-local address, and two IID slots match the compatibility object. These observations are kept separate from the original probes' `unknown` results and from audio/video acceptance.

## What was observed

- Candidate boot `fade993a-5649-44c5-9677-79f6ee82a8ad`, parent `6696/17318`, child `9360/18882`, UID guard `20011206`. Raw before/after process-stat samples retain the same child PID/birth/PPID; these samples do not prove uninterrupted liveness at every intervening instant.
- [play1](play1/record.json): video-tab click `(360,1858)`; t5/t20/t25 show the same cover content. A tutorial overlay and surrounding UI change at t20; these are not dynamic-video evidence.
- [center-tap](center-tap/record.json): click `(600,900)`; all three screenshots are byte-identical and show the same cover.
- [swipe-next](swipe-next/record.json): swipe from `(600,1450)` to `(600,400)` selects a different cover. Within that group, the reviewed content remains the same; screenshot-byte differences are not sufficient proof of video playback. The actual [swipe helper](historical-recipes/video_probe_swipe_r4.py) is preserved unchanged as historical execution evidence, not a generic rerun tool.
- These are **three groups scheduled through 25 seconds**, not the contract's two audible play/pause/resume/exit cycles. Dynamic video did not pass; audio and complete loading remain unknown.

## Object-specific observations

Each group's original `got.json` remains byte-for-byte `status=unknown`. [The later reread](got-read-r2/result.json) is an independent receipt: child birth/PPID/UID checked before each exact 8-byte read, raw command and explicit remote rc0 preserved, three observed values match the expected pointers. Two refer to compatibility IID addresses; the third is the fault-associated cache address inside the player. This does not claim all105 relocations executed or all providers were verified.

[PT_LOAD evidence](got-read-r2/compat-load-bias.json) was independently compared with the actual compatibility ELF program headers: four segments share bias `0x7f83e40000`, device/inode/path identity. Four segment starts are not four instances. [Independent checks](got-read-r2/independent-check.json) and [narrow maps excerpt](got-read-r2/mapping-excerpt.txt) retain that scope. Original unknown receipts are not rewritten to matched.

[Identity output](identity/before-video.stdout.txt) contains the four candidate SHA values and actual parent/child stats. [State summary](state/independent-summary.json) independently checks COMPLETE before/after, the same62-target plan (61 bind-target rows),351 labels each and no label/config hash differences. Snapshot equality is scoped to that plan, not every device file or playback behavior.

## Provenance and scope

Original screenshots and small technical evidence are copied unchanged; normalized records only replace personal local screenshot paths and add independent review fields plus original-record SHA. Producer pending visual verdicts are preserved as producer history. Big stderr/maps/raw snapshot files remain in private persistent storage, with portable paths and hashes in source-pins.json and raw-command-pins.json. No commercial binaries or whole raw app logs are published here.

[facts.txt](facts.txt) is the actual run_facts output for this package parent. It finds12/12 captures (nine observation images, two failed-navigation images and one recovery-feed image). Standard alive tables are absent, so all six alive entries remain unknown; zero numeric counters are not death claims. Raw process-stat facts are reported separately.

## Candidate navigation failed

`leave-video` remains a video page; `home-feed` is an empty comment composer, not feed. Both original images remain in navigation-*; outer reports no input or send. Producer directory names are not verdicts.

## Recovery and closure

[Rollback](rollback/result.json) executed against the original apply-plan with host/explicit remote rc0. The original run d3518cef/media fecf91e1/player b427614d bytes are restored; compat is absent. After fresh boot `eef63e15-9d12-47ad-b0d0-fb57ad8dbf90`, [the actual verification command](rollback-final/commands/command-00007.json) checks parent5826/birth8498 and physical/private SHA and inode equality, and emits the child stat observed as8384/birth10007, and compat absence/unmapped. [The final screenshot](rollback-final/screen.jpeg) was independently viewed and shows real recommended feed. [MAIN UNLOCK](rollback-final/canonical-unlock.txt) is20:28:45. The same62-target snapshot/351labels/config SHA is unchanged; this remains a scoped comparison.

Playback remains **NOT PASSED**; recovery is verified. The outer [archive receipt](archive/window-archive.json) verifies14,884,299 bytes, SHA `5247bf079bcbc4d5ccb4ac0ac36b880b6bef86e270fb4ba8a7bd5667d069c987`. It agrees with the private receipt; this reviewer did not repeat remote transfer/checks. The final manifest freezes evidence, not API capability. No device calls/builds/runtime tests were performed by this reviewer. Prior r3 packet is unchanged.
