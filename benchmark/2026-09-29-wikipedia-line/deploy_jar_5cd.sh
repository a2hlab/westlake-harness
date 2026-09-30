#!/bin/bash
# Locked single-file JAR overlay for B11 (Wikipedia line), with pinned baseline
# and one-umount rollback. Runs hdc from the Mac (env-mac.sh shims + full hdc path).
#
# The target JAR is already a stack of bind-mounts on 5ea:
#   base(v3a strict-*) <- b5-alias-20260928 (current effective).
# We add ONE more bind-mount on top; rollback umounts exactly our layer and the
# effective SHA returns to the recorded baseline. appspawn-x (ppid 1) shares the
# shell mount namespace, so a fresh app child forked after the mount inherits it.
#
# Usage:
#   deploy_jar.sh status
#   deploy_jar.sh deploy <local.jar> <expected_sha256> <tag> <receipt_dir>
#   deploy_jar.sh rollback <receipt_dir>
set -euo pipefail
source ~/orca/workspaces/westlake-inputs/env-mac.sh 2>/dev/null || true
SERIAL=5cd1e3dd00000000000000000923012c
HDC=(hdc -t "$SERIAL")
TARGET=/system/android/framework/oh-adapter-runtime.jar

sh_sha() { "${HDC[@]}" shell "sha256sum '$1' 2>/dev/null" | tr -d '\r' | cut -d' ' -f1; }
appspawnx_pid() {
  # parent appspawn-x = the one with PPid 1
  "${HDC[@]}" shell '
    for p in $(pidof appspawn-x); do
      grep -q "PPid:.[[:space:]]*1$" /proc/$p/status 2>/dev/null || \
      case "$(grep -m1 PPid /proc/$p/status)" in *"	1") echo $p;; esac
    done' | tr -d '\r' | head -1
}
appspawnx_sha() {
  local p; p=$("${HDC[@]}" shell 'for p in $(pidof appspawn-x); do case "$(grep -m1 PPid /proc/$p/status)" in *"	1") echo $p;; esac; done' | tr -d '\r' | head -1)
  echo "appspawnx_pid=$p" >&2
  "${HDC[@]}" shell "sha256sum /proc/$p/root$TARGET 2>/dev/null" | tr -d '\r' | cut -d' ' -f1
}
mount_count() { "${HDC[@]}" shell "grep -c 'oh-adapter-runtime.jar ' /proc/self/mountinfo" | tr -d '\r'; }

case "${1:-}" in
status)
  echo "effective (shell)    : $(sh_sha "$TARGET")"
  echo "effective (appspawnx): $(appspawnx_sha)"
  echo "mount layers         : $(mount_count)"
  "${HDC[@]}" shell "grep 'oh-adapter-runtime.jar ' /proc/self/mountinfo" | tr -d '\r'
  ;;
deploy)
  LOCAL="$2"; EXPECT="$3"; TAG="$4"; RC="$5"
  mkdir -p "$RC"
  # 0. local file identity
  GOT=$(shasum -a 256 "$LOCAL" | cut -d' ' -f1)
  [ "$GOT" = "$EXPECT" ] || { echo "LOCAL SHA mismatch: $GOT != $EXPECT" >&2; exit 3; }
  # 1. baseline = current effective (top of stack)
  BASE=$(sh_sha "$TARGET"); BASE_AX=$(appspawnx_sha)
  echo "baseline effective=$BASE appspawnx=$BASE_AX layers=$(mount_count)"
  [ "$BASE" = "$BASE_AX" ] || { echo "baseline shell/appspawnx disagree; abort" >&2; exit 4; }
  # 2. backup baseline jar
  "${HDC[@]}" file recv "$TARGET" "$RC/baseline.jar" >/dev/null
  BK=$(shasum -a 256 "$RC/baseline.jar" | cut -d' ' -f1)
  [ "$BK" = "$BASE" ] || { echo "backup SHA mismatch $BK != $BASE" >&2; exit 5; }
  # 3. push new jar
  REMOTE="/data/local/tmp/$TAG"
  "${HDC[@]}" shell "mkdir -p '$REMOTE'"
  "${HDC[@]}" file send "$LOCAL" "$REMOTE/oh-adapter-runtime.jar" >/dev/null
  PUSHED=$(sh_sha "$REMOTE/oh-adapter-runtime.jar")
  [ "$PUSHED" = "$EXPECT" ] || { echo "pushed SHA mismatch $PUSHED != $EXPECT" >&2; exit 6; }
  # 4. label + bind-mount on top
  "${HDC[@]}" shell "chmod 0644 '$REMOTE/oh-adapter-runtime.jar'; chcon u:object_r:system_file:s0 '$REMOTE/oh-adapter-runtime.jar'; mount --bind '$REMOTE/oh-adapter-runtime.jar' '$TARGET'"
  # 5. verify both views
  NEW=$(sh_sha "$TARGET"); NEW_AX=$(appspawnx_sha)
  echo "after mount effective=$NEW appspawnx=$NEW_AX layers=$(mount_count)"
  if [ "$NEW" != "$EXPECT" ] || [ "$NEW_AX" != "$EXPECT" ]; then
    echo "VERIFY FAILED -> auto rollback" >&2
    "${HDC[@]}" shell "umount '$TARGET'" || true
    exit 7
  fi
  # 6. receipt
  python3 - "$RC" "$SERIAL" "$TARGET" "$REMOTE" "$BASE" "$EXPECT" "$LOCAL" <<'PY'
import json,sys,subprocess
rc,serial,target,remote,base,expect,local=sys.argv[1:8]
boot=subprocess.run(["hdc","-t",serial,"shell","cat /proc/sys/kernel/random/boot_id"],capture_output=True,text=True).stdout.strip()
json.dump({"serial":serial,"boot_id":boot,"target":target,"remote_source":remote+"/oh-adapter-runtime.jar",
           "baseline_sha256":base,"deployed_sha256":expect,"local_source":local,
           "rollback":"hdc -t %s shell \"umount %s\"; expect sha=%s"%(serial,target,base)},
          open(rc+"/receipt.json","w"),indent=2)
print("receipt ->",rc+"/receipt.json")
PY
  echo "DEPLOY OK: $TARGET now $EXPECT (baseline $BASE preserved for rollback)"
  ;;
rollback)
  RC="$2"
  BASE=$(python3 -c "import json;print(json.load(open('$RC/receipt.json'))['baseline_sha256'])")
  "${HDC[@]}" shell "umount '$TARGET'"
  NOW=$(sh_sha "$TARGET"); NOW_AX=$(appspawnx_sha)
  echo "after rollback effective=$NOW appspawnx=$NOW_AX (baseline=$BASE) layers=$(mount_count)"
  [ "$NOW" = "$BASE" ] && [ "$NOW_AX" = "$BASE" ] && echo "ROLLBACK OK" || { echo "ROLLBACK MISMATCH" >&2; exit 8; }
  ;;
*)
  echo "usage: $0 {status|deploy <jar> <sha> <tag> <receipt_dir>|rollback <receipt_dir>}" >&2; exit 2;;
esac
