def require_board_local_identity(baseline, expected, targets, digest, changed_targets):
    for target in targets:
        if baseline.get(target) != digest or expected.get(target) != digest or target in changed_targets:
            raise ValueError("Board-local service was changed or misidentified")


def require_exact_reference_delta(before, after, targets, old_sha, new_sha):
    changed = {target for target in before.keys() | after.keys() if before.get(target) != after.get(target)}
    if changed != set(targets) or any(before[target] != old_sha or after[target] != new_sha for target in targets):
        raise ValueError("Unexpected reference identity delta")
