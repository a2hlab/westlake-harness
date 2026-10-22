# Genshin commercial-game qualification

## Current accepted status (2026-10-22)

G34 included one ordinary Genshin icon click: the captured UI went from white content to the launcher, and the parent reported child29761 exited with **signal11**. **No game frame, fault PC or stack was obtained.** The original runtime was rolled back and the window closed; see the [accepted closure evidence](locale-runtime-window/closed/README.md). This is not a first-launch plan or a game acceptance PASS.

The [diagnostic authoring stop](locale-runtime-window/diagnostic-stop-20261022/README.md) remains in effect. The [route-provider source lookup](route-provider-source-lookup/README.md) records bounded provenance findings and remaining source/build gaps; it supplies no new runtime result or crash cause. The [Android reference fresh attempt](../2026-10-22-genshin-android-reference/fresh-02-blocked/README.md) failed locally in ADB before device contact; installation and launch were not run, and Android device liveness remains unknown.

This entry-page correction adds **no new execution result or game progress**. The accepted historical static-stage record below is retained for provenance.

## Historical static-stage record

The original local search did not locate a Genshin input. Official acquisition and exact-input analysis replaced that absence; neither BoatAttack's first frame nor Toutiao's audio proves Genshin compatibility. **At that static-stage checkpoint, no Genshin device launch had been observed.**

| Stage | Evidence and implementation | Accepted scope |
|---|---|---|
| Existing input search | [intake](intake/README.md) | 393 APK manifests and 48 XAPK container metadata records; embedded XAPK APK manifests remained unknown. |
| Prior implementation reuse | [reuse](reuse/README.md) | 11 conditional Unity/graphics/input/audio mappings, 31 source references, five actual small-input tool commands. Boat-specific C7/C4 binaries are excluded from reuse. |
| Official input | [official-input](official-input/README.md) | Official CN base APK, 513,290,344 bytes; signature v1/v2, package/version/splits and download chain verified. Full game content not acquired. |
| Exact target analysis | [exact-static](exact-static/README.md) | 32 ELF libraries, five DEX files, one REA package inspection and five focused REA methods. Startup, graphics and audio observations retain dynamic-resolution limits. |
| Spare-board preparation | [spare-preflight](spare-preflight/README.md) | Fresh 5ea boot, 124 runtime and 36 boot-image members, full package list, foreground and power. Read-only evidence accepted; historical disabled recovery draft rejected separately. |
| APK library extraction | [installer-review](installer-review/README.md) | Four source pins show APK-contained libraries use a separate extraction path from optional external sidecars; actual deployed behavior remains to be observed. |

Exact APK SHA256: `abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc`. Package `com.miHoYo.Yuanshen`, version `7.1.0_48052158_48145775`, arm64-v8a. The APK and large raw dumps remain in persistent private storage; source tools, small observations and their integrity indexes are in this repository.

Outer independent checks: official-input Rust selector passed (71 references and the APK rehashed); exact-static landing checked 98 files with no source-path or frozen violations and its Rust selector passed. An additional private-receipt check passed. Independent peer checked all 95 payload hashes and all five complete REA method records. These checks establish static evidence integrity, not runtime compatibility. Original author `PENDING` fields are preserved; this page records the separate outer acceptance.

The historical first-launch preparation used [the launch contract](../../specs/commercial-game-round1/t6-first-launch.spec.md). Subsequent execution and diagnostic disposition are linked above. Login, full resource download, sound, graphics and gameplay have not passed acceptance.
