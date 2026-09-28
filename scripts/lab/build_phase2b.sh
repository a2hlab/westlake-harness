#!/bin/bash
# Framework build, steps 1-20 of the reconstructed SOURCE_STACK DAG, in dependency waves.
# Runs in the author's workspace path; each step logs to $LOGS/<step>.log and is skipped once ok.
set -u
A=/home/dspfac/a2hlab/source-closure/verify; O=$A/out; WT=$A/westlake/tools; J=$A/toolchains/jdk21/jdk-21.0.6+7/bin/java
SHIM=$HOME/a2hlab/tools/libmap32bit.so
mountpoint -q $A || { sudo mkdir -p $A && sudo mount --bind "$HOME/a2hlab/ws" $A; } || exit 1
M=$HOME/a2hlab/manifest; LOGS=$HOME/a2hlab/logs/build; mkdir -p "$LOGS"; cd "$M" || exit 1
ok() { for s; do [ -e "$LOGS/$s.ok" ] || return 1; done; }
step() {
  local name=$1; shift
  ok "$name" && { echo "SKIP $name"; return 0; }
  echo "START $name $(date +%T)"
  if "$@" > "$LOGS/$name.log" 2>&1; then touch "$LOGS/$name.ok"; echo "OK    $name $(date +%T)"; else echo "FAIL  $name $(date +%T)"; return 1; fi
}
# wave 1
step host-bootstrap python3 $WT/build_android_native.py --workspace $A --target host --extra-inventory $A/westlake/framework-tools/libraries.json --library protoc --library protoc-gen-javastream --library protoc-gen-javanano --library libbase.so --library liblog.so --jobs 6 --out $O/host-bootstrap &
step host-base python3 $WT/build_android_native.py --workspace $A --target host --library libbase.so --library liblog.so --library libz.so --out $O/host-base &
step host-crypto python3 $WT/build_android_native.py --workspace $A --target host --library libcrypto.a --out $O/host-crypto &
step framework-aidl python3 $WT/generate_framework_aidl.py --workspace $A --aidl $A/toolchains/android-build-tools35/android-15/aidl --profile $A/westlake/framework-tools/java-profile.json --jobs 6 --out $O/framework-aidl &
step framework-flags python3 $WT/generate_framework_flags.py --workspace $A --compiler-build $O/aconfig --library wifi_framework_aconfig_flags_lib --library adservices_flags_lib --library ondevicepersonalization_flags_lib --library appsearch_flags_java_lib --library bluetooth_flags_java_lib --library healthfitness-aconfig-flags-lib --library mediaprovider_flags_java_lib --library avf_aconfig_flags_java --library android.os.profiling.flags-aconfig-java --library com.android.permission.flags-aconfig-java --library media_mainline_flags_java_lib --out $O/framework-flags &
step experimental-annotations python3 tools/build_experimental_annotations.py --workspace $A --core-build $O/core-java/java --out $O/experimental-annotations &
step jarjar python3 tools/build_jarjar.py --workspace $A --out $O/jarjar &
wait; echo "WAVE1_DONE $(date +%T)"
# wave 2
ok host-bootstrap host-base && step framework-generators python3 $WT/build_framework_generators.py --workspace $A --bootstrap $O/host-bootstrap --host-base $O/host-base --jobs 6 --out $O/framework-generators &
ok host-bootstrap host-base && step framework-generators-catalog python3 $WT/build_framework_generators.py --workspace $A --bootstrap $O/host-bootstrap --host-base $O/host-base --catalog --jobs 6 --out $O/framework-generators-catalog &
ok host-bootstrap host-crypto && step hidl-generator python3 $WT/build_hidl_generator.py --workspace $A --native-tools $O/host-bootstrap --crypto-build $O/host-crypto --parser-build $O/parser-tools --jobs 6 --out $O/hidl-generator &
ok framework-aidl && step framework-misc-java python3 $WT/generate_framework_misc_java.py --workspace $A --aidl-build $O/framework-aidl --xsdc-build $O/xsdc --java $J --out $O/framework-misc-java &
ok framework-aidl host-bootstrap && step cronet-java python3 $WT/generate_cronet_java.py --workspace $A --aidl-build $O/framework-aidl --native-tools $O/host-bootstrap --out $O/cronet-java &
ok framework-flags && step framework-resources python3 tools/build_framework_resources.py --workspace $A --flag-build $O/framework-flags --out $O/framework-resources &
wait; echo "WAVE2_DONE $(date +%T)"
# wave 3
ok hidl-generator framework-aidl && step framework-hidl python3 $WT/generate_framework_hidl.py --workspace $A --aidl-build $O/framework-aidl --compiler-build $O/hidl-generator --native-tools $O/host-bootstrap --out $O/framework-hidl &
ok framework-generators framework-generators-catalog framework-aidl && step framework-module-java python3 $WT/generate_framework_module_java.py --workspace $A --aidl-build $O/framework-aidl --native-tools $O/host-bootstrap --schema-tools $O/framework-generators --catalog-build $O/framework-generators-catalog --out $O/framework-module-java &
ok framework-generators && step framework-java-gen python3 $WT/generate_framework_java.py --workspace $A --native-tools $O/host-bootstrap --schema-tools $O/framework-generators --xsdc-build $O/xsdc --java $J --out $O/framework-java-gen &
wait; echo "WAVE3_DONE $(date +%T)"
# wave 4: sequential
step framework-java python3 tools/build_framework_java.py --workspace $A --core-build $O/core-java/java --core-extension-build $O/java-extensions --support-build $O/framework-java-support --experimental-annotations-build $O/experimental-annotations --aidl-build $O/framework-aidl --flags-build $O/framework-flags --module-build $O/framework-module-java --hidl-build $O/framework-hidl --misc-build $O/framework-misc-java --cronet-build $O/cronet-java --schema-build $O/framework-java-gen --resources-build $O/framework-resources --out $O/framework-java \
 && step westlake-java python3 tools/build_westlake_java.py --workspace $A --westlake-source $A/westlake --core-build $O/core-java/java --core-extension-build $O/java-extensions --framework-build $O/framework-java --out $O/westlake-java \
 && step framework-runtime python3 tools/package_framework_runtime.py --workspace $A --rules $A/westlake/framework-tools/runtime-jarjar-rules.txt --core-build $O/core-java/java --core-extension-build $O/java-extensions --framework-build $O/framework-java --adapter-build $O/westlake-java --support-build $O/framework-java-support --jarjar-build $O/jarjar --out $O/framework-runtime \
 && step framework-boot env LD_PRELOAD=$SHIM python3 tools/build_framework_boot.py --host-build $O/host-tools/host --core-build $O/core-java/java --extension-build $O/java-extensions --framework-build $O/framework-runtime --out $O/framework-boot
echo "PHASE2B_DONE $(date +%T)"
