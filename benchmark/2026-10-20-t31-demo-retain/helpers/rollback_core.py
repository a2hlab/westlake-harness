#!/usr/bin/env python3
"""Local-only T30 admission preparation; never runs a device or lock command."""
import argparse
import datetime
import hashlib
import json
import re
import shlex
import time
import uuid
from pathlib import Path

SERIAL = "5cd1e3dd00000000000000000923012c"
ACTOR = "inner(cx-seal)"
UID = 20011300
EXE = "a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c"
RT = "/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d"
DEPLOY = "benchmark/2026-10-20-t30-request-recovery/deployment"


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_script(parent, host):
    require(parent > 1 and host > 1 and parent != host, "distinct positive PIDs")
    lines = ["(set -eu", "echo T30_ADMISSION_BEGIN"]
    for phase in ("BEFORE", "AFTER"):
        lines.append(f'printf "BOOT_{phase}="; cat /proc/sys/kernel/random/boot_id')
        for role, pid in (("P", parent), ("H", host)):
            for key, command in (
                ("STAT", f"cat /proc/{pid}/stat"),
                ("UID", f"sed -n 's/^Uid:[[:space:]]*//p' /proc/{pid}/status"),
                ("TRACER", f"sed -n 's/^TracerPid:[[:space:]]*//p' /proc/{pid}/status"),
                ("EXE", f"sha256sum /proc/{pid}/exe | cut -d' ' -f1"),
                ("MNT", f"readlink /proc/{pid}/ns/mnt"),
            ):
                lines.append(f'printf "{role}_{key}_{phase}="; {command}')
        if phase == "BEFORE":
            lines += ['printf "INIT_MNT="; readlink /proc/1/ns/mnt',
                      "echo WMS_BEGIN", "hidumper -s WindowManagerService -a '-a'",
                      "echo WMS_END"]
        for key, rel in (("BRIDGE", "liboh_adapter_bridge.so"),
                         ("SHIM", "webview-t-lib/libwebview_bionic_shim.so")):
            for view, prefix in (("PHYSICAL", RT),
                                 ("PRIVATE", f"/proc/{parent}/root/data/local/tmp/asx")):
                path = shlex.quote(prefix + "/" + rel)
                for field, command in (
                    ("SHA", f"sha256sum {path} | cut -d' ' -f1"),
                    ("META", f"stat -L -c %a:%u:%g:%d:%i {path}"),
                    ("LABEL", f"ls -Zd {path} | cut -d' ' -f1"),
                ):
                    lines.append(f'printf "{key}_{view}_{field}_{phase}="; {command}')
    lines += ["echo T30_ADMISSION_END", ")",
              'read_rc=$?; printf "T30_ADMISSION_READ_RC=%s\\n" "$read_rc"']
    return "\n".join(lines) + "\n"


def parse_stat(value):
    m = re.fullmatch(r"(\d+) \(.*\) (.+)", value)
    require(m is not None, "malformed proc stat")
    fields = m[2].split()
    require(len(fields) >= 20 and fields[0] not in ("Z", "X", "x", "T", "t"),
            "missing/dead/stopped identity")
    return int(m[1]), int(fields[1]), int(fields[19])


