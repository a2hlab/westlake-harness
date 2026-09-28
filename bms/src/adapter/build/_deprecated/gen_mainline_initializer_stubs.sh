#!/bin/bash
# Generate / regenerate all FrameworkInitializer (and related) stubs that
# either SystemServiceRegistry.<clinit> or ActivityThread.initializeMainlineModules
# invokes.
#
# AOSP 14 ships these classes in mainline APEX modules; OH ships none.
# Without stubs, the calling-site triggers NoClassDefFoundError or
# NoSuchMethodError, poisoning downstream classes.
#
# Method spec syntax in the STUBS array:
#   FQN_OF_CLASS:method1[,method2[,...]]
# Each method is either:
#   nameOnly             — declares "public static void nameOnly()"
#   name/ParamFQN1[/ParamFQN2...] — declares
#       "public static void name(ParamFQN1 a0, ParamFQN2 a1, ...)"
# Special: param "java.util.function.Consumer" automatically becomes
# Consumer<android.content.Context> (the only Consumer signature
# initializeMainlineModules uses).
#
# Idempotent.  Generated files are listed by find under framework/mainline-stubs/java
# and compiled by compile_mainline_stubs.sh.

set -e
ROOT="${ADAPTER_ROOT:-$HOME/adapter}"
STUBS_DIR="$ROOT/framework/mainline-stubs/java"

declare -a STUBS=(
    # ActivityThread.initializeMainlineModules + SystemServiceRegistry callers
    "android.os.StatsFrameworkInitializer:registerServiceWrappers,setStatsServiceManager/android.os.StatsServiceManager"
    "android.media.MediaFrameworkInitializer:registerServiceWrappers,setMediaServiceManager/android.media.MediaServiceManager"
    "android.media.MediaFrameworkPlatformInitializer:registerServiceWrappers,setMediaServiceManager/android.media.MediaServiceManager"
    "android.bluetooth.BluetoothFrameworkInitializer:registerServiceWrappers,setBluetoothServiceManager/android.os.BluetoothServiceManager,setBinderCallsStatsInitializer/java.util.function.Consumer"
    "android.scheduling.SchedulingFrameworkInitializer:registerServiceWrappers"
    "android.provider.DeviceConfigInitializer:initialize,setDeviceConfigServiceManager/android.provider.DeviceConfigServiceManager"
    "android.telephony.TelephonyFrameworkInitializer:registerServiceWrappers,setTelephonyServiceManager/android.os.TelephonyServiceManager"
    "android.nfc.NfcFrameworkInitializer:registerServiceWrappers,setNfcServiceManager/android.nfc.NfcServiceManager"
    # SystemServiceRegistry-only callers (no setter currently invoked)
    "android.adservices.AdServicesFrameworkInitializer:registerServiceWrappers"
    "android.app.appsearch.AppSearchManagerFrameworkInitializer:initialize"
    "android.app.blob.BlobStoreManagerFrameworkInitializer:initialize"
    "android.app.job.JobSchedulerFrameworkInitializer:registerServiceWrappers"
    "android.app.role.RoleFrameworkInitializer:registerServiceWrappers"
    "android.app.sdksandbox.SdkSandboxManagerFrameworkInitializer:registerServiceWrappers"
    "android.content.rollback.RollbackManagerFrameworkInitializer:initialize"
    "android.devicelock.DeviceLockFrameworkInitializer:registerServiceWrappers"
    "android.health.connect.HealthServicesInitializer:registerServiceWrappers"
    "android.nearby.NearbyFrameworkInitializer:registerServiceWrappers"
    "android.net.ConnectivityFrameworkInitializer:registerServiceWrappers"
    "android.net.ConnectivityFrameworkInitializerTiramisu:registerServiceWrappers"
    "android.net.wifi.WifiFrameworkInitializer:registerServiceWrappers"
    "android.ondevicepersonalization.OnDevicePersonalizationFrameworkInitializer:registerServiceWrappers"
    "android.safetycenter.SafetyCenterFrameworkInitializer:registerServiceWrappers"
    "android.system.virtualmachine.VirtualizationFrameworkInitializer:registerServiceWrappers"
    "android.uwb.UwbFrameworkInitializer:registerServiceWrappers"
)

emit_method() {
    local mspec="$1"     # e.g. "setStatsServiceManager/android.os.StatsServiceManager"
    local out="$2"
    local mname mparams
    if [[ "$mspec" == */* ]]; then
        mname="${mspec%%/*}"
        mparams="${mspec#*/}"      # remaining slash-separated params
    else
        mname="$mspec"
        mparams=""
    fi
    local sig="public static void ${mname}("
    if [[ -n "$mparams" ]]; then
        local i=0
        IFS='/' read -ra ARR <<< "$mparams"
        for p in "${ARR[@]}"; do
            local java_type
            if [[ "$p" == "java.util.function.Consumer" ]]; then
                java_type="java.util.function.Consumer<android.content.Context>"
            else
                java_type="$p"
            fi
            if [[ $i -gt 0 ]]; then sig+=", "; fi
            sig+="${java_type} a${i}"
            i=$((i + 1))
        done
    fi
    sig+=") { /* no-op */ }"
    echo "    $sig" >> "$out"
}

count=0
declare -A SEEN
for entry in "${STUBS[@]}"; do
    fqn="${entry%%:*}"
    if [[ -n "${SEEN[$fqn]:-}" ]]; then
        echo "  WARN: duplicate FQN $fqn — keeping first definition"
        continue
    fi
    SEEN[$fqn]=1
    methods="${entry#*:}"
    pkg="${fqn%.*}"
    cls="${fqn##*.}"
    pkg_path="${pkg//.//}"
    out_file="$STUBS_DIR/$pkg_path/$cls.java"
    mkdir -p "$STUBS_DIR/$pkg_path"

    {
        echo "// AUTO-GENERATED by gen_mainline_initializer_stubs.sh."
        echo "// Edit only if a real OH-side service replaces the no-op."
        echo "package $pkg;"
        echo ""
        echo "/** Mainline APEX stub.  The real impl lives in an APEX module"
        echo " * that OH does not ship; stubs the call sites in"
        echo " * SystemServiceRegistry.<clinit> +"
        echo " * ActivityThread.initializeMainlineModules so they link cleanly. */"
        echo "public final class $cls {"
        echo "    private $cls() {}"
    } > "$out_file"
    IFS=',' read -ra MARR <<< "$methods"
    for m in "${MARR[@]}"; do
        emit_method "$m" "$out_file"
    done
    echo "}" >> "$out_file"
    count=$((count + 1))
done

echo "Generated $count stub source files under $STUBS_DIR"
echo "Next: bash build/compile_mainline_stubs.sh"
