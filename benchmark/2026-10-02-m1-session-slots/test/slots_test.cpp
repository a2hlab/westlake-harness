// Host test of the M1 per-session slot helpers. The code under test is the first anonymous namespace of
// bms/src/adapter/framework/window/jni/oh_window_manager_client.cpp, extracted verbatim by run_slots_test.sh
// (no hand copy). Two "bridge copies" share one process environment, exactly like the two loaded instances.
#include <atomic>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#define OH_BR_IPC_SCOPE(...) ((void)0)
#include "extracted_namespace.inc"

static int fails = 0;
#define CHECK(c) do { if (!(c)) { std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); ++fails; } } while (0)

// The pre-fix reader (V1 single slot), as in bridge 84695d62, to test a mixed old/new pair.
static void* oldRead(int32_t sid) {
    const char* s = std::getenv("WESTLAKE_WINDOW_SESSION_ID_V1");
    if (!s || std::atoi(s) != sid) return nullptr;
    return reinterpret_cast<void*>(std::strtoull(std::getenv("WESTLAKE_NATIVE_WINDOW_PTR_V1"), nullptr, 0));
}

int main() {
    void* w698 = reinterpret_cast<void*>(0x7f35252510ULL);
    void* w699 = reinterpret_cast<void*>(0x7f3458a550ULL);
    // single session (98 of 144 real runs): the reader returns exactly what V1 returns
    publishProcessWindowTarget(698, w698);
    CHECK(readProcessWindowTarget(698) == w698);
    CHECK(readProcessWindowTarget(698) == oldRead(698));
    CHECK(readProcessWindowTarget(700) == nullptr);
    // the white wikipedia order: the top Activity's session (698) published first, launcher's (699) last
    publishProcessWindowTarget(699, w699);
    CHECK(oldRead(698) == nullptr);                    // pre-fix: the first session is lost (empty Surface)
    CHECK(readProcessWindowTarget(698) == w698);       // fix: both resolve
    CHECK(readProcessWindowTarget(699) == w699);
    CHECK(readProcessWindowSession() == 699);          // V1 still written: last session unchanged for old users
    // destroy clears only that session's slot
    unpublishProcessWindowTarget(698);
    CHECK(readProcessWindowTarget(698) == nullptr);
    CHECK(readProcessWindowTarget(699) == w699);
    // mixed: an old publisher writes only V1 -> the new reader falls back to V1 = today's behavior
    unsetenv("WESTLAKE_NATIVE_WINDOW_PTR_V2_699");
    CHECK(readProcessWindowTarget(699) == w699);       // via V1
    setenv("WESTLAKE_WINDOW_SESSION_ID_V1", "701", 1);
    setenv("WESTLAKE_NATIVE_WINDOW_PTR_V1", "0x1234", 1);
    CHECK(readProcessWindowTarget(699) == nullptr);    // V1 now names 701 and no V2 slot: same as pre-fix
    CHECK(readProcessWindowTarget(701) == reinterpret_cast<void*>(0x1234));
    // malformed slot -> treated as absent, falls back to V1
    setenv("WESTLAKE_NATIVE_WINDOW_PTR_V2_701", "junk", 1);
    CHECK(readProcessWindowTarget(701) == reinterpret_cast<void*>(0x1234));
    std::printf("%s (%d failure(s))\n", fails ? "FAIL" : "PASS", fails);
    return fails ? 1 : 0;
}
