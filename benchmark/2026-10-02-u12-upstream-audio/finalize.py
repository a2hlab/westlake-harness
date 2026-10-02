import ast
import json

from collect import HERE, REPO, portable, save, sha


def main():
    source = (HERE / "candidate/opensles_android_adapter.c").read_text().splitlines()
    review = []
    for line in (HERE / "evidence/strings.txt").read_text().splitlines():
        if not line.startswith(("ADDED ", "DROPPED ")):
            continue
        change, literal = line.split(None, 1)
        value = ast.literal_eval(literal)
        matches = [index for index, text in enumerate(source, 1) if value in text]
        review.append(dict(change=change, value=value, source="candidate/opensles_android_adapter.c",
             source_lines=matches, reason="New canonical IID table/configuration/translation diagnostic literal" if matches else
             "Printable rendering of adjacent IID bytes; compare old24/new16 object layout, not a deleted API name",
             disposition="outer-review-required"))
    save("strings-review.json", dict(status="PENDING_NOT_ALLOWLISTED", dropped=2, added=73, rows=review))
    validation = []
    for name in ["cargo.txt", "t1-lifecycle.json", "t1-stderr.txt", "t2-lifecycle.json", "t2-stderr.txt"]:
        raw = HERE / ".artifacts" / name
        target = HERE / "evidence" / name
        target.write_text(portable(raw.read_text()))
        validation.append(dict(raw_path=portable(raw), raw_sha256=sha(raw), evidence="evidence/" + name, sha256=sha(target)))
        if name.endswith("lifecycle.json"):
            report = json.loads(raw.read_text())
            if not report["passed"]:
                raise ValueError("contract failed: " + name)
            for result in report["verification"]["results"]:
                for evidence in result["evidence"]:
                    if evidence["type"] == "test_output" and (not evidence["passed"] or "1 passed; 0 failed" not in evidence["stdout"]):
                        raise ValueError("actual test selector absent")
    save("evidence/validation-receipts.json", dict(python_tests=6, rust_tests=3, contract_scenarios=3, skipped=0, records=validation))
    save("results.json", dict(status="VERIFIED_PRIMITIVES_NOT_ADMITTED_AUDIO", execution_enabled=False, device_io=False,
         real_play_completion_implemented=False, route_A_media_owner_registration_implemented=False,
         resident_backend_publication_implemented=False, candidate_sha256=json.loads((HERE / "build-receipt.json").read_text())["repeated_sha256"][0],
         positive_checks=["IID16/OH24 field conversion", "canonical pointer", "PCM28/OH56", "output32 canary", "callback refill8 bytes", "underrun silence"],
         negative_control="PLAY RegisterCallback and mask still12", strings_exit_code=1, strings_dropped=2, strings_added=73,
         abi_removed=0, abi_added=2, abi_call_diffs=0, removed_export_consumer_breaks=0, actual_audio_success=False,
         n1_n2_status="REJECT: historical53/103 exception identities not rebound", new_n1_findings=0,
         expected_first_fatal_moved_keys=[], expected_new_lit_keys=[], evidence=["architecture.json", "build-receipt.json", "namespace-gates.json", "strings-review.json"]))
    save("documentation.json", {
        "README.md": ["| **`benchmark/2026-10-02-u12-upstream-audio/`** | **Four upstream audio commits mapped to route-A; verified IID16/OH24, PCM/state width and continuous-refill primitives with explicit PLAY12 negative control, unapproved candidate and raw static gate rejection.** |"],
        ".octos/KNOWLEDGE-DIGEST.md": ["- U12 upstream audio (2026-10-02,cx-bms): c7d2992 PLAY callbacks/mask still delegate to OH05d8 returning12; canonical-ID memcmp uses OH24 against Android16. Candidate0e9b converts UUID fields/retains owner pointer and refills continuously, fixture PCM28→56/state canary/queue8 pass but PLAY12 remains. It only accepts injected canonical resident backend, no caller publication/media-owner registration; no ledger unlock claim. Strings2drop/73add and unrebound N1/N2 remain REJECT; not an admitted audio facade. See benchmark/2026-10-02-u12-upstream-audio/."]
    })
    paths = [path for path in HERE.rglob("*") if path.is_file() and not any(part in {".artifacts", "__pycache__", "completion-v1"}
              for part in path.relative_to(HERE).parts) and path.name != "landing-paths.txt"]
    paths += list((REPO / "specs/u12-upstream-audio").glob("*.spec.md"))
    paths += [REPO / "tools/spec-checks/tests/u12_upstream_audio.rs", HERE / "landing-paths.txt", HERE / "evidence/preflight.txt"]
    (HERE / "landing-paths.txt").write_text("\n".join(sorted({str(path.relative_to(REPO)) for path in paths})) + "\n")
    print("first delivery prepared; real PLAY completion and route-A media owner registration incomplete")


if __name__ == "__main__":
    main()
