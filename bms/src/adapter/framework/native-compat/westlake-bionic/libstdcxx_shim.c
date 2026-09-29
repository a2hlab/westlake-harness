/* Build wrapper: libstdcxx_compat.c IS the libstdc++.so shim (its own header
 * says so: "This intentionally empty DSO only satisfies the legacy dependency
 * name"). Compile it with soname libstdc++.so — see build.sh. */
#include "libstdcxx_compat.c"
