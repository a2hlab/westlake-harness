#!/usr/bin/env python3
"""Exercise the actual CLI with immutable input and rejection counterexamples."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def main():
    root = Path(os.environ.get("WESTLAKE_TEST_ARTIFACTS", Path.home() / ".local/share/westlake/spec-checks"))
    out = root / f"ttvideo-derivation-{os.getpid()}-{time.time_ns()}"
    out.mkdir(parents=True, exist_ok=False)
    source = HERE.parent / "candidate-r4/deploy-inputs/libttmplayer.so"
    data = source.read_bytes()
    assert hashlib.sha256(data).hexdigest() == "5fba80506cd1a494de5fb6aee63930192d6d0539657cca51e99381ff8a052ee4"
    rows = []

    def run(name, src, dst, proof, expected):
        argv = [sys.executable, str(HERE / "derive_ttmplayer_logmirror.py"), str(src), str(dst), str(proof)]
        r = subprocess.run(argv, capture_output=True, timeout=30)
        (out / f"{name}.stdout").write_bytes(r.stdout)
        (out / f"{name}.stderr").write_bytes(r.stderr)
        rows.append(dict(case=name, argv=argv, rc=r.returncode))
        (out / "commands.json").write_text(json.dumps(rows, indent=2) + "\n")
        assert (r.returncode == 0) == expected, (name, r.stderr)

    product, proof = out / "player.so", out / "proof.json"
    run("valid", source, product, proof, True)
    derived = product.read_bytes()
    assert len(derived) == len(data)
    changed = [i for i, (a, b) in enumerate(zip(data, derived)) if a != b]
    assert changed == list(range(0xa6f3, 0xa704))
    assert derived[0xa6f1:0xa705] == b"__wl_ttlog_00000659\0"
    assert hashlib.sha256(derived).hexdigest() == "0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471"
    before = hashlib.sha256(product.read_bytes()).hexdigest()
    run("existing-output", source, product, out / "unused-proof.json", False)
    assert hashlib.sha256(product.read_bytes()).hexdigest() == before
    assert not (out / "unused-proof.json").exists()
    drift = out / "drift.so"
    drift.write_bytes(bytes([data[0] ^ 1]) + data[1:])
    short = out / "short.so"
    short.write_bytes(data[:-1])
    for name, src in (("sha-drift", drift), ("size-drift", short), ("double-apply", product)):
        dst, evidence = out / f"{name}.so", out / f"{name}.json"
        run(name, src, dst, evidence, False)
        assert not dst.exists() and not evidence.exists()
    alias = out / "same-path"
    run("same-output-proof", source, alias, alias, False)
    assert not alias.exists()
    missing = out / "missing-target"
    dangling = out / "dangling-output"
    dangling.symlink_to(missing)
    run("dangling-symlink", source, dangling, out / "dangling-proof.json", False)
    assert dangling.is_symlink() and not missing.exists()
    report = dict(scope="EXACT_ELF_CLI_ONLY_NOT_RUNTIME", passed=len(rows),
                  source_sha256=hashlib.sha256(data).hexdigest(),
                  script_sha256=hashlib.sha256((HERE / "derive_ttmplayer_logmirror.py").read_bytes()).hexdigest(),
                  output_sha256=before, changed_byte_count=len(changed), raw_directory=str(out))
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
