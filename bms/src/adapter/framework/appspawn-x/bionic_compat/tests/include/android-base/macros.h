#pragma once

// Test-only copy of the AOSP arraysize contract needed to compile the frozen
// zip_error.cpp reference without importing an external AOSP source tree.
#define arraysize(array) (sizeof(array) / sizeof((array)[0]))
