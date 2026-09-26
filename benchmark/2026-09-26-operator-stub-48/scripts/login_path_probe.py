import re
from androguard.core.apk import APK
try:
    from androguard.core.dex import DEX
except Exception:
    from androguard.core.bytecodes.dvm import DalvikVMFormat as DEX
apk="/Users/zhaoyue/OrbStack/a2hlab/home/zhaoyue/a2hlab/app-inputs/toutiao/toutiao.apk"
a=APK(apk)
# 1) does any account/login-guide class reference metasec (ms.bd.c.m or MSManagerUtils)?
login_pkgs=("Lcom/ss/android/account", "OneKeyLogin", "RedPacket", "red_packet")
metasec_refs=[]
# 2) who calls AccountManager.loginInner and TransparentAccountLoginActivity onCreate trigger
callers_loginInner=[]
for db in a.get_all_dex():
    d=DEX(db)
    for cls in d.get_classes():
        cn=cls.get_name()
        is_login = cn.startswith("Lcom/ss/android/account") or "OneKeyLogin" in cn or "RedPacket" in cn
        for m in cls.get_methods():
            try: ins=list(m.get_instructions())
            except Exception: continue
            for i in ins:
                o=i.get_output()
                if is_login and ("ms/bd/c/m;->a(" in o or "MSManagerUtils" in o or "mobsec/metasec" in o):
                    metasec_refs.append((cn,m.get_name(),o[:80]))
                if "AccountManager;->loginInner" in o:
                    callers_loginInner.append((cn,m.get_name(),o[:90]))
print("== metasec refs INSIDE account/login/red-packet classes: %d"%len(metasec_refs))
for x in metasec_refs[:20]: print("   ",x)
print("\n== callers of AccountManager.loginInner: %d"%len(callers_loginInner))
for x in callers_loginInner[:20]: print("   ",x)
