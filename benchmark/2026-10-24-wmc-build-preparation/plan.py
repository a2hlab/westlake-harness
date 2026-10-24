#!/usr/bin/env python3
"""Print a pinned, non-executing WMC baseline build plan. Never runs tools."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OBJECT_SHA = 'f91b354ffa408fed7ff3002e1ed24a786b65621fd9b985c37db9b0fab461b8ed'
BRIDGE_SHA = 'b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4'
OBJECT_SUFFIX = '/out-ability38/native-policy/oh_window_manager_client.o'


def load_locked():
    pins = json.loads((HERE / 'plan-input-pins.json').read_text())
    for name, expected in pins.items():
        path = HERE / name
        if path.parent != HERE or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('plan input pin mismatch: ' + name)
    return json.loads((HERE / 'recorded-commands.json').read_text())


def plan():
    recorded = load_locked()
    compile_argv = list(recorded['compile'])
    # Map only the two proven producer roots into a fresh, closed staging tree.
    # Preserve all option ordering and prefix-map RHS values.
    compile_argv = [x.replace('$HISTORICAL_ROOT_0', '$STAGED_INPUTS')
                    .replace('$HISTORICAL_ROOT_1', '$STAGED_INPUTS') for x in compile_argv]
    compile_argv[compile_argv.index('-o') + 1] = '$OUT/oh_window_manager_client.o'
    compile_argv[compile_argv.index('-MF') + 1] = '$OUT/oh_window_manager_client.o.d'
    control = [x.replace('$ORB_WS', '$STAGED_INPUTS') for x in recorded['link']]
    control[control.index('-o') + 1] = '$OUT/bridge-original-object.so'
    positions = [i for i, x in enumerate(control) if x.endswith(OBJECT_SUFFIX)]
    if len(positions) != 1:
        raise ValueError('WMC must occur exactly once in recorded link')
    relink = list(control)
    relink[positions[0]] = '$OUT/oh_window_manager_client.o'
    relink[relink.index('-o') + 1] = '$OUT/bridge-recompiled-wmc.so'
    def step(name, argv, output, expected):
        return {'name': name, 'argv': argv, 'output': output, 'expected_sha256': expected,
                'required_logs': ['$OUT/raw/' + name + suffix for suffix in
                                  ('.argv.json', '.stdout', '.stderr', '.rc')]}
    return {
        'status': 'PLAN_ONLY_NOT_EXECUTION_READY', 'executes_commands': False,
        'candidate_source': None, 'candidate_support': False,
        'steps': [step('01-link-original-object', control, '$OUT/bridge-original-object.so', BRIDGE_SHA),
                  step('02-compile-original-wmc', compile_argv, '$OUT/oh_window_manager_client.o', OBJECT_SHA),
                  step('03-link-recompiled-wmc', relink, '$OUT/bridge-recompiled-wmc.so', BRIDGE_SHA)],
        'host_split': {'compile': 'original Linux clang++ driver; archived clang-15 bytes; launcher alias/resource closure still to stage',
                       'link': 'exact T29 macOS clang++ driver and ld.lld; no compiler substitution assumed'},
        'blocked_execution_requirements': [
            'Stage and rehash all recorded explicit inputs; do not overwrite historical trees.',
            'Resolve nine Ability38 header snapshot-to-original dependency bindings or explicitly review their use before baseline reproduction.',
            'Close sysroot/resource/system-header inputs omitted by original -MMD and host dynamic-tool dependencies; no complete SDK closure claimed.',
            'Review original working directory / relative includes and staging prefix-map effects; do not assume path remapping byte-neutral.'
        ],
        'future_execution_policy': [
            'OUT must be new, exclusive, and outside all frozen input trees; no in-place output.',
            'Run existing frozen check before compilation, preserve its actual checked count.',
            'Pin all staged inputs before and after; never use unpinned include fallbacks.',
            'Before each subprocess write exact argv and open persistent stdout/stderr streams; always record rc, including exceptions/timeouts.',
            'Any rc or object/ELF full-SHA mismatch stops; no fallback to historical object for the recompiled step.',
            'Compare full ABI/DT_NEEDED/JNI records only after exact baseline; candidate changes are out of this plan.',
            'Do not execute this plan through a shell with unresolved aliases; no device, VM or network actions.'
        ]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()  # --execute and unknown arguments are deliberately rejected.
    print(json.dumps(plan(), indent=2))


if __name__ == '__main__':
    main()
