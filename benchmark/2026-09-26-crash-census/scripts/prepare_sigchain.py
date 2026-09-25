"""Emit a private diagnostic sigchain source; never edit the input/shared tree.

Hook after the last ART handler declines, before the unchanged OH chain continues.
No extra OH handler slot, no new sigaction/rethrow, and original mask/flags retained.
"""
import argparse
import hashlib
from pathlib import Path

HOOK = r'''
// crash42 diagnostic-only wrapper; same callback return value and context.
using Crash42Fn = bool (*)(int, siginfo_t*, void*);
static Crash42Fn crash42_original[NSIG][2];
static unsigned crash42_order[NSIG][2];
static unsigned crash42_generation;
static bool crash42_call(unsigned slot, int sig, siginfo_t* si, void* uc) {
  const int saved = errno;
  Crash42Fn original = crash42_original[sig][slot];
  if (original == nullptr) { errno = saved; return false; }
  const bool claimed = original(sig, si, uc);
  const int after_original = errno;
  if (!claimed && crash42_order[sig][slot] >= crash42_order[sig][1-slot]) {
    wl_crash_snapshot(sig, si, uc);
  }
  errno = after_original;
  return claimed;
}
static bool crash42_first(int sig, siginfo_t* si, void* uc) {
  return crash42_call(0, sig, si, uc);
}
static bool crash42_second(int sig, siginfo_t* si, void* uc) {
  return crash42_call(1, sig, si, uc);
}
static Crash42Fn crash42_wrapper[2] = {crash42_first, crash42_second};
'''

def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Source drift: expected exactly one '+repr(old[:80]))
    return source.replace(old, new)

def prepare(source):
    source = replace_once(source, '#include <cerrno>',
                          '#include <cerrno>\n#include <cstdlib>\n#include "crash_snapshot.h"')
    source = replace_once(source, 'static struct sigaction g_art_sa[NSIG];',
                          HOOK+'\nstatic struct sigaction g_art_sa[NSIG];')
    source = replace_once(source, 'void SigchainStartReassert() {', '''void SigchainStartReassert() {
  // Existing post-fork child entry, outside signal context. No constructor capture.
  const char* snapshot_dir = getenv("WESTLAKE_CRASH42_DIR");
  if (snapshot_dir != nullptr) {
    const int saved = errno;
    if (wl_crash_snapshot_init(snapshot_dir) != 0) {
      static const char failure[] = "[CRASH42] init failed (or already initialized)\\n";
      ssize_t n = write(2, failure, sizeof(failure)-1); (void)n;
    }
    errno = saved;
  }''')
    source = replace_once(source, '    add_special_signal_handler(signal, sca);', '''    SigchainAction observed = *sca;
    for (unsigned slot = 0; slot < 2; ++slot) {
      if (crash42_original[signal][slot] == nullptr) {
        crash42_original[signal][slot] = sca->sc_sigaction;
        crash42_order[signal][slot] = ++crash42_generation;
        observed.sc_sigaction = crash42_wrapper[slot];
        break;
      }
    }
    add_special_signal_handler(signal, &observed);''')
    source = replace_once(source, '    remove_special_signal_handler(signal, fn);', '''    Crash42Fn registered = fn;
    int removed = -1;
    for (unsigned slot = 0; slot < 2; ++slot) {
      if (crash42_original[signal][slot] == fn) {
        registered = crash42_wrapper[slot]; removed = static_cast<int>(slot); break;
      }
    }
    remove_special_signal_handler(signal, registered);
    if (removed >= 0) {
      crash42_original[signal][removed] = nullptr;
      crash42_order[signal][removed] = 0;
    }''')
    source = replace_once(source,
        '  // Not claimed → chain to the handler we displaced (OHOS libdfx\'s crash reporter).',
        '  wl_crash_snapshot(sig, info, uc);\n\n'
        '  // Not claimed → chain to the handler we displaced (OHOS libdfx\'s crash reporter).')
    return source

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path); ap.add_argument('output', type=Path)
    args = ap.parse_args()
    if args.source.resolve() == args.output.resolve(): raise ValueError('Private output required')
    if hashlib.sha256(args.source.read_bytes()).hexdigest() != '22138666ebdb30a0674078b84aed78a2d8eefec722fb50e6c28da7dc87d61cac':
        raise ValueError('Source differs from audited sigchain; review before adapting')
    args.output.write_text(prepare(args.source.read_text()))
