def known_delta(member, historical):
    keys = ["target", "candidate_sha256", "deployed_sha256", "delta_sha256", "open_site_delta"]
    return any(all(member.get(key) == row.get(key) for key in keys) for row in historical)


def class_allowance(actual, reviewed):
    if not set(actual) <= set(reviewed):
        raise ValueError("Unapproved class addition")
    return sorted(set(actual))


def same_objects(old, new):
    if old != new:
        raise ValueError("Object inventory drift")
    return True
