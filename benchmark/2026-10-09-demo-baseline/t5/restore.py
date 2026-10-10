import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "scripts/lab"))
import lab_paths


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def expand(value, base):
    if not isinstance(value, str):
        raise ValueError("artifact path required")
    value = value.replace("$WORKSPACES/", str(lab_paths.workspaces()) + "/", 1)
    path = Path(value)
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def pinned(binding, base):
    path = expand(binding["path"], base)
    if not re.fullmatch(r"[0-9a-f]{64}", binding.get("sha256", "")) or digest(path) != binding["sha256"]:
        raise ValueError("archived source SHA mismatch: " + binding["path"])
    return path


def validate(seal, deployment, base):
    if seal.get("schema") != "demo-seal/v1" or deployment.get("schema") != "demo-restore-deployment/v1":
        raise ValueError("wrong seal/deployment schema")
    if deployment.get("execution_enabled") is not True:
        raise ValueError("deployment is pending or disabled")
    expected = {}
    if set(seal["files"]) != {"runtime", "boot", "overlays", "installation"}:
        raise ValueError("incomplete seal files")
    for members in seal["files"].values():
        for target, sha in members.items():
            if target in expected and expected[target] != sha:
                raise ValueError("conflicting seal SHA")
            expected[target] = sha
    for package in seal["packages"]:
        target, sha = package["apk_path"], package["apk_sha256"]
        if target in expected and expected[target] != sha:
            raise ValueError("conflicting APK SHA")
        expected[target] = sha
    members = deployment["files"]
    targets = [member["target"] for member in members]
    if len(set(targets)) != len(targets) or set(targets) != set(expected):
        raise ValueError("deployment must cover exactly every sealed file and APK")
    for member in members:
        target = member["target"]
        if not re.fullmatch(r"/[A-Za-z0-9_./:+@-]+", target) or ".." in target.split("/"):
            raise ValueError("unsafe sealed target")
        if member["source"]["sha256"] != expected[target]:
            raise ValueError("source differs from sealed SHA: " + target)
        pinned(member["source"], base)
        if member["mode"] not in {"restore", "verify-only"}:
            raise ValueError("invalid restoration mode")
    restored = {member["target"] for member in members if member["mode"] == "restore"}
    covered = []
    layers = []
    allowed_layers = ["u13", "toutiao-route-b", "boatattack"]
    for provider in deployment["providers"]:
        if provider.get("layer") not in allowed_layers:
            raise ValueError("unknown restoration layer")
        layers.append(provider["layer"])
        if provider["interpreter"] not in {"python3", "bash"}:
            raise ValueError("unsupported provider interpreter")
        pinned(provider["program"], base)
        pinned(provider["rollback"], base)
        if not provider["targets"] or not set(provider["targets"]).issubset(restored):
            raise ValueError("provider has undeclared or immutable targets")
        covered.extend(provider["targets"])
    if set(covered) != restored or len(covered) != len(set(covered)):
        raise ValueError("every mutable target needs exactly one reviewed provider")
    if not layers or layers[0] != "u13" or len(set(layers)) != len(layers) or layers != sorted(layers, key=allowed_layers.index):
        raise ValueError("restore layers must be U13 then Route B then BoatAttack")
    overlays = seal.get("overlay_deployments", [])
    if any(row.get("state") not in {"active", "absent"} for row in overlays):
        raise ValueError("unresolved sealed overlay")
    active = {row["id"] for row in overlays if row["state"] == "active"}
    if active != set(layers) - {"u13"}:
        raise ValueError("provider layers differ from sealed active overlays")
    return expected


class Backend:
    def __init__(self, serial, seal_path, output, observed=None):
        self.serial, self.seal_path, self.output = serial, seal_path, output
        self.observed = observed
        self.sequence = 0

    def record(self, command, stem):
        result = subprocess.run(command, capture_output=True, timeout=1200)
        (self.output / (stem + ".stdout.txt")).write_bytes(result.stdout)
        (self.output / (stem + ".stderr.txt")).write_bytes(result.stderr)
        save(self.output / (stem + ".command.json"), {"argv": list(map(str, command)), "exit_code": result.returncode})
        return result

    def read(self):
        self.sequence += 1
        stem = "read-" + str(self.sequence)
        receipt = self.output / (stem + ".json")
        command = ["bash", str(REPO / "scripts/lab/demo_selfcheck.sh"), "--seal", str(self.seal_path),
                   "--serial", self.serial, "--out", str(receipt)]
        if self.observed:
            command += ["--observed", str(self.observed)]
        result = self.record(command, stem)
        if result.returncode not in {0, 1} or not receipt.is_file():
            raise ValueError("read-only selfcheck rejected; no provider started")
        return json.loads(receipt.read_text())

    def held(self):
        result = self.record(["bash", str(lab_paths.harness() / "scripts/lab/board_note.sh"), "held", self.serial], "held-" + str(self.sequence))
        if result.returncode != 0 or result.stderr:
            raise ValueError("external held lock missing")
        return result.stdout.decode().strip()

    def apply(self, provider, program, deployment_path, step):
        folder = self.output / ("provider-" + str(step))
        command = [provider["interpreter"], str(program), "--seal", str(self.seal_path), "--serial", self.serial,
                   "--deployment", str(deployment_path), "--out", str(folder)]
        result = self.record(command, "provider-" + str(step))
        if result.returncode != 0:
            raise ValueError("provider failed; preserve external lock and use reviewed rollback")


