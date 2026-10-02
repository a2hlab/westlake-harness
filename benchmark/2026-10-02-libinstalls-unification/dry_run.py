import shutil

from audit import BINARIES, HERE, LAB, NEW, OLD, portable, run, save
from stats import SERIALS


def main():
    kit = HERE / ".artifacts/one-lib-kit"
    kit.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BINARIES["new"], kit / "libinstalls.z.so")
    manifest = dict(schema=1, candidate={"libinstalls.z.so": NEW}, baseline={"libinstalls.z.so": OLD})
    save("kit-manifest.json", manifest)
    save(".artifacts/one-lib-kit/manifest.json", manifest)
    receipts = []
    for board in ["5ea", "5cd"]:
        result = run("transaction-dry-run-" + board, ["python3", LAB / "swap_installer.py", "dry-run", "--serial", SERIALS[board],
                     "--kit", kit, "--transaction-name", "libinstalls-51e1b525-offline", "--lane", "cx-bms"])
        if result["exit_code"] != 0 or '"device_io": false' not in result["text"]:
            raise ValueError("offline transaction dry-run failed")
        receipts.append({key: value for key, value in result.items() if key != "text"})
    save("evidence/transaction-dry-runs.json", receipts)
    print("transaction dry-run: two boards, one-lib manifest, two aliases each, device_io=false; NO apply/restart")


if __name__ == "__main__":
    main()
