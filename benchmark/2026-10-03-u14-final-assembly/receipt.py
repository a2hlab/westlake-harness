import json
import shlex

from common import BASE, HERE, PLAN, RELEASE, portable, save, sha
from validation import IMAGES, JARS, check_receipt


def verify_wrapper(original, amended, actual_lab_home):
    expected = original.replace('[ "$(hostname -s)" = hw248 ]', '[ "$(hostname -s)" = ecs-9f6c ]')
    expected = expected.replace('export U14_ROOT=', 'export HOME=' + actual_lab_home + '\nexport U14_ROOT=', 1)
    if amended != expected:
        raise ValueError("Unapproved bake wrapper amendment")


def main():
    if not RELEASE.is_dir():
        raise ValueError("Actual U14 bake has not arrived")
    files = []
    for line in (RELEASE / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        name = name.lstrip("*")
        path = (RELEASE / name).resolve()
        if not path.is_relative_to(RELEASE.resolve()) or sha(path) != digest:
            raise ValueError("Incoming release inventory mismatch: " + name)
        files.append(dict(name=name, sha256=digest))
    original = RELEASE / "plan-original/planned-bake.sh"
    amended = RELEASE / "plan/planned-bake.sh"
    if sha(original) != sha(PLAN / "planned-bake.sh"):
        raise ValueError("Original approved plan wrapper mismatch")
    first_log = (RELEASE / "logs/dex2oat-run1.log").read_text().splitlines()
    actual_binary = shlex.split(next(line.split("dex2oat.cc:3192] ", 1)[1] for line in first_log if "dex2oat.cc:3192] " in line))[0]
    suffix = "/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64"
    if not actual_binary.endswith(suffix):
        raise ValueError("Frozen compiler path differs from recorded recipe")
    verify_wrapper(original.read_text(), amended.read_text(), actual_binary.removesuffix(suffix))
    if sha(RELEASE / "plan/dex2oat-tee.sh") != sha(PLAN / "dex2oat-tee.sh"):
        raise ValueError("Live compiler wrapper changed")
    planned = json.loads((PLAN / "paired-receipt.template.json").read_text())
    inputs = {name + ".jar": sha(RELEASE / "jars9" / (name + ".jar")) for name in JARS}
    if inputs != planned["input_jars"]:
        raise ValueError("Actual incoming BCP inventory differs from approved plan")
    runs = []
    for number in [1, 2]:
        root = RELEASE / ("run" + str(number))
        if {path.name for path in root.iterdir()} != IMAGES:
            raise ValueError("Actual run image set differs")
        session = RELEASE / "logs" / ("bake-run" + str(number) + ".session.log")
        compiler = RELEASE / "logs" / ("dex2oat-run" + str(number) + ".log")
        compiler_status = json.loads((RELEASE / "logs" / ("dex2oat-run" + str(number) + ".status.json")).read_text())
        session_status = json.loads((RELEASE / "logs" / ("session-run" + str(number) + ".status.json")).read_text())
        driver_status = json.loads((RELEASE / "logs" / ("t5-run" + str(number) + ".status.json")).read_text())
        if compiler_status != {"dex2oat_exit_code": 0, "tee_exit_code": 0} or session_status != {"session_tee_exit_code": 0, "script_exit_code": 0} or driver_status["t5_exit_code"] not in [0, 6]:
            raise ValueError("Actual compiler/live logging failed")
        marker = "dex2oat.cc:3192] "
        argv_lines = [line.split(marker, 1)[1] for line in compiler.read_text().splitlines() if marker in line]
        if len(argv_lines) != 1:
            raise ValueError("Actual compiler argv missing or ambiguous")
        argv = shlex.split(argv_lines[0])
        incoming = [value.removeprefix("--dex-file=") for value in argv if value.startswith("--dex-file=")]
        if [value.rsplit("/", 1)[1] for value in incoming] != [name + ".jar" for name in JARS] or any("/work/incoming/" not in value for value in incoming):
            raise ValueError("Actual nine compiler inputs or order differs")
        text = session.read_text()
        if planned["dex2oat_sha256"] not in text or planned["driver_sha256"] not in text or "host=ecs-9f6c" not in text or "[u14-bake] end=" not in text:
            raise ValueError("Live tool/machine/session identity incomplete")
        identity = dict(machine="hw248 (actual ecs-9f6c)", architecture="Linux x86_64", session_sha256=sha(session),
            frozen_dex2oat_sha256=planned["dex2oat_sha256"], frozen_driver_sha256=planned["driver_sha256"],
            hostlibs_sha256=sha(RELEASE / "logs" / ("hostlibs-run" + str(number) + ".sha256")),
            ldd_sha256=sha(RELEASE / "logs" / ("ldd-run" + str(number) + ".txt")), wrapper_sha256=sha(amended))
        identity_path = HERE / "receipts" / ("toolchain-run" + str(number) + ".json")
        save(identity_path, identity)
        receipt = dict(status="verified", input_jars=inputs, outputs={name: sha(root / name) for name in sorted(IMAGES)},
            build_command=argv_lines[0], actual_argv=argv, dex2oat_sha256=planned["dex2oat_sha256"], driver_sha256=planned["driver_sha256"],
            toolchain_identity_sha256=sha(identity_path), toolchain_identity=identity_path, build_log=compiler, build_log_sha256=sha(compiler),
            session_log=session, session_log_sha256=sha(session), wrapper_sha256=sha(amended), original_wrapper_sha256=sha(original),
            compiler_tee_wrapper_sha256=sha(RELEASE / "plan/dex2oat-tee.sh"), dex2oat_exit_code=0, tee_exit_code=0, session_tee_exit_code=0,
            script_exit_code=0, t5_exit_code=driver_status["t5_exit_code"], exception_used=False, u14_outer_exception_approval=None,
            scope="Verified actual build execution and selected output inventory; strict paired-byte reproduction separately rejected pending outer review",
            persistent_root=RELEASE, run=number)
        check_receipt(receipt, inputs, receipt["outputs"])
        private = HERE / ".artifacts/receipts" / ("paired-run" + str(number) + ".json")
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_text(json.dumps(receipt, default=str, indent=2) + "\n")
        save("receipts/paired-run" + str(number) + ".json", receipt)
        runs.append(receipt)
        for source in [session, compiler, RELEASE / "logs" / ("hostlibs-run" + str(number) + ".sha256"), RELEASE / "logs" / ("ldd-run" + str(number) + ".txt")]:
            destination = HERE / "evidence" / source.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(portable(source.read_text()))
    if runs[0]["actual_argv"] != runs[1]["actual_argv"] or runs[0]["input_jars"] != runs[1]["input_jars"]:
        raise ValueError("Two actual compiler invocations differ")
    if (RELEASE / "logs/hostlibs-run1.sha256").read_bytes() != (RELEASE / "logs/hostlibs-run2.sha256").read_bytes():
        raise ValueError("Two actual host dependency inventories differ")
    comparisons = []
    for name in sorted(IMAGES):
        first, second = (RELEASE / "run1" / name).read_bytes(), (RELEASE / "run2" / name).read_bytes()
        offsets = [] if first == second else [index for index, (left, right) in enumerate(zip(first, second)) if left != right]
        comparisons.append(dict(name=name, run1_sha256=runs[0]["outputs"][name], run2_sha256=runs[1]["outputs"][name],
            identical=first == second, same_size=len(first) == len(second), differing_bytes=len(offsets), offsets=[hex(value) for value in offsets],
            historical_interval_only=name == "boot.art" and len(first) == len(second) and bool(offsets) and all(0x3e3b8 <= value < 0x3e3c0 for value in offsets)))
    review = dict(status="REJECT", strict_identical=sum(row["identical"] for row in comparisons), total=27, comparisons=comparisons,
        approved_by=None, applied=False, object_owner="pending fresh U14 oatdump; historical interval is not proof of new object identity",
        approval_required="Exact U14 input map and paired boot.art SHA; old T7d registry does not apply")
    save("reproduction-review.json", review)
    save("receipts/incoming-inventory.json", dict(count=len(files), files=files, sha256sums_sha256=sha(RELEASE / "SHA256SUMS"), verified=True))
    for source in [original, amended, RELEASE / "planned-bake-amendment.diff"]:
        save_path = HERE / "inputs" / ("original-" + source.name if source == original else source.name)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(portable(source.read_text()))
    print("INCOMING verified=" + str(len(files)) + " build_runs=2 compiler/tee/session_tee=0/0/0 t5=6/6")
    print("PAIRED execution=verified strict_reproduction=" + str(review["strict_identical"]) + "/27 pending_object_and_outer_review=true")


if __name__ == "__main__":
    main()
