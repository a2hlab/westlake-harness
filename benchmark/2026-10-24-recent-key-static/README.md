# OH 6.1.0.31 Recent key — static candidate, not executed

The earlier local subset search was inconclusive; the RUNBOOK-mapped source root `hw248:/opt/build-trees/oh610_lts_source` contains the definition. Its `build/version.gni:16` and `base/startup/init/services/etc/param/ohos.para:32` identify **6.1.0.31**. Product context is wukong100 as supplied; no device was queried.

- `foundation/multimodalinput/input/interfaces/native/innerkits/event/include/key_event.h:3167–3172`: Recent key, since API18.
- `foundation/multimodalinput/input/frameworks/proxy/events/src/key_event.cpp:853`: **KEYCODE_RECENT = 10011**. Repository commit `9f2252ce9b195931f34c8dcc4d924d39fabebe88` (`OpenHarmony-v6.1-Release-13-g9f2252ce9`); checked files clean.
- `test/testfwk/arkxtest/uitest/input/ui_input.cpp:206–212`: parses the numeric keyID, constructs `AnonymousSingleKey` and calls `TriggerKey`. `uitest/server/system_ui_controller.cpp:890–910` forwards the code to MMI key events. Repository commit `3d3416b34dd33b45df6f6665a1144a7c98397006`, tag `OpenHarmony-v6.1-Release`.
- SystemUI `features/navigationservice/.../common/constants.ts:25` uses **3** as its navigation-button selector; `KeyCodeEvent.ts:100–103` instead publishes `CREATE_RECENT_WINDOW_EVENT`. Do not confuse this local selector with the MMI keyID.

**Command candidate only:**

```sh
/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc -t 61b0657200000000000000000324012c shell 'uitest uiInput keyEvent 10011'
```

This injects the ordinary Recent key; it does not itself close a task or terminate a child. Source version is established; deployed-binary identity and real UI response remain unverified. A separately authorized normal UI observation can check the resulting screenshot/layout. No historical coordinates, guessed keycode, new controller or device action was used here. `oh610-source-excerpts.jsonl` pins exact source lines/SHA; `oh610-results.json` records mapping and limits. Prior inconclusive `results.json` remains unchanged.
