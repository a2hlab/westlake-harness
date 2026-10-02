import json
from pathlib import Path
import shlex
import shutil
import subprocess

from audit import HERE, HOST, REPO, WS, portable, save, sha


def main():
    frozen = REPO / "benchmark/2026-10-02-n11h-host-owner"
    source = frozen / "inputs/host-r3.c"
    header = frozen / "inputs/resident-compat.h"
    if sha(source) != "507bf160dfae87851345c8fc564c9378356a773cc84272d2ec0635b1c0ef0c50" or sha(header) != "e4f7321547d6cafac5734a7ff3b9338cc0e8a93e94ff5932bafa3caa23cb35e0":
        raise ValueError("accepted r3 source mismatch")
    recipe_path = WS / "westlake-harness/benchmark/2026-10-01-u10-bundle/r2-host-build-receipt.json"
    if sha(recipe_path) != "8eaec4315b379e1e3675b38a5e298271716279c049db1ba3ede5c3815ea0cb40":
        raise ValueError("r3 frozen object recipe changed")
    recipe = json.loads(recipe_path.read_text())
    import sys
    sys.path.insert(0, str(frozen))
    from elf_readonly import rodata_strings
    strings = rodata_strings(HOST)
    suffix = "/benchmark/2026-10-01-u10-native-shims/.artifacts/host-r3/candidate-stock-host.c"
    old_source = next(value for value in strings if value.endswith(suffix))
    old_header = next(value for value in strings if value.endswith("/host-r3/resident-compat.h"))
    original_root = old_source[:-len(suffix)]
    out = HERE / ".artifacts/host"
    out.mkdir(parents=True, exist_ok=True)
    inputs = {str(source): sha(source), str(header): sha(header), str(recipe_path): sha(recipe_path)}
    variants = {
        "baseline": header.read_text(),
        "resident-global-proposal": header.read_text().replace("RTLD_NOW | RTLD_NOLOAD);", "RTLD_NOW | RTLD_NOLOAD | RTLD_GLOBAL);", 1)
    }
    (HERE / "resident-compat-proposal.h").write_text(variants["resident-global-proposal"])
    commands, repeats = [], []
    for repeat in [1, 2]:
        identities = {}
        for variant, text in variants.items():
            folder = out / variant
            folder.mkdir(exist_ok=True)
            generated = folder / "candidate-stock-host.c"
            generated.write_bytes(source.read_bytes())
            generated_header = folder / "resident-compat.h"
            generated_header.write_text(text)
            compile_command, link_command = [[value.replace("$WORKSPACES", str(WS)).replace("$REPO", str(REPO))
                                             for value in command] for command in recipe["runs"][0]["commands"]]
            if sha(compile_command[0]) != recipe["compiler_sha256"]:
                raise ValueError("frozen host compiler changed")
            inputs[compile_command[0]] = sha(compile_command[0])
            old_object = compile_command[compile_command.index("-o") + 1]
            new_object = folder / "host.o"
            compile_command[compile_command.index("-c") + 1] = str(generated)
            compile_command[compile_command.index("-o") + 1] = str(new_object)
            compile_command[1:1] = ["-I" + str(folder), "-ffile-prefix-map=" + str(REPO) + "=" + original_root,
                                     "-ffile-prefix-map=" + str(generated) + "=" + old_source,
                                     "-ffile-prefix-map=" + str(generated_header) + "=" + old_header]
            target = folder / "appspawn-x"
            link_command[link_command.index("-o") + 1] = str(target)
            objects = out / "objects"
            objects.mkdir(exist_ok=True)
            allowed = {row["sha256"] for row in recipe["reused_objects"]}
            for index, value in enumerate(link_command):
                if value == old_object:
                    link_command[index] = str(new_object)
                elif value.endswith(".o"):
                    digest = sha(value)
                    if digest not in allowed:
                        raise ValueError("stock object drift")
                    copied = objects / (digest + ".o")
                    shutil.copyfile(value, copied)
                    inputs[value] = digest
                    link_command[index] = str(copied)
            for phase, command in [("compile", compile_command), ("link", link_command)]:
                print(variant + " " + phase + " " + shlex.join(command), flush=True)
                result = subprocess.run(command, capture_output=True, text=True, cwd=REPO)
                print(result.stdout, end="", flush=True)
                print(result.stderr, end="", flush=True)
                if result.returncode:
                    raise ValueError("host build failed")
                commands.append(dict(repeat=repeat, variant=variant, phase=phase, command=[portable(value) for value in command]))
            identities[variant] = sha(target)
            if variant == "baseline" and sha(target) != sha(HOST):
                raise ValueError("failed exact65cc baseline reproduction")
        repeats.append(identities)
        print("REPEAT " + str(repeat) + " " + json.dumps(identities), flush=True)
    if repeats[0] != repeats[1]:
        raise ValueError("host repeat byte drift")
    save("host-build-receipt.json", dict(device_io=False, repeated=repeats, baseline_reproduced=True,
         source_sha256=sha(source), candidate_header_sha256=sha(HERE / "resident-compat-proposal.h"),
         inputs=[dict(path=portable(path), sha256=digest) for path, digest in inputs.items()], commands=commands,
         status="UNAPPROVED_SCOPE_PROPOSAL_NOT_RELOCATION_OR_SINGLE_COPY_PROOF",
         source_delta="Only existing sealed resident NOLOAD query gains RTLD_GLOBAL; no new query, path, inherit or app/default fresh load"))


if __name__ == "__main__":
    main()
