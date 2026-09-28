#!/bin/bash
# Fetch the Rust 1.94.0 x86_64-linux archives the manifest pins, from a mirror first, then the
# official server with resume; verify each against inputs/rust-compiler194-linux-x64/index.json.
cd "$HOME/a2hlab/downloads" || exit 1
for f in rustc-1.94.0-x86_64-unknown-linux-gnu.tar.xz cargo-1.94.0-x86_64-unknown-linux-gnu.tar.xz rust-std-1.94.0-x86_64-unknown-linux-gnu.tar.xz; do
  want=$(python3 -c "import json,sys;print(next(c['sha256'] for c in json.load(open('$HOME/a2hlab/ws/inputs/rust-compiler194-linux-x64/index.json'))['components'] if c['archive']=='$f'))")
  [ -s "$f" ] && [ "$(sha256sum "$f" | cut -c1-64)" = "$want" ] && { echo "OK   $f (already)"; continue; }
  rm -f "$f"
  for u in "https://mirrors.ustc.edu.cn/rust-static/dist/2026-03-05/$f" "https://rsproxy.cn/dist/2026-03-05/$f"; do
    curl -fsSL --retry 3 --max-time 900 -o "$f" "$u" && [ "$(sha256sum "$f" | cut -c1-64)" = "$want" ] && { echo "OK   $f from ${u%%/dist*}"; break; }
    rm -f "$f"
  done
  [ -s "$f" ] && continue
  for i in 1 2 3 4 5 6 7 8; do curl -fsSL -C - --max-time 600 -o "$f" "https://static.rust-lang.org/dist/2026-03-05/$f" && break; done
  [ "$(sha256sum "$f" | cut -c1-64)" = "$want" ] && echo "OK   $f from static.rust-lang.org" || echo "BAD  $f"
done
