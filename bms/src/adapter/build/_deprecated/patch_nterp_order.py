#!/usr/bin/env python3
"""Patch framework/appspawn-x/bionic_compat/src/art_runtime_stubs.cpp so that
ExecuteNterpImpl / ExecuteNterpWithClinitImpl are placed AT
artNterpAsmInstructionStart (matching AOSP arm/nterp.S layout), instead of
being emitted as separate weak stubs that land after artNterpAsmInstructionEnd.

Rationale:
  Current libart.so has
    artNterpAsmInstructionStart = 0x00226424
    artNterpAsmInstructionEnd   = 0x0022e424
    ExecuteNterpImpl            = 0x0022e9ac   <- AFTER End, wrong order
  In real ART, ExecuteNterpImpl sits at the beginning of the opcode-handler
  table, i.e. inside [Start, End).  This patch puts ExecuteNterpImpl and
  ExecuteNterpWithClinitImpl as labels right at artNterpAsmInstructionStart.
"""
import sys, os, re

path = os.environ.get(
    'STUBS_PATH',
    os.path.expanduser('~/adapter/framework/appspawn-x/bionic_compat/src/art_runtime_stubs.cpp'),
)

with open(path, 'r') as f:
    src = f.read()

old_asm = (
    '// nterp interpreter table spacing (NOT in .S file)\n'
    '__asm__(\n'
    '    ".global artNterpAsmInstructionStart\\n"\n'
    '    ".type artNterpAsmInstructionStart, %function\\n"\n'
    '    "artNterpAsmInstructionStart:\\n"\n'
    '    ".space 32768, 0\\n"\n'
    '    ".global artNterpAsmInstructionEnd\\n"\n'
    '    ".type artNterpAsmInstructionEnd, %function\\n"\n'
    '    "artNterpAsmInstructionEnd:\\n"\n'
    '    "bx lr\\n"\n'
    ');'
)

new_asm = (
    '// nterp interpreter table spacing (NOT in .S file)\n'
    '// Layout matches AOSP art/runtime/interpreter/mterp/armng/main.S:\n'
    '//   ExecuteNterpImpl == ExecuteNterpWithClinitImpl == artNterpAsmInstructionStart\n'
    '//   [ 256 opcode handlers * 128 bytes = 32768 bytes ]\n'
    '//   artNterpAsmInstructionEnd\n'
    '// CheckNterpAsmConstants() requires (End - Start) == 256 * 128, and\n'
    '// NterpMethodHeader is derived from ExecuteNterpImpl assuming it sits\n'
    '// inside [Start, End). Interpreter-only mode never calls this entry,\n'
    '// so a single "bx lr" at the head + trailing padding is safe.\n'
    '__asm__(\n'
    '    ".global ExecuteNterpImpl\\n"\n'
    '    ".type ExecuteNterpImpl, %function\\n"\n'
    '    ".global ExecuteNterpWithClinitImpl\\n"\n'
    '    ".type ExecuteNterpWithClinitImpl, %function\\n"\n'
    '    ".global artNterpAsmInstructionStart\\n"\n'
    '    ".type artNterpAsmInstructionStart, %function\\n"\n'
    '    "ExecuteNterpImpl:\\n"\n'
    '    "ExecuteNterpWithClinitImpl:\\n"\n'
    '    "artNterpAsmInstructionStart:\\n"\n'
    '    "    bx lr\\n"\n'
    '    ".space 32764, 0\\n"\n'
    '    ".global artNterpAsmInstructionEnd\\n"\n'
    '    ".type artNterpAsmInstructionEnd, %function\\n"\n'
    '    "artNterpAsmInstructionEnd:\\n"\n'
    '    "    bx lr\\n"\n'
    ');'
)

if old_asm not in src:
    sys.exit('FAIL: old asm block not found in ' + path)
# Replace only the second (active) occurrence — the first one is inside the #if 0 disabled block.
# We do that by locating all occurrences and replacing the last one.
idx = src.rfind(old_asm)
src = src[:idx] + new_asm + src[idx + len(old_asm):]

old_qs = (
    '// --- Interpreter/helper entrypoints ---\n'
    'QUICK_STUB(ExecuteNterpImpl)\n'
    'QUICK_STUB(ExecuteNterpWithClinitImpl)\n'
    'QUICK_STUB(ExecuteSwitchImplAsm)\n'
    'QUICK_STUB(NterpGetInstanceFieldOffset)'
)
new_qs = (
    '// --- Interpreter/helper entrypoints ---\n'
    '// ExecuteNterpImpl / ExecuteNterpWithClinitImpl are provided as strong labels\n'
    '// at artNterpAsmInstructionStart (see asm block above); do not redefine here.\n'
    'QUICK_STUB(ExecuteSwitchImplAsm)\n'
    'QUICK_STUB(NterpGetInstanceFieldOffset)'
)
if old_qs not in src:
    sys.exit('FAIL: active QUICK_STUB block not found')
idx = src.rfind(old_qs)
src = src[:idx] + new_qs + src[idx + len(old_qs):]

with open(path, 'w') as f:
    f.write(src)

print('patched OK:', path)
