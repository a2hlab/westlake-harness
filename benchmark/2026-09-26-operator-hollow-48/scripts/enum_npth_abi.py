import re
from androguard.core.apk import APK
try:
    from androguard.core.dex import DEX
except Exception:
    from androguard.core.bytecodes.dvm import DalvikVMFormat as DEX
apk="/Users/zhaoyue/OrbStack/a2hlab/home/zhaoyue/a2hlab/app-inputs/toutiao/toutiao.apk"
a=APK(apk)
want={"Lcom/bytedance/crash/jni/NativeBridge;","Lcom/bytedance/apm/profiler/Profiler;"}
out={}
for db in a.get_all_dex():
    d=DEX(db)
    for cls in d.get_classes():
        if cls.get_name() in want:
            for m in cls.get_methods():
                if "native" in m.get_access_flags_string():
                    out.setdefault(cls.get_name(),[]).append((m.get_name(),m.get_descriptor()))
for cn in sorted(out):
    print("# %s  (%d natives)"%(cn,len(out[cn])))
    for nm,desc in sorted(out[cn]):
        # JNI signature = descriptor without spaces
        sig=desc.replace(" ","")
        print("%s|%s"%(nm,sig))
print("# TOTAL %d"%sum(len(v) for v in out.values()))
