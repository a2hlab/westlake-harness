import hashlib
import json

ENVELOPE = {"issue_id", "disposition", "exception"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def finding(row):
    return {key: value for key, value in row.items() if key not in ENVELOPE}


def issue_id(gate, row, manifest, inputs):
    bound = dict(gate=gate, package_manifest_sha256=manifest, inputs_sha256=inputs, finding=finding(row))
    return hashlib.sha256(canonical(bound).encode()).hexdigest()


def differences(old, new, path=""):
    rows = []
    if isinstance(old, dict) and isinstance(new, dict):
        for key in sorted(old.keys() | new.keys()):
            field = path + "/" + key
            if key not in old or key not in new:
                rows.append(dict(path=field, old_present=key in old, new_present=key in new, old=old.get(key), new=new.get(key)))
            else:
                rows.extend(differences(old[key], new[key], field))
    elif isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            rows.append(dict(path=path + "/length", old=len(old), new=len(new)))
        for index, (before, after) in enumerate(zip(old, new)):
            rows.extend(differences(before, after, path + "/" + str(index)))
    elif canonical(old) != canonical(new):
        rows.append(dict(path=path, old=old, new=new))
    return rows


def field_proof(old, new, name):
    before = old.get("detail", old)
    after = new.get("detail", new)
    if name in ["profile", "kind"]:
        before, after = old, new
    segments = name.split(".")
    for segment in segments:
        before = before.get(segment) if isinstance(before, dict) else None
        after = after.get(segment) if isinstance(after, dict) else None
    return dict(old=before, new=after, equal=canonical(before) == canonical(after),
        interpretation="Compare actual field; missing N2 function/evidence is not invented evidence")