def readable(receipt):
    checks = {row["path"]: row for row in receipt["checks"]}
    for target in ("serial", "stable-boot", "read-errors"):
        if not checks.get(target, {}).get("equal"):
            raise ValueError("unreliable initial observation: " + target)
    if not receipt.get("boot_before") or receipt["boot_before"] != receipt.get("boot_after"):
        raise ValueError("missing or changed boot identity")
    if any(not row["equal"] for target, row in checks.items() if target.startswith("param:")):
        raise ValueError("system version/parameters differ; no OS replacement is allowed")
    return checks


def authorize(approval, seal_path, deployment_path, serial, rehearsal):
    if approval.get("schema") != "demo-restore-authorization/v1" or approval.get("authorized") is not True:
        raise ValueError("explicit write authorization required")
    expected_signer = "outer(claude)" if rehearsal else "user"
    if approval.get("authorized_by") != expected_signer or approval.get("serial") != serial:
        raise ValueError("wrong authorization signer/board")
    if approval.get("seal_sha256") != digest(seal_path) or approval.get("deployment_sha256") != digest(deployment_path):
        raise ValueError("authorization object binding changed")
    until = datetime.fromisoformat(approval["valid_until"].replace("Z", "+00:00"))
    if until.tzinfo is None or until <= datetime.now(timezone.utc) or not approval.get("holder"):
        raise ValueError("expired authorization or missing lock holder")


def restore(seal, deployment, deployment_path, backend, execute=False, approval=None):
    base = deployment_path.parent
    validate(seal, deployment, base)
    deployment_sha = digest(deployment_path)
    effective_seal_sha = digest(backend.seal_path)
    if json.loads(deployment_path.read_text()) != deployment or json.loads(backend.seal_path.read_text()) != seal:
        raise ValueError("input documents differ from validated objects")
    before = backend.read()
    checks = readable(before)
    for member in deployment["files"]:
        if member["mode"] == "verify-only" and not checks.get(member["target"], {}).get("equal"):
            raise ValueError("immutable prerequisite drift: " + member["target"])
    report = {"schema": "demo-restore-receipt/v1", "mode": "execute" if execute else "dry-run",
              "before": before, "remote_write_steps": 0, "unlock_attempted": False,
              "status": "already-equal" if before["passed"] else "planned", "steps": []}
    if not execute or before["passed"]:
        return report
    if not approval:
        raise ValueError("authorization required before write")
    if approval.get("boot_id") != before["boot_before"]:
        raise ValueError("authorization boot binding changed")
    for index, provider in enumerate(deployment["providers"], 1):
        until = datetime.fromisoformat(approval["valid_until"].replace("Z", "+00:00"))
        if until.tzinfo is None or until <= datetime.now(timezone.utc):
            raise ValueError("write authorization expired during replay")
        validate(seal, deployment, base)
        if backend.held() != approval["holder"]:
            raise ValueError("external holder drift")
        current = backend.read()
        readable(current)
        if current["boot_before"] != before["boot_before"]:
            raise ValueError("boot changed between precheck and replay")
        if digest(deployment_path) != deployment_sha or digest(backend.seal_path) != effective_seal_sha:
            raise ValueError("sealed input documents changed during dispatch")
        validate(seal, deployment, base)
        program = pinned(provider["program"], base)
        backend.apply(provider, program, deployment_path, index)
        report["steps"].append({"provider": provider["program"], "targets": provider["targets"]})
        report["remote_write_steps"] += 1
    if backend.held() != approval["holder"]:
        raise ValueError("external holder drift after replay")
    after = backend.read()
    readable(after)
    if after["boot_before"] != before["boot_before"]:
        raise ValueError("boot changed during replay")
    if not after["passed"]:
        raise ValueError("post-replay seal still differs; keep lock, do not claim restoration")
    report.update(after=after, status="restored-selfcheck-equal")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal", type=Path, required=True)
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--out", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument("--observed", type=Path)
    args = parser.parse_args()
    try:
        if args.out.exists():
            raise ValueError("fresh output directory required")
        if args.execute and (args.observed or not args.authorization):
            raise ValueError("execution requires live reads and explicit authorization")
        if args.serial not in lab_paths.boards("oh"):
            raise ValueError("non-whitelisted board")
        seal = json.loads(args.seal.read_text())
        deployment = json.loads(args.deployment.read_text())
        if args.rehearsal:
            if args.serial == seal["serial"]:
                raise ValueError("rehearsal must be on a spare board")
        elif args.serial != seal["serial"]:
            raise ValueError("wrong sealed board")
        validate(seal, deployment, args.deployment.resolve().parent)
        approval = json.loads(args.authorization.read_text()) if args.authorization else None
        if args.execute:
            authorize(approval, args.seal, args.deployment, args.serial, args.rehearsal)
        args.out.mkdir(parents=True)
        projected = dict(seal, serial=args.serial)
        projected_path = args.out / "serial-projection.json"
        save(projected_path, projected)
        backend = Backend(args.serial, projected_path, args.out, args.observed)
        result = restore(projected, deployment, args.deployment.resolve(), backend, args.execute, approval)
        result.update(seal_sha256=digest(args.seal), deployment_sha256=digest(args.deployment),
                      serial_projection_only=args.rehearsal, live_rehearsal_verified=False)
        save(args.out / "result.json", result)
        print(json.dumps({key: result[key] for key in ("status", "mode", "remote_write_steps")}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        if args.out.is_dir() and not (args.out / "result.json").exists():
            save(args.out / "result.json", {"status": "refused-keep-external-lock", "error": str(error), "unlock_attempted": False})
        print("REJECT " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