def fill(repo, context, held, raw, now, plan):
    from window_paths import deploy
    d = deploy()
    require(Path(context["deploy"]).resolve() == d, "context deployment")
    require(context["serial"] == SERIAL, "serial")
    require(Path(context["repo"]).resolve() == repo.resolve(), "context MAIN")
    holder = context["holder"]
    require(held.strip() == holder, "held full-line drift")
    tokens = holder.split()
    require(len(tokens) == 3 and tokens[0] == ACTOR and tokens[1].isdigit(), "holder")
    start = float(context["start"])
    require(abs(datetime.datetime.fromisoformat(tokens[2]).timestamp() - start) < 1,
            "holder start")
    age = now - start
    require(0 <= age < 1800, "hard deadline reached")
    lines = raw.splitlines()
    require(lines[0] == "T30_ADMISSION_BEGIN" and
            lines[-2:] == ["T30_ADMISSION_END", "T30_ADMISSION_READ_RC=0"],
            "remote completion/rc missing")
    require(lines.count("WMS_BEGIN") == lines.count("WMS_END") == 1, "WMS framing")
    lo, hi = lines.index("WMS_BEGIN"), lines.index("WMS_END")
    require(lo < hi, "WMS ordering")
    values = {}
    for line in lines[1:lo] + lines[hi + 1:-2]:
        key, sep, value = line.partition("=")
        require(sep and key not in values and value, "malformed/duplicate field")
        values[key] = value
    boot = values["BOOT_BEFORE"]
    require(str(uuid.UUID(boot)) == boot == values["BOOT_AFTER"], "boot drift")
    identities = {}
    for role, uid in (("P", 0), ("H", UID)):
        before = parse_stat(values[f"{role}_STAT_BEFORE"])
        after = parse_stat(values[f"{role}_STAT_AFTER"])
        require(before == after and before[2] > 0, "PID/PPID/birth drift")
        for key in ("UID", "TRACER", "EXE", "MNT"):
            require(values[f"{role}_{key}_BEFORE"] == values[f"{role}_{key}_AFTER"],
                    "identity field drift")
        require(values[f"{role}_UID_BEFORE"].split() == [str(uid)] * 4, "UID")
        require(values[f"{role}_TRACER_BEFORE"].strip() == "0", "tracer")
        require(re.fullmatch("[0-9a-f]{64}", values[f"{role}_EXE_BEFORE"]), "exe SHA")
        require(re.fullmatch(r"mnt:\[\d+\]", values[f"{role}_MNT_BEFORE"]), "namespace")
        identities[role] = before
    require(identities["P"][1] == 1 and values["P_EXE_BEFORE"] == EXE, "parent identity")
    require(values["P_MNT_BEFORE"] != values["INIT_MNT"], "parent private namespace")
    rows = [x.split() for x in lines[lo + 1:hi] if x.split() and x.split()[0] == "imehost0"]
    require(len(rows) == 1 and len(rows[0]) >= 8, "unique host WMS")
    require(rows[0][2] == str(identities["H"][0]) and rows[0][3].isdigit() and int(rows[0][3]) > 0, "host/WID")
    ad = json.loads((d / "admission.template.json").read_text())
    for key, name in (
        ("executor_sha256", "executor.py"), ("parameters_sha256", "parameters.json"),
        ("source_pins_sha256", "executor-source-pins.json"),
        ("readonly_inputs_sha256", "readonly-inputs.json"),
        ("bridge_candidate_sha256", "bridge-candidate.json"),
        ("shim_candidate_sha256", "shim-candidate.json"),
    ):
        require(ad[key] == sha(d / name), "template pin drift: " + key)
    for rel, digest in json.loads((d / "executor-source-pins.json").read_text()).items():
        require(sha(repo / rel) == digest, "source pin drift: " + rel)
    for key, mode, candidate_name in (
        ("BRIDGE", "644", "bridge-candidate.json"),
        ("SHIM", "755", "shim-candidate.json"),
    ):
        for field in ("SHA", "META", "LABEL"):
            observed = {values[f"{key}_{view}_{field}_{phase}"]
                        for view in ("PHYSICAL", "PRIVATE") for phase in ("BEFORE", "AFTER")}
            require(len(observed) == 1, key + " physical/private drift: " + field)
        meta = values[f"{key}_PHYSICAL_META_BEFORE"]
        require(re.fullmatch(mode + r":20011300:20011300:\d+:\d+", meta), "metadata")
        label = values[f"{key}_PHYSICAL_LABEL_BEFORE"]
        require(label == "u:object_r:appdat:s0", "label")
        candidate = json.loads((d / candidate_name).read_text())
        require(values[f"{key}_PHYSICAL_SHA_BEFORE"] == candidate["before_sha256"] or
                values[f"{key}_PHYSICAL_SHA_BEFORE"] == candidate["after_sha256"],
                "foreign current SHA")
        ad[key.lower() + "_metadata"] = ":".join(meta.split(":")[:3])
        ad[key.lower() + "_label"] = label
    require(plan["mode"] == "apply" and plan["holder"] == holder and
            plan["start"] == start and plan["serial"] == SERIAL and
            plan["uid"] == UID and plan["compat_before_absent"] is True,
            "original apply plan identity")
    require(plan["executor_sha256"] == ad["executor_sha256"], "plan executor")
    for key, filename in (("bridge", "bridge-candidate.json"), ("shim", "shim-candidate.json")):
        candidate = json.loads((d / filename).read_text())
        require(plan[key + "_before_sha"] == candidate["before_sha256"] and
                plan[key + "_after_sha"] == candidate["after_sha256"] and
                plan[key + "_candidate_sha256"] == ad[key + "_candidate_sha256"] and
                plan[key + "_metadata"] == ad[key + "_metadata"] and
                plan[key + "_label"] == ad[key + "_label"], "plan candidate/meta drift")
    ad.update(approved_by="outer(codex)", holder=holder, window_start=start, boot=boot,
              parent_mnt=values["P_MNT_BEFORE"],
              host=dict(pid=identities["H"][0], birth=identities["H"][2], uid=UID),
              status="FRESH_ROLLBACK_ADMISSION_EXECUTOR_GUARDS_REQUIRED")
    # Live slot fields remain unobserved; the existing executor rechecks device state.
    require(ad["fresh_three_slot_receipt_sha256"] is None, "no fabricated live slots")
    budget = dict(start=start, elapsed_seconds=age, stop_experiment_at=start + 1200,
                  hard_end_at=start + 1800, recovery_remaining_seconds=1800 - age)
    return ad, identities, budget

