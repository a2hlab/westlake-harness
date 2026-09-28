#!/usr/bin/env bash

# Minimal source-membership oracle: one owner, five non-quarantined system-side
# sources, and no guest/runtime denylist source.
bld bionic_compat "-nostdinc++" \
    $BC_SRC/system_properties.cpp \
    $BC_SRC/malloc_compat.cpp \
    $BC_SRC/fdsan_stubs.cpp \
    $BC_SRC/liblog_android_supplement.cpp \
    $BC_SRC/sync_builtins.c
