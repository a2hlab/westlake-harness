#!/usr/bin/env python3
"""Replay the observed EGL -> GL initialization dependency using the real caller/cache."""
import ast
import subprocess
import tempfile
from pathlib import Path
P=Path(__file__).resolve().parent; R=P.parents[2]
base=R/'benchmark/2026-09-30-n4-native'
module=ast.parse((base/'test_egl_cache.py').read_text())
preamble=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='preamble' for t in n.targets))
preamble=preamble.replace('#include <cstdio>','#include <cstdio>\n#include <cstring>\nstatic bool gl_registered=false;')
preamble=preamble.replace('jclass FindClass(const char*) { return lookup(); }','''jclass FindClass(const char* name) {
 if (std::strcmp(name,"com/google/android/gles_jni/EGLContextImpl")==0 && !gl_registered) {exception=true;return nullptr;}
 return lookup();
}''')
preamble=preamble.replace('bool ExceptionCheck()', 'void ExceptionDescribe() {}\n void ExceptionClear() {exception=false;}\n bool ExceptionCheck()')
source=(base/'src/oh_egl_impl.cpp').read_text();cache=source[source.index('static bool cacheEglFields'):source.index('static const jint gNull_attrib_base')]
helpers='''
int n2_register_GLImpl(JNIEnv*) {gl_registered=true;return 0;}
int register_com_google_android_gles_jni_EGLImpl(JNIEnv* e) {nativeClassInit(e,nullptr);return e->ExceptionCheck()?-1:0;}
'''
functions=[]
for name,path in [('old',base/'src/AndroidRuntime.cpp'),('fixed',P/'AndroidRuntime.cpp')]:
 s=path.read_text();start=s.index('        register_android_graphics_compat_shim(env);')+len('        register_android_graphics_compat_shim(env);');end=s.index('        if (register_n2_Camera(env)',start)
 functions.append('int '+name+'(JNIEnv* env) {\n'+s[start:end]+'return 0;}\n')
main='''int main() {
 JNIEnv bad;bad.frames=1;assert(old(&bad)==-1 && bad.exception && !gl_registered && !gConfig_class);
 reset();gl_registered=false;JNIEnv good;good.frames=1;assert(fixed(&good)==0 && !good.exception && gl_registered && gConfig_class);
 puts("PASS original startup fails / reordered startup caches fields: real source, mocked observed cross-class initialization dependency");
}'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'test.cpp').write_text(preamble+cache+helpers+''.join(functions)+main)
 subprocess.run(['c++','-std=c++17',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
