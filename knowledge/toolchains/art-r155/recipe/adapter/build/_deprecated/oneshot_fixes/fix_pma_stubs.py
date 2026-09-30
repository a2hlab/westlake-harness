#!/usr/bin/env python3
"""Auto-add missing abstract method stubs to PackageManagerAdapter.java"""
import subprocess, re, sys

ADAPTER = "/home/HanBingChen/adapter"
AOSP = "/home/HanBingChen/aosp"
F = f"{ADAPTER}/framework/package-manager/java/PackageManagerAdapter.java"
CLASSES_JAR = f"{AOSP}/out/target/common/obj/JAVA_LIBRARIES/framework-minus-apex_intermediates/classes.jar"
JSON_JAR = f"{AOSP}/out/soong/.intermediates/libcore/mmodules/intracoreapi/art.module.intra.core.api.stubs/android_common/turbine-combined/art.module.intra.core.api.stubs.jar"
JAVAC = f"{AOSP}/prebuilts/jdk/jdk17/linux-x86/bin/javac"
AIDL = f"{AOSP}/frameworks/base/core/java/android/content/pm/IPackageManager.aidl"

import glob
java_files = sorted(glob.glob(f"{ADAPTER}/framework/**/java/**/*.java", recursive=True))
java_files = [f for f in java_files if "appspawn-x" not in f]

def compile():
    r = subprocess.run(
        [JAVAC, "-source", "11", "-target", "11", "-classpath", f"{CLASSES_JAR}:{JSON_JAR}",
         "-d", "/tmp/adapter_java_classes", "-Xlint:none"] + java_files,
        capture_output=True, text=True)
    return r.stderr

def get_missing_method(stderr):
    for line in stderr.split("\n"):
        if "does not override abstract method" in line:
            m = re.search(r"abstract method (\S+)\(", line)
            if m:
                return m.group(1)
    return None

def get_aidl_sig(method_name):
    with open(AIDL, "r") as f:
        for line in f:
            if method_name + "(" in line:
                sig = line.strip().rstrip(";")
                # Remove 'in ' parameter modifier
                sig = re.sub(r'\bin\b ', '', sig)
                # Remove 'inout ' parameter modifier
                sig = re.sub(r'\binout\b ', '', sig)
                return sig
    return None

def default_return(ret_type):
    if ret_type == "void": return ""
    if ret_type == "boolean": return "return false;"
    if ret_type == "int": return "return 0;"
    if ret_type == "long": return "return 0L;"
    if "[]" in ret_type: return "return null;"
    return "return null;"

for i in range(30):
    stderr = compile()
    method = get_missing_method(stderr)
    if not method:
        print(f"Round {i+1}: All abstract methods resolved!")
        break

    print(f"Round {i+1}: Adding stub for {method}")
    sig = get_aidl_sig(method)
    if not sig:
        sig = f"void {method}()"
        print(f"  WARNING: {method} not in AIDL, using void stub")

    ret_type = sig.split()[0]
    ret_val = default_return(ret_type)

    stub = f"""
    @Override
    public {sig} {{
        {ret_val}
    }}
"""

    with open(F, "r") as f:
        content = f.read()

    # Insert before getHoldLockToken
    marker = "    @Override\n    public android.os.IBinder getHoldLockToken"
    if marker in content:
        content = content.replace(marker, stub + marker)
    else:
        # Fallback: insert before last }
        content = content.rstrip().rsplit("}", 1)
        content = content[0] + stub + "\n}"

    with open(F, "w") as f:
        f.write(content)

# Final compile
stderr = compile()
nerr = stderr.count("error:")
import os
nclass = sum(1 for _ in os.popen("find /tmp/adapter_java_classes -name '*.class'"))
print(f"\n=== Final: Errors={nerr}, Classes={nclass} ===")

# Create jar
if nclass > 0:
    os.system(f"cd /tmp/adapter_java_classes && jar cf {ADAPTER}/out/adapter/oh-adapter-framework.jar .")
    size = os.path.getsize(f"{ADAPTER}/out/adapter/oh-adapter-framework.jar")
    print(f"jar: {size // 1024}K")
