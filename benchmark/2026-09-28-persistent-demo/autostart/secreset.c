/* secreset — clear inherited securebits (incl SECBIT_KEEP_CAPS_LOCKED) then exec.
 * Runs as root from the init boot script; children inherit the unlocked securebits
 * so the westlake spawn child's PR_SET_KEEPCAPS(0) no longer returns EPERM. */
#include <sys/prctl.h>
#include <unistd.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
int main(int argc, char **argv){
    if (argc < 2){ fprintf(stderr,"usage: secreset <cmd> [args...]\n"); return 2; }
    /* PR_SET_SECUREBITS=0 clears all securebits and their LOCKED flags. Needs CAP_SETPCAP. */
    if (prctl(PR_SET_SECUREBITS, 0, 0, 0, 0) != 0)
        fprintf(stderr,"[secreset] PR_SET_SECUREBITS(0) failed: %s (continuing)\n", strerror(errno));
    else
        fprintf(stderr,"[secreset] securebits cleared\n");
    prctl(PR_SET_KEEPCAPS, 0, 0, 0, 0);
    execv(argv[1], &argv[1]);
    fprintf(stderr,"[secreset] execv %s failed: %s\n", argv[1], strerror(errno));
    return 127;
}
