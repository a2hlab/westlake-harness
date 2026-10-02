import json

from collect import HERE, save


def main():
    logs = json.loads((HERE / "log-index.json").read_text())
    rows = [
        dict(key="fd-im-vector-app", package="im.vector.app", wall="private-zlib-alias",
             category="missing SONAME in selected private namespace", layer="native payload + narrow host route",
             namespace=dict(name="westlake.anl.app.26007.3", status="observed", lines=[25552, 25555, 25559]),
             failure_lines=[25555, 25556, 25559, 25560, 25575, 25664],
             verdict="load-wall repairable by the already reviewed U12 private closure; current T8 launch dies",
             fix="Reuse U12 host2a871 U11ZlibRoot(im.vector.app) with alias50b9->providerab082 only in westlake_native. Keep root libz absent; retain one factory libc owner.",
             implementation="benchmark/2026-10-02-u12-private-zlib/inputs/zlib-route.h:20; U12 final assembly already contains host, alias and provider",
             prior_coverage="U12 host2a87118e + private libz50b9ab6a/libshared_libzab0820c6",
             conditional_move_vs_t8=1, incremental_move_vs_u12=0, delivered_u13_prediction_vs_t8=1,
             observed_moves=0, permission_only_moves=0, next_first_fatal="unknown; realm also imports android_set_abort_message@LIBC, which still requires real scope proof",
             t20="unknown", risks=["Realm's extracted .10.19.0 fallback bytes were not captured; public consumer SHA is verified",
                                   "No U12 window result is borrowed; inventory coverage is not successful JNI_OnLoad"]),
        dict(key="mindustry", package="io.anuke.mindustry", wall="opensles-provider-and-abi",
             category="facade missing exports plus OH provider path not visible", layer="native audio facade + exact owner route",
             namespace=dict(name="westlake.anl.app.6536.3", status="observed", lines=[19400]),
             failure_lines=[19400, 19403, 19404, 19427],
             verdict="load-wall conditionally repairable; direct OH replacement and the current unadmitted ABI-only audio donor are not approved fixes",
             fix="Publish the existing OH05d8 owner narrowly and provide all five Android libarc imports through an ABI-converting facade; do not rename OH ELF or add slCreateEngine to generic compat.",
             implementation="benchmark/2026-10-02-u11-native-batch/; benchmark/2026-10-02-u12-upstream-audio/; both explicitly hold production audio publication",
             prior_coverage="None in the delivered U12/U13 package: facade remains5891f899; upstream-audio0e9b is not admitted",
             conditional_move_vs_t8=1, incremental_move_vs_u12=1, delivered_u13_prediction_vs_t8=0,
             observed_moves=0, permission_only_moves=0,
             next_first_fatal="exact next fatal unknown; libarc calls PLAY RegisterCallback/set-mask at a2290/a22a4, while OH05d8 returns12 FEATURE_UNSUPPORTED. This is a known next capability wall, not a new measured fatal.",
             t20="unknown", risks=["Android32/OH64 scalar widths and Android16/OH24 IID differ",
                                   "Successful symbol binding cannot supply real PLAY completion",
                                   "No PLAY implementation or candidate is started in this task"]),
        dict(key="fd-meet", package="org.jitsi.meet", wall="soloader-relocation-scope",
             category="existing versioned providers outside consumer relocation scope, not private-directory denial",
             layer="ANL/host common namespace constructor and resident-owner publication",
             namespace=dict(name=None, status="numeric app namespace unlogged on the failing calls; source-derived ordinary ANL app domain",
                            evidence="ANL_Dlopen source:450-473; org.jitsi.meet absent from native_cluster_path:63-67; host StockOpenNamespace@d464",
                            not_established="the B8 runtime-CL namespace log does not identify this consumer's namespace instance"),
             failure_lines=[25374, 25376, 25477, 25483, 25505, 25507, 25527],
             verdict="scope repair conditionally viable; permission-only and compat-export-only prescriptions rejected",
             fix="Coordinate N11h/Gecko's common constructor: publish the unique resident compat and existing pthread-bridge/ABI atfork provider into the actual SoLoader consumer lookup scope before relocation. Inspect both public and lib-main paths. The ordinary app already inherits libbionic_compat at cffc; merely adding its SONAME again is not the fix. Preserve once-only inherit and no duplicate runtime. Do not add a new errno/abort owner or blindly move Meet to private old-runtime domains.",
             implementation="benchmark/2026-10-02-u12-compat-relocation-scope/; existing pthread bridge and private ABI both export __register_atfork@@LIBC",
             prior_coverage="Compat015aa already exports abort; pthread bridge and private ABI already export atfork. No complete consumer-scope proof/fix in current U12/U13.",
             conditional_move_vs_t8=1, incremental_move_vs_u12=1, delivered_u13_prediction_vs_t8=0,
             observed_moves=0, permission_only_moves=0,
             next_first_fatal="If only fallback abort scope changes, public libreactnative/hermes __register_atfork remains the preceding retry cause. With both real owners accessible, exact next fatal unknown; libreactnative imports six AAsset operations so single runtime/AssetManager ownership must be kept.",
             t20="unknown", risks=["SoLoader logs failed removal of write permission, but then extracts and reaches relocation in lib-main; it is not the terminal cause",
                                   "Fallback libc++ bytes are not directly captured, so its identity is not claimed equal to the public SHA",
                                   "Consumer @LIBC vs compat unversioned is not evidence of version rejection: atfork already has matching LIBC providers; factory fd3c behavior accepts absent version tables as recorded in the existing audit"])
    ]
    for row in rows:
        context = logs[row["key"]]
        index = {item["line"]: item for item in context["rows"]}
        row.update(pid=context["pid"], source=context["source"], hilog_sha256=context["source_sha256"],
                   terminal=context["terminal"], evidence=[index[line] for line in row["failure_lines"]])
        row["evidence_grade"] = "Observed dependency/relocation failure; repair viability conditional, selected symbol owner unobserved"
        if row["key"] == "fd-meet":
            row["scope_inference"] = "Leading explanation from route, matching provider versions and failed relocations; live owner lookup/saved scope not directly captured"
    consumers = json.loads((HERE / "consumer-comparison.json").read_text())["consumers"]
    providers = json.loads((HERE / "selected-provider-facts.json").read_text())
    zlib_names = {item["name"] for item in providers["u12-zlib-provider"]["exports"]}
    realm = next(row for row in consumers if row["key"] == "fd-im-vector-app")
    zlib_required = [row["spelling"] for row in realm["strong_undefined"] if row["name"] in zlib_names]
    save("results.json", dict(rows=rows, conditional_move_vs_t8=3, incremental_planned_move_vs_u12=2,
        observed_moves=0, current_delivered_u13_incremental_move_vs_u12=0,
        counts=dict(keys=3, consumers=len(consumers), strong_undefined=sum(len(row["strong_undefined"]) for row in consumers),
                    weak_undefined=sum(len(row["weak_undefined"]) for row in consumers),
                    zlib_imports=len(zlib_required)), realm_zlib_imports=zlib_required,
        realm_zlib_note="No direct strong UND zlib imports; retained DT_NEEDED libz.so still must load, as the actual linker errors prove",
        prediction_semantics="Conditional counts require the named complete repair; not submitted candidates, signed window results or t20 gains",
        execution_enabled=False, no_candidates=True, no_device_operations=True))
    save("documentation.json", {"README.md": ["| **`benchmark/2026-10-02-u13-native-load-3/`** | **Window5 Element/Mindustry/Meet exact loading roots:153-provider inventory/1150 UND, U12 zlib coverage, OH audio ABI wall and SoLoader owner scope; read-only, no candidates.** |"],
        ".octos/KNOWLEDGE-DIGEST.md": ["- U13 load3(2026-10-02,cx-bms):窗5Element缺libz已由U12私有alias覆盖不重复算+1；Mindustry同PID19400拒OH绝对路径后19403缺slCreateEngine，5891门面≠05d8实现且PLAY12仍在；Meet先public atfork后lib-main abort，pthread bridge/ABI已有LIBC atfork，015aa已有abort，解包后到重定位不等于权限墙。普通ANL app域数号未打印，B8创建日志不能替代消费者scope证明。3计划条件移动/0实测，新U13相对U12目前0；证据benchmark/2026-10-02-u13-native-load-3/。"]})
    print(json.dumps(dict(keys=len(rows), conditional_t8_moves=3, current_u13_incremental_moves=0,
                          next_planned_incremental_u12_moves=2, observed_moves=0)))


if __name__ == "__main__":
    main()
