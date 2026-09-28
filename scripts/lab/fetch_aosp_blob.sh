#!/bin/bash
# fetch_aosp_blob.sh <aosp project path> <ref> <file in repo> <out file>
# Partial clone (no blobs) from googlesource, falling back to the TUNA AOSP mirror; then read one blob.
set -u
proj=$1 ref=$2 file=$3 out=$4
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
for base in https://android.googlesource.com https://mirrors.tuna.tsinghua.edu.cn/git/AOSP; do
  rm -rf "$work/r"; git init -q "$work/r"; cd "$work/r" || exit 1
  git remote add origin "$base/$proj"
  if timeout 900 git -c protocol.version=2 fetch -q --depth=1 --filter=blob:none origin "refs/tags/$ref:refs/tags/$ref" 2>/dev/null \
     && timeout 1800 git cat-file blob "$ref:$file" > "$out.part" 2>/dev/null && [ -s "$out.part" ]; then
    mv "$out.part" "$out"; echo "GOT $file from $base"; exit 0
  fi
  rm -f "$out.part"; cd /; echo "failed via $base"
done
exit 1
