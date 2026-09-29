# B92: mapped initial stack is not the pthread default

The default-stack proposal cannot fix this board: its default already is
8,388,608 bytes. The device probe reports 135,168 bytes for the initial thread
before and after `pthread_setattr_default_np`, and the same size after fork.
A new pthread reports 8,391,240 bytes. See `device-stack-probe.txt`.
Westlake's comment attributing the initial size to the default is inaccurate
for this OH musl version; its explicit-pthread solution remains applicable.

The port copies Westlake `child_main.cpp:1500-1560` (commit
`532633da63b770d3d459c74683db6d7a1f82a022`) into Route-A's actual
`child_main_after_stock.cpp`, linked into **runtime-provider**, not the host.
It launches ActivityThread on an explicit 8 MiB pthread, attaches that thread
to ART, and detaches the unused original launcher before joining. Attribute,
creation and detach failures exit with diagnostics instead of falling back
to the proven small stack. The optional 1–512 MiB setting is retained.

The new thread also reaches Route-A's READY requirement. The outer loop
authorized removing that requirement. The oc-t4 patch (`3302406b`) was ported
onto the current ANL source: its prebuilt version lacks the v2 permitted-path
fix and would regress Flutter. This build preserves the fix and its escape
negative tests. It does not change namespaces or ART.

## Host evidence

- Original provider `a24bc454` reproduced **byte-for-byte** using its original
  source pathname and recorded compile/link commands. An earlier build from
  the evidence pathname differed because of debug/source pathname; it is not
  the reproduction used for this verdict.
- New provider `0509fe23` and ANL `a9c9187d` each reproduced twice identically.
- NEEDED order and exported symbols unchanged (`elf-compatibility.json`).
  Added imports are pthread/strtol and stdio/getenv from existing libc.
- ANL **138 checks, 0 failures**: includes the v2 permitted-root positive,
  symlink/foreign-root negatives, strict-mode negatives, and default allow.
- The first Docker host-test invocation stopped before compilation because
  its image lacks `rg`; the complete script passed on Mac. ARM64 builds used
  dockbuild throughout. Host tests do not establish device success.
- Known answers: 69 tests, 2 skipped, OK. B11 lifecycle: 4 Skip; B8: 6 Skip
  (selectors matched zero tests). These are not passes.
- Package dry-run passed. ART, host, child plugin, installer and Java unchanged.

## Reproduction and handoff

Restore B9 v3 inputs from
`../2026-09-29-unlocked-generation/source-preservation.json` and
`source-link-inputs.json` (persistent hw248 source/tool/link archives).
Production sources and ANL tests are tracked with this report.
`original-commands.json`, `build-provider.sh`, `reproduce-baseline.sh`,
`build-anl.sh` and `toolchain.json` record this experiment. Same-path baseline
reproduction temporarily substitutes only the private build-tree unit and
restores it with an EXIT trap.

`HANDOFF.md` and `replacements.json` provide complete Mac packages, exact
single-file targets and reverse rollback. cc-wiki owns 5ea; cx-t0 performed
no writes. ANL precedes the big-stack provider. Actual route-a paths are the
experimental targets; existing Android alias binds remain old until v3c.
The unified package must make both aliases refer to the same bytes.

## Device result (cc-wiki, 5ea)

With provider 0509fe23, ANL a9c9187d and Java v4 2fbfd8bc:
`[CM-BIGSTACK] launcher DetachCurrentThread before join rc=0` and
`[CM-BIGSTACK] ActivityThread on dedicated pthread stack=8390896 bytes`.
Wikipedia no longer hits the small-stack SIGSEGV. At t5 it shows its own
Wikipedia home; t20 is the OH desktop. The next main-thread failure is
`NoSuchMethodError: No virtual method setProperty(Ljava/lang/String;Ljava/lang/Object;)V
in class Lorg/ccil/cowan/tagsoup/Parser;`. Background networking still throws
`UnsupportedOperationException: TLS shim: no real networking (construct-only SSLContext on OH)`.
This fixes the stack wall, **not stable Wikipedia or TLS**.

Deployer HelloWorld SHA/maps checks passed: one ART, route-a openjdkjvm,
846 bridge. The later controls run shows HelloWorld's lifecycle/button UI
and ZigZag's TAP TO PLAY/BEST SCORE menu at t20. Outer review accepted them
in PROGRESS(92), 2026-09-30 01:02:43. Screens and process evidence are under
`evidence/`; facts.txt is copied verbatim:

```text
wikipedia            shots 2/2  alive t5=yes t20=no  child_hilog=54415  foreground_unconfirmed
TOTAL keys=1 screenshots_captured=2/2 alive_t5=1 alive_t20=0
helloworld           shots 2/2  alive t5=yes t20=yes  child_hilog=5238  foreground_unconfirmed
zigzag               shots 2/2  alive t5=yes t20=yes  child_hilog=12475  foreground_unconfirmed
TOTAL keys=2 screenshots_captured=4/4 alive_t5=2 alive_t20=2
```

R2: stack and control regression **verified**; full Wikipedia B11 acceptance
**partially**, with tagsoup and TLS still pending. Lifecycle Skip is not pass.
