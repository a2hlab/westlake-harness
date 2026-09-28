// The only fixture aperture write primitive.  The address is supplied by the
// main-ELF reservation owner callback; this DSO never reads TPIDR_EL0 and never
// references the reservation TLS symbol itself.

.text
.p2align 2
.globl WLAF_StoreAndReadback
.hidden WLAF_StoreAndReadback
.type WLAF_StoreAndReadback,%function
WLAF_StoreAndReadback:
    str x1, [x0]
    ldr x0, [x0]
    ret
.size WLAF_StoreAndReadback, .-WLAF_StoreAndReadback
