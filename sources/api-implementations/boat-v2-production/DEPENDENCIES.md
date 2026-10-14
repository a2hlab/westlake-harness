# Fixed dependencies

The offline default entries never download, deploy, or run the Unity editor.
`dependencies.lock.json` pins the new execution toolchain, not an inferred historical producer.

* APK input: SHA `8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444`.
  Existing local input: `$WORKSPACES/../00.Workspace-games-ad1ab0a7/APKS/BoatAttack/dist/boat-attack-a.apk`.
  Pass that file with `--apk`. The archive members and their raw SHA are checked before transformation.
  A new Unity build is not a substitute for this exact input unless it independently matches the lock.
* Transform tool: Homebrew patchelf 0.19.1, `--patchelf` explicit path, exact binary SHA in the lock.
  Obtain the preserved toolchain from this closeout archive (outer persistence receipt), or supply an
  independently acquired copy matching the SHA. No `brew install` occurs in this recipe.
* Signal toolchain: OpenHarmony native SDK clang 15.0.4, `--sdk` explicit root.
  The lock enumerates 2,418 compiler/linker/strip/readelf/nm, sysroot and Clang-resource files.
  Use preserved archive `toolchain/sdk/` or a local SDK with all those exact bytes.
  Mac host system libraries/OS and Python are host prerequisites, not rebuilt by this package.
  The Linux SDK is not silently accepted as an equivalent compiler. A different SDK needs a separate
  new-execution lock and an honest output comparison.
* Python 3 standard library and an arm64 macOS host supporting these recorded executables.
  Python executable/version and platform are recorded in the new invocation environment.

## Project-to-APK recipe (not executed in this small closeout)

The game project is public source under its original Unity Companion License (`project/LICENSE.md`).
The Unity editor/Android module remain external licensed build tools, not missing Westlake API source.
Obtain a NEW independent clone (never use an active/dirty project):

```sh
git clone https://github.com/Unity-Technologies/BoatAttack.git "$NEW_CHECKOUT"
git -C "$NEW_CHECKOUT" checkout --detach dfaa9ef49a727c54c58ac1da0c5375760b0b6e8a
git -C "$NEW_CHECKOUT" lfs pull
python3 sources/api-implementations/boat-v2-production/project/build_project.py \
  --checkout "$NEW_CHECKOUT" --out "$NEW_PREPARATION"
```

Unity Hub editor **2020.3.23f1 (c5d91304a876)** with Android IL2CPP/ARM64 build support,
its Android SDK/NDK/OpenJDK/Gradle, and the delivered `Packages` locks are required.
Unity Package Manager acquires the packages at the recorded versions/registries.
The preparation applies the original camera priority change and original Editor build method.
For a separately approved large build, run the same entry on another clean checkout with `--run --unity "$UNITY"`;
provide `BOAT_KEYSTORE`, `BOAT_KEY_ALIAS`, `BOAT_KEYSTORE_PASS` via the environment.
Do not publish signing credentials. New JAR/APK signing or Unity compilation is not claimed byte-identical.
Original build-a.sh SHA and source provenance are in `source.lock.json`; that device-free recipe is extracted,
not invoked through the old multipurpose device script.

The precise historical SDK, signing input and complete Unity/LFS package checksum closure are not asserted
by the source commit alone. This entry exposes the real build path without upgrading that historical claim.
