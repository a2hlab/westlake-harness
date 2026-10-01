/*
 * AOSP 16 DSOs are built with sized deallocation and may reference the
 * Itanium C++ ABI symbol _ZdlPvm.  The D600 libc++ exports that symbol, but
 * it is outside the sealed child loader's provider scope.  Keep ownership of
 * allocation in the device libc++ by forwarding only the ignored size to the
 * ordinary global delete operator.
 */

#include <cstddef>
#include <new>

__attribute__((visibility("default"))) void operator delete(
    void* pointer, std::size_t) noexcept {
    ::operator delete(pointer);
}
