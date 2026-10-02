#include <stdio.h>
#include "ctype_compat.c"

int main(void) {
    if (_ctype_ != _C_ctype_) return 1;
    for (unsigned index = 0; index < sizeof(_C_ctype_); ++index) {
        printf("%02x", (unsigned char)_ctype_[index]);
    }
    puts("");
    return 0;
}
