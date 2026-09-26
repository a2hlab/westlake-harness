import re
from androguard.core.apk import APK
try:
    from androguard.core.dex import DEX
except Exception:
    from androguard.core.bytecodes.dvm import DalvikVMFormat as DEX
apk="/Users/zhaoyue/OrbStack/a2hlab/home/zhaoyue/a2hlab/app-inputs/toutiao/toutiao.apk"
a=APK(apk)
TGT="TransparentAccountLoginActivity"
# 1) methods that reference the Transparent login activity specifically
hits=[]
for db in a.get_all_dex():
    d=DEX(db)
    for cls in d.get_classes():
        for m in cls.get_methods():
            try: ins=list(m.get_instructions())
            except Exception: continue
            for i in ins:
                if TGT in i.get_output():
                    hits.append((cls.get_name(),m.get_name(),i.get_name(),i.get_output()))
print("== refs to %s: %d"%(TGT,len(hits)))
for cn,mn,inm,o in hits:
    print("  %s->%s [%s] %s"%(cn,mn,inm,o[:100]))
# 2) does any metasec wrapper (MSManagerUtils / ms.bd.c.m) sit on a path to login?
#    quick: strings mentioning login-guide / auto-login triggers
print("\n== login-guide / auto-popup trigger strings ==")
seen=set()
for db in a.get_all_dex():
    d=DEX(db)
    for s in d.get_strings():
        sv=s.decode() if isinstance(s,bytes) else str(s)
        if re.search(r"(login_guide|auto.?login|one.?key|login_popup|force_login|red_packet|login_dialog|transparent_login|guide_login)", sv, re.I):
            seen.add(sv)
for s in sorted(seen)[:25]: print("  ",s)
