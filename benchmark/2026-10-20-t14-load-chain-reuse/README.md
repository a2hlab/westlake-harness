# T14 conditional reuse card: already covered load chain only

**No deployment admission. No board calls, compilation, derivation or old-root-cause investigation.** Select a reuse only after T14 captures its actual first load error; optional MDL ENOENT is not that selection signal.

| Layer | Existing minimal artifact/recipe | Strongest retained evidence |
|---|---|---|
| Android OpenSL IID and player dependency routing | R3/r4 four-file set: run template 79275cf9, compat9f558aaf, media d2882303, player5fba8050 | static README Update4 observed exact61b player IID error; Update8 and R4 cards record subsequent load/cache progression |
| mffmpeg by-name init safety | candidate-r3/derive_mffmpeg.py: exact fecf91e1 -> d2882303 | source/recipe/raw execution receipt and remote mirror in selected-change-r3.json; this was a static-predicted hazard, not a T14 observed failure |
| Player proc cache binding | candidate-r4/derive_ttmplayer_selfrel.py: exact b427614d -> 5fba8050 | 105 relocations, raw derive receipt rc0 and exact source SHA in candidate-r4/raw-log-manifest.txt; no re-analysis here |
| Complete later observation bundle | R8 reuses R3 media/routing and R4 cache fix; player0b4d95c5 plus compat6e83e924 adds bounded log mirror | candidate-r8/window/results.json: exact two log hops matched, 256 records, setDataSource/prepare reached; cover stayed static, audio unknown |

**Choice:** R4 is the minimal previously prepared four-artifact load/cache set. R8 is the more completely archived, actually executed observation set carrying those changes; it is not an audio fix or playback seal. Do not add R9 networking or R10 window-provider work for an IID load failure.

## Exact reusable identities and build provenance

- media original `fecf91e1fcda600661f501ce76a97456ad7e330b584013f2b742afb680b337c9` -> `d2882303bf5dc34e297a404e4b57a214d9c30ddaf0f496eb2ef9f7dcac09c4b4`. Recipe SHA `2165a64fd206af09eb252761f5374827b1d812100a5955c9ea2ccb9f9805e923`; R3 raw/mirror location is in static/selected-change-r3.json.
- player original `b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02` -> R4 `5fba80506cd1a494de5fb6aee63930192d6d0539657cca51e99381ff8a052ee4` -> R8 `0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471`. R4 recipe SHA `5e1530098039d49c768d1eac9a66b91303ccb07f58d27ca826a57564bd226fc6`. R8 derive source/raw receipts and exact R4 input archive are in candidate-r8/candidate.json and archive-receipt.json.
- minimal compat `9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f`; R8 mirror compat `6e83e924aae709f0c90ba2a966910febb63471b7a9a6294c6dee585a73ff3b4b`. Original source/build/toolchain in candidate/; R8 source/build_candidate.sh/raw rc0 records in candidate-r8/.
- R8 offline archive `$HW248_ARTIFACT_ROOT/toutiao-video-r8-offline-20261019/offline.tar.gz`, SHA `16ff9162c9fe53aedc6cf1c6d79b9fd03a0afc9fa2d25c183418fe87d8d2cdd5`; source-inputs.tar.gz SHA `7e8e8cb02d7df8dc9a372e207335b156c5acc8c797470f2dd3a4e89ce2c0dbf2`. R8 actual window archive SHA `dae77825dfac6d87608a88438c0991ad3af3c49854db9fb47518854c02af1f4e`, path candidate-r8/window/archive-receipt.json. These records jointly cover the four-file set; do not claim one standalone tar is an unchanged 5cd deployment package.

## Current 5cd differences that prevent copying the executor

The saved actual5cd run hashes `5a3aef638000e49f2a966b2179d57fe7628c29a4897921209fec539bd5dc1b79`. The exact diff from61b d3518cef has only UID20011206 ->20011300 and WL_PARENT_ID33 ->29 (baseline-run.diff). The observed media/player hashes match R3/R4 exact original inputs. The5cd cfg is19d0201b, not61b91e31b. Window29 is a saved value, not a future live-WID assertion.

The R8 executable/admission explicitly pins61b, owner20011206, cfg91e31b and exact WID-derived61b templates. Reuse its CAS/backup logic only through a separately reviewed5cd plan, with fresh actual serial/boot/parent/birth/private inode/run/UID/label/WID/provider reads. Never push its61b run template or reuse old apply-plan.

## Rollback and next decision

The recorded R8 window restored run/media/player from its original apply plan, removed the exact temporary compat, fresh-booted, checked original private inodes/parameter absence and actual feed, then unlocked. For5cd the rollback targets are its own fresh run5a3a-derived preimage, original mediafecf/playerb427, prior compat presence and original5cd cfg/control state—not61b d351/UID20011206. Old evidence does not authorize a5cd restart. T14 forbids deployment/reboot, so selecting this candidate only opens a later dedicated deployment contract.

If T14 emits the known IID or matching player load error, select the existing bounded set; retain any additional provider closure requirements. If there is no actual player attempt or a different first failure, keep this card pending. Screenshots or library maps alone do not establish loader success.
