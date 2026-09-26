# r5 sigaction neuter — libmonitorcollector-lib.so (#48)
date: 2026-09-27

## Product (on-disk, gitignored; from codex-2's exact patched baseline f3918bdc)
- libmonitorcollector-lib.R5NEUTER48.so   sha256 8c97ef7cd666517e92c0a79a9471518afff0133a891f775d5291a557cdbacf31
    baseline (f3918bdc, hooks already neutered) sha256 f3918bdc42b60a19edc3b80c4bd1c1cadc972eba286e5f1b1447505a6bff1793 (313744 B)
Board overlay path: /data/local/tmp/asx/lib/arm64-v8a/libmonitorcollector-lib.so (app namespace; overlay, not BCP).

## Root cause (r5)
monitorcollector embeds xhook (xh_core_refresh / xh_core_clear). xhook installs a SIGSEGV handler
(to catch faults while it probes memory during hooking) via sigaction(SIGSEGV, &act, &old) with a
NON-NULL old. The lib is Bionic-built (small struct sigaction, sa_mask sigset_t 8B/64 sig); musl's
sigaction writes the FULL 152-byte struct (sa_mask sigset_t 128B/1024 sig) into old -> ~112B
overrun. When old sits near a mapping/page edge, the tail hits an unmapped/RO page -> SIGSEGV
(r5: platform-handle thread, musl sigaction+0x184 stp [x19,#96]). This is the SAME Bionic-vs-musl
sigaction ABI class as npth's r5 (patched in 7639af00) — monitorcollector is a second offender.
f3918bdc neutered monitorcollector's bytehook/shadowhook HOOK installs but NOT these sigaction calls.

## What changed (8 bytes, 2 instructions) — same method as npth 7639af00
Replace each reachable  with  (d2800000) — fake success (sigaction
returns 0), so musl is never called and never writes the oversized old struct -> no OOB. vaddr==
file-offset in .text:
  0x1d214  xh install:  sigaction(SIGSEGV=11, act=sp+8, old=static 0x4d428) -> the r5 OOB  -> mov x0,#0
  0x1df78  xh_core_clear restore sigaction                                  -> mov x0,#0
The 3rd sigaction site 0x1d318 is a -tail-call INSIDE the SIGSEGV handler function itself; it is
reachable ONLY if the handler was installed, and the install (0x1d214) is now faked, so the handler
is never installed and 0x1d318 is dead -> left as-is (patching a tail-branch cleanly is awkward and
unnecessary). assert confirms 0 remaining .

## Safety proof
1. Fake success (x0=0): callers check w0 for success — 0x1d218  sees w0=0 -> success
   path (no error handling triggered); 0x1df78's caller continues (0x1df7c adrp, no w0 branch). So
   the neuter presents a clean "sigaction succeeded" to xhook.
2. Losing xhook's SIGSEGV handler is moot: monitorcollector's bytehook/shadowhook hooks are already
   neutered (f3918bdc) AND the process runs on the hollow engines (no inline hooks installed at all),
   so xhook never probes/hooks -> there are no hooking faults for its SIGSEGV handler to catch. The
   handler was purely defensive for the (now non-existent) hooking activity.
3. Exports/SONAME/NEEDED unchanged (dyn-sym FUNC set identical -> no UnsatisfiedLinkError); ELF valid;
   only 8 bytes changed. No behavior change except: monitorcollector no longer installs/restores its
   SIGSEGV handler (moot) and no longer overruns musl's old buffer (the fix).
4. Namespace-robust: this is a file-level patch of the .so that the app loads (SOURCE-NATIVE-LOAD /
   any namespace) -> takes effect regardless of the OH-musl namespace isolation that made a universal
   sigaction shim uncertain (r5 crashed INSIDE musl -> monitorcollector's sigaction resolved directly
   to musl, so a per-lib file patch is the reliable fix).

## Verify / reproduce
scripts/assert_r5neuter.sh out/libmonitorcollector-lib.R5NEUTER48.so -> ALL PASS.
scripts/patch_monitorcollector_sigaction.py on the f3918bdc baseline reproduces it.
Not deployed (board is codex-2's); hand to codex-2 to overlay + merge-test with the hollow engines + r1 guard.
