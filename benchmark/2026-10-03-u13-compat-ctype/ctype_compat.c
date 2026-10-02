#define _U 0x01
#define _L 0x02
#define _N 0x04
#define _S 0x08
#define _P 0x10
#define _C 0x20
#define _X 0x40
#define _B 0x80
#define __BEGIN_HIDDEN_DECLS
#define __END_HIDDEN_DECLS
#include "inputs/aosp/libc/upstream-openbsd/lib/libc/gen/ctype_.c"
_Static_assert(sizeof(_C_ctype_) == 257, "legacy ctype table extent");
_Static_assert(sizeof(_ctype_) == 8, "AArch64 pointer export");
