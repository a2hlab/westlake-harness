import json
import subprocess
import sys

from prepare import HERE, MASTER, PRIVATE, WS, portable, save, sha
import generation_bundle


def main():
    root = WS / "westlake-harness-bms/benchmark/2026-10-03-u14-effective-rebind/.artifacts/common-reviewed"
    bundle, manifest, _ = generation_bundle.validate(root)
    jars = generation_bundle.bcp_members(root, bundle, manifest)
    records = []
    for label, name in [("stubs", "adapter-mainline-stubs"), ("framework", "framework")]:
        args = [sys.executable, str(MASTER / "scripts/lab/deployed_class_diff.py"), str(PRIVATE / "jars9" / (name + ".jar")),
            "--deployed", str(jars[name]), "--frozen"]
        if label == "stubs":
            classes = json.loads((MASTER / "benchmark/2026-10-03-u15-stubs-nsd/results.json").read_text())["new_classes"]
            args.extend(["--allow-add", *classes])
        raw = HERE / ".artifacts/raw" / (label + "-classes-correct-args.txt")
        raw.parent.mkdir(parents=True, exist_ok=True)
        with raw.open("w") as handle:
            result = subprocess.run(args, stdout=handle, stderr=subprocess.STDOUT)
        evidence = HERE / "evidence" / raw.name
        evidence.parent.mkdir(exist_ok=True)
        evidence.write_text(portable(raw.read_text()))
        records.append(dict(name=label, argv=portable(args), exit_code=result.returncode, raw=portable(raw),
            raw_sha256=sha(raw), evidence=str(evidence.relative_to(HERE)), evidence_sha256=sha(evidence),
            allow_scope="8 exact NSD classes only; outer approval pending" if label == "stubs" else "none; UTF8 decoding failure stays unknown"))
        print(label + " classes exit=" + str(result.returncode))
    save("static-input-checks.json", dict(status="FRESH_MAC_INPUT_CHECKS_ONLY", results=records, approvals_applied=False,
        corrected_invocation="allow-add takes one option followed by all descriptors; the initial repeated-option invocation is retained separately"))


if __name__ == "__main__":
    main()
