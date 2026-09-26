/* AUTO-GENERATED hollow libnpth.so stub (#48). Do not hand-edit. */
#include <jni.h>
#include <stddef.h>

/* typed no-op natives (args ignored) */
static void      noop_void(JNIEnv*e,jclass c){(void)e;(void)c;}
static jboolean  noop_bool(JNIEnv*e,jclass c){(void)e;(void)c;return JNI_FALSE;}
static jint      noop_int(JNIEnv*e,jclass c){(void)e;(void)c;return 0;}
static jlong     noop_long(JNIEnv*e,jclass c){(void)e;(void)c;return 0;}
static jobject   noop_object(JNIEnv*e,jclass c){(void)e;(void)c;return NULL;}
static jstring   noop_string(JNIEnv*e,jclass c){(void)c;return (*e)->NewStringUTF(e,"");}
static jobjectArray noop_strarray(JNIEnv*e,jclass c){(void)c;jclass s=(*e)->FindClass(e,"java/lang/String");return s?(*e)->NewObjectArray(e,0,s,NULL):NULL;}

/* com/bytedance/apm/profiler/Profiler : 10 natives */
static const JNINativeMethod g_m0[] = {
    {"nAttachThread","(I)Z",(void*)noop_bool},
    {"nCheck","()Z",(void*)noop_bool},
    {"nClear","()V",(void*)noop_void},
    {"nDetachThread","(I)Z",(void*)noop_bool},
    {"nDump","(JJ)Ljava/lang/String;",(void*)noop_string},
    {"nGetStack","(I)Ljava/lang/String;",(void*)noop_string},
    {"nInit","()Z",(void*)noop_bool},
    {"nSetAlog","(J)V",(void*)noop_void},
    {"nStart","(I)Z",(void*)noop_bool},
    {"nStop","()Z",(void*)noop_bool},
};

