// The registry's only Bionic stack-guard aperture write primitive. The address
// is resolved and ownership-checked by the caller; this DSO never reads TP.

.text
.p2align 2
.globl WLTG_StoreGuardAndReadback
.hidden WLTG_StoreGuardAndReadback
.type WLTG_StoreGuardAndReadback,%function
WLTG_StoreGuardAndReadback:
    str x1, [x0]
    ldr x0, [x0]
    ret
.size WLTG_StoreGuardAndReadback, .-WLTG_StoreGuardAndReadback
