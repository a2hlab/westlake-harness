from collections import Counter
import json
from pathlib import Path
import re

from audit import HERE, MASTER, NEW, OLD, WS, portable, save, sha


SIGNOFF = MASTER / "benchmark/2026-10-01-u9-sweep/outer-signoff.json"
IDENTITY = MASTER / "benchmark/2026-10-01-installation-chain-identity/current-u9.json"
EXTRA_PREFIX = WS / "westlake-harness-u7-executor/benchmark/2026-10-01-u9-native/rollout/approved-j10g/boards"
SERIALS = {"5ea": "5ea34a4500000000000000001123012c", "5cd": "5cd1e3dd00000000000000000923012c", "61b": "61b0657200000000000000000324012c"}


def outcome(record, text):
    receipt = record.get("install") or {}
    success = "install bundle successfully." in text
    failure = re.search(r"(?m)^\s*error:\s*failed to install bundle\b", text) is not None
    if success and failure:
        return "unknown"
    if receipt.get("return_code") == 0 and receipt.get("success_text") is True and success:
        return "accepted"
    if failure and receipt.get("success_text") is not True:
        return "rejected"
    if isinstance(receipt.get("return_code"), int) and receipt["return_code"] != 0 and text.strip():
        return "rejected"
    return "unknown"


def observation(path, selected, identities):
    record_path, install_path, log_path = [path / name for name in ["record.json", "install.txt", "install-hilog.txt"]]
    record = json.loads(record_path.read_text())
    serial = record["serial"]
    services = identities["boards"][serial]["services"]
    digest = services["/system/lib64/libinstalls.z.so"]
    if digest != services["/system/lib64/platformsdk/libinstalls.z.so"]:
        raise ValueError("recorded service aliases disagree")
    evidence = [dict(path=portable(record_path), sha256=sha(record_path)), dict(path=portable(install_path), sha256=sha(install_path))]
    counts, witnesses, groups = Counter(), [], set()
    if log_path.exists():
        evidence.append(dict(path=portable(log_path), sha256=sha(log_path)))
        for number, line in enumerate(log_path.read_text(errors="replace").splitlines(), 1):
            if "installd_operator.cpp:" not in line:
                continue
            kind = next((label for label, needle in [("extracted", "extracted APK native"), ("exception", "accepted reviewed APK payload exception"),
                                                    ("native-rejected", "APK native extraction failed"), ("complete", "APK native extraction complete")]
                         if needle in line), None)
            if kind:
                counts[kind] += 1
                group = re.search(r"\[([0-9a-f]+), [0-9a-f]+, 0\]", line)
                if group:
                    groups.add(group[1])
                if kind != "extracted":
                    witnesses.append(dict(path=portable(log_path), line=number, kind=kind, text=line))
    return dict(key=record["key"], serial=serial, board=serial[:8], package=record["package"], apk_sha256=record["apk_sha256"],
                selected_u9=selected, outcome=outcome(record, install_path.read_text()), installer_sha256=digest,
                installer_binding="Recorded service identity by board; not fresh process-map proof for this attempt",
                payload_log_counts=dict(counts), log_trace_groups=sorted(groups),
                payload_counts_scope="Observed installer log lines, not independent app installs; multiple trace groups remain explicit",
                evidence=evidence, witnesses=witnesses)


def aggregate(rows):
    grouped = {}
    for board in SERIALS.values():
        subset = [row for row in rows if row["serial"] == board]
        counts = Counter(row["outcome"] for row in subset)
        payloads = Counter()
        for row in subset:
            payloads.update(row["payload_log_counts"])
        grouped[board[:8]] = dict(attempts=len(subset), unique_keys=len({row["key"] for row in subset}),
                                 accepted=counts["accepted"], rejected=counts["rejected"], unknown=counts["unknown"],
                                 payload_log_counts=dict(payloads))
    return grouped


def collect():
    signoff = json.loads(SIGNOFF.read_text())
    identities = json.loads(IDENTITY.read_text())
    if len(signoff["keys"]) != 166:
        raise ValueError("expected signed166 selection")
    rows = []
    for key, entry in sorted(signoff["keys"].items()):
        shard = entry["shard"]
        if shard.startswith("61b seal single-key (20261001T202852-6ce86d30)"):
            shard = "61b seal"
        if shard not in signoff["runs"]:
            raise ValueError("unresolved signed shard: " + shard)
        root = Path(signoff["runs"][shard].replace("$WORKSPACES", str(WS))).parent
        row = observation(root / key, True, identities)
        if row["key"] != key:
            raise ValueError("key/record drift")
        rows.append(row)
    extras = [EXTRA_PREFIX / "5ea/runner/original/20261001T182856-dc113ea4" / SERIALS["5ea"] / "fd-seal",
              EXTRA_PREFIX / "5ea-r2-vm/runner/seal/20261001T193640-32ca0073" / SERIALS["5ea"] / "fd-seal",
              WS / "westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-t8-rerun/window/boards/u101-t8-A1-r2-20261002T052621/5ea/runner/toutiao-gain/20261002T133815-b6713937" / SERIALS["5ea"] / "toutiao"]
    additional = [observation(path, False, identities) for path in extras]
    other = [row for row in rows if row["key"] != "toutiao"]
    if len(other) != 165 or len({row["key"] for row in rows}) != 166:
        raise ValueError("unique key accounting drift")
    return dict(schema_version=1, device_access=False, selection=dict(path=portable(SIGNOFF), sha256=sha(SIGNOFF),
                note="166 signed per-key attempts, not all historical attempts; Seal selected from approved61b retest"),
                identity=dict(path=portable(IDENTITY), sha256=sha(IDENTITY), current_loader_proof="unobserved by this offline task"),
                signed166=aggregate(rows), signed_other165=aggregate(other),
                additional_diagnostic_attempts=aggregate(additional), pooled_observed_attempts=aggregate(rows + additional),
                selected=rows, additional=additional,
                limitations=["Disjoint key sets across boards, not 166 paired installs with each binary",
                             "Signed last successful selection does not erase prior Seal rejection attempts",
                             "Payload log warnings are not terminal bm rejection unless the install receipt rejects",
                             "No fresh live service read or maps; future admission must verify actual installd owner"])


