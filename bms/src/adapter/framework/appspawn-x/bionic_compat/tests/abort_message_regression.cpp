#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

extern "C" void android_set_abort_message(const char* message);
extern "C" const char* android_get_abort_message(void);

struct AbortMessage {
    size_t size;
    char message[0];
};

struct MagicAbortMessage {
    uint64_t magic1;
    uint64_t magic2;
    AbortMessage abort_message;
};

static int CheckMapping(const char* expected)
{
    const char* actual = android_get_abort_message();
    if (actual == nullptr || strcmp(actual, expected) != 0) return 1;
    const auto* abort_message = reinterpret_cast<const AbortMessage*>(
        reinterpret_cast<const uint8_t*>(actual) - offsetof(AbortMessage, message));
    const auto* mapping = reinterpret_cast<const MagicAbortMessage*>(
        reinterpret_cast<const uint8_t*>(abort_message) -
        offsetof(MagicAbortMessage, abort_message));
    if (mapping->magic1 != UINT64_C(0xb18e40886ac388f0) ||
        mapping->magic2 != UINT64_C(0xc6dfba755a1de0b5)) return 2;
    if (abort_message->size != sizeof(MagicAbortMessage) + strlen(expected) + 1) return 3;
    return 0;
}

int main(int argc, char** argv)
{
    if (argc != 2) return 10;
    if (strcmp(argv[1], "null") == 0) {
        android_set_abort_message(nullptr);
        if (CheckMapping("(null)") != 0) return 11;
    } else {
        android_set_abort_message("first abort message");
        android_set_abort_message("second must not replace first");
        if (CheckMapping("first abort message") != 0) return 12;
    }
    printf("PASS abort_message_aosp_layout mode=%s\n", argv[1]);
    return 0;
}

