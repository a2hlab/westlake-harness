#!/system/bin/sh
# Boat-layer boot-autostart overlay (v2 seal, cc-t3 #91). Standalone: runs on the board's NORMAL boot (route-a
# complete) AFTER the base recover binds /system/android, and BEFORE any U13 appspawn-x app child is spawned
# (tap-to-start). Binds the validated single-file shared overlay (adapter 8ab85446 + jar 6333bcab) over the restored
# base, and the 3 app-private Unity libs into the installed BoatAttack lib dir. Window-8 proved an init-ns bind placed
# before a fresh spawn is inherited by the child, so this reaches BoatAttack's child when it is tapped.
#
# OUTER DECISION (2026-10-11): v2 uses STOCK runtime 18763dd4 — NO runtime bind (window-9 rendered on stock; adc125f4 /
# 94718e0d are NOT in v2, one fewer variable). This script therefore binds ONLY adapter + jar + 3 private.
#
# Sealed enforcement preserved (no setenforce). Idempotent. DISABLED marker short-circuits. NEVER launches the app.
set -u
ROOT=/data/westlake-demo/u13; ARCH="$ROOT/sources-boat-v2"; LOG="$ROOT/boat-overlay.log"
BUNDLE=com.Unity3d.BoatAttackDay; LIBD="/data/app/el1/bundle/public/$BUNDLE/android/lib/arm64-v8a"
ADAPTER_T=/system/android/lib64/liboh_adapter_bridge.so; ADAPTER_SHA=8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e; ADAPTER_BASE=84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a
JAR_T=/system/android/framework/oh-adapter-runtime.jar; JAR_SHA=6333bcab4ca2daad03965712deac6adf028a6ff0dfac04fc8ea91af177828852; JAR_BASE=bbc3f530190fe98e2979dc4059379f8a0259d1f6ab243830347ca875cdb62f9b
# v2 = STOCK runtime; the runtime target is intentionally NOT bound. Recorded for the KA/readback gate.
RUNTIME_T=/system/android/lib64/liboh_android_runtime.so; RUNTIME_STOCK=18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae
log(){ echo "boat-overlay: $*"; echo "[$(date +%H:%M:%S 2>/dev/null)] $*" >> "$LOG" 2>/dev/null; }
fail(){ log "FAIL $*"; exit 1; }
sha(){ sha256sum "$1" 2>/dev/null|cut -d' ' -f1; }
bind_over(){ # src target want base
  local src=$1 tgt=$2 want=$3 base=$4
  [ -e "$tgt" ] || fail "TARGET_MISSING $tgt"
  cur=$(sha "$tgt"); [ "$cur" = "$want" ] && { log "already $tgt=$want"; return 0; }
  [ "$cur" = "$base" ] || log "WARN $tgt base=$cur (expect $base) — still overlaying $want"
  [ "$(sha "$src")" = "$want" ] || fail "SRC_SHA $src"
  chcon "$(ls -Z "$tgt" 2>/dev/null|grep -oE 'u:object_r:[A-Za-z0-9_]+:s0'|head -1)" "$src" 2>/dev/null
  mount -o bind "$src" "$tgt" 2>/dev/null || fail "BIND $tgt"
  [ "$(sha "$tgt")" = "$want" ] || fail "VERIFY $tgt"; log "overlaid $tgt -> $want"; }

[ -e "$ROOT/BOAT_DISABLED" ] && { log "DISABLED -> skip boat overlay"; exit 0; }
[ -d "$ARCH" ] || fail MISSING_BOAT_SOURCES

# v2 runtime policy check: leave the runtime at stock (do NOT bind). Warn loudly if the live runtime is not stock
# (someone left a candidate bound) — we still proceed with adapter/jar/private, but the readback gate will catch it.
rt_now=$(sha "$RUNTIME_T")
[ "$rt_now" = "$RUNTIME_STOCK" ] || log "WARN runtime=$rt_now not stock $RUNTIME_STOCK (v2 does not bind runtime; investigate)"

# shared: adapter + jar (single-file bind over the restored base). NO runtime bind (v2 stock).
bind_over "$ARCH/liboh_adapter_bridge.so" "$ADAPTER_T" "$ADAPTER_SHA" "$ADAPTER_BASE"
bind_over "$ARCH/oh-adapter-runtime.jar"  "$JAR_T"     "$JAR_SHA"     "$JAR_BASE"

# app-private: only if BoatAttack is installed (seal installs it once). signal-box target may not exist -> create.
if [ -d "$LIBD" ]; then
  [ -e "$LIBD/libwestlake_bionic_signal_box.so" ] || { touch "$LIBD/libwestlake_bionic_signal_box.so"; chown 0:0 "$LIBD/libwestlake_bionic_signal_box.so"; chmod 0644 "$LIBD/libwestlake_bionic_signal_box.so"; chcon u:object_r:data_app_el1_file:s0 "$LIBD/libwestlake_bionic_signal_box.so" 2>/dev/null; }
  for pr in "libwestlake_bionic_signal_box.so:7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da" \
            "libunity.so:1bea0fae1e6e76db15f17fca2bfa91b9c303ce278d6a4dcfba6af233b68b64ac" \
            "libil2cpp.so:f6b806b5c55e702b98caa2e85d2f9afb678bc47dcc4067017b33f5269afed746"; do
    f=${pr%:*}; want=${pr##*:}; [ "$(sha "$ARCH/$f")" = "$want" ] || fail "BOAT_PRIVATE_SRC_SHA $f"
    chcon u:object_r:data_app_el1_file:s0 "$ARCH/$f" 2>/dev/null
    mount -o bind "$ARCH/$f" "$LIBD/$f" 2>/dev/null || fail "BOAT_PRIVATE_BIND $f"
    [ "$(sha "$LIBD/$f")" = "$want" ] || fail "BOAT_PRIVATE_VERIFY $f"; log "boat private $f -> $want"
  done
else
  log "BoatAttack not installed ($LIBD absent) — shared overlay applied; private binds skipped (install APK first)"
fi
log "boat overlay done (v2 stock runtime, NO runtime bind) — NO app launched (tap-to-start)"
exit 0