def plan():
    paths = ["/system/lib64/libinstalls.z.so", "/system/lib64/platformsdk/libinstalls.z.so"]
    return dict(schema_version=1, execution_enabled=False, state="PENDING_OUTER_REVIEW_USER_PRESENT_WINDOW", device_access=False,
                target_sha256=NEW, source="$WORKSPACES/oh61-bms-kit-b79/out/wukong100/bundlemanager/bundle_framework/libinstalls.z.so",
                operations=[dict(board=SERIALS[board], action="replace-only-libinstalls", paths=paths,
                                 expected_before_sha256=OLD, expected_after_sha256=NEW, rollback_sha256=OLD) for board in ["5ea", "5cd"]],
                already_target=dict(board=SERIALS["61b"], action="read-only verify both aliases and actual installd owner", expected_sha256=NEW),
                immutable_companions=dict(libbms="6aadb8b4ca9ad7d1dbaf6d99ca70f4603e3e7a2ec152fb60aee49137751afbf9",
                                          libapk_installer="7048c7c50a828fc744b5f06e4e9ec50ac317a2272f33789249fc63e43a655a18"),
                mechanism="Existing swap_installer.py reads candidate/baseline manifest keys; a one-lib kit yields only two aliases. No new --libs flag or source extension is needed. Do not use --accept-baseline (it only accepts BMS/APK pairs).",
                rollback="Hash-verified original backup per alias before writes; isolated transaction per board; on failure stop and restore both old hashes then recover the exact current signed generation. Do not continue to second board.",
                restart_risk="foundation restart can reboot/drop USB and bind mounts; explicit outer approval, idle board lease, daytime user present and physical recovery required",
                gates_before=["Two pinned artifact SHAs, archive/compiler/source provenance", "Raw strings allowances individually reviewed; retain parsing/pointer artifacts and rc1",
                              "ABI exports1096 unchanged, no consumer removals; inspect CFI body data/flags, not one misleading stripped call label",
                              "B10 open sites/namespace edges old and new; explain every change, N1/N2 bound to final composition",
                              "Four exact payload positives and mutated bundle/ABI/name/bytes/CRC/owner/mode negatives; no generic extension bypass",
                              "Fresh shell AND installd process-root/mapped identity for both aliases; no reliance on app-maps WHOIS",
                              "No concurrent promotion window; full current runtime/boot/318 assertions and service snapshots; final manifest/hash/read-only-data review"],
                gates_after=["Both aliases and actual newly running installd owner map/inode agree with51e1; foundation alone is not enough",
                             "Fresh installs Toutiao and Seal plus exact payload readback, X manifest and HelloWorld/Zigzag controls",
                             "Other165 fresh-install regression coverage after first-board canary; APK/input identities pinned, compare installation not t20",
                             "Control screenshots outer-reviewed; missing evidence unknown, installation success is not lighting",
                             "Recompute installation-service identity, extended123-file runtime fingerprint and final smoke pins; both paths already tracked since8859d87899, do not re-add or retain split expected hashes",
                             "On reboot restore current signed generation selected by outer at window start, never old v3a/v4 plan; verify boot/runtime/services/control evidence before release"],
                expect=dict(confirm="5ea/5cd fresh bm install succeeds for pinned Toutiao and Seal, exact exception lines/payload SHA seen, owner is51e1 and companions unchanged; non-target installs remain accepted",
                            refute="Either alias/owner stays2c9, generic validation accepts a mutated payload, fresh install still fails the same gate or controls/non-target installs regress; stop and roll back"))


def main():
    result = collect()
    save("installations.json", result)
    save("alignment-plan.json", plan())
    for label in ["signed166", "signed_other165", "additional_diagnostic_attempts", "pooled_observed_attempts"]:
        for board, row in result[label].items():
            print(label + " " + board + ": attempts=" + str(row["attempts"]) + " accepted=" + str(row["accepted"]) +
                  " rejected=" + str(row["rejected"]) + " unknown=" + str(row["unknown"]) + " payload_logs=" + str(row["payload_log_counts"]))
    print("plan: execution_enabled=false; proposed5ea->5cd,61b verify-only; no board commands")


if __name__ == "__main__":
    main()
