# Asset file descriptors: offline single-library repair plan

The previous assumption that returning a ParcelFileDescriptor requires a native Binder bridge is wrong. The active source selects a layoutlib fallback on OH: ReturnParcelFileDescriptor throws UnsupportedOperationException("Implement me"). Its unused __ANDROID__ branch also closes the descriptor and returns null. NewPipe's ProfileVerifier and uhabits reach this common helper. Merely defining __ANDROID__ would not fix either branch.

## Existing implementation

Mac source found first: vm-copies/westlake-current, commit 532633da63b770d3d459c74683db6d7a1f82a022, framework/android-runtime/src/android_util_AssetManager_aosp.cpp:247. results.json records full source paths and SHA. No VM or remote search is needed. The implementation calls Asset::openFileDescriptor, writes APK byte offset and length, constructs java.io.FileDescriptor and android.os.ParcelFileDescriptor(FileDescriptor), then transfers descriptor ownership to Java. This is a local Java constructor, not a Binder transaction. Source provenance is confirmed; validation on the two requested apps is still pending.

asset-fd.patch replaces only that helper and its obsolete conditional with the existing Westlake body. NativeOpenAssetFd and NativeOpenNonAssetFd share it. The active build recipe is benchmark/2026-09-30-commonevent-registration/runtime-recipe.sh (AssetManager translation unit listed at line 379).

## Smallest replacement

Rebuild only liboh_android_runtime.so from the exact active runtime source variant, preserving SQLite, VelocityTracker, CommonEvent and that board's graphics variant. Do not substitute a 9e14 build for 5ea's 32df graphics variant. Use prepare_for_base.py with the target board's actual active package, then deploy_generation.sh --replace /system/android/lib64/liboh_android_runtime.so. Save the current JAR receipt, expose the baked JAR for deployment checks, restore exactly the same overlay afterward. Roll back only this replacement on a control regression.

## Acceptance and negative cases

1. Host: strict link, unchanged JNI signature (JLjava/lang/String;[J)Landroid/os/ParcelFileDescriptor;, expected changed helper only, package dry-run.
2. Stored APK asset: descriptor reads exact bytes at reported start offset, correct length, Java close owns the fd.
3. Missing or compressed asset: FileNotFoundException rather than UnsupportedOperationException; no leaked descriptor. Repeated open/close must not grow the process fd count.
4. Fixed-JAR clean installs of NewPipe and fd-uhabits: no Implement me at nativeOpenAssetFd; capture t5/t20 and first subsequent fatal error. HW/ZZ controls first.
5. Predict only removal of this JNI wall for both apps, not that all later UI/network walls disappear.

No build or device change for this repair has been performed. Flutter r4 remains first in the board queue.
