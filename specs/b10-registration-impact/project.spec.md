spec: project
name: "B10 registration ownership and native consumers"
---

## 意图

Inventory U8 registration delegation and initialization side effects against explicitly identified AOSP 14 r1 sources, then measure the 166-app native consumer surface.

## 约束

- Offline, no device writes, runtime changes, push, or changes to frozen predictions.
- Artifact identity must run before reading deployed libraries. Never substitute N10b candidate bytes for U8.
- Record owner-specific caches: initialization in liboh_android_runtime does not initialize libandroid's separate globals.
- A delegated entire registration function is not a skipped cache initialization merely because it is called through dlsym.
- Native symbol imports and literal lookup candidates are exposure, not proof of execution or a crash.
- Wrong-version or unpinned reference files remain unverified, never silently called AOSP 14 r1.
