import json
from pathlib import Path

from common import HERE, REPO, save, sha


def main():
    composition = json.loads((HERE / "composition.json").read_text())
    summary = json.loads((HERE / "report-summary.json").read_text())
    save("pending-batch-extensions.json", dict(applied=False, execution_enabled=False, items=[
        dict(component="stock-host-app-ns", state="pending candidate", owner="cc-wiki", reference="31096f56d6"),
        dict(component="icu-wall-two", state="plan b approved; candidate pending", owner="cc-wiki", reference="82b91863f2"),
        dict(component="native-abi-gecko", state="additional outer-approved scope; no artifact applied", owner="cc-t3", reference="f8647dfd31"),
        dict(component="runtime-jar", state="0349eb83 reserved only", owner="cc-t3", reference="2c70182c73"),
        dict(component="bt-stubs-and-paired-images", state="87cf65cc reserved; image rebake pending", owner="cc-t3", reference="166b005c5d")]))
    save("results.json", dict(schema_version=1, task="U14 bridge-only offline draft", composition=composition,
        checks={name: value for name, value in summary.items() if name != "records"},
        pending_approvals=["39 newly covered N1 findings", "one independently explained ADR diagnostic static delta", "three same-byte admission bindings if baseline still T8", "strings rows retained for review"],
        execution_enabled=False, final_batch_complete=False, promotion_proved=False,
        current_baseline_limitation="61b has two board-local libinstalls copies; explicit effective variant requested by outer 03:30, next task. No full-identity production PASS claimed."))
    save("documentation.json", dict(layout_row="| **`benchmark/2026-10-03-u14-native-assembly/`** | **Disabled U13-plus-bridge skeleton, explicit transaction base, direct z-level provider, 219 consumers, raw ADR and newly covered N1 review.** |",
        digest_line="- U14桥草稿(2026-10-03,cx-bms):912内容基座≠190事务基座，后者必须参数+SHA+签认；7daa对846新增UND4=继承e34三项+M5 zLevel，35NEEDED不变且9551/ad01直接导出。open ADR位移保留raw1并独立证同libmali/0x102；159旧finding换绑preview不等于39新覆盖已批，219导出断0不证明ns可达。VM/生产未跑，61b两份libinstalls须专用有效基座，禁用草稿不晋级。见benchmark/2026-10-03-u14-native-assembly/。"))
    paths = sorted(path.relative_to(REPO).as_posix() for path in HERE.rglob("*") if path.is_file()
        and not any(part in [".artifacts", "__pycache__"] for part in path.parts)
        and path.name not in ["landing-paths.txt", "preflight.txt", "listing-receipt.json"])
    paths += ["specs/u14-native-assembly/project.spec.md", "specs/u14-native-assembly/t1-compose.spec.md", "specs/u14-native-assembly/t2-static.spec.md", "tools/spec-checks/tests/u14_native_assembly.rs"]
    landing = HERE / "landing-paths.txt"
    landing.write_text("\n".join(sorted(paths)) + "\n")
    save("listing-receipt.json", dict(listing_sha256=sha(landing), count=len(paths), execution_enabled=False))
    print("landing paths=" + str(len(paths)) + " sha256=" + sha(landing))


if __name__ == "__main__":
    main()
