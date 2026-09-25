#!/usr/bin/env bash
# #46: regenerate the disassembly/string excerpts cited by the triage report.
set -euo pipefail
EV=$HOME/a2hlab/tmp/wv46/ev
mkdir -p "$EV"
LIB=$HOME/a2hlab/app-inputs/toutiao/lib/arm64-v8a
OD=$HOME/a2hlab/ws/toolchains/clang-15/bin/llvm-objdump
S=$HOME/a2hlab/tmp/wv46/strs.py
NDIS=/tmp/c3/npth.dis
[ -f "$NDIS" ] || $OD -d --no-show-raw-insn "$LIB/libnpth.so" > "$NDIS"

{
  echo "# libnpth.so sha256"; sha256sum "$LIB/libnpth.so"
  echo; echo "# (1) dump-pthread routine 0x17930: pthread_self() then x = *x until NULL (Bionic next@0; musl self@0)"
  python3 "$S" "$LIB/libnpth.so" "$NDIS" 17930 17a10 >/dev/null
  awk '/^   17930:/,/^   17a10:/' "$NDIS"
  echo; echo "# (2) callers of 0x17930 (return value unused)"
  for c in 193a0 19ac0 28d10; do python3 "$S" "$LIB/libnpth.so" "$NDIS" $(printf %x $((0x$c-0x20))) $(printf %x $((0x$c+0x10))); echo --; done
  echo; echo "# (3) native-info dump dispatcher 0x28bfc: one-shot latches, [+32] = dump pthread, then PriorityMonitor/anr"
  python3 "$S" "$LIB/libnpth.so" "$NDIS" 28bfc 28d74
  echo; echo "# (4) bounded pthread-field probe 0x17690 (scans pthread_self()+16 .. page end; safe on musl)"
  awk '/^   176d0:/,/^   177e8:/' "$NDIS"
  echo; echo "# (5) fork heap-dump path (nativeDumpHprof): ScopedGCCriticalSection + ScopedSuspendAll, fork, child DumpHeap"
  python3 "$S" "$LIB/libnpth.so" "$NDIS" 1fa20 1fe1c
  echo; echo "# (6) signal handler re-raise: rt_tgsigqueueinfo(getpid(), gettid(), signo, info)"
  awk '/^   13810:/,/^   13878:/' "$NDIS"
  echo; echo "# (7) child signal reset table at 0x33e98 (stride 48): SIGABRT BUS FPE ILL SEGV TRAP SYS STKFLT PIPE -> SIG_DFL"
  awk '/^   13000:/,/^   130f4:/' "$NDIS" | grep -E "signal@plt|ret"
} > "$EV/npth-disassembly.txt"

{
  echo "# libumeng-spy.so sha256"; sha256sum "$LIB/libumeng-spy.so"
  echo; echo "# Java_com_umeng_umzid_Spy_getNativeID: pipe, signal(SIGCHLD) when arg, fork, parent select(1s)/read, child probes"
  sed -n 658,1010p /tmp/c3/spy.ann.dis
  echo; echo "# 0xc024 (called from the child via 0xc2b0): stat, fopen boot_id, popen getprop x3"
  python3 "$S" "$LIB/libumeng-spy.so" /tmp/c3/spy.ann.dis c024 c2ac
} > "$EV/umeng-spy-disassembly.txt"

{
  echo "# dex call chains (dexdump of toutiao.apk classes*.dex)"
  echo "## fork heap dump: who calls Npth.dumpHprof -> NativeBridge.o -> nativeDumpHprof"
  python3 $HOME/a2hlab/tmp/wv46/callers.py "Lcom/bytedance/crash/jni/NativeBridge;.nativeDumpHprof:(ILjava/lang/String;)I" 3
  echo "## umeng ZID: who calls Spy.getNativeID"
  python3 $HOME/a2hlab/tmp/wv46/callers.py "Lcom/umeng/umzid/Spy;.getNativeID:(Z)Ljava/lang/String;" 3
  echo "## only literal \"work_thread\" in the APK"
  grep -h -B1 'const-string.*"work_thread"' /tmp/c3/dex/classes*.txt | cut -c40-220
  echo "## libnpth load: System.loadLibrary(\"npth\") chain up to Application (catches listed are monitor-exit + rethrow)"
  python3 $HOME/a2hlab/tmp/wv46/callers.py "LX/BEO;.<init>:(Landroid/content/Context;Ljava/io/File;)V" 5
  python3 $HOME/a2hlab/tmp/wv46/callers.py "Lcom/bytedance/crash/Npth;.init:(Landroid/content/Context;Lcom/bytedance/crash/ICommonParams;)V" 3
  python3 $HOME/a2hlab/tmp/wv46/callers.py "Lcom/ss/android/article/news/ArticleApplication;.npthCallInit:(Landroid/content/Context;Z)V" 3
  echo "## isSoLoaded guard scan over the three npth JNI classes"
  python3 $HOME/a2hlab/tmp/wv46/guard.py
  echo "## DT_NEEDED on libnpth.so itself (none) vs helper libs"
  cd "$LIB"; for x in *.so; do readelf -d "$x" 2>/dev/null | grep -q 'NEEDED.*\[libnpth.so\]' && echo "NEEDS libnpth.so: $x"; done; echo "(end)"
} > "$EV/dex-and-load-chains.txt" 2>&1

sha256sum "$EV"/*
