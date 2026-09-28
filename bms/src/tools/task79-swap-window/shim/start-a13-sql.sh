#!/system/bin/sh
# Restart appspawn-x with the two preloads Noice needs:
#   libwl_stackgrow.so   -- walks the main stack down before ART reads its bounds, so
#                           ART does not freeze it at 128 KB and put its guard page there
#   libwl_sqlite_jni.so  -- supplies the SQLite JNI this substrate never shipped
# Only PIDs whose /proc/<pid>/exe is exactly /system/bin/appspawn-x.real are killed.
for p in /proc/[0-9]*; do
  pid=${p#/proc/}
  exe=$(readlink "$p/exe" 2>/dev/null)
  if [ "$exe" = "/system/bin/appspawn-x.real" ]; then echo "KILL $pid"; kill -9 "$pid" 2>/dev/null; fi
done
sleep 1
rm -f /dev/unix/socket/AppSpawnX
: > /data/local/tmp/appspawn-verifier-stderr.log
# STOPGAP until libart's fix102 AXML parser can be rebuilt: it misses
# <application android:theme="@0x7f14023d"> because that attribute is a reference,
# so ApplicationInfo.theme stays 0 and AppCompat refuses to inflate.
export WL_APP_THEME=com.github.ashutoshgngwr.noice:0x7f14023d
# Same parser gap, different attribute: <application android:name> is missed too, so
# ApplicationInfo.className is null and makeApplication() builds a bare
# android.app.Application.  Noice is a Hilt app, so MainActivity.onCreate then dies with
# "Given component holder class android.app.Application does not implement interface ...".
export WL_APP_CLASS=com.github.ashutoshgngwr.noice.NoiceApplication
# ContextImpl.getSharedPreferences only consults UserManager when targetSdkVersion >= O,
# and getSystemService(UserManager.class) is null here (no "user" SA on this board), so
# every getSharedPreferences() NPEs.  Report a pre-O target to skip that guard.
export WL_APP_TARGET_SDK=25
# WL_ZERO_OH_TOKEN was a dead end: the token is NOT why CreateWindow returns 1005.
# The real reason is that this board has no legacy WindowManagerService at all --
# SA 4606 is served by the SceneBoard stack, which answers OHOS.ISceneSessionManager,
# while the adapter writes an OHOS.IWindowManager interface token.  Leave the real
# token in place (it is the more correct of the two protocol rows).  Set
# WL_ZERO_OH_TOKEN=1 to bring the zeroing back.
export LD_PRELOAD=/data/local/tmp/libwl_stackgrow.so:/data/local/tmp/libwl_sqlite_jni.so
# Launch appspawn-x.real DIRECTLY, not /system/bin/appspawn-x.
#
# /system/bin/appspawn-x used to be a symlink to appspawn-x.real (which is why every
# running daemon's /proc/<pid>/exe read back as .real, and why the kill loop above
# matches on that path).  It has since been replaced with a standalone binary from a
# different build.
#
# That matters because appspawn-x pins the SHA-256 + Build-ID of the exact
# liboh_adapter_bridge.so and liboh_android_runtime.so it was compiled against
# (adapter_bridge_identity.cpp / WLAR_ADAPTER_BRIDGE_SHA256_HEX).  Whatever is at
# /system/bin/appspawn-x now is pinned to a bridge this board does not have, so it
# dies right after JNI_CreateJavaVM with:
#     [AppSpawnX][E] exact adapter bridge admission failed before runtime load
#     [AppSpawnX][E] Failed to start ART VM on worker pthread, ret=-1
# .real is pinned to the artifacts this board actually carries, so it boots.
#
# If this ever fails the same way, check the pins before anything else:
#   sha256sum /system/android/lib64/liboh_adapter_bridge.so
#   strings /system/bin/appspawn-x.real | grep -oE '[0-9a-f]{64}' | sort -u
# The bridge hash must appear in both lists.
DAEMON=/system/bin/appspawn-x.real
[ -x "$DAEMON" ] || DAEMON=/system/bin/appspawn-x
echo "DAEMON=$DAEMON"

# --- hap-domain wrapper pairing -------------------------------------------------
# ChildMain::applySELinux dlopens a FIXED path and refuses to call into it unless
# its GNU Build-ID equals the one compiled into the daemon
# (child_main.cpp / kHapDomainWrapperPinnedBuildId).  Daemon and wrapper only ship
# as a pair.  If they are mismatched the child dies right after the DAC step with:
#     [AppSpawnX][E] applySELinux: wrapper Build-ID mismatch ... failing closed
#     [AppSpawnX][E] applySELinux failed, ret=-1 - aborting child
# and there is NOTHING in the child log after that, which reads like a silent death.
#
# .real pins 007c6462ffdf5c01a9906d46b8a2492a9ca2f6c1.  /system/lib64 may hold a
# DIFFERENT wrapper belonging to another build of appspawn-x -- do not overwrite it,
# somebody else's daemon is paired to it.  Instead bind-mount our matching copy over
# the path inside a PRIVATE mount namespace, so only this daemon and the children it
# forks see the swap.  It evaporates when the daemon exits; nothing on disk changes.
WRAP_SYS=/system/lib64/libwestlake_hap_domain_wrapper.so
WRAP_OURS=/data/local/tmp/libwestlake_hap_domain_wrapper.so
NEED_BIND=1
if [ ! -f "$WRAP_OURS" ]; then
  echo "WRAP=missing-ours ($WRAP_OURS) -- child will abort in applySELinux"
  NEED_BIND=0
elif [ "$(sha256sum <"$WRAP_SYS" 2>/dev/null)" = "$(sha256sum <"$WRAP_OURS" 2>/dev/null)" ]; then
  echo "WRAP=already-paired (no bind needed)"
  NEED_BIND=0
fi

if [ "$NEED_BIND" = 1 ]; then
  echo "WRAP=bind-in-namespace"
  # toybox unshare has no --propagation, so make / rprivate by hand FIRST; without
  # that the bind can propagate out of the namespace and clobber the shared path.
  unshare -m sh -c "
    mount -o rprivate / 2>/dev/null || mount -o private / 2>/dev/null
    mount -o bind $WRAP_OURS $WRAP_SYS || { echo 'BIND_FAILED'; exit 1; }
    exec $DAEMON
  " >/data/local/tmp/aspx-stdout.log 2>&1 &
else
  "$DAEMON" >/data/local/tmp/aspx-stdout.log 2>&1 &
fi
echo SPAWNED=$!
# Leak check: from OUT here the shared path must still be whatever it was.
sleep 1
echo "WRAP_SYS_NOW=$(sha256sum <"$WRAP_SYS" 2>/dev/null | cut -c1-16)"
echo "WRAP_OURS   =$(sha256sum <"$WRAP_OURS" 2>/dev/null | cut -c1-16)"
sleep 3
for p in /proc/[0-9]*; do
  pid=${p#/proc/}
  exe=$(readlink "$p/exe" 2>/dev/null)
  if [ "$exe" = "/system/bin/appspawn-x.real" ]; then echo "RUNNING $pid"; fi
done
