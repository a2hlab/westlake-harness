// Main-ELF reservation accessor for the appspawn-x native-compat prepare path.
// The linker, not a literal TP+0x28, resolves the current thread's reservation
// base through TLSLE relocations against the main executable's PT_TLS symbol.

.text
.p2align 2
.globl WestLakeNativeCompatReservationBase
.hidden WestLakeNativeCompatReservationBase
.type WestLakeNativeCompatReservationBase,%function
WestLakeNativeCompatReservationBase:
    mrs x0, tpidr_el0
    add x0, x0, #:tprel_hi12:westlake_bionic_tls_slots_2_7_reservation
    add x0, x0, #:tprel_lo12_nc:westlake_bionic_tls_slots_2_7_reservation
    ret
.size WestLakeNativeCompatReservationBase, .-WestLakeNativeCompatReservationBase
