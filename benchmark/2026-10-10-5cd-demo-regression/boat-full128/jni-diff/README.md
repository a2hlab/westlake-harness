# Boat runtime JNI regression: exact-artifact static comparison

The earlier Boat-only validation did not protect the shared runtime JNI surface. The 128-app regression caught a real missing JNI implementation; SELinux CANTOPEN is a different failure. Do not freeze `adc125f4` as a substitute for U13 `18763dd4` on this evidence.

## Evidence first

- Boat: `adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130`,744856bytes. U13: `18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae`,3194328bytes. Both were available locally; no build or board modification was used for this comparison.
- `results.json` and `scoped-table-delta.json` are derived from relocations, function pointers and ELF STT_FILE/table symbols using the existing scanner, not absence of strings alone. U13 has1443 detected native-table rows/787exports; Boat1095rows/268exports.349 U13 rows lack a match within the same compiled table/source scope;269 unique name/descriptor pairs are absent anywhere in the Boat scanned tables. These are two different counts, not runtime failures.
- The four SQLite/CursorWindow registrars are strong U13 functions but weak8-byte Boat functions, body `e0031f2ac0035fd6` (`mov w0,wzr; ret`). They return success without registering methods. `nativeOpen(Ljava/lang/String;ILjava/lang/String;ZZII)J` is present in U13 and absent from Boat tables. The observed LibreSudoku UnsatisfiedLinkError independently confirms this one path.

## Missing class/table inventory

| Class or compiled table owner | U13 entries absent in the same Boat table | Basis |
|---|---:|---|
| android.database.sqlite.SQLiteConnection |27| ELF table + explicit source attribution |
| android.database.CursorWindow |21| ELF table + source;3 generic method signatures also exist in unrelated Boat tables |
| android.database.sqlite.SQLiteDebug |1| ELF table + source, nativeGetPagerStats |
| android.database.sqlite.SQLiteGlobal |1| ELF table + source, nativeReleaseMemory |
| android.view.VelocityTracker |7| Entire compiled table absent; startup registrar absent; source registration excerpt |
| android.media.AudioSystem |4| Source registration + compiled kMethods absent |
| adapter.activity.ActivityManagerAdapter CommonEvent additions |5| Source registration + compiled kMethods absent |
| android.graphics.BLASTBufferQueue sync additions |4| Explicit class registration and scoped table delta |
| com.google.android.gles_jni.GLImpl table |250| Compiled TU/table absent + corresponding registrar absent; separate GLImpl class string is only corroboration |
| com.google.android.gles_jni.EGLImpl table |28| Compiled TU/table absent + corresponding registrar absent; same evidence limitation |
| android.graphics.EmbossMaskFilter |1| Source registration + compiled table absent |
| android.hardware.Camera |2 additional unscoped rows| Camera source matches table function symbols; getNumberOfCameras and _getCameraInfo |
| android.media.audiopolicy.AudioProductStrategy |1 additional unscoped row| Source matches listAudioProductStrategies function; stack/unnamed table |

The final3 rows are outside the349 object-scoped count. `source-registration-excerpts.txt`/index identify explicit class bindings for custom additions. All method names, descriptors, table addresses and function symbols are in the JSON inventories; registrations executed at runtime were **not** observed by this static scan. Some APIs might be provided later/by other libraries. No claim is made that every static difference crashes an app.

## Small affected API examples

- VelocityTracker: nativeInitialize(I)J, nativeDispose(J)V, nativeClear(J)V, nativeAddMovement(JLandroid/view/MotionEvent;)V, nativeComputeCurrentVelocity(JIF)V, nativeGetVelocity(JII)F, nativeIsAxisSupported(I)Z.
- AudioSystem: newAudioSessionId()I, native_getMaxChannelCount()I, native_getMaxSampleRate()I, native_getMinSampleRate()I.
- CommonEvent: nativeSubscribeCommonEvent, nativeUnsubscribeCommonEvent, nativePublishCommonEvent, nativeFinishCommonEvent, nativeGetStickyCommonEvent.
- BLAST: nativeSyncNextTransaction(JLjava/util/function/Consumer;Z)Z, nativeStopContinuousSyncTransaction(J)V, nativeClearSyncTransaction(J)V, nativeGatherPendingTransactions(JJ)Landroid/view/SurfaceControl$Transaction;.
- SQLiteConnection includes nativeOpen plus statement/transaction/binding/execute APIs; complete27-entry list is below.

```
nativeOpen(Ljava/lang/String;ILjava/lang/String;ZZII)J
nativeClose(J)V
nativeRegisterCustomScalarFunction(JLjava/lang/String;Ljava/util/function/UnaryOperator;)V
nativeRegisterCustomAggregateFunction(JLjava/lang/String;Ljava/util/function/BinaryOperator;)V
nativeRegisterLocalizedCollators(JLjava/lang/String;)V
nativePrepareStatement(JLjava/lang/String;)J
nativeFinalizeStatement(JJ)V
nativeGetParameterCount(JJ)I
nativeIsReadOnly(JJ)Z
nativeGetColumnCount(JJ)I
nativeGetColumnName(JJI)Ljava/lang/String;
nativeBindNull(JJI)V
nativeBindLong(JJIJ)V
nativeBindDouble(JJID)V
nativeBindString(JJILjava/lang/String;)V
nativeBindBlob(JJI[B)V
nativeResetStatementAndClearBindings(JJ)V
nativeExecute(JJZ)V
nativeExecuteForLong(JJ)J
nativeExecuteForString(JJ)Ljava/lang/String;
nativeExecuteForBlobFileDescriptor(JJ)I
nativeExecuteForChangedRowCount(JJ)I
nativeExecuteForLastInsertedRowId(JJ)J
nativeExecuteForCursorWindow(JJJIIZ)J
nativeGetDbLookaside(J)I
nativeCancel(J)V
nativeResetCancel(JZ)V
```

## Reproduction and limits

`compare_runtime_jni.py --u13 <18763dd4-file> --boat <adc125f4-file> --out <directory>` checks full input hashes before scanning. `known-answers.txt`: four artifact-tied assertions pass (4 empty SQLite registrars, exact nativeOpen delta,27 SQLiteConnection rows,7 VelocityTracker rows). No artifact was rebuilt.

REA tools were not connected; read-only doctor reported registration drift (`rea-doctor.json`). No configuration repair/installation was performed. Analysis used installed LLVM and the existing repository scanner.

Repair entry point: preserve U13’s shared JNI surface and port the independently proven Boat rendering change into that baseline, rather than replacing the entire runtime with this older, smaller runtime. A new candidate must still pass the authorized128-app reboot regression. This report creates no patch or deployment.
