#!/usr/bin/env bash
set -u

HDC="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc"
TARGET="${1:-5583f5be00000000000000000323012c}"
ROOT="/opt/Bridge"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$ROOT/evidence/runs/fn01-fn03-clean-launcher-${TARGET:0:4}-$TS"
RAW="$RUN_DIR/raw"
mkdir -p "$RAW"

PKGS=(
  com.a2hlab.bridge.fn0103.alpha
  com.a2hlab.bridge.fn0103.beta
  com.a2hlab.bridge.fn0103.gamma
)

APKS=(
  "$ROOT/APKS/Fn01F03-ProbeAlpha/dist/fn0103-probe-alpha.apk"
  "$ROOT/APKS/Fn01F03-ProbeBeta/dist/fn0103-probe-beta.apk"
  "$ROOT/APKS/Fn01F03-ProbeGamma/dist/fn0103-probe-gamma.apk"
)

names=(alpha beta gamma)

run_hdc() {
  local out="$1"
  shift
  "$HDC" -t "$TARGET" "$@" >"$RAW/$out" 2>&1
  printf "%s rc=%s\n" "$*" "$?" >>"$RUN_DIR/commands.log"
}

cap_state() {
  local tag="$1"
  run_hdc "$tag-ams.txt" shell aa dump -l
  run_hdc "$tag-wms.txt" shell hidumper -s WindowManagerService -a -w
  run_hdc "$tag-ps.txt" shell ps -ef
  run_hdc "$tag-screenshot.jpeg" shell snapshot_display -f "/data/local/tmp/$tag.jpeg"
  run_hdc "$tag-screenshot-pull.txt" file recv "/data/local/tmp/$tag.jpeg" "$RAW/$tag.jpeg"
}

{
  echo "target=$TARGET"
  echo "run_dir=$RUN_DIR"
  echo "hdc=$HDC"
  date -u
} >"$RUN_DIR/METADATA.txt"

run_hdc "targets.txt" list targets
run_hdc "setenforce.txt" shell setenforce 0
run_hdc "getenforce.txt" shell getenforce

for pkg in "${PKGS[@]}"; do
  run_hdc "uninstall-$pkg.txt" shell bm uninstall -n "$pkg"
done

for i in "${!APKS[@]}"; do
  remote="/data/local/tmp/fn0103-${names[$i]}-$TS.apk"
  run_hdc "send-${names[$i]}.txt" file send "${APKS[$i]}" "$remote"
  run_hdc "install-${names[$i]}.txt" shell bm install -p "$remote"
done

for pkg in "${PKGS[@]}"; do
  run_hdc "dump-$pkg.txt" shell bm dump -n "$pkg"
done

run_hdc "input-home.txt" shell uinput -T -d 0 -i 1 -m 1
sleep 2
cap_state "00-home-before"
run_hdc "hilog-clear.txt" shell hilog -r

clicks=(
  "alpha 738 184"
  "beta 1010 184"
  "gamma 190 470"
)

for click in "${clicks[@]}"; do
  set -- $click
  name="$1"
  x="$2"
  y="$3"
  run_hdc "$name-click.txt" shell uinput -T -d "$x" "$y" -u "$x" "$y"
  sleep 13
  cap_state "$name-after-click"
  run_hdc "$name-hilog-full.txt" shell hilog -x
  run_hdc "$name-home.txt" shell uinput -T -d 0 -i 1 -m 1
  sleep 2
  run_hdc "$name-home-screenshot.jpeg" shell snapshot_display -f "/data/local/tmp/$name-home.jpeg"
  run_hdc "$name-home-screenshot-pull.txt" file recv "/data/local/tmp/$name-home.jpeg" "$RAW/$name-home.jpeg"
  run_hdc "$name-hilog-clear.txt" shell hilog -r
done

python3 - "$RUN_DIR" <<'PY'
import pathlib
import sys

run = pathlib.Path(sys.argv[1])
raw = run / "raw"
pkgs = [
    ("alpha", "com.a2hlab.bridge.fn0103.alpha", "Probe Alpha"),
    ("beta", "com.a2hlab.bridge.fn0103.beta", "Probe Beta"),
    ("gamma", "com.a2hlab.bridge.fn0103.gamma", "Probe Gamma"),
]

def text(name):
    p = raw / name
    return p.read_text(errors="replace") if p.exists() else ""

rows = []
for name, pkg, label in pkgs:
    dump = text(f"dump-{pkg}.txt")
    ams = text(f"{name}-after-click-ams.txt")
    wms = text(f"{name}-after-click-wms.txt")
    ps = text(f"{name}-after-click-ps.txt")
    hilog = text(f"{name}-hilog-full.txt")
    install = text(f"install-{name}.txt")
    rows.append({
        "name": name,
        "pkg": pkg,
        "install_ok": (
            ("successfully" in install.lower() or "success" in install.lower())
            and "[fail]" not in install.lower()
            and "error" not in install.lower()
        ),
        "bms_pkg": pkg in dump,
        "bms_label": label in dump,
        "ams_seen": pkg in ams,
        "wms_seen": pkg in wms,
        "ps_seen": pkg in ps,
        "hilog_seen": pkg in hilog,
    })

passed = all(r["install_ok"] and r["bms_pkg"] and r["bms_label"] and r["ams_seen"] and r["wms_seen"] and r["ps_seen"] for r in rows)

lines = [
    "# Fn01-Fn03 Clean Launcher 5583 Verdict",
    "",
    f"Run dir: `{run}`",
    "",
    "| app | install | bms package | bms label | AMS after click | WMS after click | process after click | hilog package | verdict |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---|",
]
for r in rows:
    ok = r["install_ok"] and r["bms_pkg"] and r["bms_label"] and r["ams_seen"] and r["wms_seen"] and r["ps_seen"]
    lines.append(
        f"| {r['name']} | {r['install_ok']} | {r['bms_pkg']} | {r['bms_label']} | "
        f"{r['ams_seen']} | {r['wms_seen']} | {r['ps_seen']} | {r['hilog_seen']} | {'PASS' if ok else 'FAIL'} |"
    )
lines.extend([
    "",
    f"Overall: `{'PASS' if passed else 'FAIL'}`",
    "",
    "This launcher-only check does not use `aa start` as success proof.",
])
(run / "VERDICT.md").write_text("\n".join(lines) + "\n")
print(run)
sys.exit(0 if passed else 2)
PY
