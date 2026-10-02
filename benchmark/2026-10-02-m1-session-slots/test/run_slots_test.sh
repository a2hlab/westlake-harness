#!/bin/bash
# Host test of the per-session slot helpers. Takes the bridge window client from this repo; if it does not carry
# the M1 change yet (master: bms/src is not landed by land.py), applies ../bridge-m1.patch to a temporary copy.
# Then extracts the first anonymous namespace verbatim (no hand copy) and runs slots_test.cpp against it.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../../.." && pwd)
rel=bms/src/adapter/framework/window/jni/oh_window_manager_client.cpp
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/tree/$(dirname "$rel")"
cp "$repo/$rel" "$work/tree/$rel"
if ! grep -q 'kSessionNativeWindowEnvPrefix' "$work/tree/$rel"; then
    (cd "$work/tree" && git init -q . && git apply "$here/../bridge-m1.patch")
    echo "applied bridge-m1.patch to a copy of $rel"
fi
awk '/^namespace \{/{n++} n==1{print} n==1 && /^\}  \/\/ namespace/{exit}' "$work/tree/$rel" > "$work/extracted_namespace.inc"
grep -q 'kSessionNativeWindowEnvPrefix' "$work/extracted_namespace.inc"
c++ -std=c++17 -Wall -Wextra -Werror -Wno-unused-function -I"$work" "$here/slots_test.cpp" -o "$work/slots_test"
"$work/slots_test"
