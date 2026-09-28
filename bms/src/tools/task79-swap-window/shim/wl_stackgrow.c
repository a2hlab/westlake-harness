/* wl_stackgrow.so -- LD_PRELOAD for appspawn-x.
 *
 * Why this exists
 * ---------------
 * On this board the app's main thread ends up with a 128 KB stack that can never
 * grow, and any deep native frame dies with SIGSEGV.  Observed on 5ce2dcee:
 * SkPngCodec::processData() wants a ~64 KB frame and faults on the guard page,
 * killing the app ~3 s into MainActivity.
 *
 * The mechanism: musl's pthread_getattr_np() cannot report the *main* thread's
 * real stack size.  For the main thread t->stack is 0, so musl probes downward
 * from the auxv page with mremap and returns only how much is CURRENTLY MAPPED.
 * At ART startup that is 128 KB.  ART believes that number, sets stack_begin
 * accordingly and mmaps its PROT_NONE stack-overflow guard immediately below it
 * (Thread::InstallImplicitProtection).  That mapping then permanently blocks the
 * kernel's expand_downwards(), so the stack is frozen at 128 KB even though
 * RLIMIT_STACK is 16 MB.  Compare /proc/1/maps: init has the same small [stack]
 * but no PROT_NONE below it, so its stack still grows.
 *
 * The fix here: a constructor -- which runs before ART's Thread::InitStackHwm --
 * walks the stack down in small steps so the kernel grows the [stack] VMA first.
 * musl's probe then reports the real size and ART puts its guard at the bottom.
 * Every app process forked from the daemon inherits the roomy stack.
 *
 * This is a substrate-side workaround.  The real fix belongs in ART: for the main
 * thread, take the bounds from getrlimit(RLIMIT_STACK) rather than trusting
 * pthread_getattr_np.
 */
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/mman.h>
#include <unistd.h>
#include <fcntl.h>

/* Report the *measured* size of the [stack] VMA.  The previous version of this
 * shim printed an unconditional "grew main stack by N KB" after wl_walk()
 * returned, which was a self-report, not evidence: the growth silently did
 * nothing and the message still claimed success. */
static size_t wl_stack_vma_kb(void) {
  FILE *f = fopen("/proc/self/maps", "r");
  char line[256];
  size_t kb = 0;
  if (!f) return 0;
  while (fgets(line, sizeof(line), f)) {
    unsigned long lo, hi;
    if (strstr(line, "[stack]") && sscanf(line, "%lx-%lx", &lo, &hi) == 2) {
      kb = (size_t)(hi - lo) / 1024;
      break;
    }
  }
  fclose(f);
  return kb;
}

#ifndef WL_STEP
#define WL_STEP 16384          /* per-frame bite; well under the kernel's guard gap */
#endif

static volatile char wl_sink;

__attribute__((noinline)) static void wl_walk(size_t remaining) {
  volatile char frame[WL_STEP];
  /* Force the frame to really be reserved.  Without an opaque use of its
   * address clang keeps only the individual volatile byte accesses and packs
   * them into a 48-byte frame -- the 16 KB array is never allocated and the
   * stack pointer barely moves, so the walk silently does nothing. */
  __asm__ volatile("" :: "r"(frame) : "memory");
  /* touch every page of this frame so the kernel really faults them in */
  for (size_t i = 0; i < WL_STEP; i += 4096) frame[i] = (char)i;
  frame[WL_STEP - 1] = 1;
  wl_sink = frame[0];
  if (remaining > WL_STEP) wl_walk(remaining - WL_STEP);
  /* Keep the frame live across the recursive call.  Without this the call is
   * in tail position and clang -O2 turns the recursion into a loop that reuses
   * a single 16 KB frame, so the stack never actually grows.  noinline does not
   * prevent sibling-call optimisation -- only a live use after the call does. */
  __asm__ volatile("" :: "r"(frame) : "memory");
}

