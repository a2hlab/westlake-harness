// A separate TU uses Westlake's narrow AndroidRuntime registration shim.
#include <jni.h>
#include <stdio.h>
int register_com_google_android_gles_jni_GLImpl(JNIEnv*);
extern "C" int n2_register_GLImpl(JNIEnv* env) {
    int rc=register_com_google_android_gles_jni_GLImpl(env);
    fprintf(stderr,"[N2-GLImpl] full AOSP table rc=%d\n",rc);
    return rc;
}
