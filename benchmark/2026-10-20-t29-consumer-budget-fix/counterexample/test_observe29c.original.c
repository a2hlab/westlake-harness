/* test_observe29c.c — host test for the T29 consumer logger (observe29c.c).
 *
 * Mirrors the peer's test_observe29.c idiom: hook `write` via macro, #include the .c so each argv
 * mode runs against a fresh per-process DSO state. Ports the 12 proven cpu cases (concurrency,
 * reserved quotas, sink dev/ino, write-result accounting, bounded line) to the consumer record and
 * adds two consumer-specific cases (producer ref/unref independence; invalid early-return). */
#define _GNU_SOURCE 1
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int fault;
static unsigned attempts;
static ssize_t observed_write(int fd, const void *p, size_t n) {
  attempts++;
  if (fault == 1) { errno = EPIPE; return -1; }      /* closed reader */
  if (fault == 2) { errno = EINTR; return -1; }      /* interrupted */
  if (fault == 3) { errno = EIO;   return (ssize_t)n - 1; } /* short write */
  return write(fd, p, n);
}
#define write observed_write
#include "observe29c.c"
#undef write

static struct r29c_record rec(uintptr_t w) {
  struct r29c_record r;
  memset(&r, 0, sizeof(r));
  r.phase = R29C_UPDATE;
  r.wrapper = w;
  r.call = 1;
  return r;
}
static void pipe_stderr(void) {
  int p[2]; assert(pipe(p) == 0); assert(close(p[0]) == 0);
  assert(dup2(p[1], 2) == 2); assert(close(p[1]) == 0);
}
static void emit_preserve(struct r29c_record *r) {
  errno = EDOM; r29c_observe(r); assert(errno == EDOM);   /* errno-neutral */
}
static void *worker(void *unused) {
  (void)unused; struct r29c_record r = rec(1);
  for (unsigned i = 0; i < 10000; i++) emit_preserve(&r);
  return NULL;
}

