#!/bin/bash
set -eu
p=/Users/zhaoyue/workspace/hanbin_adapter/out/host-tools/dex2oat64
sha256sum "$p"
ldd "$p"
nm -C "$p" | grep 'OatHeader::kOatVersion' || true
"$p" --help 2>&1 | head -6
