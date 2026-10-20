// Included ONLY in oh_audiotrack_shim.cpp after ATShim/getShim are defined.
// No standalone DSO, guessed object offsets, or replacement registration table.
// Caller has the same owner lifetime precondition as existing owner methods.
static jint nEffectiveBufferSizeFailure(JNIEnv* env, const char* message) {
    if (!env->ExceptionCheck()) {
        jclass exception = env->FindClass("java/lang/IllegalStateException");
        if (exception) {
            env->ThrowNew(exception, message);
            env->DeleteLocalRef(exception);
        }
    }
    return -1;
}

static jint nGetEffectiveBufferSizeFrames(JNIEnv* env, jobject thiz) {
    if (env->ExceptionCheck()) return -1;
    ATShim* s = getShim(env, thiz);
    if (env->ExceptionCheck()) return -1;
    if (!s) return nEffectiveBufferSizeFailure(env, "AudioTrack is not initialized");
    // This mutex protects fields, NOT getShim vs concurrent deletion; it does
    // not create a new lifetime guarantee absent from the original owner.
    std::lock_guard<std::mutex> lock(s->mu);
    if (s->stopping || s->bytesPerFrame <= 0 || s->cap > s->ring.size())
        return nEffectiveBufferSizeFailure(env, "Invalid AudioTrack ring state");
    const size_t frames = s->cap / static_cast<size_t>(s->bytesPerFrame);
    if (frames == 0 || frames > static_cast<size_t>(INT32_MAX))
        return nEffectiveBufferSizeFailure(env, "AudioTrack buffer frame count out of range");
    return static_cast<jint>(frames);
}
