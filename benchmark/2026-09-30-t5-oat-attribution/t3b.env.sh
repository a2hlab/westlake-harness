# Source BEFORE the T3b build in the build owner's isolated workspace.
# Evidence: build-flags.json and libart-*.asm, R155 libart SHA 59e1bb45...
# This file sets environment only; it does not start a build or touch a board.
export ART_USE_READ_BARRIER=false
export ART_DEFAULT_GC_TYPE=CMS
export ART_USE_GENERATIONAL_CC=false
export ART_HEAP_POISONING=false
export ART_TEST_DEBUG_GC=false
# ART_READ_BARRIER_TYPE is ignored with read barriers disabled. Do not claim
# its original environment value was recovered.
# Select release dex2oat64 and libart.so targets. Do not set arbitrary NDEBUG
# flags globally or substitute the debug dex2oatd64/libartd.so variants.
# TLAB is derived by build/art.go; there is no direct ART_USE_TLAB env knob.
# Optimization/C++ interpreter/sanitizers remain unknown: archive their actual
# build values instead of silently adopting upstream defaults as R155 facts.
