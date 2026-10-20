/* test_observer.c — real host test for the T27 observer (offline; no device).
 * Includes observer.c to reach its static emit/store, like the peer probe. Uses typed fake
 * provider/owner callbacks + canaries + an fd-2 capture. Returns 0 on all-pass, nonzero on failure.
 * Build: cc -std=c11 -I. test_observer.c -o test_observer -lpthread ; run: ./test_observer */
#include "observer.c"
#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int g_fail = 0;
#define CHECK(c) do { if (!(c)) { fprintf(stdout, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); g_fail = 1; } } while (0)

/* ---- typed fakes ---- */
static int g_getcfg_calls, g_fromnwb_calls, g_create_calls;
static void fake_get_config(void *buffer, wl_t27_cfg *out) {
  (void) buffer; g_getcfg_calls++;
  /* SDK order width,height,format,usage,stride */
  out->width = 576; out->height = 1024; out->format = 11; out->usage_low32 = 0x1a2b; out->stride = 2304;
  errno = EIO;               /* a getter perturbs errno; pure observers must hide it */
}
static void *fake_from_nwb(void *wb) { g_fromnwb_calls++; errno = ENOTCONN; return (void *) ((char *) wb + 0x10); }
static void *fake_create(void *d, void *c, uint32_t t, void *cb, const int32_t *a) {
  (void) d; (void) c; (void) t; (void) cb; (void) a; g_create_calls++;
  errno = ECONNREFUSED;      /* the PROVIDER errno the caller must see after create */
  return (void *) 0xBEEF;
}

/* capture fd 2 into a temp file; returns its contents (caller frees). */
static char *capture(void (*body)(void)) {
  char tmpl[] = "/tmp/wl_t27_capXXXXXX";
  int fd = mkstemp(tmpl);
  int saved2 = dup(2);
  fflush(stderr); dup2(fd, 2);
  body();
  fflush(stderr); dup2(saved2, 2); close(saved2);
  off_t n = lseek(fd, 0, SEEK_END); lseek(fd, 0, SEEK_SET);
  char *buf = malloc((size_t) n + 1);
  ssize_t r = read(fd, buf, (size_t) n); buf[r > 0 ? r : 0] = '\0';
  close(fd); unlink(tmpl);
  return buf;
}

static wl_t27_getters G_FULL, G_NONE;

/* bodies for capture */
static void body_create(void) {
  wl_t27_create_call(1, 2, (void *) fake_create, (void *) 0x1234, (void *) 0x5678, 0x3140,
                     (void *) 0x9abc, (const void *) 0xdef0);
}
static long g_longfile_len;
static void body_longfile(void) {
  wl_t27_record r; wl_hdr(&r, 1, 2, WL_T27_CREATE_CALL);
  static char path[2048]; memset(path, 'x', sizeof path - 1); path[sizeof path - 1] = '\0';
  r.create.file = path; r.create.base = (void *) 0xBA5E; r.create.rel_off = 0x1234;
  r.create_ret = (void *) 0xBEEF; g_longfile_len = (long) strlen(path);
  wl_t27_emit(&r);
}
static void body_overflow(void) { for (int i = 0; i < 300; i++) wl_t27_cpu_native(i, i, 0, 0, 0, &G_NONE, 0); }

int main(void) {
  G_FULL.get_config = fake_get_config; G_FULL.from_nwb = fake_from_nwb;
  G_NONE.get_config = NULL;            G_NONE.from_nwb = NULL;

  /* 1. pure observer preserves ENTRY errno despite the getter perturbing it */
  wl_t27_reset();
  errno = EPERM;
  wl_t27_cpu_native(1, 1, (void *) 0xA, (void *) 0xB, (void *) 0xC, &G_FULL, (void *) 0xD);
  CHECK(errno == EPERM);                         /* entry errno preserved */
  CHECK(wl_t27_getter_calls() == 1);             /* admitted getter counted */
  { wl_t27_record s; CHECK(wl_t27_snapshot(&s, 1) == 1);
    CHECK(s.cfg.format == 11 && s.cfg.usage_low32 == 0x1a2b && s.cfg.stride == 2304); /* SDK order */
    CHECK(s.getter_called == 1); }

  /* 2. NULL/foreign getter => zero getter calls, UNKNOWN cfg, record still made */
  wl_t27_reset();
  errno = EPERM;
  wl_t27_cpu_native(2, 2, 0, 0, 0, &G_NONE, (void *) 0xD);
  CHECK(errno == EPERM);
  CHECK(wl_t27_getter_calls() == 0);
  { wl_t27_record s; CHECK(wl_t27_snapshot(&s, 1) == 1);
    CHECK(s.cfg.format == WL_T27_UNKNOWN_I32 && s.getter_called == 0); }

  /* 3. import: from_nwb + get_config both counted */
  wl_t27_reset(); errno = EPERM;
  wl_t27_import_config(3, 3, (void *) 0x1, (void *) 0x2, 7, 9, &G_FULL);
  CHECK(errno == EPERM);
  CHECK(wl_t27_getter_calls() == 2);             /* from_nwb + get_config */
  CHECK(g_fromnwb_calls >= 1 && g_getcfg_calls >= 2);

  /* 4. create: PROVIDER errno preserved, single invocation, return propagated */
  wl_t27_reset(); g_create_calls = 0; errno = EPERM;
  void *ret = wl_t27_create_call(4, 4, (void *) fake_create, (void *) 0x1, (void *) 0x2, 0x3140,
                                 (void *) 0x3, (const void *) 0x4);
  CHECK(ret == (void *) 0xBEEF);
  CHECK(errno == ECONNREFUSED);                  /* provider errno, NOT entry EPERM, NOT swallowed */
  CHECK(g_create_calls == 1);                    /* exactly one invocation */

  /* 5. full line + newline + all create fields present (no 256 truncation) */
  wl_t27_reset();
  char *out = capture(body_create);
  CHECK(strchr(out, '\n') != NULL);
  CHECK(strstr(out, "create_base=") && strstr(out, "rel=") && strstr(out, "ret=0xbeef"));
  CHECK(strstr(out, "disp=0x1234") && strstr(out, "tgt=0x3140"));
  CHECK(strstr(out, "<TRUNC>") == NULL);         /* short line not truncated */
  free(out);

  /* 6. long file => explicit <TRUNC> tag AND guaranteed newline; base/rel survive (precede file) */
  wl_t27_reset();
  out = capture(body_longfile);
  CHECK(g_longfile_len > 1024);
  CHECK(strstr(out, "<TRUNC>") != NULL);
  CHECK(out[strlen(out) - 1] == '\n');           /* newline guaranteed on truncation */
  CHECK(strstr(out, "create_base=0xba5e") != NULL); /* base not silently cut */
  free(out);

  /* 7. print cap + drop marker + ring drop counting */
  wl_t27_reset();
  out = capture(body_overflow);
  CHECK(wl_t27_printed() == WL_T27_PRINT_CAP);    /* 256 durable lines */
  CHECK(wl_t27_print_suppressed() == 300 - WL_T27_PRINT_CAP);
  CHECK(strstr(out, "print-cap=256 reached") != NULL); /* single drop marker emitted */
  CHECK(wl_t27_count() == WL_T27_SLOTS && wl_t27_dropped() == 300 - WL_T27_SLOTS);
  free(out);

  fprintf(stdout, g_fail ? "T27 OBSERVER TESTS: FAIL\n" : "T27 OBSERVER TESTS: PASS\n");
  return g_fail;
}
