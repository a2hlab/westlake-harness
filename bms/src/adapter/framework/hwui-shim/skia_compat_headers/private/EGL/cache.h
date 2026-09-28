#pragma once
namespace android {
class egl_cache_t {
public:
    static egl_cache_t* get() { return nullptr; }
    void initialize(void*) {}
    void terminate() {}
    void setBlob(const void*, size_t, const void*, size_t) {}
    size_t getBlob(const void*, size_t, void*, size_t) { return 0; }
};
}
