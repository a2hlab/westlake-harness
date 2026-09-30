#!/usr/bin/env python3
"""Copy complete pinned donor functions; add only explicit JNI entry points."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
source=R/'benchmark/2026-09-30-n3-native/offline-followup/upstream/framework/activity/jni/activity_task_manager_adapter.cpp'
s=source.read_text()
functions=['std::string jstr(', 'static void wl_log_and_clear_webview_exception(', 'static bool wl_set_webview_supported_cache(', 'static bool wl_prime_webview_update_service_impl(', 'bool wl_prime_webview_update_service(', 'bool wl_publish_webview_update_service_after_bind(']
# All selected functions end at a column-zero brace; no source rewriting.
parts=[];origins=[]
for name in functions:
 start=s.index(name);end=s.index('\n}',start)+2;body=s[start:end]
 parts.append(body);origins.append({'function':name,'first_line':s[:start].count('\n')+1,'last_line':s[:end].count('\n')+1,'sha256':hashlib.sha256(body.encode()).hexdigest()})
header='''// N3b: unchanged Westlake 532633da provider publication bodies.
#include <jni.h>
#include <cstdio>
#include <string>
#include <mutex>
#include <unistd.h>
namespace {
'''
cpp=header+'\n\n'.join(parts[:4])+'\n} // namespace\n\n'+'\n\n'.join(parts[4:])+'''

// Explicit Java cooperation point. Do not run during native registration,
// on log output, or on a background watcher. The owning Java helper calls
// prime before bind and publish only after Application.onCreate returned.
// Serialize whole transactions, including the donor's cache readbacks.
namespace { std::recursive_mutex publication_mutex; }
extern "C" JNIEXPORT jboolean JNICALL
Java_adapter_core_WestlakeWebViewInstall_nativePrime(JNIEnv* env, jclass) {
    if (env->ExceptionCheck()) return JNI_FALSE;
    std::lock_guard<std::recursive_mutex> lock(publication_mutex);
    return wl_prime_webview_update_service(env) ? JNI_TRUE : JNI_FALSE;
}
extern "C" JNIEXPORT jboolean JNICALL
Java_adapter_core_WestlakeWebViewInstall_nativePublishAfterBind(JNIEnv* env, jclass) {
    if (env->ExceptionCheck()) return JNI_FALSE;
    std::lock_guard<std::recursive_mutex> lock(publication_mutex);
    return wl_publish_webview_update_service_after_bind(env) ? JNI_TRUE : JNI_FALSE;
}
'''
(P/'src/webview_publication.cpp').write_text(cpp)
(P/'source-origins.json').write_text(json.dumps({'origin':str(source.relative_to(R)),'commit':'532633da63b770d3d459c74683db6d7a1f82a022','sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'functions':origins,'candidate_sha256':hashlib.sha256(cpp.encode()).hexdigest(),'adaptation':'standalone TU includes and serialized explicit JNI wrappers; all six donor bodies unchanged'},indent=2)+'\n')
print('Copied',len(parts),'whole pinned functions')
