# Genshin commercial-game qualification

The original local search did not locate a Genshin input. Official acquisition and exact-input analysis now replace that absence; neither BoatAttack's first frame nor Toutiao's audio proves Genshin compatibility. **No Genshin device launch has been observed in this accepted static slice.**

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

The next experiment is a bounded normal first launch on spare 5ea, under [the launch contract](../../specs/commercial-game-round1/t6-first-launch.spec.md). Fresh state and recovery preparation precede the write window. Capture actual startup stderr/hilog and display images, then pursue the first observed blocker. 61b's existing demo remains unchanged. Login, full resource download, sound, graphics and gameplay have not passed acceptance.
