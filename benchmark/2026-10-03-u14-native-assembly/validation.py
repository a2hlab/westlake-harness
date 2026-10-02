import re


def require_single_delta(old, new, member, expected_sha):
    changed = sorted(name for name in old.keys() | new.keys() if old.get(name) != new.get(name))
    if changed != [member] or new[member] != expected_sha:
        raise ValueError("Unexpected assembly payload delta")
    return changed


def require_transaction_identity(expected, actual):
    if not re.fullmatch(r"[0-9a-f]{64}", expected or "") or expected != actual:
        raise ValueError("Explicit transaction baseline identity mismatch")


def require_empty_slots(slots):
    if len(slots) != 3 or {row["id"] for row in slots} != {"stock-host-app-ns", "icu-wall-two", "u14-jar-v1"}:
        raise ValueError("Missing held slot")
    if any(row.get("applied") is not False for row in slots):
        raise ValueError("Unreviewed slot was applied")
