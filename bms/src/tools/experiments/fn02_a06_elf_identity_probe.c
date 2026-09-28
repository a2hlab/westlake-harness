#include "westlake_elf_identity.h"

#include <elf.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    char resolved[PATH_MAX] = {0};
    int rc;

    if (argc != 4) {
        (void)fprintf(
            stderr,
            "usage: %s ABSOLUTE_ELF_PATH SHA256_HEX BUILD_ID_HEX\n",
            argv[0]);
        return 2;
    }

    errno = 0;
    rc = WLEI_VerifyFileHex(
        argv[1], EM_AARCH64, argv[2], argv[3],
        resolved, sizeof(resolved));
    (void)printf(
        "probe=Fn02.A06 path=%s sha256=%s build_id=%s "
        "verify_rc=%d errno=%d errno_text=%s resolved=%s\n",
        argv[1], argv[2], argv[3], rc, errno, strerror(errno),
        resolved[0] == '\0' ? "<none>" : resolved);
    return rc == 0 ? 0 : 1;
}
