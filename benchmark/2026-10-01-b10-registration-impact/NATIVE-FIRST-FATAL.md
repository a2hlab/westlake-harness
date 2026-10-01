# U8 first-fatal operand follow-up

## Correction to the stack-only interpretation

The absent converter stack frame did **not** exclude AssetManager: both deployed converters tail-call `GetLongField`. The additional read-only disassembly identifies `AssetManager.mObject:J` as the null **field ID**, not a missing `SceneInfo` field. For ath0-rpn, the premise “null pointer” is false: the observed fault is a **nonzero invalid virtual-table pointer** loaded through the second nonpurgeable GPU resource.

No target memory or binary was changed. APK/provider hashes, exact Skia BuildID, register dump and disassembly coordinates are recorded in `NATIVE-FIRST-FATAL.json` and `evidence/`.

## glmark2: `android.content.res.AssetManager.mObject:J`

1. APK `org.linaro.glmark2_2.apk` SHA `45bb2451be0db777cb5e5ac1cadcc7a09333e59a0912d6536108d2b66857d6ae`; AArch64 member SHA `af99ef0fe7a4723020ef7f29eba2606dc46b32f40343aae519d3d4118eaf1b14`.
2. `Java_org_linaro_glmark2_native_getSceneInfo` starts at **0xad60c**. The U8 crash caller **+60 = 0xad648** is `bl AAssetManager_fromJava@plt`. The incoming third argument (`AssetManager`) is moved into x1 at **0xad638**. This is before the function's later SceneInfo class/constructor lookups. Full function disassembly contains no direct JNI `GetFieldID` table load at offset **752**; the later table offset **264** is `GetMethodID`, not `GetFieldID`.
3. Exact U8 `libandroid` converter **0x7d9d8–0x7d9ec** loads x2 from `gAssetManagerOffsets.mObject`, loads JNI function-table offset **808** (`GetLongField`), then **`br x3`**, not `blr`. U8 runtime converter **0x1daa48–0x1daa5c** has the same tail-call shape. Thus the retained caller LR makes the converter disappear from the stack; it was not an inlined app field lookup.
4. ELF relocations bind the cache-address GOT slots:
   - libandroid GOT **0x88b70** → `_ZN7android20gAssetManagerOffsetsE`, definition **0x8b9e0**;
   - runtime GOT **0x2085c8** → the same symbol name, definition **0x20f1c0**.
   These are separate definitions; their actual interposition/namespace bindings were not captured. Do not pick one solely from `DT_NEEDED` or the absence of its stack frame.
5. Original lookup strings are at AOSP14r1 `frameworks/base/core/jni/android_util_AssetManager.cpp:1564`: `GetFieldIDOrDie(env, assetManager, "mObject", "J")`, where the class is `android/content/res/AssetManager`. The U8 donor performs the same lookup at `android_util_AssetManager_aosp.cpp:1577`.

**Established:** the converter consumes a null cached ID for `AssetManager.mObject:J`; this explains U8 `hilog.txt:45186–45191` and `:45326–45327`. **Not established:** that the Java field itself is absent, which owner was selected, or whether skipped registration/interposition/classloader failure left that owner's ID null. N10b cache initialization is a relevant experiment, not an already-proven unlock.

## ath0-rpn: second nonpurgeable GPU resource, not null

The local b68 system Skia binary has SHA `caa86d58671eef0079cdcfa60cf943c6cda6ee7934ecfdf59bf37df754a2abe4` and **BuildID `2f7219f228e1e8c11205d5c787f8e153`**, exactly matching the selected U8 fault. Other local stub/deployment copies were rejected because their identities differ.

The selected source is **5ea-seq-cv2/20261001T122134-78628011**, not the invalid concurrent 5ea-cv2 directory. Target PID/TID **27323/27348**, report timestamp **12:22:55.963**, hilog SHA `325d2ebe5574019573eae9eb7c7296a15c4498fc6f38809e4336a14d7d64ae6a`.

| Instruction / value | Meaning |
| --- | --- |
| 0x10e9d74: `ldr x21, [x0, #200]` | Obtain the resource-cache pointer from the direct context. |
| 0x10e9d90: `ldr x8, [x21, #56]` | Read the nonpurgeable resource-array storage. |
| 0x10e9d98: `ldr x0, [x8, x22, lsl #3]` | Read the resource pointer at index x22. |
| 0x10e9d9c: `ldr x8, [x0]` | Read that resource's virtual-table pointer. |
| **0x10e9da0: `ldr x8, [x8]`** | **Faulting load of the virtual method.** |
| 0x10e9da4: `blr x8` | Intended resource `dumpMemoryStatistics` call; not reached on the faulting iteration. |

Registers `hilog.txt:47190–47198`: **x22=1**, resource **x0=0x7f17252b4f** (nonzero, not eight-byte aligned), virtual-table **x8=0x7f0e749d1800** (nonzero), which exactly equals **SEGV_MAPERR fault address** at `:47178`. Direct context **x20=0x7f1adff2d0**, resource cache **x21=0x7f1b191530**, trace object **x19=0x7f03ffae28** are all nonzero. The saved LR **0x7f0dce9da8** is consistent with completing an earlier resource callback before the index-1 dispatch.

Same-b68 source evidence: `GrDirectContext.cpp:606` invokes `fResourceCache->dumpMemoryStatistics`; the inlined first loop is `GrResourceCache.cpp:1313–1314`, `fNonpurgeableResources[i]->dumpMemoryStatistics`. Its purgeable loop is later, not this PC. Source file hashes and excerpts are in `evidence/skia-source.json`; matching binary BuildID establishes the disassembly target, but does not constitute a cold source rebuild.

**Established object:** `fResourceCache->fNonpurgeableResources[1]` and its invalid virtual-table operand. **Unknown upstream cause:** corrupted array element, stale/freed resource, incompatible layout or another prior writer. The captured logs/registers provide no allocation/free/write history, so this audit does not claim which one produced the invalid operand. A null guard for Context or trace object would not fix the observed fault.

## Offline replay

```sh
OUT="$(mktemp -d /tmp/native-first-fatal.XXXXXX)"
python3 benchmark/2026-10-01-b10-registration-impact/inspect_first_fatal.py \
  --workspaces "$WORKSPACES" --output "$OUT"
```

The script verifies APK/member/hilog SHA and exact Skia SHA/BuildID, runs provider `artifact_identity` before disassembly, preserves the full app function and converter/Skia slices, and refuses mismatched fault operands. It extracts binaries only into scratch and removes the extracted APK member afterward. No board access is required.
