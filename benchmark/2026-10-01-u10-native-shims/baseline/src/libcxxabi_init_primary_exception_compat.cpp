/*
 * LLVM 19 libc++ uses __cxa_init_primary_exception() from make_exception_ptr,
 * but the D600 image provides the LLVM 15 libc++abi predating that extension.
 * The exception header layout itself is unchanged on LP64 Itanium-ABI targets.
 * Implement only the missing initializer and keep allocation, ref-counting,
 * unwinding, and destruction owned by the device libc++abi.
 *
 * Layout and initialization semantics follow LLVM libc++abi cxa_exception.h
 * and cxa_exception.cpp (Apache-2.0 WITH LLVM-exception).
 */

#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <unwind.h>

namespace std {
class type_info;
using unexpected_handler = void (*)();
using terminate_handler = void (*)();
unexpected_handler get_unexpected() noexcept;
terminate_handler get_terminate() noexcept;
[[noreturn]] void terminate() noexcept;
}  // namespace std

namespace {

struct CxaExceptionHeader {
    void* reserve;
    size_t referenceCount;
    std::type_info* exceptionType;
    void (*exceptionDestructor)(void*);
    std::unexpected_handler unexpectedHandler;
    std::terminate_handler terminateHandler;
    CxaExceptionHeader* nextException;
    int handlerCount;
    int handlerSwitchValue;
    const unsigned char* actionRecord;
    const unsigned char* languageSpecificData;
    void* catchTemp;
    void* adjustedPtr;
    _Unwind_Exception unwindHeader;
};

static_assert(sizeof(void*) == 8, "compatibility ABI is AArch64/LP64 only");
static_assert(offsetof(CxaExceptionHeader, unwindHeader) +
                      sizeof(_Unwind_Exception) ==
                  sizeof(CxaExceptionHeader),
              "libc++abi exception header tail layout drift");

constexpr uint64_t kClangExceptionClass = 0x434c4e47432b2b00ULL;

extern "C" void __cxa_decrement_exception_refcount(void*) noexcept;

void CleanupPrimaryException(_Unwind_Reason_Code reason,
                             _Unwind_Exception* unwindException) {
    if (reason != _URC_FOREIGN_EXCEPTION_CAUGHT) {
        std::terminate();
    }
    __cxa_decrement_exception_refcount(unwindException + 1);
}

}  // namespace

extern "C" __attribute__((visibility("default"))) void*
__cxa_init_primary_exception(void* object,
                             std::type_info* typeInfo,
                             void (*destructor)(void*)) noexcept {
    auto* header = reinterpret_cast<CxaExceptionHeader*>(object) - 1;
    header->referenceCount = 0;
    header->unexpectedHandler = std::get_unexpected();
    header->terminateHandler = std::get_terminate();
    header->exceptionType = typeInfo;
    header->exceptionDestructor = destructor;
    memcpy(&header->unwindHeader.exception_class,
           &kClangExceptionClass,
           sizeof(kClangExceptionClass));
    header->unwindHeader.exception_cleanup = CleanupPrimaryException;
    return header;
}
