#!/usr/bin/env python3
"""Turn deps39.json into the #39 rebuild batch plan: 47 mechanical libs grouped by
DT_NEEDED level, each with a disposition; 10 OH-facing libs with shim class + effort."""
import json, sys
d = json.load(open(sys.argv[1]))['libs']

OH_FACING = ['libandroid.so','libhwui.so','liboh_account_state.so','liboh_adapter_bridge.so',
 'liboh_android_runtime.so','liboh_connectivity_state.so','liboh_hwui_shim.so',
 'liboh_ime_helper_capi.so','liboh_permission_queries.so','libwl_opengl_jni.so']

# disposition of the 47 mechanical (libc-only) libs. Buckets:
#   retire  = musl-compat shim, unneeded once the process is real Bionic
#   aosp    = generic AOSP lib -> take AOSP14/15 prebuilt or rebuild from AOSP source with NDK
#   rebuild = westlake-specific -> recompile against Bionic sysroot
#   art     = libart, must match the Android boot image it loads
RETIRE = {'libwestlake_bionic.so','liboh_tls_boundary.so','liboh_popen_boundary.so',
 'liboh_process_cpu_time.so','libwestlake_libcore_linux.so','libwestlake_securec.so'}
AOSP = {'libz.so','liblog.so','libbase.so','libicuuc.so','libicui18n.so','libexpat.so',
 'libpng.so','libjpeg.so','libwebp.so','libgif.so','libft2.so','libharfbuzz_ng.so',
 'libcutils.so','libutils.so','libnativehelper.so','libziparchive.so','libandroidfw.so',
 'libjavacrypto.so','libstdc++.so','libbinder_ndk.so','libjnigraphics.so','libminikin.so',
 'libstatssocket.so','libstatspull.so','libstats_jni.so','libsoundpool.so','libmedia_jni.so',
 'libicu_jni.so','libultrahdr.so','libwuffs.so','libwestlake_webp.so'}
ART = {'libart.so'}

def dispo(n):
    if n in ART: return 'art'
    if n in RETIRE: return 'retire'
    if n in AOSP: return 'aosp'
    return 'rebuild'

mech = [n for n in d if n not in OH_FACING]
print("### 47 mechanical (libc-only) libraries — batch by topo level over in-runtime DT_NEEDED\n")
print("Batch order = level asc (a level-N lib only needs levels < N already rebuilt).\n")
by = {}
for n in sorted(mech, key=lambda x:(d[x]['level'], d[x]['producer'], x)):
    by.setdefault(d[n]['level'], []).append(n)
tot=0
for lv in sorted(by):
    print(f"**Batch L{lv}** ({len(by[lv])} libs)")
    for n in by[lv]:
        i=d[n]; tot+=i['bytes']
        print(f"- `{n[:-3]}` · {i['producer'].split('/')[-1]} · {i['bytes']//1024}KB · dispo=**{dispo(n)}** · needs={[x[:-3] for x in i['in_runtime']]}")
    print()
print(f"mechanical count={len(mech)} bytes={tot} ({tot//(1024*1024)}MB)\n")
from collections import Counter
c=Counter(dispo(n) for n in mech)
print("disposition tally (mechanical):", dict(c), "\n")

print("### 10 OH-facing libraries — shim class + effort\n")
def cls(ext):
    # OH C-API (libace_napi/native_* / *_ndk) = thin; C++ innerkit (ipc/utils/want/...) = fat
    return 'C-API' if any(k in ext for k in ('native_','_ndk','napi','hilog','hitrace','EGL','GLES','vulkan','surface','sync_fence','begetutil')) else 'C++innerkit'
rows=[]
for n in OH_FACING:
    i=d[n]; es=i.get('external_symbols',{}) or {}
    syms=sum(v for v in es.values() if v)
    nlibs=len([e for e in i['external']])
    capi=sum(v for e,v in es.items() if v and cls(e)=='C-API')
    cxx=sum(v for e,v in es.items() if v and cls(e)=='C++innerkit')
    rows.append((n,i['level'],nlibs,syms,capi,cxx))
    print(f"- `{n[:-3]}` L{i['level']} · {nlibs} ext libs · {syms} syms (C-API {capi} / C++innerkit {cxx})")
print()
# effort heuristic: C-API syms are thin forwarders (~0.5 person-day/10), C++ innerkit need vtable/RTTI bridges (~1.5 pd/10)
print("### effort estimate (person-days), heuristic 10 C-API syms≈0.5pd, 10 C++innerkit syms≈1.5pd, +1pd base/lib\n")
te=0
for n,lv,nl,sy,capi,cxx in sorted(rows,key=lambda r:-(r[4]*0.05+r[5]*0.15)):
    e=1+capi*0.05+cxx*0.15; te+=e
    print(f"- `{n[:-3]}`: {e:.1f} pd")
print(f"\nOH-facing total ≈ {te:.0f} person-days ({te/5:.1f} person-weeks)")
