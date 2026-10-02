import json
import re
import sys

from audit import HERE, LOADER, MASTER, REPO, WS, module, portable, save, sha


def main():
    sys.path.insert(0, str(REPO / "scripts/lab"))
    import first_fatal

    signoff_path = MASTER / "benchmark/2026-10-01-u9-sweep/outer-signoff.json"
    signoff = json.loads(signoff_path.read_text())
    symbol_pattern = re.compile(r"\b(__errno|__cmsg_nxthdr|__system_property_read|__gnu_strerror_r)\b")
    error_pattern = re.compile(r"cannot locate symbol|relocat|UnsatisfiedLinkError|dlopen failed", re.I)
    matches, inputs, rows = [], [], []
    for shard, facts in signoff["runs"].items():
        root = WS / facts.removeprefix("$WORKSPACES/")
        for log in sorted(root.parent.glob("*/hilog.txt")):
            hits = []
            for number, text in enumerate(log.read_text(errors="replace").splitlines(), 1):
                if error_pattern.search(text) and (match := symbol_pattern.search(text)):
                    hits.append(dict(line=number, symbol=match[1], text=text))
            inputs.append(dict(shard=shard, key=log.parent.name, path=portable(log), sha256=sha(log)))
            if not hits:
                continue
            record, events, pids, reports, disappeared, pins = first_fatal.load_run(log.parent)
            bound_hits = []
            for hit in hits:
                event = first_fatal.classify.parse(hit["text"], hit["line"])
                hit["pid"] = event["pid"] if event else None
                hit["app_pid"] = bool(event and event["pid"] in pids)
                if hit["app_pid"]:
                    bound_hits.append(hit)
            if not bound_hits:
                continue
            fatal = first_fatal.analyze(events, pids, reports, disappeared)
            selected = [event for event in events if event["pid"] in pids and any(token in event["message"] for token in
                        ["ExceptionHandler", "Uncaught", "Couldn't load", "FATAL", "main_threw", "TelephonyManager",
                         "BBQ.", "DrawFrame", "process kept alive", "alive", "GeckoLoader"])]
            selected += [event for event in events if event["pid"] in pids and
                         ("Directory separator" in event["message"] or "Uncaught exception handled" in event["message"])]
            selected = sorted({event["line"]: event for event in selected}.values(), key=lambda event: event["line"])
            evidence = "evidence/u9-" + record["key"] + "-hilog.txt"
            excerpt = {hit["line"]: hit["text"] for hit in bound_hits}
            excerpt.update({event["line"]: event["text"] for event in selected})
            if fatal.get("root"):
                excerpt.update({event["line"]: event["text"] for event in fatal["root"].get("chain", [])})
            (HERE / evidence).write_text(portable("\n".join(f"{number}: {text}" for number, text in sorted(excerpt.items()))) + "\n")
            row = dict(key=record["key"], signed_status=signoff["keys"][record["key"]]["verdict"],
                       shard=shard, run=portable(log.parent), hilog_sha256=sha(log), target_pids=sorted(pids),
                       symbol_events=bound_hits, first_fatal=fatal, evidence=evidence, source_identity=pins)
            if record["key"] == "x":
                row.update(exports_only_prediction="first-fatal-unchanged", next_fatal="Observed TelephonyManager null cast at32788/32789 remains; errno warnings on another TID are not this root", conditional_scope_next="Same already-observed Java wall; second launch/window outcome unknown")
            elif record["key"] == "ooniprobe":
                row.update(exports_only_prediction="no-fatal-to-move-lit-negative-control", next_fatal="none observed", conditional_scope_next="unknown; do not count a lit negative control as unlocked")
            else:
                row.update(exports_only_prediction="gnu-wall-unchanged", next_fatal="Existing __gnu_strerror_r relocation remains:4698 adds only errno/cmsg and does not alter GNU export/scope", conditional_scope_next="If the separate scope pair binds GNU to the sole compat owner, later Gecko loading/API failure is unknown; Directory separator retry is observed after failed load, not a proven future independent fatal")
            rows.append(row)
            matches.extend(dict(key=record["key"], **hit) for hit in bound_hits)
    counts = {symbol: sorted({hit["key"] for hit in matches if hit["symbol"] == symbol})
              for symbol in ["__errno", "__cmsg_nxthdr", "__system_property_read", "__gnu_strerror_r"]}
    save("observations.json", dict(signoff_path=portable(signoff_path), signoff_sha256=sha(signoff_path),
         run_shards=len(signoff["runs"]), scanned_logs=len(inputs), inputs=inputs, actual_error_keys=counts,
         rows=rows, predicted_first_fatal_moved_keys_exports_only=[],
         conditional_load_wall_candidates_scope_pair=["fd-fennec_fdroid", "firefox"],
         conditional_first_fatal_moved_keys_scope_pair="unknown: process disappearance does not identify a root or killing sender",
         static_import_count_is_upper_bound=True, execution_enabled=False))
    sys.path.insert(0, str(REPO / "benchmark/2026-10-02-u11-native-batch"))
    collect = module("batch_collect", REPO / "benchmark/2026-10-02-u11-native-batch/collect.py")
    elf_module = module("batch_elf", REPO / "benchmark/2026-10-02-u11-native-batch/elf_readonly.py")
    save("evidence/current-policy.json", dict(path=portable(LOADER), sha256=sha(LOADER), baked=collect.baked_policy(LOADER, elf_module)))
    for symbol, keys in counts.items():
        print(symbol + " actual-U9-error-keys=" + str(len(keys)) + " " + ",".join(keys))
    print("4698 expected first-fatal moved keys: [] (not a claim of no runtime effect)")


if __name__ == "__main__":
    main()
