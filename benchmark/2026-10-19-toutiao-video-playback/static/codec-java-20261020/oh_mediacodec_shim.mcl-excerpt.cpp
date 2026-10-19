
// ================= MediaCodecList (report an MP3 decoder) =================
static jint mclCount(JNIEnv*, jclass) { return 1; }
static void mclInit(JNIEnv*, jclass) {}
static jstring mclGetName(JNIEnv* env, jclass, jint) { return env->NewStringUTF("OH.audio.mp3.decoder"); }
static jstring mclGetCanonical(JNIEnv* env, jclass, jint) { return env->NewStringUTF("OH.audio.mp3.decoder"); }
static jint mclGetAttributes(JNIEnv*, jclass, jint) { return 0; } // 0 = decoder (not encoder)
// Only our own component matches; anything else must miss, or callers resolve foreign codec names
// to index 0 and then query capabilities we never provide.
static jint mclFindByName(JNIEnv* env, jclass, jstring name) {
    if (name == nullptr) return -1;
    const char* n = env->GetStringUTFChars(name, nullptr);
    if (n == nullptr) return -1;
    int r = (strcmp(n, "OH.audio.mp3.decoder") == 0) ? 0 : -1;
    env->ReleaseStringUTFChars(name, n);
    return r;
}
// §497: cached at registration time. Looking java/lang/String up lazily inside the native was the
// actual crash: ART's NewObjectArray JniAbortF()s -- ABORTS the process, it does not throw -- if the
// element class is null, and FindClass can fail here because these natives run on the app's
// ExoPlayer:Playback thread, not the thread that registered them. Faultlog:
//   #07 art::JNI<false>::NewObjectArray(...)+500  <- JniAbortF -> Abort, Tid Name:ExoPlayer:Playb
static jclass g_strClass = nullptr;   // global ref

static jobjectArray mclSupportedTypes(JNIEnv* env, jclass, jint) {
    // Never enter ART's JNI with an exception pending: most calls abort rather than throw.
    if (env->ExceptionCheck()) env->ExceptionClear();
    jclass strC = g_strClass;
    if (strC == nullptr) {                       // registration-time caching did not happen
        strC = env->FindClass("java/lang/String");
        if (env->ExceptionCheck()) env->ExceptionClear();
    }
    if (strC == nullptr) { MCERR("no java/lang/String — returning empty type list"); return nullptr; }
    // ★AOSP's own pattern (frameworks/base/media/jni/android_media_MediaCodecList.cpp): allocate with
    // a NULL initializer, then SetObjectArrayElement. Passing the jstring as the initializer is what
    // aborted: in this libart, NewObjectArray+500 is the JniAbortF branch for an initializer ART
    // considers incompatible with the component class — and a JNI abort KILLS THE PROCESS rather than
    // throwing. Caching the class (my first attempt) did not touch that branch at all.
    jobjectArray arr = env->NewObjectArray(1, strC, nullptr);
    if (arr == nullptr) return nullptr;          // exception already pending; let it propagate
    jstring mime = env->NewStringUTF("audio/mpeg");
    if (mime == nullptr) return nullptr;
    env->SetObjectArrayElement(arr, 0, mime);
    env->DeleteLocalRef(mime);
    return arr;
}
// getCodecCapabilities(index, type) -> a minimal CodecCapabilities for the mime.
// ExoPlayer's MediaCodecUtil only queries isFeatureRequired/isFeatureSupported.
static jobject mclGetCaps(JNIEnv* env, jclass, jint, jstring type) {
    jclass ccC = env->FindClass("android/media/MediaCodecInfo$CodecCapabilities");
    if (!ccC) { if(env->ExceptionCheck())env->ExceptionClear(); return nullptr; }
    const char* t = type ? env->GetStringUTFChars(type, nullptr) : nullptr;
    jstring mime = env->NewStringUTF((t && *t) ? t : "audio/mpeg");
    if (type && t) env->ReleaseStringUTFChars(type, t);
    if (env->ExceptionCheck()) env->ExceptionClear();
    MCLOG("FindClass(MediaCodecList) -> %p", (void*)mcl);
    if (mcl) {
        JNINativeMethod ml[] = {
            {"native_init","()V",(void*)mclInit},
            {"native_getCodecCount","()I",(void*)mclCount},
            {"getCodecName","(I)Ljava/lang/String;",(void*)mclGetName},
            {"getCanonicalName","(I)Ljava/lang/String;",(void*)mclGetCanonical},
            {"getAttributes","(I)I",(void*)mclGetAttributes},
            {"findCodecByName","(Ljava/lang/String;)I",(void*)mclFindByName},
            {"getSupportedTypes","(I)[Ljava/lang/String;",(void*)mclSupportedTypes},
            {"getCodecCapabilities","(ILjava/lang/String;)Landroid/media/MediaCodecInfo$CodecCapabilities;",(void*)mclGetCaps},
            {"native_getGlobalSettings","()Ljava/util/Map;",(void*)mclGlobalSettings},
        };
        if (g_strClass == nullptr) {
            jclass sc = env->FindClass("java/lang/String");
            if (env->ExceptionCheck()) env->ExceptionClear();
            if (sc != nullptr) { g_strClass = (jclass)env->NewGlobalRef(sc); }
            MCLOG("cached java/lang/String -> %p", (void*)g_strClass);
        }
        int rc2 = env->RegisterNatives(mcl, ml, sizeof(ml)/sizeof(ml[0]));
        if (env->ExceptionCheck()) env->ExceptionClear();
        MCLOG("register MediaCodecList rc=%d (%d methods)", rc2, (int)(sizeof(ml)/sizeof(ml[0])));
        // A nonzero rc means a signature did not match; report which ones exist so the mismatch is
        // identifiable rather than silent.
        if (rc2 != 0) {
            for (size_t i = 0; i < sizeof(ml)/sizeof(ml[0]); i++) {
                int one = env->RegisterNatives(mcl, &ml[i], 1);
                if (env->ExceptionCheck()) env->ExceptionClear();
                MCLOG("  %s%s -> rc=%d", ml[i].name, ml[i].signature, one);
            }
