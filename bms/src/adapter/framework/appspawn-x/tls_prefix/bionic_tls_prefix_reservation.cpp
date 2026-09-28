// Copyright (c) 2026 WestLake contributors.
//
// Reserve the positive AArch64 Bionic TCB-slot aperture in appspawn-x's main
// ELF PT_TLS segment.  This translation-layer object owns addresses only; it
// does not assign Android semantics to a slot and it never reads or writes TP.
//
// OpenHarmony's AArch64 musl uses TLS_ABOVE_TP with GAP_ABOVE_TP == 16.  When
// the main executable has no PT_TLS segment, musl starts initial DSO TLS at
// offset zero.  That lets a host TLS object alias Bionic's fixed TP-relative
// slots.  Linking this object directly into the main executable makes the
// main PT_TLS segment cover [TP+0x10, TP+0x40), so later DSO TLS starts after
// the positive Bionic slot aperture.
//
// Slot ownership is deliberately narrower than slot semantics:
//   * slots 2..7 are address-reserved by this object;
//   * the current CardWords admission evidence recognizes only slot 5
//     (TP+0x28, stack guard) as a closed guest access class;
//   * slots 2/3/4/6/7 remain unusable until their semantics are implemented
//     and certified;
//   * slots -1..1 are outside this object.  A generation that needs any of
//     them must fail closed unless a separately reviewed mechanism owns them.
//
// The final linked ELF, not this source file, is authoritative.  A post-link
// verifier must reject the artifact unless this TLS symbol begins at the main
// module's TP+0x10 and the main PT_TLS segment ends at or beyond TP+0x40.

#include <stddef.h>
#include <stdint.h>

#if !defined(__aarch64__)
#error "The Bionic positive-slot TLS reservation is AArch64-only"
#endif

namespace {

constexpr size_t kPointerSize = sizeof(uintptr_t);
constexpr size_t kFirstReservedSlot = 2;
constexpr size_t kLastReservedSlot = 7;
constexpr size_t kRequiredStart = kFirstReservedSlot * kPointerSize;
constexpr size_t kRequiredEnd = (kLastReservedSlot + 1) * kPointerSize;
constexpr size_t kReservationSize = kRequiredEnd - kRequiredStart;
constexpr size_t kReservationAlignment = 16;

static_assert(kPointerSize == 8, "AArch64 Bionic slots are eight bytes");
static_assert(kRequiredStart == 0x10, "slots 0..1 are not owned here");
static_assert(kRequiredEnd == 0x40, "positive Bionic slot aperture changed");
static_assert(kReservationSize == 48, "slots 2..7 must occupy 48 bytes");
static_assert(kReservationAlignment == kRequiredStart,
              "musl GAP_ABOVE_TP phase must remain explicit");

} // namespace

extern "C" {

extern thread_local uint8_t
    westlake_bionic_tls_slots_2_7_reservation[kReservationSize];

} // extern "C"

// OH's standalone clang driver defaults C/C++ thread_local variables to
// emutls, which creates __emutls_v.* process objects rather than an ELF PT_TLS
// segment. Emit the reservation explicitly as a file-backed, zero-filled
// .tdata image. After MAIN admission the adapter-owned publisher changes the
// child-private image once; exact OH Musl then copies those bytes into every
// later thread before its start routine. SHF_GNU_RETAIN (R) prevents a future
// --gc-sections build from discarding the layout contract. No C++ TLS access,
// constructor, Musl-global write, or runtime helper is emitted here.
__asm__(".pushsection .tdata.westlake_bionic_tls_prefix,\"awTR\",@progbits\n"
        ".p2align 4\n"
        ".globl westlake_bionic_tls_slots_2_7_reservation\n"
        ".hidden westlake_bionic_tls_slots_2_7_reservation\n"
        ".type westlake_bionic_tls_slots_2_7_reservation,@object\n"
        "westlake_bionic_tls_slots_2_7_reservation:\n"
        ".zero 48\n"
        ".size westlake_bionic_tls_slots_2_7_reservation, "
        ".-westlake_bionic_tls_slots_2_7_reservation\n"
        ".popsection\n");
