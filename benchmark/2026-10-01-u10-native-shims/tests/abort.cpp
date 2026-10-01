#include <cassert>
#include <cstdint>
#include <cstring>
#include <pthread.h>

extern "C" void android_set_abort_message(const char*);
extern "C" const char* android_get_abort_message(void);

static void* later(void*) {
    android_set_abort_message("later must not replace first");
    return nullptr;
}

int main(int count, char**) {
    assert(android_get_abort_message() == nullptr);
    const char* first = count > 1 ? nullptr : "first message";
    android_set_abort_message(first);
    const char* stored = android_get_abort_message();
    assert(stored != nullptr);
    assert(std::strcmp(stored, first == nullptr ? "(null)" : first) == 0);
    uint64_t magic[2];
    std::memcpy(magic, stored - sizeof(size_t) - sizeof(magic), sizeof(magic));
    assert(magic[0] == UINT64_C(0xb18e40886ac388f0));
    assert(magic[1] == UINT64_C(0xc6dfba755a1de0b5));
    pthread_t workers[4];
    for (size_t index = 0; index < 4; ++index) {
        assert(pthread_create(&workers[index], nullptr, later, nullptr) == 0);
    }
    for (size_t index = 0; index < 4; ++index) {
        assert(pthread_join(workers[index], nullptr) == 0);
    }
    assert(android_get_abort_message() == stored);
    assert(std::strcmp(stored, first == nullptr ? "(null)" : first) == 0);
    return 0;
}
