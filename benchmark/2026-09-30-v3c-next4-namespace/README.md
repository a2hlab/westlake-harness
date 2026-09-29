# next4: OH owner repair tested, candidate rejected

Next3 mistook dependency reachability for namespace ownership. Its fatal
`Add too many the special handlers at last!` does **not** prove all four musl
slots are occupied: OH's at-last API checks only slot 3 and aborts whenever it
is occupied. DFX already has a per-DSO `g_hasInit` guard. A second DSO instance
has a fresh guard. Next3's crash stack places DFX InitHandler inside Unity's
dlopen; the crashed child's full maps were not captured, so duplicate mapping
is a source-supported explanation to test, not a counted device observation.

OH6.1 musl commit 02dd8d82887b040b85a4294e9a5039f016fd607a and faultloggerd
083ceb848a909fb5f398017ad2c39d2839b5e558 were read from the frozen OH6.1 tree.
The source is copied under source-evidence. Mac sources were checked first,
then OrbStack; OH musl was absent there, so hw248 was read last. The Linux
loader explicitly stops inheritance after one hop. With LOCAL_NS_PREFERED,
putting system directories in app search paths can instantiate system DSOs
locally instead of reusing their existing owner. DFX singleton state must not
be duplicated; increasing the table or suppressing its fatal error is not a
repair.

## Choice and change

Choose namespace narrowing. The complete preceding graph has **39 direct OH
boundary names**; ZigZag/libandroid/bridge alone reach 36 boundary names and
281 transitive platform files. Keep the 39 names as a bounded direct default-
namespace inheritance edge. The OH loader resolves their internal dependencies
in the OH owner domain. Remove all five OH directories from app-local search
and permitted paths. Preserve existing runtime roots and direct app path
admission, including v2 permitted-path behavior. No musl/DFX/ART change.

The default-owner callback lives in appspawn-x, so this repair changes one
host translation unit as well as ANL. The actual unlocked B9 source is saved
here; the tracked older host source still has obsolete identity checks and is
not the deployed build input. B80's INET service object and all other host
objects remain. The host recipe strictly links against the existing frozen
inputs and compares two builds byte-for-byte. The actual callback is executed
in a host recorder test; the old callback is rejected as a negative control.

AudioSystem.newAudioSessionId copies the existing Westlake return-zero JNI
stub (OrbStack ws/art-build/stubs/audiosystem_jni_stub.cc:248), with its SHA and
excerpt recorded. Zero is the no-AudioFlinger allocation sentinel, **not** a
unique positive session or proof of playback. The existing VT, SQLite,
CommonEvent, and three AudioSystem capability registrations remain.

## Host gates and device plan

ANL: 145 checks, zero failures. Actual namespace callback: bounded direct OH
owner edge, failing lookup stops configuration, foreign namespace denied;
old callback negative rejected. Host and ANL each repeat byte-identically.
NEEDED order, SONAME and exports match next3; only added import is host
`dlns_get`, declared by the frozen OH ABI. Full package dry-run covers 281 files.
Source/header changes, actual recipes and tests are versioned before device
activation. Compiler/sysroot/remaining objects use existing B9/B80/B87 archives;
see their source-preservation/source-link-inputs/persistence reports.

Candidate package: /Users/zhaoyue/orca/workspaces/westlake-generation-v3c-next4-audio-anl.
Only host, both ANL aliases and Android runtime change from signed v3c.
5cd only; keep r17m, expose r8b around one upgrade transaction. No installer,
foundation or board reboot. Predict ZigZag passes the prior missing-library and
DFX duplicate-init walls; HW/Auxio/NetGuard retain UI. VLC should pass the
missing-newAudioSessionId lookup, without claiming playback. Any control
regression rejects the candidate and triggers exact v3c rollback. Screenshots
and facts.txt determine the device verdict; static gates alone do not sign it.

## Device result: do not deploy as a signed baseline

Run `next4-r17m-5cd` used fixed r17m and master preflight. HelloWorld controls,
Auxio five tabs/music-source button and NetGuard main screen remain visible.
ZigZag returned to the OH desktop at both capture times. The old at-last fatal
is absent. One early map sample has one DFX, one route ART and one route
openjdkjvm; this sample precedes the Unity load and is not a fault-time map.
It cannot prove later DSO uniqueness. There are two liblog path mappings.

The new ZigZag fatal is `SIGSEGV(SEGV_MAPERR)@0x00000bf3a9be7eed` on TuanjieMain:
`ANativeWindow_getFormat+60` in vendor libnativewindow -> Mali
`new_window_surface` -> OH libEGL -> libtuanjie. Candidate and baseline both
have OH_EglHijack logs; the candidate additionally has a failed app-domain
libmali preload. These observations are recorded, not a proven new root cause.
See zigzag-fault.txt and egl-log-comparison.json. No signal-table workaround
or speculative window fix was deployed.

VLC passed the formerly missing `newAudioSessionId` lookup and reached native
library loading: `libvlc.so: __pthread_cleanup_push: symbol not found`.
This does not validate playback or session-ID allocation. Candidate rejected;
rollback and the baseline ZigZag control are recorded below once complete.
Screenshots, original records, process tables, preflight, fingerprint and raw
facts are under evidence/. R2 is partially; package signing is rejected.

### Candidate facts (verbatim)

```text
RUNTIME fingerprint=a0698535ecaf files=117 (runtime-fingerprint.txt; compare before blaming the JAR across boards)
fd-auxio             shots 2/2  alive t5=yes t20=yes  child_hilog=41268  foreground_unconfirmed
fd-netguard          shots 2/2  alive t5=yes t20=yes  child_hilog=13058  foreground_unconfirmed
helloworld           shots 2/2  alive t5=yes t20=yes  child_hilog=5780  foreground_unconfirmed
vlc                  shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
zigzag               shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
TOTAL keys=5 screenshots_captured=10/10 alive_t5=3 alive_t20=3
```

| App | t20 screenshot | Visual result |
| --- | --- | --- |
| helloworld | [t20](evidence/next4-r17m-5cd/5cd1e3dd00000000000000000923012c/helloworld/t20.jpeg) | Hello World controls |
| fd-auxio | [t20](evidence/next4-r17m-5cd/5cd1e3dd00000000000000000923012c/fd-auxio/t20.jpeg) | Five tabs and music source |
| fd-netguard | [t20](evidence/next4-r17m-5cd/5cd1e3dd00000000000000000923012c/fd-netguard/t20.jpeg) | Main screen |
| zigzag | [t20](evidence/next4-r17m-5cd/5cd1e3dd00000000000000000923012c/zigzag/t20.jpeg) | OH desktop |
| vlc | [t20](evidence/next4-r17m-5cd/5cd1e3dd00000000000000000923012c/vlc/t20.jpeg) | OH desktop |

### Rollback verified; 5cd released

Restored signed v3c `668e4f7c` plus fixed r17m `a5cbd8d7`, same boot. Final
117 live SHA values, installer bytes and active ledger match (`final/receipt.json`).
The rollback control again shows [ZigZag TAP TO PLAY](evidence/next4-rollback-r17m-5cd/5cd1e3dd00000000000000000923012c/zigzag/t20.jpeg).
Board lock released and held is empty. No writes to 5ea/61b.

```text
RUNTIME fingerprint=7f649f45b05a files=117 (runtime-fingerprint.txt; compare before blaming the JAR across boards)
zigzag               shots 2/2  alive t5=yes t20=yes  child_hilog=13008  foreground_unconfirmed
TOTAL keys=1 screenshots_captured=2/2 alive_t5=1 alive_t20=1
```
