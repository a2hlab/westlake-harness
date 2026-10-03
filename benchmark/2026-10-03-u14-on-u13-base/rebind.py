import argparse
from pathlib import Path
import subprocess

from binding import INSTALLERS, check_artifacts, check_base, check_plan
from common import HERE, PRIOR, expand, load, save, sha
import generation_bundle as bundle
import generation_static_checks as static
import u7_executor as executor


def main():
    parser = argparse.ArgumentParser(description="Disabled metadata-only U14 rebinding to a reviewed U13 per-board BASE")
    parser.add_argument("--variant", choices=["common", "61b"], required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--base-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    baseline, output = args.base.resolve(), args.out.resolve()
    if not output.is_relative_to(HERE / ".artifacts") or output.exists():
        raise ValueError("Fresh output inside this packet .artifacts is required")
    identities = load(HERE / "base-identities.json")["variants"]
    pins = identities[args.variant]
    signed_root = expand(pins["unarmed"])
    if sha(signed_root / "bundle.json") != pins["signed_unarmed_bundle_sha256"]:
        raise ValueError("Signed original U13 changed")
    data, _, _ = bundle.validate(baseline)
    signed_data, _, _ = bundle.validate(signed_root)
    check_base(args.variant, args.base_sha256, sha(baseline / "bundle.json"), data, signed_data, identities)
    original = PRIOR / ".artifacts" / (args.variant + "-reviewed")
    prior = load(PRIOR / args.variant / "reviewed-composition.json")
    if sha(original / "bundle.json") != prior["bundle_sha256"]:
        raise ValueError("Reviewed U14 bundle changed")
    bundle.validate(original)
    identity = prior["baseline"]
    if executor.fingerprints(identity["expected"], identity["reference_paths"]) != identity["fingerprints"]:
        raise ValueError("Complete planned U13 identity fingerprint changed")
    effective_base = static.effective(baseline)
    if any(identity["expected"].get(target) != row["sha256"] for target, row in effective_base.items()):
        raise ValueError("BASE payload differs from the signed planned U13 candidate identity")
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["/bin/cp", "-cR", original, output], check=True)
    candidate = load(output / "bundle.json")
    candidate["static_checks"]["baseline_bundle_sha256"] = args.base_sha256
    candidate["image_gate_reference"]["baseline_bundle_sha256"] = args.base_sha256
    candidate["rollout_ready"] = False
    if candidate != load(original / "bundle.json"):
        (output / "bundle.json").chmod((output / "bundle.json").stat().st_mode | 0o200)
        save(output / "bundle.json", candidate)
    for kind, row in candidate["reference"].items():
        actual = {line.split(maxsplit=1)[1]: line.split(maxsplit=1)[0] for line in (output / row["source"]).read_text().splitlines()}
        expected = {target: identity["expected"][target] for target in identity["reference_paths"][kind]}
        if actual != expected:
            raise ValueError("Reference is not the full U13 candidate identity: " + kind)
    for row in candidate["image_gate_reference"]["members"]:
        if row["sha256"] != effective_base[row["target"]]["sha256"]:
            raise ValueError("Image reference differs from BASE")
    _, manifest, _ = bundle.validate(output)
    previous = {target: row["sha256"] for target, row in static.effective(original).items()}
    current = {target: row["sha256"] for target, row in static.effective(output).items()}
    check_artifacts(previous, current)
    if sha(output / "native/package.json") != prior["native_manifest_sha256"] or sha(output / "native/native-checks/native-gates.json") != prior["native_inputs_sha256"]:
        raise ValueError("Reviewed native finding binding changed")
    plan = executor.prepare(output, baseline / "native")
    check_plan(plan, identity["expected"])
    receipt = executor.receipt_check(output, candidate, manifest)
    if receipt["status"] not in ["verified", "verified-with-exception"]:
        raise ValueError("Paired build receipt changed")
    increments = []
    for target, row in static.effective(output).items():
        old = effective_base.get(target)
        if old and old["sha256"] == row["sha256"]:
            continue
        layer = "image" if target.startswith("/system/android/framework/arm64/") else "JAR" if target.endswith(".jar") else "native"
        increments.append(dict(target=target, layer=layer, baseline_sha256=old["sha256"] if old else None, candidate_sha256=row["sha256"], operation="replace" if old else "add"))
    public = HERE / args.variant
    save(public / "composition.json", dict(variant=args.variant, package=output, bundle_sha256=sha(output / "bundle.json"),
        transaction_base=baseline, transaction_base_sha256=args.base_sha256, original_u14_bundle_sha256=prior["bundle_sha256"],
        native_manifest_sha256=sha(output / "native/package.json"), native_inputs_sha256=sha(output / "native/native-checks/native-gates.json"),
        candidate_artifacts_unchanged=True, complete_u13_identity=identity, baseline_kind="signed U13 content, promotion not asserted",
        installers=[dict(target=target, baseline_sha256=identity["expected"][target], expected_sha256=plan["expected"][target], changed=False) for target in INSTALLERS],
        increments=increments, increment_counts={layer: sum(row["layer"] == layer for row in increments) for layer in ["native", "JAR", "image"]},
        paired_receipt_status=receipt["status"], promotion_confirmed=False, execution_enabled=False, rollout_ready=False, device_access=False, vm_run=False))
    save(public / "transaction-plan.json", plan)
    save(public / "manifest.json", manifest)
    save(public / "bundle.json", candidate)
    save(public / "artifact-stability.json", dict(previous=previous, current=current, unchanged=previous == current))
    print(args.variant + " rebind exit=0 BASE=" + args.base_sha256 + " bundle=" + sha(output / "bundle.json") + " disabled")


if __name__ == "__main__":
    main()
