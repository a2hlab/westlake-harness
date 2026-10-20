// Compile the actual getter against an explicit host JNI/owner seam.
// This does not emulate ART, the deployed struct layout, or owner lifetime.
#include <cassert>
#include <cstdint>
#include <mutex>
#include <string>
#include <iostream>
using jint = int32_t;
using jobject = void*;
using jclass = void*;
struct JNIEnv {
    bool pending = false;
    bool find_fails = false;
    int thrown = 0;
    std::string message;
    bool ExceptionCheck() { return pending; }
    jclass FindClass(const char* name) {
        assert(std::string(name)=="java/lang/IllegalStateException");
        if (find_fails) { pending=true; message="class lookup failed"; return nullptr; }
        return this;
    }
    int ThrowNew(jclass, const char* msg) { pending=true; ++thrown; message=msg; return 0; }
    void DeleteLocalRef(jclass) {}
};
// size-only seam enables overflow tests without allocating gigabytes.
struct RingSize { size_t value=16384; size_t size() const { return value; } };
struct ATShim {
    std::mutex mu;
    size_t cap=16384, count=0;
    int bytesPerFrame=4;
    bool stopping=false;
    RingSize ring;
};
static ATShim* owner=nullptr;
static int lookups=0;
static bool lookup_throws=false;
static ATShim* getShim(JNIEnv* env, jobject) {
    ++lookups;
    if (lookup_throws) { env->pending=true; env->message="lookup exception"; }
    return owner;
}
#include "audiotrack_effective_size.inc"
int main() {
    ATShim track; owner=&track; JNIEnv env;
    assert(nGetEffectiveBufferSizeFrames(&env,nullptr)==4096);
    track.count=16380;
    assert(nGetEffectiveBufferSizeFrames(&env,nullptr)==4096);
    assert(track.cap==16384 && track.count==16380 && track.bytesPerFrame==4);
    // Incomplete trailing bytes are not a whole frame, never rounded upward.
    track.cap=16383;
    assert(nGetEffectiveBufferSizeFrames(&env,nullptr)==4095);
    auto bad=[&]() { env=JNIEnv{}; assert(nGetEffectiveBufferSizeFrames(&env,nullptr)==-1); assert(env.pending && env.thrown==1); };
    owner=nullptr; bad(); owner=&track;
    track.stopping=true; bad(); track.stopping=false;
    track.bytesPerFrame=0; bad(); track.bytesPerFrame=-4; bad(); track.bytesPerFrame=4;
    track.cap=3; bad();
    track.cap=16385; bad();
    track.cap=(static_cast<size_t>(INT32_MAX)+1)*4; track.ring.value=track.cap; bad();
    track.cap=static_cast<size_t>(INT32_MAX)*4; track.ring.value=track.cap; env=JNIEnv{};
    assert(nGetEffectiveBufferSizeFrames(&env,nullptr)==INT32_MAX && !env.pending);
    env.pending=true; env.message="original"; const int old=lookups;
    assert(nGetEffectiveBufferSizeFrames(&env,nullptr)==-1 && lookups==old && env.message=="original" && env.thrown==0);
    env=JNIEnv{}; lookup_throws=true;
    assert(nGetEffectiveBufferSizeFrames(&env,nullptr)==-1 && env.message=="lookup exception" && env.thrown==0); lookup_throws=false;
    owner=nullptr; env=JNIEnv{}; env.find_fails=true;
    assert(nGetEffectiveBufferSizeFrames(&env,nullptr)==-1 && env.pending && env.thrown==0);
    std::cout << "HOST_GETTER_14_CASES_PASS (JNI/owner seam; not ART or lifetime proof)\n";
}
