#!/usr/bin/env python3
"""Apply the 3 framework-fix edits to baksmali'd adapter-runtime-bcp (5ea34a45).
Pure-additive, anchored on unique lines, assert-verified. Reuses the existing
pure-DEFAULT no-op Answers (ExternalSyntheticLambda2 -> alarm -> DEFAULT)."""
import sys, pathlib
base = pathlib.Path(sys.argv[1])  # out-smali dir

def edit(rel, anchor, insert, after=True, occ=1):
    p = base / rel
    s = p.read_text()
    assert s.count(anchor) >= occ, f"anchor not found ({s.count(anchor)}x) in {rel}: {anchor!r}"
    # locate the occ-th occurrence (line-based)
    idx = -1
    for _ in range(occ):
        idx = s.index(anchor, idx + 1)
    line_end = s.index("\n", idx + len(anchor) - 1) + 1
    if after:
        s2 = s[:line_end] + insert + s[line_end:]
    else:
        line_start = s.rfind("\n", 0, idx) + 1
        s2 = s[:line_start] + insert + s[line_start:]
    assert s2 != s
    p.write_text(s2)
    print("PATCHED", rel)

# --- Edit 1: LocalServiceBinders.get(): early no-op ITelephonyRegistry proxy ---
edit("adapter/core/LocalServiceBinders.smali",
     ".method public static declared-synchronized get(Ljava/lang/String;)Landroid/os/IBinder;\n    .registers 8",
     '''
    # [WESTLAKE #48 X/Twitter] telephony.registry -> no-op ITelephonyRegistry (reuse pure-DEFAULT Answers = ExternalSyntheticLambda2/alarm)
    const-string v0, "telephony.registry"

    invoke-virtual {p0, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v0

    if-eqz v0, :wl_tr_orig

    const-string v1, "com.android.internal.telephony.ITelephonyRegistry"

    new-instance v2, Ladapter/core/LocalServiceBinders$$ExternalSyntheticLambda2;

    invoke-direct {v2}, Ladapter/core/LocalServiceBinders$$ExternalSyntheticLambda2;-><init>()V

    invoke-static {p0, v1, v2}, Ladapter/core/LocalServiceBinders;->proxy(Ljava/lang/String;Ljava/lang/String;Ladapter/core/LocalServiceBinders$Answers;)Landroid/os/IBinder;

    move-result-object v0

    return-object v0

    :wl_tr_orig
''')

# --- Edit 2: OHServiceManager.getService(): route telephony.registry to LocalServiceBinders.get ---
edit("adapter/core/OHServiceManager.smali",
     "    invoke-static {p1}, Ladapter/core/OHServiceManager;->lookupAdapter(Ljava/lang/String;)Landroid/os/IBinder;",
     '''    # [WESTLAKE #48 X/Twitter] telephony.registry -> LocalServiceBinders no-op (before lookupAdapter default:null)
    const-string v0, "telephony.registry"

    invoke-virtual {p1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v0

    if-eqz v0, :wl_tr_orig2

    invoke-static {p1}, Ladapter/core/LocalServiceBinders;->get(Ljava/lang/String;)Landroid/os/IBinder;

    move-result-object v0

    return-object v0

    :wl_tr_orig2
''', after=False, occ=2)

# --- Edit 3: ApplicationMetaDataReader.populate(): force Flutter Impeller off ---
edit("adapter/packagemanager/ApplicationMetaDataReader.smali",
     "    iput-object p1, p0, Landroid/content/pm/ApplicationInfo;->metaData:Landroid/os/Bundle;",
     '''    # [WESTLAKE #48 LocalSend/Flutter] force Skia GL (Impeller ext-proc NULL -> first-frame pc=0)
    const-string v0, "io.flutter.embedding.android.EnableImpeller"

    invoke-virtual {p1, v0}, Landroid/os/Bundle;->containsKey(Ljava/lang/String;)Z

    move-result v1

    if-nez v1, :wl_impeller_skip

    const-string v0, "io.flutter.embedding.android.EnableImpeller"

    const/4 v1, 0x0

    invoke-virtual {p1, v0, v1}, Landroid/os/Bundle;->putBoolean(Ljava/lang/String;Z)V

    :wl_impeller_skip
''', after=False)

print("ALL 3 EDITS APPLIED")
