VOLATILE = {"issue_id", "disposition", "exception"}


def exact_finding(finding):
    return {name: value for name, value in finding.items() if name not in VOLATILE}


def compare_new(old, new):
    old_rows = [item for item in old["gates"]["N1"]["findings"] if item.get("profile") == "u13-m1-compat-shim.cpp"]
    new_rows = [item for item in new["gates"]["N1"]["findings"] if item.get("profile") == "u13-m1-compat-shim.cpp"]
    previous = {item["detail"]["function"]: item for item in old_rows}
    current = {item["detail"]["function"]: item for item in new_rows}
    if len(old_rows) != 2 or len(new_rows) != 2 or len(previous) != 2 or previous.keys() != current.keys():
        raise ValueError("New N1 profile findings differ")
    rows = []
    for function, finding in current.items():
        prior = previous[function]
        rows.append(dict(function=function, old_issue_id=prior["issue_id"], new_issue_id=finding["issue_id"],
            equal=exact_finding(prior) == exact_finding(finding), old_finding=exact_finding(prior), new_finding=exact_finding(finding)))
    return rows
