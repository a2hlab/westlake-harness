import re

JARS = ["core-oj", "core-libart", "core-icu4j", "okhttp", "bouncycastle", "apache-xml",
        "adapter-mainline-stubs", "framework", "oh-adapter-framework"]
IMAGE_NAMES = {segment + "." + suffix for segment in ["boot", *["boot-" + name for name in JARS[1:]]]
               for suffix in ["art", "oat", "vdex"]}
BASES = {"common": "29c8a62cc78f5ba1eddea75fceb46e96baacba7e9b4d6fd046c9d8951ebe904f",
         "61b": "8a260cec9b4ab3505cf72fe445e34643f0f1441abe9367658f3240d2e45a6a8b"}
STUBS = "85938130cbb016c568d0086a43f6dc865d638e63625c401e82f93987b1fa3c01"
OLD_STUBS = "94a949053ec8c5a520a9a228b64ae8adb861977f92a6b5f63fa689214c4628fe"
RUNTIME_JAR = "f6f5face66a90a16020877cddc5bb6e5bed28063dfabf02fa77064c00c50bb81"
OLD_RUNTIME_JAR = "20e748e57c6ee8bd0b97dcfff074c3a1c001dd727cbcee6a754f60a598642770"
FRAMEWORK = "9e55e28623c86cc553bb2449cb18948e383a05fb0283b045d969655813b7d1b7"
DEX2OAT = "ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b"
DRIVER = "14b1f709cbeae35c2e606ee923d26a9f59e92dd827da84bdf5126de79a675d46"
HOME_ID = "4e5277d9907dc562d2135c48e53fa1ed5764ab628dae1e8e397499e708a1c102"
REMOTE_ROOT = "$HW248_HOME/u16-stubs-8593-runtime-f6f5-v1"
ADDED = ["Landroid/net/ConnectivityManager$OnNetworkActiveListener;", "Landroid/net/DhcpInfo$1;",
         "Landroid/net/DhcpInfo;", "Landroid/net/wifi/SupplicantState$1;", "Landroid/net/wifi/SupplicantState;",
         "Landroid/net/wifi/WifiManager$MulticastLock;", "Landroid/net/wifi/WifiManager$SuggestionConnectionStatusListener;",
         "Landroid/net/wifi/WifiManager$WifiLock;"]


def check_plan(plan, images, slots):
    if any(plan.get(name) is not False for name in ["execution_enabled", "rollout_ready", "bake_executed", "promotion_confirmed"]):
        raise ValueError("Preparation must stay disabled")
    if plan["final_bundle_sha256"] is not None or plan["transaction_base"] != {"common": None, "61b": None}:
        raise ValueError("No inferred final package or transaction promotion")
    if {name: row["sha256"] for name, row in plan["content_bases"].items()} != BASES:
        raise ValueError("Wrong U15 content identity")
    rows = plan["bcp"]
    if [row["name"] for row in rows] != [name + ".jar" for name in JARS]:
        raise ValueError("Nine ordered BCP inputs required")
    changes = [row["name"] for row in rows if row["sha256"] != row["u15_sha256"]]
    if changes != ["adapter-mainline-stubs.jar"] or plan["changed_bcp"] != changes:
        raise ValueError("Only stubs BCP swap allowed")
    if rows[6]["sha256"] != STUBS or rows[6]["u15_sha256"] != OLD_STUBS or rows[7]["sha256"] != FRAMEWORK:
        raise ValueError("Stubs/framework identity drift")
    if plan["runtime_jar"]["sha256"] != RUNTIME_JAR or plan["runtime_jar"]["u15_sha256"] != OLD_RUNTIME_JAR or plan["runtime_jar"]["in_bcp"] is not False:
        raise ValueError("Runtime JAR must remain outside BCP")
    if len(images) != 27 or {row["name"] for row in images} != IMAGE_NAMES:
        raise ValueError("27 distinct images required")
    if any(row["candidate_sha256"] is not None or row["rebake"] is not True for row in images):
        raise ValueError("All output identities remain unknown until full bake")
    if slots["execution_enabled"] is not False or slots["rollout_ready"] is not False:
        raise ValueError("Native preparation disabled")
    if [row["id"] for row in slots["slots"]] != ["t4-m1-split-runtime", "flutter-impeller-extension-proc"]:
        raise ValueError("Both pending native slots must stay explicit")
    if any(row["state"] != "pending" or row["sha256"] is not None or row["applied"] is not False for row in slots["slots"]):
        raise ValueError("Pending native arrival cannot imply composition")
    if slots["excluded"] != ["t2-icon-raster"] or slots["dependency_blocked"] != ["t5-webview-A0"]:
        raise ValueError("Batch scope changed")
    if plan["machine"]["hostname"] != "ecs-9f6c" or plan["machine"]["home_identity_sha256"] != HOME_ID:
        raise ValueError("Frozen machine identity drift")
    if plan["frozen_tools"]["dex2oat64"]["sha256"] != DEX2OAT or plan["frozen_tools"]["driver"]["sha256"] != DRIVER:
        raise ValueError("Frozen toolchain identity drift")


def check_receipt(receipt, inputs, outputs):
    if receipt.get("status") != "verified" or receipt.get("input_jars") != inputs or receipt.get("outputs") != outputs:
        raise ValueError("Exact fresh input/output pair required")
    if len(inputs) != 9 or len(outputs) != 27 or set(outputs) != IMAGE_NAMES:
        raise ValueError("Incomplete bake group")
    for name in ["dex2oat_exit_code", "tee_exit_code", "session_tee_exit_code", "script_exit_code"]:
        if receipt.get(name) != 0:
            raise ValueError("Compiler or live logging failed")
    if receipt.get("frozen_driver_exit_code") not in [0, 6]:
        raise ValueError("Frozen-driver status missing or invalid")
    if receipt.get("dex2oat_sha256") != DEX2OAT or receipt.get("driver_sha256") != DRIVER:
        raise ValueError("Frozen tools changed")
    if not receipt.get("actual_argv"):
        raise ValueError("Actual argv missing")
    for name in ["argv_sha256", "toolchain_identity_sha256", "hostlibs_sha256", "build_log_sha256", "session_log_sha256"]:
        if not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get(name, ""))):
            raise ValueError("Actual evidence SHA missing")
    if any(not re.fullmatch(r"[0-9a-f]{64}", str(value)) for value in outputs.values()):
        raise ValueError("Actual output SHA missing")
    if receipt.get("exception_used"):
        approval = receipt.get("u16_outer_exception_approval") or {}
        if approval.get("input_jars") != inputs or approval.get("outputs") != outputs or approval.get("approved_by") != "outer(claude)":
            raise ValueError("Historical approval cannot replace fresh U16 exact-pair review")