/* expand_downwards() refuses to grow the stack across an existing mapping, so a
 * PROT_NONE guard sitting directly beneath [stack] freezes it for good.  That
 * is exactly the end state seen in the app process: 128 KB of stack with a 4 KB
 * ---p page at gap 0 below it.  Measured in appspawn-x, though, no such page
 * exists yet when this constructor runs (1.4 GB free below), which confirms the
 * ordering in the header comment: ART installs the guard afterwards, against
 * whatever size musl reported.  So this is a defensive pre-step -- drop an
 * adjacent guard if one is already there -- and the growth itself comes from
 * the walk below.  Returns the KB of free space beneath the stack. */
static unsigned long wl_clear_stack_guard(void) {
  FILE *f;
  char line[256], perm[8], pperm[8];
  unsigned long slo = 0, plo = 0, phi = 0, pplo = 0, pphi = 0;
  unsigned long glo = 0, ghi = 0, below = 0;

  pperm[0] = 0;
  f = fopen("/proc/self/maps", "r");
  if (!f) return 0;
  while (fgets(line, sizeof(line), f)) {
    unsigned long lo, hi;
    if (sscanf(line, "%lx-%lx %7s", &lo, &hi, perm) != 3) continue;
    if (strstr(line, "[stack]")) {
      slo = lo; glo = plo; ghi = phi; below = pphi;
      strcpy(pperm, perm[0] ? perm : "?");
      strcpy(pperm, perm);
      break;
    }
    pplo = plo; pphi = phi;
    plo = lo; phi = hi;
    strcpy(pperm, perm);
  }
  fclose(f);
  (void)pplo;
  if (!slo) return 0;
  /* the mapping directly beneath the stack, only if it is an anonymous
   * PROT_NONE page of at most 64 KB -- i.e. unmistakably a guard */
  if (ghi == slo && pperm[0] == '-' && pperm[1] == '-' && pperm[2] == '-' &&
      (ghi - glo) <= 64u * 1024) {
    if (munmap((void *)glo, (size_t)(ghi - glo)) == 0) {
      fprintf(stderr, "[wl_stackgrow] dropped guard %lx-%lx below stack\n", glo, ghi);
      return (slo - below) / 1024;
    }
    fprintf(stderr, "[wl_stackgrow] munmap of guard %lx-%lx FAILED\n", glo, ghi);
    return 0;
  }
  return ghi ? (slo - ghi) / 1024 : 0;
}

static int wl_is_appspawn(void) {
  char buf[256];
  int fd, n;
  fd = open("/proc/self/cmdline", O_RDONLY);
  if (fd < 0) return 0;
  n = (int)read(fd, buf, sizeof(buf) - 1);
  close(fd);
  if (n <= 0) return 0;
  buf[n] = 0;
  return strstr(buf, "appspawn") != NULL;
}

__attribute__((constructor(101))) static void wl_grow_main_stack(void) {
  struct rlimit rl;
  size_t before, after;
  unsigned long room;
  size_t want = 8u << 20;                       /* AOSP's main-thread stack size */
  if (getrlimit(RLIMIT_STACK, &rl) == 0 && rl.rlim_cur != RLIM_INFINITY) {
    size_t lim = (size_t)rl.rlim_cur;
    if (lim > (2u << 20)) {
      size_t usable = lim - (2u << 20);         /* leave headroom under the limit */
      if (usable < want) want = usable;
    } else {
      want = lim / 2;
    }
  }
  /* only the spawn daemon matters -- every app process is forked from it and
   * inherits the grown stack.  Leave the launcher's shell utilities alone. */
  if (!wl_is_appspawn()) return;
  room = wl_clear_stack_guard();
  before = wl_stack_vma_kb();
  /* the kernel keeps stack_guard_gap (1 MB) clear below a growable stack */
  if (room > 1536) {
    size_t usable = (size_t)(room - 1536) * 1024;
    if (usable < want) want = usable;
  }
  wl_walk(want);
  after = wl_stack_vma_kb();
  fprintf(stderr, "[wl_stackgrow] main stack %zu KB -> %zu KB (asked %zu KB, room %lu KB)%s\n",
          before, after, want / 1024, room, after > before ? "" : "  *** NO GROWTH ***");
  fflush(stderr);
}
