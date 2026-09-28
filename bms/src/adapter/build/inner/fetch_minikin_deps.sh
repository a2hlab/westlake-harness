#!/bin/bash
# fetch_minikin_deps.sh — clone AOSP source trees missing from ECS partial sync.
#
# Context: ~/aosp/ on ECS is a partial repo sync (80+ projects). The 3 source
# trees below are listed in the AOSP master manifest with groups="pdk*" so
# they were filtered out by the default repo sync. They are needed to cross-
# compile libminikin and its dependencies into out/aosp_lib/.
#
# Bypasses repo because the local repo tool tries to write to
# /etc/.repo_gitconfig.json which is root-owned (permission error).
#
# Created 2026-04-11 per CLAUDE.md single-command-recovery rule.
set -e
AOSP_ROOT="${AOSP_ROOT:-$HOME/aosp}"
MIRROR=https://mirrors.tuna.tsinghua.edu.cn/git/AOSP
BRANCH=android-14.0.0_r1

for proj in frameworks/minikin external/harfbuzz_ng external/freetype; do
    if [ -d "$AOSP_ROOT/$proj" ]; then
        echo "OK: $proj already exists"
        continue
    fi
    echo "Cloning $proj ..."
    mkdir -p "$AOSP_ROOT/$(dirname $proj)"
    git clone --depth 1 --branch $BRANCH $MIRROR/platform/$proj $AOSP_ROOT/$proj
done
