#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include "observe29c.h"

int main(int argc, char **argv) {
  assert(argc == 2);
  const int ref = !strcmp(argv[1], "ref");
  assert(ref || !strcmp(argv[1], "unref"));
  struct r29c_record r;
  memset(&r, 0, sizeof(r));
  r.phase = ref ? R29C_PRODUCER_REPLACE : R29C_PRODUCER_DESTROY;
  r.wrapper = r.oh = 0x123;
  r.valid = R29C_OH | (ref ? R29C_NEWWIN | R29C_REFRC : R29C_OLDWIN | R29C_UNREFRC);
  r.called = 1;
  r.transition = 1;
  if (ref) {
    r.new_window = 0x123;
    r.ref_called = r.ref_rc_valid = 1;
  } else {
    r.old_window = 0x123;
    r.unref_called = r.unref_rc_valid = 1;
  }
  struct r29c_stats s;
  for (unsigned i = 1; i <= 5; ++i) {
    r.call = i;
    if (i > 2) {
      if (ref) r.ref_rc = -29;
      else r.unref_rc = -31;
    }
    errno = EDOM;
    r29c_observe(&r);
    assert(errno == EDOM);
    r29c_stats_read(&s);
    assert(s.writes == i);
    assert(s.first_limit == (i == 5));
  }
  /* Both quotas exhausted: no more formatting, time lookup or write. */
  struct r29c_stats before = s;
  r.call = 6;
  r29c_observe(&r);
  r29c_stats_read(&s);
  assert(s.writes == before.writes && s.formatted == before.formatted && s.timed == before.timed);
  assert(s.identities == 1 && !s.final_exhaustion);
  printf("PASS failure_budget %s: success2 + error2 + FIRST_LIMIT; errno preserved\n", argv[1]);
  return 0;
}
