#!/usr/bin/env bash

# Single-variable mutant of ../positive/build.sh: the old signal box is made
# producer-reachable.  The oracle must reject this exact addition.
bld bionic_compat "-nostdinc++" \
    $BC_SRC/system_properties.cpp \
    $BC_SRC/malloc_compat.cpp \
    $BC_SRC/fdsan_stubs.cpp \
    $BC_SRC/liblog_android_supplement.cpp \
    $BC_SRC/sync_builtins.c \
    $BC_SRC/unity_signal_box.c
