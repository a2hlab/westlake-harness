# BMS route (Android APK installed into OpenHarmony BMS), copied in

The app-lighting campaign switched routes on 2026-09-28 (user decision): instead of Westlake's direct
launch — the APK only staged, running under the host bundle `org.westlake.imehost`, unknown to the
system — Android APKs are **installed into a patched OpenHarmony BMS** (`bm install -p x.apk`) and
launched from their desktop icon. This directory is that route's source, copied verbatim so it runs from
this repo; only the board allowlists were widened to our boards.

## Where it came from

| | |
|---|---|
| Source checkout | `~/orca/00.Workspace-games-ad1ab0a7`, branch `games/boatattack-repro`, commit `43ec24af9` (2026-09-24) |
| Copied from | the working clone `~/orca/workspaces/westlake-bms-suite`, which adds our serials to the allowlists |
| Validated there | OpenHarmony **6.1.0.31** D600 boards `61ae0be5…` and `5ce2dcee…` (8605): HelloWorld, ZigZag, Capybara Adventure, BoatAttack Android APKs on screen and interactive (`~/orca/00.Workspace/evidence/current-apk-lightup.md`) |
| Same architecture as | hanbin (`~/workspace/hanbin_adapter`): patched `bundle_installer` recognises `.apk` → `base_bundle_installer::ProcessBundleInstall` (in `libbms.z.so`) → dlopen `libapk_installer.so` → BMS `InnerBundleInfo` |
| On our boards | 2026-09-28 17:44: HelloWorld `restore` PASS on 5ea34a45 (black first screen → touch → red text, `Color -> RED`) |

## Layout (kept identical to the source, because the scripts use relative paths)

| Path | What |
|---|---|
| `.agents/skills/reproduce-helloworld/` | `scripts/reproduce.sh {check,quick,status,restore,rollback} <serial>` — the first gate on a new board |
| `.agents/skills/reproduce-zigzag-apk/` | same commands for ZigZag (Unity, EGL, native libs, touch) |
| `.agents/skills/reproduce-capybara-apk/`, `reproduce-boat-attack-apk/` | the next two gates; each extends the shared runtime generation (landscape parent session, real touchscreen projection, Swappy); BoatAttack also has `autostart-*` (boot-ready, launch from the desktop icon) |
| `.agents/skills/reproduce-oh61-game-suite/` | runs the four in order: `restore <serial>` on a new board, `quick` on an accepted one |
| `src/adapter/` | the adapter source: `framework/package-manager` (`jni/apk_installer.cpp`, `component_resolver`, `bms_projection`, `install_plan`), `appspawn`, `framework/*`, `ohos_patches/`, `aosp_patches/` |
| `src/tools/devices/` | per-game light-up drivers (`zigzag-apk-lightup.sh`, `boat-attack-apk-lightup.sh`, …) |
| `src/tools/wl-tools/` | `resign.sh` and signing inputs (public SDK cert chain; the SDK keystore's public default password) |

**Not in git** (their own rule, and ours: no APK/HAP/.so/payload/large run output): `APKS/`, `var/`,
`.bridge-payload/`, `.state/` are symlinks into `~/orca/workspaces/westlake-bms-suite`; binary files under
`src/adapter` (`frozen/*.so`, `third_party/oh_stubs/lib/*.so`, jars) were left out of the copy.

## Run

```sh
cd bms
.agents/skills/reproduce-helloworld/scripts/reproduce.sh check   <serial>   # read-only
.agents/skills/reproduce-helloworld/scripts/reproduce.sh restore <serial>   # deploy the shared generation + HelloWorld
.agents/skills/reproduce-zigzag-apk/scripts/reproduce.sh restore <serial>
```

Serials: `5ea34a4500000000000000001123012c`, `61b0657200000000000000000324012c`,
`5cd1e3dd00000000000000000923012c`. Take our board lock first (`scripts/lab/board_note.sh lock`); the
scripts also take their own device-channel lock.

Acceptance is a screenshot, and — from #15 — a running BMS or a matching global library hash does **not**
prove the patched BMS is loaded: check the library mapped in `/proc/<foundation pid>/root` + `maps`, and
read back an installed APK with `bm dump -n`.

## Not carried over

00.Workspace's own gates that do not apply here: the two-board serial allowlist (widened), the T006/CTS
one-click payload's `OpenHarmony-7.0.0.38` check (that path is for CTS on OH 7.0; we stay on 6.1), and
the absolute `games-c-5ea1` path the ZigZag driver pointed at (repointed, driver SHA re-pinned).
