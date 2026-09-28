#!/usr/bin/env python3
"""Fail-closed M04 source-to-producer reachability oracle.

This gate intentionally proves only source membership in one shell producer.
It does not parse ELF files, approve runtime semantics, or authorize product
activation.  Comments are removed before references are counted so a denylist
name in documentation cannot be mistaken for executable build membership.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List


EXPECTED_NON_QUARANTINED_SOURCES = (
    "system_properties.cpp",
    "malloc_compat.cpp",
    "fdsan_stubs.cpp",
    "liblog_android_supplement.cpp",
    "sync_builtins.c",
)

# These are source-level quarantine rules, not judgments that every function in
# each file is wrong.  A production producer must not make the whole file
# reachable without a later, narrower review and an explicit policy revision.
DENYLIST = {
    "art_runtime_stubs.cpp": "broad_runtime_stub_and_global_interposition",
    "art_quick_entrypoints_arm64.S": "broad_runtime_noop_entrypoints",
    "bionic_tls_abi.c": "constructor_direct_tp_and_global_guard_rewrite",
    "bionic_tls_abi.h": "fixed_tp_slot_write_contract_without_musl_ownership",
    "misc_compat.cpp": "fixed_entropy_fallback_and_musl_global_guard_rewrite",
    "palette_system_stub.c": "unconditional_fake_success",
    "unity_libc_stubs.c": "unity_specific_layout_and_stdio_overlay",
    "unity_pthread_box.c": "global_pthread_interposition_and_unowned_boxing",
    "unity_signal_box.c": "title_allowlist_raw_signal_and_pretend_success",
}

SOURCE_TOKEN = re.compile(
    r"(?:\$BC_SRC|\$\{BC_SRC\})/"
    r"(?P<name>[A-Za-z0-9_.+-]+\.(?:cpp|cc|c|S))"
    r"(?![A-Za-z0-9_.+-])"
)


class InputError(Exception):
    """The oracle input itself is invalid or escaped the project root."""


def strip_shell_comment(line: str) -> str:
    """Remove an unquoted shell comment while preserving quoted '#'."""

    quote = ""
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote != "'":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = ""
            continue
        if char in ("'", '"'):
            quote = char
            continue
        if char == "#" and (index == 0 or line[index - 1].isspace()):
            return line[:index]
    return line


def logical_shell_lines(text: str) -> List[str]:
    """Return executable logical lines with comments and continuations folded."""

    commands: List[str] = []
    pending = ""
    for physical in text.splitlines():
        executable = strip_shell_comment(physical).rstrip()
        if not executable and not pending:
            continue
        continued = executable.endswith("\\")
        if continued:
            executable = executable[:-1].rstrip()
        pending = f"{pending} {executable}".strip()
        if not continued and pending:
            commands.append(pending)
            pending = ""
    if pending:
        commands.append(pending)
    return commands


def count_token(text: str, token: str) -> int:
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_.+-]){re.escape(token)}"
        rf"(?![A-Za-z0-9_.+-])"
    )
    return len(pattern.findall(text))


def normalized_input(project_root: Path, recipe: Path) -> tuple[Path, Path]:
    if project_root.is_symlink():
        raise InputError(f"project root is a symlink: {project_root}")
    root = project_root.resolve(strict=True)
    if not root.is_dir():
        raise InputError(f"project root is not a directory: {root}")
    if recipe.is_symlink():
        raise InputError(f"recipe is a symlink: {recipe}")
    resolved_recipe = recipe.resolve(strict=True)
    if not resolved_recipe.is_file():
        raise InputError(f"recipe is not a regular file: {resolved_recipe}")
    try:
        resolved_recipe.relative_to(root)
    except ValueError as error:
        raise InputError(f"recipe escaped project root: {resolved_recipe}") from error
    return root, resolved_recipe


def scan(project_root: Path, recipe: Path) -> int:
    root, resolved_recipe = normalized_input(project_root, recipe)
    recipe_name = resolved_recipe.relative_to(root).as_posix()
    commands = logical_shell_lines(resolved_recipe.read_text(encoding="utf-8"))
    active_text = "\n".join(commands)

    bionic_commands = [
        command for command in commands
        if re.match(r"^bld\s+bionic_compat(?:\s|$)", command)
    ]
    bionic_text = "\n".join(bionic_commands)

    expected_counts = {
        name: count_token(bionic_text, name)
        for name in EXPECTED_NON_QUARANTINED_SOURCES
    }
    expected_total_counts = {
        name: count_token(active_text, name)
        for name in EXPECTED_NON_QUARANTINED_SOURCES
    }
    deny_counts = {
        name: count_token(active_text, name)
        for name in DENYLIST
    }

    classified = set(EXPECTED_NON_QUARANTINED_SOURCES) | set(DENYLIST)
    unclassified = sorted({
        match.group("name")
        for command in bionic_commands
        for match in SOURCE_TOKEN.finditer(command)
        if match.group("name") not in classified
    })
    backup_commands = [command for command in commands if ".bak" in command]

    missing = sorted(name for name, count in expected_counts.items() if count == 0)
    duplicate = sorted(
        name for name, count in expected_counts.items()
        if count > 1 or expected_total_counts[name] != count
    )
    reachable_deny = sorted(name for name, count in deny_counts.items() if count > 0)

    print(f"M04_REACHABILITY recipe={recipe_name}")
    for name in EXPECTED_NON_QUARANTINED_SOURCES:
        print(
            "EXPECTED "
            f"source={name} refs={expected_counts[name]} "
            f"total_refs={expected_total_counts[name]}"
        )
    for name in sorted(DENYLIST):
        print(
            "DENY "
            f"source={name} refs={deny_counts[name]} reason={DENYLIST[name]}"
        )
    for name in unclassified:
        print(f"UNCLASSIFIED source={name}")
    print(
        "SUMMARY "
        f"bionic_commands={len(bionic_commands)} "
        f"missing={len(missing)} duplicate={len(duplicate)} "
        f"deny_reachable={len(reachable_deny)} "
        f"backup_commands={len(backup_commands)} "
        f"unclassified={len(unclassified)}"
    )

    failed = (
        len(bionic_commands) != 1
        or bool(missing)
        or bool(duplicate)
        or bool(reachable_deny)
        or bool(backup_commands)
        or bool(unclassified)
    )
    if failed:
        reasons = []
        if len(bionic_commands) != 1:
            reasons.append("producer_cardinality")
        if missing:
            reasons.append("missing_expected")
        if duplicate:
            reasons.append("duplicate_expected")
        if reachable_deny:
            reasons.append("deny_reachable")
        if backup_commands:
            reasons.append("backup_reachable")
        if unclassified:
            reasons.append("unclassified")
        print(f"M04_REACHABILITY_FAIL reasons={','.join(reasons)}")
        return 3

    print("M04_REACHABILITY_PASS")
    return 0


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--recipe", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    try:
        return scan(args.project_root, args.recipe)
    except (InputError, OSError, UnicodeError) as error:
        print(f"M04_REACHABILITY_INPUT_ERROR error={error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