int main(int argc, char **argv) {
  assert(argc == 2); const char *mode = argv[1];
  struct r29c_record r = rec(1); struct r29c_stats a, b;

  if (!strcmp(mode, "pipe")) {
    /* a real closed-reader pipe as fd2: zero writes, zero attempts, no formatting/timing, and the
     * process SIGPIPE disposition is NOT changed by the logger. */
    struct sigaction old, after; assert(sigaction(SIGPIPE, NULL, &old) == 0);
    pipe_stderr(); emit_preserve(&r); r29c_stats_read(&a);
    assert(sigaction(SIGPIPE, NULL, &after) == 0);
    assert(a.sink_state == 2 && a.writes == 0 && attempts == 0 && a.formatted == 0 && a.timed == 0);
    assert(old.sa_handler == after.sa_handler);
  } else if (!strcmp(mode, "fd2_rebind")) {
    /* the sink is OWNED after first bind; later rebinding fd2 must not change where we write */
    emit_preserve(&r); r29c_stats_read(&a); assert(a.sink_state == 1);
    int original = dup(2); assert(original >= 0); pipe_stderr();
    r = rec(2); emit_preserve(&r); r29c_stats_read(&b);
    assert(b.writes == a.writes + 1 && b.sink_state == 1);
    assert(dup2(original, 2) == 2); assert(close(original) == 0);
  } else if (!strcmp(mode, "sink_drift")) {
    /* drift the OWNED sink fd to a pipe: the pre-write dev/ino re-check disables the sink */
    emit_preserve(&r); r29c_stats_read(&a);
    int p[2]; assert(pipe(p) == 0); assert(close(p[0]) == 0);
    assert(dup2(p[1], sink) == sink); assert(close(p[1]) == 0);
    r = rec(2); emit_preserve(&r); r29c_stats_read(&b);
    assert(b.sink_state == 2 && b.writes == a.writes);
  } else if (!strcmp(mode, "epipe") || !strcmp(mode, "eintr") || !strcmp(mode, "short")) {
    /* one write attempt, no retry; a failed/short write is a loss and disables the sink */
    fault = !strcmp(mode, "epipe") ? 1 : (!strcmp(mode, "eintr") ? 2 : 3);
    emit_preserve(&r); r29c_stats_read(&a);
    assert(attempts == 1 && a.writes == 1 && a.losses == 1 && a.sink_state == 2);
    r = rec(2); emit_preserve(&r); assert(attempts == 1);   /* no further attempt */
  } else if (!strcmp(mode, "hot_new") || !strcmp(mode, "parallel")) {
    /* same key, success phase: cap 2 records + 1 FIRST_LIMIT notice = 3 writes, deterministic even
     * under 8 concurrent threads x 10000 emits (mutex). Exhausted re-run costs no format/time/write. */
    if (!strcmp(mode, "parallel")) {
      pthread_t t[8]; for (unsigned i = 0; i < 8; i++) assert(!pthread_create(&t[i], NULL, worker, NULL));
      for (unsigned i = 0; i < 8; i++) assert(!pthread_join(t[i], NULL));
    } else worker(NULL);
    r29c_stats_read(&a); assert(a.writes == 3 && a.first_limit == 1);
    worker(NULL); r29c_stats_read(&b);
    assert(a.formatted == b.formatted && a.timed == b.timed && a.writes == b.writes);
    r = rec(2); r.oh = 123; r.valid = R29C_OH; emit_preserve(&r); r29c_stats_read(&b);
    assert(b.writes == a.writes + 1 && b.identities == 2);
  } else if (!strcmp(mode, "reserve")) {
    /* 30 invalid/overflow quota, then the ordinary first-limit; a 17th identity hits the hard final */
    r.invalid = 1; for (unsigned i = 0; i < 100; i++) emit_preserve(&r);
    r29c_stats_read(&a); assert(a.invalids == 30 && a.first_limit == 1 && !a.final_exhaustion);
    for (unsigned i = 1; i <= 17; i++) { r = rec(i); emit_preserve(&r); }
    r29c_stats_read(&b); assert(b.identities == 16 && b.final_exhaustion == 1 && b.writes == 48);
  } else if (!strcmp(mode, "total")) {
    /* fill the entire 16 x 8 x 6 x (2+2) normal lane + 30 invalid + first + final = 3104, bytes bound */
    for (unsigned w = 1; w <= 16; w++)
      for (unsigned ep = 0; ep < 8; ep++)
        for (unsigned ph = 0; ph < 6; ph++)
          for (int err = 0; err < 2; err++)
            for (unsigned n = 0; n < 2; n++) {
              r = rec(w); r.transition = 1; r.valid = R29C_NEWWIN | R29C_OH;
              r.new_window = 17 + ep; r.oh = 100 + w; r.phase = ph; r.rc = err ? -EBUSY : 0;
              emit_preserve(&r);
            }
    for (unsigned n = 0; n < 30; n++) { r = rec(0); r.invalid = 1; emit_preserve(&r); }
    r = rec(1); emit_preserve(&r); r = rec(17); emit_preserve(&r);
    r29c_stats_read(&a);
    assert(a.writes == 3104 && a.bytes <= 2383872 && a.first_limit == 1 && a.final_exhaustion == 1);
    for (unsigned i = 0; i < 10000; i++) emit_preserve(&r);
    r29c_stats_read(&b); assert(b.writes == a.writes && b.formatted == a.formatted && b.timed == a.timed);
  } else if (!strcmp(mode, "epochs")) {
    /* 8 epochs then a 9th transition saturates -> hard final; non-transition emits do not re-open quota */
    for (unsigned i = 0; i < 9; i++) {
      r = rec(1); r.transition = 1; r.valid = R29C_NEWWIN; r.new_window = 17 + i; emit_preserve(&r);
    }
    r29c_stats_read(&a); assert(a.writes == 9 && a.final_exhaustion == 1);
    r = rec(1); r.transition = 0; for (unsigned i = 0; i < 100; i++) emit_preserve(&r);
    r29c_stats_read(&b); assert(a.writes == b.writes);
    r = rec(2); emit_preserve(&r); r29c_stats_read(&b); assert(b.writes == a.writes + 1);
  } else if (!strcmp(mode, "long")) {
    /* a fully-populated record still fits one bounded line (< 768 bytes), one write */
    memset(&r, 0x7f, sizeof(r)); r.invalid = 0; r.phase = R29C_UPDATE; r.valid = UINT32_MAX;
    emit_preserve(&r); r29c_stats_read(&a);
    assert(a.writes == 1 && a.bytes < 768);
  } else if (!strcmp(mode, "refunref")) {
    /* producer ref/unref are recorded INDEPENDENTLY of raw/public rc; a void provider gives
     * rc_valid=0 and NEVER flips the success/error lane. */
    struct r29c_record d = rec(0x900); d.phase = R29C_PRODUCER_DESTROY; d.transition = 1;
    d.valid = R29C_OLDWIN; d.old_window = 0xAA;
    d.unref_called = 1; d.unref_rc_valid = 0; d.unref_rc = 0;   /* void unref */
    emit_preserve(&d);
    struct r29c_record c = rec(0x900); c.phase = R29C_PRODUCER_REPLACE; c.transition = 1;
    c.valid = R29C_OLDWIN | R29C_NEWWIN; c.old_window = 0xAA; c.new_window = 0xBB;
    c.ref_called = 1; c.ref_rc_valid = 0; c.ref_rc = 0;         /* void ref */
    emit_preserve(&c);
    r29c_stats_read(&a); assert(a.writes == 2 && a.losses == 0);
    /* ref_rc_valid/ref_rc must NOT change the lane: three success replaces (rc=0,raw=0,exbranch=0)
     * with varying ref_rc still land in the SAME success lane -> 2 fit, 3rd -> FIRST_LIMIT */
    for (int i = 0; i < 3; i++) {
      struct r29c_record e = rec(0xC00); e.phase = R29C_PRODUCER_REPLACE;
      e.valid = R29C_NEWWIN | R29C_REFRC; e.new_window = 0xBB;
      e.ref_called = 1; e.ref_rc_valid = 1; e.ref_rc = i;  /* recorded, but never a control signal */
      emit_preserve(&e);
    }
    r29c_stats_read(&b); assert(b.first_limit == 1 && b.writes == a.writes + 3);
  } else if (!strcmp(mode, "invalid_consumer")) {
    /* an invalid early-return (state released / null) logs only safe fields and uses the 30 quota;
     * it never touches the normal identity lane. */
    for (unsigned i = 0; i < 35; i++) {
      struct r29c_record v; memset(&v, 0, sizeof(v));
      v.phase = R29C_UPDATE; v.wrapper = 0; v.invalid = 1;      /* no STATE/IMAGE/OH -> unknown */
      v.existing_exception_branch = 1; v.released_valid = 1; v.released = 1;
      emit_preserve(&v);
    }
    r29c_stats_read(&a);
    assert(a.invalids == 30 && a.first_limit == 1 && a.identities == 0 && a.final_exhaustion == 0);
  } else assert(!"unknown test");

  printf("PASS observe29c %s\n", mode);
  return 0;
}
