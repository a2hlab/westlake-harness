/* Edge Case / FR-001: the system MUST establish a private PER-FORK capability channel
 * (non-shared pathname, non-shared listener) — not a channel reused across requests.
 * This test creates channels for two independent requests (neither is actually forked;
 * this targets fork_capability_channel_create() in isolation) and asserts they resolve
 * to two DIFFERENT underlying sockets (distinct dev/inode identity), not the same shared
 * channel handed out twice. A degenerate "shared listener" implementation would still
 * pass every other existing test (US1/US2/US3 each only ever create one channel at a
 * time), which is exactly why FR-001 had zero mutant coverage before this file existed. */
#include "fork_capability.h"
#include "test_util.h"

#include <sys/stat.h>
#include <unistd.h>

int main(void) {
    int p1, c1, p2, c2;
    CHECK(fork_capability_channel_create(&p1, &c1) == 0, "first channel create failed");
    CHECK(fork_capability_channel_create(&p2, &c2) == 0, "second channel create failed");

    struct stat sp1, sp2, sc1, sc2;
    CHECK(fstat(p1, &sp1) == 0, "fstat p1 failed");
    CHECK(fstat(p2, &sp2) == 0, "fstat p2 failed");
    CHECK(fstat(c1, &sc1) == 0, "fstat c1 failed");
    CHECK(fstat(c2, &sc2) == 0, "fstat c2 failed");

    /* Two independently created per-fork channels must never resolve to the same
     * underlying socket (same device+inode) on either endpoint — otherwise a
     * "private per-fork channel" has degenerated into a shared channel that a
     * second, unrelated fork's child could read from or write to. */
    CHECK(!(sp1.st_dev == sp2.st_dev && sp1.st_ino == sp2.st_ino),
          "two per-fork parent endpoints must not share the same underlying socket identity");
    CHECK(!(sc1.st_dev == sc2.st_dev && sc1.st_ino == sc2.st_ino),
          "two per-fork child endpoints must not share the same underlying socket identity");

    close(p1);
    close(c1);
    close(p2);
    close(c2);
    TEST_MAIN_EXIT();
}