/* com/bytedance/crash/jni/NativeBridge : 71 natives */
static const JNINativeMethod g_m1[] = {
    {"doRegister","(Ljava/lang/String;Ljava/lang/String;)V",(void*)noop_void},
    {"doSetDropDataState","(I)V",(void*)noop_void},
    {"nAnrDumpNativeInfo","(J)V",(void*)noop_void},
    {"nAnrDumpNativeInit","(Ljava/lang/String;)J",(void*)noop_long},
    {"nAnrDumpNativeRelease","(J)V",(void*)noop_void},
    {"nAnrDumpTrace","(Ljava/lang/String;)V",(void*)noop_void},
    {"nAnrEnterMonitorLooper","()V",(void*)noop_void},
    {"nAnrInitOnMainThread","()V",(void*)noop_void},
    {"nAnrNativeProfilerDump","(JLjava/lang/String;J)V",(void*)noop_void},
    {"nAnrNativeProfilerExit","(J)V",(void*)noop_void},
    {"nAnrNativeProfilerFormat","(Ljava/lang/String;[J)V",(void*)noop_void},
    {"nAnrNativeProfilerJvmStart","(J)I",(void*)noop_int},
    {"nAnrNativeProfilerRunTest","(Ljava/lang/String;)Ljava/lang/String;",(void*)noop_string},
    {"nAnrNativeProfilerStart","()J",(void*)noop_long},
    {"nAnrNativeProfilerStop","(J)V",(void*)noop_void},
    {"nCheckSigHandler","()V",(void*)noop_void},
    {"nCoredumpNativeInit","(Ljava/lang/String;)V",(void*)noop_void},
    {"nCrashDumpNativeInfo","(J)J",(void*)noop_long},
    {"nDumpLogcat","(Ljava/lang/String;I)V",(void*)noop_void},
    {"nDumpOsMemory","(Ljava/lang/String;)V",(void*)noop_void},
    {"nDumperLateInit","()V",(void*)noop_void},
    {"nEnablePrioriryParams","(ZZI)V",(void*)noop_void},
    {"nFlock","(Ljava/lang/String;)I",(void*)noop_int},
    {"nGetApexVersion","()I",(void*)noop_int},
    {"nGetBuildID","(Ljava/lang/String;)Ljava/lang/String;",(void*)noop_string},
    {"nGetFdCount","(Ljava/lang/String;)I",(void*)noop_int},
    {"nGetFdLeakReason","(Ljava/lang/String;)Ljava/lang/String;",(void*)noop_string},
    {"nGetJvmMonitorState","()I",(void*)noop_int},
    {"nGetNativePthreadKeyLeakLibrary","(Ljava/lang/String;)Ljava/lang/String;",(void*)noop_string},
    {"nGetOOMReason","(Ljava/lang/String;)[Ljava/lang/String;",(void*)noop_strarray},
    {"nGetStackTrace","(Z)Ljava/lang/String;",(void*)noop_string},
    {"nGetThreadCount","(Ljava/lang/String;)I",(void*)noop_int},
    {"nGetThreadCpuTimeMills","(I)J",(void*)noop_long},
    {"nGetThreadLeakLibrary","(Ljava/lang/String;)Ljava/lang/String;",(void*)noop_string},
    {"nGetThreadLeakName","(Ljava/lang/String;)Ljava/lang/String;",(void*)noop_string},
    {"nGetVmRss","(Ljava/lang/String;)J",(void*)noop_long},
    {"nGetVmSize","(Ljava/lang/String;I)J",(void*)noop_long},
    {"nGetVmaCount","(Ljava/lang/String;)I",(void*)noop_int},
    {"nIncreaseFdLimit","()Z",(void*)noop_bool},
    {"nIs64BitRuntime","()Z",(void*)noop_bool},
    {"nLoadNativeCrashAbortReason","(Ljava/lang/String;)Ljava/lang/String;",(void*)noop_string},
    {"nLoadNativeCrashBacktrace","(Ljava/lang/String;)Ljava/lang/String;",(void*)noop_string},
    {"nLoadNativeCrashSummary","(Ljava/lang/String;)Lcom/bytedance/crash/crash/NativeCrashSummary;",(void*)noop_object},
    {"nNativePthreadKeyCount","(Ljava/lang/String;)I",(void*)noop_int},
    {"nNotifyUploadDone","()V",(void*)noop_void},
    {"nParseSmaps","(Ljava/lang/String;)V",(void*)noop_void},
    {"nPriorityMonitorInit","(Ljava/lang/String;)V",(void*)noop_void},
    {"nRecoverSignalHandler","()V",(void*)noop_void},
    {"nResetNativeInfoLatches","()V",(void*)noop_void},
    {"nSet64Bit","(Z)V",(void*)noop_void},
    {"nSetAlogFlushAddr","(J)V",(void*)noop_void},
    {"nSetAnrDumpAsync","(Z)V",(void*)noop_void},
    {"nSetAnrResendSigquit","(Z)V",(void*)noop_void},
    {"nSetAppVersion","(Ljava/lang/String;)V",(void*)noop_void},
    {"nSetDumpTraceTryCatch","(Z)V",(void*)noop_void},
    {"nSignalToProcess","(II)Z",(void*)noop_bool},
    {"nStartDumperThread","()V",(void*)noop_void},
    {"nStartNativeCrashMonitor","(ILjava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;JJLjava/lang/String;)I",(void*)noop_int},
    {"nStartProfilerJavaLockMonitor","()V",(void*)noop_void},
    {"nStringDumperCreate","(Ljava/lang/String;I)J",(void*)noop_long},
    {"nStringDumperDumpByteArray","(J[BI)V",(void*)noop_void},
    {"nStringDumperDumpCharArray","(J[CI)V",(void*)noop_void},
    {"nStringDumperDumpString","(JLjava/lang/String;I)V",(void*)noop_void},
    {"nStringDumperFlushBuffer","(J)V",(void*)noop_void},
    {"nStringDumperRelease","(J)V",(void*)noop_void},
    {"nUnFlock","(I)V",(void*)noop_void},
    {"nativeDumpHprof","(ILjava/lang/String;)I",(void*)noop_int},
    {"nativeDumpTags","(Ljava/lang/String;)V",(void*)noop_void},
    {"nativeGetFdListForAPM","()[Ljava/lang/String;",(void*)noop_strarray},
    {"nativeGetTags","()[Ljava/lang/String;",(void*)noop_strarray},
    {"unRegister","(Ljava/lang/String;)V",(void*)noop_void},
};

JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM*vm,void*reserved){
    JNIEnv*env=NULL;(void)reserved;
    if((*vm)->GetEnv(vm,(void**)&env,JNI_VERSION_1_6)!=JNI_OK||!env) return JNI_VERSION_1_6;
    { jclass c=(*env)->FindClass(env,"com/bytedance/apm/profiler/Profiler");
      if(c){ (*env)->RegisterNatives(env,c,g_m0,10); (*env)->DeleteLocalRef(env,c); }
      if((*env)->ExceptionCheck(env)) (*env)->ExceptionClear(env); }
    { jclass c=(*env)->FindClass(env,"com/bytedance/crash/jni/NativeBridge");
      if(c){ (*env)->RegisterNatives(env,c,g_m1,71); (*env)->DeleteLocalRef(env,c); }
      if((*env)->ExceptionCheck(env)) (*env)->ExceptionClear(env); }
    /* NO worker/monitor thread spawned, no hooks, no sigaction, no heap monitor. */
    return JNI_VERSION_1_6;
}
