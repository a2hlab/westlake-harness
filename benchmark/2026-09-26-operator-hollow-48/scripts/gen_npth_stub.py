#!/usr/bin/env python3
"""Generate a hollow libnpth.so stub source from the app-facing ABI list.

Input: npth-app-abi-48.txt lines `# L<class>;  (N natives)` then `name|sig`.
Output: a C file that registers every app npth native as a typed-safe no-op and
whose JNI_OnLoad spawns NO worker/monitor thread (the autonomous mallocng corruptor
is gone). No hooks, no sigaction, no heap monitor: the whole lib does nothing.

Only 7 no-op fns are needed (one per return type): a JNI native ignores its args,
so on aarch64 a (JNIEnv*, jclass) fn registered for any signature is safe (extra
args sit in x2+ unread; caller-cleaned). RegisterNatives validates the sig STRING
against the Java method, not the C fn.
usage: gen_npth_stub.py <abi.txt> <out.c>
"""
import sys, re

def ret_of(sig):
    return sig.split(")", 1)[1]

NOOP = {  # return descriptor -> (noop C fn, jni return C type)
    "V": "noop_void", "Z": "noop_bool", "I": "noop_int", "J": "noop_long",
}
def noop_for(ret):
    if ret in NOOP: return NOOP[ret]
    if ret == "Ljava/lang/String;": return "noop_string"
    if ret == "[Ljava/lang/String;": return "noop_strarray"
    return "noop_object"  # any other object / array

def main():
    abi, out = sys.argv[1], sys.argv[2]
    classes = []   # (jni_class_name, [(name, sig), ...])
    cur = None
    for line in open(abi):
        line = line.rstrip("\n")
        m = re.match(r"#\s*L(\S+?);", line)
        if m:
            cur = (m.group(1), []); classes.append(cur); continue
        if "|" in line and cur is not None:
            nm, sig = line.split("|", 1); cur[1].append((nm, sig))
    # de-dup classes (abi file may repeat headers)
    merged = {}
    for cn, meths in classes:
        merged.setdefault(cn, [])
        for m in meths:
            if m not in merged[cn]: merged[cn].append(m)
    total = sum(len(v) for v in merged.values())
    w = open(out, "w")
    w.write('/* AUTO-GENERATED hollow libnpth.so stub (#48). Do not hand-edit. */\n')
    w.write('#include <jni.h>\n#include <stddef.h>\n\n')
    w.write('/* typed no-op natives (args ignored) */\n')
    w.write('static void      noop_void(JNIEnv*e,jclass c){(void)e;(void)c;}\n')
    w.write('static jboolean  noop_bool(JNIEnv*e,jclass c){(void)e;(void)c;return JNI_FALSE;}\n')
    w.write('static jint      noop_int(JNIEnv*e,jclass c){(void)e;(void)c;return 0;}\n')
    w.write('static jlong     noop_long(JNIEnv*e,jclass c){(void)e;(void)c;return 0;}\n')
    w.write('static jobject   noop_object(JNIEnv*e,jclass c){(void)e;(void)c;return NULL;}\n')
    w.write('static jstring   noop_string(JNIEnv*e,jclass c){(void)c;return (*e)->NewStringUTF(e,"");}\n')
    w.write('static jobjectArray noop_strarray(JNIEnv*e,jclass c){(void)c;jclass s=(*e)->FindClass(e,"java/lang/String");return s?(*e)->NewObjectArray(e,0,s,NULL):NULL;}\n\n')
    arrays = []
    for i, (cn, meths) in enumerate(merged.items()):
        arr = "g_m%d" % i
        arrays.append((cn, arr, len(meths)))
        w.write('/* %s : %d natives */\n' % (cn, len(meths)))
        w.write('static const JNINativeMethod %s[] = {\n' % arr)
        for nm, sig in meths:
            w.write('    {"%s","%s",(void*)%s},\n' % (nm, sig, noop_for(ret_of(sig))))
        w.write('};\n\n')
    w.write('JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM*vm,void*reserved){\n')
    w.write('    JNIEnv*env=NULL;(void)reserved;\n')
    w.write('    if((*vm)->GetEnv(vm,(void**)&env,JNI_VERSION_1_6)!=JNI_OK||!env) return JNI_VERSION_1_6;\n')
    for cn, arr, n in arrays:
        w.write('    { jclass c=(*env)->FindClass(env,"%s");\n' % cn)
        w.write('      if(c){ (*env)->RegisterNatives(env,c,%s,%d); (*env)->DeleteLocalRef(env,c); }\n' % (arr, n))
        w.write('      if((*env)->ExceptionCheck(env)) (*env)->ExceptionClear(env); }\n')
    w.write('    /* NO worker/monitor thread spawned, no hooks, no sigaction, no heap monitor. */\n')
    w.write('    return JNI_VERSION_1_6;\n}\n')
    w.close()
    print("generated %s: %d classes, %d natives" % (out, len(merged), total))

if __name__ == "__main__":
    main()
