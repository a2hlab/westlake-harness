#!/usr/bin/env bash
# Canned reproduction for sweep_bind_deploy: off-board self-test + a synthetic dry-run. No board.
set -e
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
echo "### 1. self-test (pure logic)"
bash "$HERE/sweep_bind_deploy.sh" --self-test
echo "### 2. synthetic dry-run (prints plan, touches no board)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
printf '{"runtime_files":{"/system/android/framework/oh-adapter-runtime.jar":"aa"},"boot_files":{"/system/android/framework/adapter-mainline-stubs.jar":"bb"}}' > "$tmp/expected.json"
: > "$tmp/rt.jar"; : > "$tmp/stubs.jar"
bash "$HERE/sweep_bind_deploy.sh" --dry-run --serial DEADBEEF00000000000000000000DEAD --lane cc-t3 \
  --bind "$tmp/rt.jar:/system/android/framework/oh-adapter-runtime.jar" \
  --bind "$tmp/stubs.jar:/system/android/framework/adapter-mainline-stubs.jar" \
  --expected "$tmp/expected.json" --keys aegis,anki \
  --rollback-runtime-fp 73ecf422dba2 --rollback-boot-fp 0876029078e2 --out "$tmp/out"
echo "### replay OK"
