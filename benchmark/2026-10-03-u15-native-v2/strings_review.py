import ast
import hashlib
import json

from common import HERE, portable, save, sha


def main():
    deltas = json.loads((HERE / "static-deltas.json").read_text())["members"]
    rows = []
    objects = {}
    for member in deltas:
        name = member["object"]
        raw = HERE / ".artifacts/raw" / ("strings-" + name + ".txt")
        counts = {"added": 0, "dropped": 0}
        for line in raw.read_text().splitlines():
            if not line.startswith(("ADDED ", "DROPPED ")):
                continue
            action, expression = line.split(None, 1)
            text = ast.literal_eval(expression)
            counts["added" if action == "ADDED" else "dropped"] += 1
            if name == "runtime":
                source = "inputs/source/egl.cpp:41"
                reason = "Converter dlsym name becomes a direct same-image reference; export is retained in ABI/dynsym."
                if "EGLImpl window surface" in text or text == "WL-OPENGL":
                    source = "inputs/source/egl.cpp:60"
                    reason = "New HiLogPrint diagnostic for GL-thread Java Surface to ANativeWindow/OH conversion."
                elif "not found" in text:
                    source = "inputs/source/egl.cpp:53"
                    reason = "Direct non-null function address eliminates old dynamic-lookup-miss diagnostic; no failed lookup fallback is added."
                elif "row " in text:
                    reason = "Debug producer row address shifts with the changed object; not a runtime message. Proposed review only."
                elif text != "ANativeWindow_fromSurface":
                    reason = "Printable non-text fragment shifts with code/readonly layout. Do not infer semantic equivalence from strings; outer binary review required."
            elif name == "host":
                source = "inputs/source/n4-host.c:362"
                reason = "Mindustry owner validation uses Android simple-buffer-queue IID instead of unsupported old buffer-queue IID."
                if "org.jitsi.meet" in text:
                    source = "inputs/source/n4-host.c:" + ("290" if text.startswith("/") else "127")
                    reason = "Meet enters matching ANL/host native-domain lists and resident runtime publication, atomically with the ANL alias pair."
                elif "/" in text:
                    source = "inputs/source/n4-host.c:1" if "stock-host" in text else "inputs/source/u10-1-resident-compat.h:1"
                    reason = "Same resident-compat code, build-time source location changes in __FILE__/debug literal; public view is portable, raw literal hash retained."
                elif not text.startswith("SL_IID_"):
                    source = "inputs/source/n4-host.c:123"
                    reason = "Address/table printable fragment changed with the extra package literal and layout; outer binary review required, not automatic allow."
            else:
                source = "inputs/source/u15-app-native-loader.c:1"
                lines = (HERE / "inputs/source/u15-app-native-loader.c").read_text().splitlines()
                location = next(index for index, value in enumerate(lines, 1) if '"org.jitsi.meet"' in value)
                source = "inputs/source/u15-app-native-loader.c:" + str(location)
                reason = "Matching Meet native-domain package whitelist; must ship with host and both identical ANL aliases."
            rows.append(dict(object=name, action=action, string=portable(text),
                raw_string_sha256=hashlib.sha256(text.encode()).hexdigest(), source=source, reason=reason,
                evidence="evidence/strings-" + name + ".txt", raw_sha256=sha(raw),
                proposed_action="allow exact pair only after outer review", approved_by=None, applied=False))
        objects[name] = dict(**counts, candidate_sha256=member["candidate_sha256"], deployed_sha256=member["deployed_sha256"],
            evidence="evidence/strings-" + name + ".txt", approved_by=None,
            note="Production tool uses selected readonly strings, not every dynstr/debug name. Flutter has zero selected-string changes; three exports/imports are independently checked." if name == "flutter" else "raw strings refusals retained")
    save("strings-review.json", dict(schema="u15-native-strings-outer-review/v2", objects=objects, rows=rows,
        approved_by=None, applied=False, full_bundle_sha256=None,
        rule="Unsigned exact object pairs; no automatic approval for metadata, fragments or donor ledger"))
    table = ["# U15 native v2: unsigned strings review", "", "Original stdout and hashes are retained. None of these rows is signed or applied.",
        "Flutter has 0/0 selected readonly-string changes under the production tool; ATrace +3 exports and +3 direct runtime imports are checked separately.",
        "", "| Object | Action | Exact public-view string | Source | Proposed reason |", "|---|---|---|---|---|"]
    for row in rows:
        text = row["string"].replace("|", "&#124;").replace("`", "&#96;")
        table.append("| " + " | ".join([row["object"], row["action"], "`" + text + "`", "`" + row["source"] + "`", row["reason"]]) + " |")
    (HERE / "STRINGS-REVIEW.md").write_text("\n".join(table) + "\n")
    print("STRINGS REVIEW unsigned rows=" + str(len(rows)) + " objects=" + str(len(objects)))


if __name__ == "__main__":
    main()
