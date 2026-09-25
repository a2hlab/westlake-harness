#include <cassert>
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <signal.h>
#include <ucontext.h>
#include <cstdio>

struct SigchainAction {
  bool (*sc_sigaction)(int, siginfo_t*, void*);
  sigset_t sc_mask;
  uint64_t sc_flags;
};
static SigchainAction installed[2];
static int count, calls, records;
static bool claim;
extern "C" {
void AddSpecialSignalHandlerFn(int, void*);
void RemoveSpecialSignalHandlerFn(int, bool (*)(int, siginfo_t*, void*));
void SigchainStartReassert();
void add_special_signal_handler(int sig, SigchainAction* action) {
  assert(sig == SIGSEGV && count < 2); installed[count++] = *action;
}
void remove_special_signal_handler(int sig, bool (*fn)(int, siginfo_t*, void*)) {
  assert(sig == SIGSEGV);
  int slot = 0; while (slot < count && installed[slot].sc_sigaction != fn) ++slot;
  assert(slot < count);
  for (int i = slot+1; i < count; ++i) installed[i-1] = installed[i];
  --count;
}
int wl_crash_snapshot_init(const char*) { return 0; }
void wl_crash_snapshot(int sig, const siginfo_t*, const void*) {
  assert(sig == SIGSEGV); ++records;
}
}
static bool first(int sig, siginfo_t*, void*) {
  assert(sig == SIGSEGV); ++calls; return claim;
}
static bool second(int sig, siginfo_t*, void*) {
  assert(sig == SIGSEGV); ++calls; return false;
}
static bool deliver() {
  siginfo_t si = {}; si.si_signo = SIGSEGV; si.si_code = SEGV_MAPERR;
  ucontext_t uc = {};
  for (int i = 0; i < count; ++i) {
    if (installed[i].sc_sigaction(SIGSEGV, &si, &uc)) return true;
  }
  assert(si.si_code == SEGV_MAPERR);
  return false;
}
int main() {
  SigchainAction a = {}; a.sc_sigaction = first; a.sc_flags = 1;
  sigemptyset(&a.sc_mask); sigaddset(&a.sc_mask, SIGUSR1);
  AddSpecialSignalHandlerFn(SIGSEGV, &a);
  assert(installed[0].sc_flags == 1 && sigismember(&installed[0].sc_mask, SIGUSR1));
  a.sc_sigaction = second; a.sc_flags = 0; AddSpecialSignalHandlerFn(SIGSEGV, &a);
  SigchainStartReassert();  // Native OH chain: no reassert thread should start.
  claim = true; errno = EDOM; assert(deliver());
  assert(calls == 1 && records == 0 && errno == EDOM);
  claim = false; assert(!deliver()); assert(calls == 3 && records == 1);
  RemoveSpecialSignalHandlerFn(SIGSEGV, first);
  assert(!deliver()); assert(calls == 4 && records == 2);
  a.sc_sigaction = first; AddSpecialSignalHandlerFn(SIGSEGV, &a);
  // Re-added handler is last despite reusing slot 0: capture only after it declines.
  claim = true; assert(deliver()); assert(calls == 6 && records == 2);
  claim = false; assert(!deliver()); assert(calls == 8 && records == 3);
  RemoveSpecialSignalHandlerFn(SIGSEGV, first);
  RemoveSpecialSignalHandlerFn(SIGSEGV, second); assert(count == 0);
  puts("PASS: callback order, masks, flags, claim, removal and re-registration preserved");
}
