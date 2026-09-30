"""N1: bind the bounded source/DEX scanner to a newly built package."""

from pathlib import Path
import sys

from native_gate_common import read_json, verified_file


SCANNER = Path(__file__).resolve().parents[2] / "benchmark/2026-09-29-static-wall-prediction"


def check(package, inputs, root):
    sys.path.insert(0, str(SCANNER))
    from scan_native_initialization import scan
    from rules_native_initialization import Source

    config = inputs["initialization"]
    manifest_path = verified_file(root, config["manifest"])
    package.artifact(config["dex_artifact"])
    manifest = read_json(manifest_path)
    dex_path = verified_file(manifest_path.parent, manifest["dex"])
    if read_json(dex_path).get("jar_sha256") != config["dex_artifact"]["sha256"]:
        raise ValueError("DEX initialization evidence does not bind the packaged JAR")
    profiles = manifest["profiles"]
    if not profiles or {profile["rule"] for profile in profiles} != {"namespace", "jni-order"}:
        raise ValueError("N1 requires namespace and JNI-order profiles")
    names = [profile["name"] for profile in profiles]
    if len(names) != len(set(names)):
        raise ValueError("duplicate initialization profile")
    for profile in profiles:
        identity = profile["identity"]
        if identity["manifest_sha256"] != package.sha256:
            raise ValueError("historical profile does not bind candidate package: " + profile["name"])
        package.native_artifact(dict(path=identity["artifact"], sha256=identity["artifact_sha256"]))
        if profile["rule"] == "namespace":
            entry = manifest["sources"][profile["source"]]
            source = verified_file(manifest_path.parent, entry)
            if not Source(profile["source"], source.read_text()).functions:
                raise ValueError("namespace source contains no function to inspect")
    report = scan(manifest_path)
    findings = []
    for profile in report["profiles"]:
        for kind in ("findings", "unknown", "unresolved_calls"):
            for detail in profile.get(kind, []):
                findings.append(dict(profile=profile["profile"], kind=kind, detail=detail))
    return findings, dict(scanner=report, dex_artifact=config["dex_artifact"],
                          scope="bounded build-attested source/DEX order; not source-to-binary equivalence")
