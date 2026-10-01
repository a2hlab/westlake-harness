import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess


HERE = Path(__file__).resolve().parent
BASELINE_SHA = "7fe4369d26d5c832099177984a0d1fc7d75c0deabc40ef5f7237ab593ab2cd47"
RECIPE_SHA = "584ef75f831da5d4338ead9dce38d96fa64446bdbd0c9acc961e52cfb78771cb"
N11_RECEIPT_SHA = "df5d6dad841dc4dd35b8a643b2d20845dea264e3ce0d0fe14fa1c446827eefd1"


def digest(filename):
    return hashlib.sha256(Path(filename).read_bytes()).hexdigest()


def portable(value, workspaces, output):
    return value.replace(str(output.resolve()), "$OUT").replace(str(HERE.parents[1]), "$REPO").replace(str(workspaces.resolve()), "$WORKSPACES")


def main():
    parser = argparse.ArgumentParser(description="Replay stock-host link with only exact main-object replacement")
    parser.add_argument("--workspaces", type=Path, default=os.environ.get("WORKSPACES"))
    parser.add_argument("--sdk", type=Path, default="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    workspaces = args.workspaces.resolve()
    plugin = workspaces / "_cc-wiki-b1-src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin"
    commands_file = plugin / "out/route-a-generation/logs/commands.txt"
    recipe = workspaces / "westlake-generation-u9-j10g-238ffc14/native/handoff/evidence/recipe-appspawn-x.sh"
    if digest(recipe) != RECIPE_SHA or digest(HERE / "visibility/baseline-stock-host.c") != BASELINE_SHA:
        raise ValueError("stock-host source or link recipe identity mismatch")
    actual_receipt = workspaces / "westlake-harness-t4/benchmark/2026-10-01-n11-single-owner/host-build-receipt.json"
    if digest(actual_receipt) != N11_RECEIPT_SHA:
        raise ValueError("actual U8/U9 host main command receipt mismatch")
    actual_baseline = json.loads(actual_receipt.read_text())["baseline"]
    compile_command = actual_baseline["commands"][0]
    link_command = next(shlex.split(line) for line in recipe.read_text().splitlines() if " -pie " in line)
    original_source = compile_command[compile_command.index("-c") + 1]
    if digest(original_source) != BASELINE_SHA:
        raise ValueError("recorded compilation uses a different main")
    reused = [{"path": portable(value, workspaces, args.out), "sha256": digest(value)}
              for value in link_command if value.endswith(".o")]
    original_main = next(value for value in link_command if value.endswith("/westlake_stock_host_main.o"))
    approved_objects = set(actual_baseline["link_objects"].values())
    for value in link_command:
        if value.endswith(".o") and value != original_main and digest(value) not in approved_objects:
            raise ValueError("reused object differs from byte-reproduced U9 host: " + value)
    compiler = args.sdk / "llvm/bin/clang"
    args.out.mkdir(parents=True, exist_ok=True)
    records = []
    for variant in ["baseline", "candidate"]:
        output = args.out / (variant + "-stock-host.o")
        command = compile_command.copy()
        command[0] = str(compiler)
        command = [value for value in command if not value.startswith("-B")]
        command[command.index("-c") + 1] = str(HERE / "visibility" / (variant + "-stock-host.c"))
        command[command.index("-o") + 1] = str(output)
        command += ["-I" + str(HERE / "visibility")]
        subprocess.run(command, check=True)
        records.append(command)
        target = args.out / ("appspawn-x-" + variant)
        command = link_command.copy()
        command[0] = str(compiler)
        command = [value for value in command if not value.startswith("-B")]
        command[command.index(original_main)] = str(output)
        command[command.index("-o") + 1] = str(target)
        subprocess.run(command, check=True)
        records.append(command)
    receipt = {"schema": "u10-resident-host-build-v1", "recipe_sha256": RECIPE_SHA,
               "actual_main_command_receipt_sha256": N11_RECEIPT_SHA,
               "actual_main_command_receipt": "westlake-harness-t4/benchmark/2026-10-01-n11-single-owner/host-build-receipt.json",
               "compile_commands_sha256": digest(commands_file), "baseline_main_sha256": BASELINE_SHA,
               "compiler_sha256": digest(compiler), "reused_objects": reused,
               "candidate_main_sha256": digest(HERE / "visibility/candidate-stock-host.c"),
               "resident_header_sha256": digest(HERE / "visibility/resident-compat.h"),
               "commands": [[portable(value, workspaces, args.out) for value in command] for command in records],
               "artifacts": {variant: digest(args.out / ("appspawn-x-" + variant)) for variant in ["baseline", "candidate"]},
               "generation_identity": "Historical generation macros retained for isolated ABI comparison only; cx-t0 must regenerate U10 closure/plugin identities before assembly",
               "reproducibility": "Reuses original SHA-recorded host objects and historical frozen sources; not a full clean rebuild of every host object"}
    (args.out / "host-build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt["artifacts"]))


if __name__ == "__main__":
    main()
