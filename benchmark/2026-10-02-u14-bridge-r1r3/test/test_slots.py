#!/usr/bin/env python3
"""Host test of the R3 / M1 process-published slot code, compiled from the patched sources themselves.

    test_slots.py <generation dir> [<generation dir> ...]

From each generation's patched window-jni/oh_window_manager_client.cpp the first anonymous namespace (publish /
read / acquire / unpublish) is cut out verbatim and compiled on the host with stubs for OH_BR_IPC_SCOPE and a
stand-in RSSurfaceNode. A driver then replays the multi-window case of M1 (session 702 published, then 703) and the
single-window case, reading back the way the other bridge copy does (process environment only), and prints what
each lookup returns. Expected:
  R3 only (846-faithful): single window -> node of that session; two windows -> 703 resolves, 702 does NOT (V1 slot)
  R3 + M1:               every published session resolves to its own node and window; destroy removes only its own
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

DRIVER = r'''
#include <cstdio>
int main() {
    auto a = std::make_shared<OHOS::Rosen::RSSurfaceNode>(); a->id = 702;
    auto b = std::make_shared<OHOS::Rosen::RSSurfaceNode>(); b->id = 703;
    int wa = 0, wb = 0;
    publishProcessWindowTarget(702, &wa, a);
    auto s1 = acquireProcessPublishedSurface(702);
    std::printf("single: 702 node=%d window_ok=%d\n", s1 ? s1->id : -1, readProcessWindowTarget(702) == &wa);
    publishProcessWindowTarget(703, &wb, b);
    auto n702 = acquireProcessPublishedSurface(702), n703 = acquireProcessPublishedSurface(703);
    std::printf("two: 702 node=%d window_ok=%d | 703 node=%d window_ok=%d\n",
                n702 ? n702->id : -1, readProcessWindowTarget(702) == &wa,
                n703 ? n703->id : -1, readProcessWindowTarget(703) == &wb);
    unpublishProcessWindowTarget(702);
    auto m702 = acquireProcessPublishedSurface(702), m703 = acquireProcessPublishedSurface(703);
    std::printf("after destroy 702: 702 node=%d | 703 node=%d window_ok=%d\n",
                m702 ? m702->id : -1, m703 ? m703->id : -1, readProcessWindowTarget(703) == &wb);
    std::printf("use_count(703)=%ld (b + holder + n703 + m703)\n", (long)b.use_count());
    return 0;
}
'''

PRELUDE = r'''
#include <atomic>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <mutex>
#include <vector>
#define OH_BR_IPC_SCOPE(...) do {} while (0)
namespace OHOS { namespace Rosen { struct RSSurfaceNode { int id = 0; }; } }
'''


def main():
    for gen in sys.argv[1:]:
        src = (Path(gen) / 'window-jni/oh_window_manager_client.cpp').read_text(encoding='utf-8-sig')
        start = src.index('\nnamespace {\n')
        end = src.index('\n}  // namespace\n', start) + len('\n}  // namespace\n')
        block = src[start:end]
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / 't.cpp'
            c.write_text(PRELUDE + block.replace('namespace {', 'namespace slots {', 1) +
                         '\nusing namespace slots;\n' + DRIVER)
            exe = Path(d) / 't'
            r = subprocess.run(['clang++', '-std=c++17', '-Wall', '-o', str(exe), str(c)], capture_output=True, text=True)
            if r.returncode:
                print(gen, 'COMPILE FAILED\n', r.stderr[:2000])
                continue
            out = subprocess.run([str(exe)], capture_output=True, text=True).stdout
        print(f'== {Path(gen).name}\n{out}', end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
