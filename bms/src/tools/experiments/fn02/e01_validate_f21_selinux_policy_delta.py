#!/usr/bin/env python3
"""Validate one device-policy SELinux permission delta for Fn02 E1/F21."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


SCHEMA = "bridge.fn02.e01.f21-selinux-policy-delta.v2"
RESULT = "F21_SELINUX_POLICY_DEVICE_BASELINE_PLUS_ONE_PERMISSION_VALIDATED"
ALLOW_RE = re.compile(
    r"^\(allow ([^ ]+) ([^ ]+) \(([^ ]+) \(([^)]*)\)\)\)$"
)


class ValidationError(ValueError):
    """The policy inputs do not satisfy the frozen one-permission contract."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_policy(
    path: Path,
) -> tuple[list[str], list[str], dict[tuple[str, str, str], set[str]]]:
    other_lines: list[str] = []
    attribute_lines: list[str] = []
    allows: dict[tuple[str, str, str], set[str]] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("(typeattribute ") or line.startswith("(typeattributeset "):
            attribute_lines.append(line)
            continue
        match = ALLOW_RE.fullmatch(line)
        if match is None:
            other_lines.append(line)
            continue
        key = (match.group(1), match.group(2), match.group(3))
        if key in allows:
            raise ValidationError(f"duplicate allow key in {path}: {key}")
        allows[key] = set(match.group(4).split())
    return other_lines, attribute_lines, allows


def validate_overlay(
    overlay: Path, source: str, target: str, object_class: str, permission: str
) -> None:
    expected = f"(allow {source} {target} ({object_class} ({permission})))"
    actual = [
        line.strip()
        for line in overlay.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith(";")
    ]
    if actual != [expected]:
        raise ValidationError(
            f"overlay must contain exactly {expected!r}; observed {actual!r}"
        )


def validate(
    base_cil: Path,
    roundtrip_cil: Path,
    candidate_cil: Path,
    overlay: Path,
    source: str,
    target: str,
    object_class: str,
    permission: str,
) -> dict[str, object]:
    validate_overlay(overlay, source, target, object_class, permission)
    base_other, base_attributes, base_allows = normalized_policy(base_cil)
    roundtrip_other, roundtrip_attributes, roundtrip_allows = normalized_policy(
        roundtrip_cil
    )
    candidate_other, candidate_attributes, candidate_allows = normalized_policy(
        candidate_cil
    )

    if base_other != roundtrip_other or base_allows != roundtrip_allows:
        raise ValidationError(
            "binary-to-CIL-to-binary baseline is not semantically identical"
        )
    if (
        base_cil.read_bytes() != roundtrip_cil.read_bytes()
        or base_attributes != candidate_attributes
    ):
        raise ValidationError(
            "full policy structure or candidate attributes are not identical"
        )
    if roundtrip_other != candidate_other:
        raise ValidationError("candidate changes non-allow policy semantics")
    if set(roundtrip_allows) != set(candidate_allows):
        raise ValidationError("candidate changes the set of allow rule keys")

    key = (source, target, object_class)
    if key not in roundtrip_allows:
        raise ValidationError(f"target allow key is absent from baseline: {key}")
    before = roundtrip_allows[key]
    after = candidate_allows[key]
    if permission in before:
        raise ValidationError(f"baseline already grants {permission}: {key}")

    changed = {
        rule_key: candidate_allows[rule_key] - roundtrip_allows[rule_key]
        for rule_key in roundtrip_allows
        if candidate_allows[rule_key] != roundtrip_allows[rule_key]
    }
    removed = {
        rule_key: roundtrip_allows[rule_key] - candidate_allows[rule_key]
        for rule_key in roundtrip_allows
        if candidate_allows[rule_key] != roundtrip_allows[rule_key]
    }
    if changed != {key: {permission}} or removed != {key: set()}:
        raise ValidationError(
            f"candidate delta is not exactly {key} + {permission}: "
            f"added={changed!r}, removed={removed!r}"
        )

    return {
        "schema": SCHEMA,
        "experiment_result": RESULT,
        "formal_verdict": "NONE",
        "claim_boundary": "HOST_POLICY_SEMANTIC_DELTA_ONLY_NO_DEVICE_MUTATION",
        "inputs": {
            "base_cil": {"path": str(base_cil), "sha256": sha256(base_cil)},
            "roundtrip_cil": {
                "path": str(roundtrip_cil),
                "sha256": sha256(roundtrip_cil),
            },
            "candidate_cil": {
                "path": str(candidate_cil),
                "sha256": sha256(candidate_cil),
            },
            "overlay": {"path": str(overlay), "sha256": sha256(overlay)},
        },
        "baseline_roundtrip_semantically_equal": True,
        "baseline_roundtrip_full_structure_equal": True,
        "policy_attributes_preserved": True,
        "only_delta": {
            "source": source,
            "target": target,
            "class": object_class,
            "added_permission": permission,
            "permissions_before": sorted(before),
            "permissions_after": sorted(after),
        },
        "action_verdict": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-cil", type=Path, required=True)
    parser.add_argument("--roundtrip-cil", type=Path, required=True)
    parser.add_argument("--candidate-cil", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--source", default="appspawn")
    parser.add_argument("--target", default="system_file")
    parser.add_argument("--class", dest="object_class", default="file")
    parser.add_argument("--permission", default="lock")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        receipt = validate(
            args.base_cil,
            args.roundtrip_cil,
            args.candidate_cil,
            args.overlay,
            args.source,
            args.target,
            args.object_class,
            args.permission,
        )
    except (OSError, UnicodeError, ValidationError) as error:
        print(f"E01_F21_SELINUX_POLICY_DELTA_ERROR: {error}")
        return 1

    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
