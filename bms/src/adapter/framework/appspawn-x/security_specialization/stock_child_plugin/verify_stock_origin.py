#!/usr/bin/env python3
"""Static proof that route A retains the exact frozen stock appspawn path."""

from __future__ import annotations

import json
import pathlib
import re
import subprocess


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def ordered(text: str, tokens: list[str], label: str) -> None:
    position = -1
    for token in tokens:
        found = text.find(token, position + 1)
        require(found >= 0, f"{label}: missing token: {token}")
        require(found > position, f"{label}: order drift at: {token}")
        position = found


def function(text: str, signature: str, next_signature: str) -> str:
    start = text.find(signature)
    require(start >= 0, f"missing function: {signature}")
    end = text.find(next_signature, start + len(signature))
    require(end > start, f"missing function boundary after: {signature}")
    return text[start:end]


def inert_provider_topology(plugin_source: str, target_build: str,
                            route_build: str) -> bool:
    required = (
        "WLASC_ReceiptConsume",
        "PublishChildHookTable(&request)",
        "WLSCPL_LoadSealedProvider(",
        "load_result.provider_handle, &child_services",
        'resolver(provider_handle,\n                              "WLAR_InstallHostRuntimeServices")',
        'resolver(provider_handle,\n                            "WLAR_EnterAndroidAfterStockSpecialization")',
        "install(services)",
        "entry(request, receipt)",
    )
    forbidden = (
        "RTLD_DEFAULT",
        "RTLD_NEXT",
        "RTLD_GLOBAL",
        "WLAR_ServerPreload(",
        "WLAR_ZygotePreFork(",
        "WLAR_ZygotePostForkParent(",
    )
    if (not all(item in plugin_source for item in required) or
            any(item in plugin_source for item in forbidden)):
        return False
    child = plugin_source[plugin_source.index("static int WestlakeRunAndroidChild("):
                          plugin_source.index("static int WestlakeServerPrepareInert(")]
    loader = plugin_source[plugin_source.index("static int LoadSealedProviderAfterHooks("):
                           plugin_source.index("static int WestlakeRunAndroidChild(")]
    resolver = plugin_source[plugin_source.index("static int InvokeProviderChildEntryWithResolver("):
                             plugin_source.index("static void *ResolveProviderChildSymbol(")]
    target_link = target_build[target_build.index("build_pass()"):
                               target_build.index("build_pass pass1")]
    host_link = route_build[route_build.index("build_stock_host()"):
                            route_build.index("build_stock_host pass1")]
    return (
        child.index("WLASC_ReceiptConsume") <
        child.index("PublishChildHookTable(&request)") <
        child.index("LoadSealedProviderAfterHooks(&request, &receipt)") and
        loader.index("WLSCPL_LoadSealedProvider(") <
        loader.index("InvokeProviderChildEntryWithResolver(") and
        resolver.index('resolver(provider_handle,') <
        resolver.index("install(services)") <
        resolver.index("entry(request, receipt)") and
        "-lwestlake_android_runtime_provider" not in target_link and
        "-lwestlake_android_runtime_provider" not in host_link)


def main() -> int:
    plugin = pathlib.Path(__file__).resolve().parent
    root = plugin.parents[4]
    frozen = root / "adapter/frozen/references/oh-appspawn-security-v7"
    appspawn = frozen / "base/startup/appspawn"

    server = (appspawn / "common/appspawn_server.c").read_text()
    service_path = appspawn / "standard/appspawn_service.c"
    service = service_path.read_text()
    modulemgr = (appspawn / "modules/modulemgr/appspawn_modulemgr.c").read_text()
    common = (appspawn / "modules/common/appspawn_common.c").read_text()
    sandbox = (appspawn /
               "modules/sandbox/normal/appspawn_sandbox_manager.cpp").read_text()
    module_build = (appspawn /
                    "modules/module_engine/BUILD.gn").read_text()
    standard_build = (appspawn / "standard/BUILD.gn").read_text()
    ace_build = (appspawn / "modules/ace_adapter/BUILD.gn").read_text()
    stub = json.loads((appspawn /
                       "modules/module_engine/stub/libappspawn.stub.json").read_text())
    plugin_source = (plugin /
                     "src/westlake_android_child_plugin.c").read_text()
    host_source = (plugin / "src/westlake_stock_host_main.c").read_text()
    target_build = (plugin / "build_target_in_container.sh").read_text()
    route_build = (
        plugin / "build_route_a_generation_in_container.sh"
    ).read_text()

    process = function(service, "static void ProcessSpawnReqMsg(",
                       "static uint32_t g_lastDiedAppId")
    ordered(process, [
        "CheckAppSpawnMsg(message)",
        "CreateAppSpawningCtx()",
        "property->message = message",
        "AppSpawnHookExecute(STAGE_PARENT_PRE_FORK",
        "RunAppSpawnProcessMsg(",
        "AppSpawnHookExecute(STAGE_PARENT_POST_FORK",
        "if (ret != 0)",
        "AddChildWatcher(property)",
    ], "stock parent decoder/fork/result path")

    child = function(server, "int AppSpawnChild(",
                     "static int CloneAppSpawn(")
    ordered(child, [
        "AppSpawnExecuteClearEnvHook(content, client)",
        "AppSpawnExecuteSpawningHook(content, client)",
        "AppSpawnExecutePreReplyHook(content, client)",
        "NotifyResToParent(content, client, 0)",
        "AppSpawnExecutePostReplyHook(content, client)",
        "content->runChildProcessor(content, client)",
    ], "stock child security/result/processor path")

    spawning = function(modulemgr, "int AppSpawnExecuteSpawningHook(",
                        "int AppSpawnExecutePostReplyHook(")
    require(
        "AppSpawnHookExecute(STAGE_CHILD_EXECUTE, HOOK_STOP_WHEN_ERROR" in
        spawning,
        "stage31 is not STOP_WHEN_ERROR",
    )
    require("content->runChildProcessor = loop" in modulemgr,
            "RegChildLooper no longer owns the stock child entry")

    ordered(common, [
        "SetAppAccessToken(content, property)",
        "SetInternetPermission(property)",
        "SetUidGid(content, property)",
        "SetSelinuxCon(content, property)",
    ], "stock token/internet/DAC/SELinux source ownership")
    require("STAGE_CHILD_EXECUTE, HOOK_PRIO_SANDBOX, SetAppSandboxProperty" in
            sandbox, "normal stock sandbox stage31 registration missing")
    require("APP_FLAGS_NO_SANDBOX" in sandbox and
            "APP_FLAGS_IGNORE_SANDBOX" in sandbox,
            "stock bypass behavior evidence missing")

    exports = {entry["name"] for entry in stub}
    required_exports = {
        "AddServerStageHook",
        "AddAppSpawnHook",
        "GetAppSpawnMsgInfo",
        "CheckAppSpawnMsgFlag",
        "RegChildLooper",
    }
    require(required_exports <= exports,
            f"stock host export ABI missing: {required_exports - exports}")
    require("ohos_native_stub_library(\"libappspawn_stub_empty\")" in
            module_build and
            "symlink_target_name = [ \"libappspawn_module_engine.so\" ]" in
            module_build,
            "empty runtime alias provenance changed")

    for source in (
        "common/appspawn_server.c",
        "modules/modulemgr/appspawn_modulemgr.c",
        "standard/appspawn_appmgr.c",
        "standard/appspawn_msgmgr.c",
        "standard/appspawn_service.c",
    ):
        require(source.split("/")[-1] in standard_build,
                f"stock-host source missing from exact GN target: {source}")

    require('module_install_dir = "lib64/appspawn/appspawn"' in ace_build,
            "ACE competing child processor path evidence changed")
    ordered(host_source, [
        "MODULE_DEFAULT",
        "stock_argv[0] = stock_long_proc_name",
        "stock_argv[1] = (char *)0",
        "AppSpawnModuleMgrInstall(WLASC_PLUGIN_NAME)",
        "StartSpawnService(&start_argument",
        "content->runAppSpawn(content, 1, stock_argv)",
    ], "adapter stock-host main")
    require("WLASC_PLUGIN_NAME \"westlake_android_child\"" in host_source,
            "explicit plugin identity missing")
    require("MODULE_APPSPAWN" not in host_source,
            "host would scan and race the ACE child processor")

    for token in (
        "STAGE_PARENT_PRE_FORK",
        "STAGE_CHILD_EXECUTE",
        "WLASC_GUARD_PRIORITY",
        "WLASC_TAIL_PRIORITY",
        "WLSCPL_GetBuildGeneratedManifest",
        "WLSCPL_LoadSealedProvider",
        "InvokeProviderChildEntryWithResolver",
    ):
        require(token in plugin_source, f"plugin contract missing: {token}")
    require(inert_provider_topology(plugin_source, target_build, route_build),
            "plugin/host did not preserve the inert explicit-provider topology")
    for mutant in (
        "WLASC_ReceiptConsume",
        "PublishChildHookTable(&request)",
        "WLSCPL_LoadSealedProvider(",
        "load_result.provider_handle, &child_services",
        "install(services)",
        "entry(request, receipt)",
    ):
        require(not inert_provider_topology(
                    plugin_source.replace(mutant, "mutated", 1),
                    target_build, route_build),
                f"inert provider topology mutant survived: {mutant}")
    require(
        re.search(
            r"g_stock_host_services\.reg_child_looper\(\s*"
            r"&content->content,\s*"
            r"WestlakeRunAndroidChild\s*\)",
            plugin_source,
        ) is not None,
        "plugin contract missing: RegChildLooper stock child entry",
    )
    require("services.reg_child_looper = RegChildLooper;" in host_source,
            "stock host does not bind the RegChildLooper service")
    require("services.clear_child_environment = AppSpawnEnvClear;" in host_source,
            "stock host does not bind the child PRE_RUN cleanup service")
    require("g_stock_host_services.clear_child_environment(content, client);"
            in plugin_source,
            "plugin contract missing: generation-bound child PRE_RUN cleanup")

    forbidden = re.compile(
        r"\b(?:mount|umount2|unshare|chroot|pivot_root|setcon|setexeccon|"
        r"setfscreatecon|SetSelfTokenID|setresuid|setresgid|setgroups)\s*\("
    )
    require(not forbidden.search(plugin_source),
            "plugin duplicates stock security specialization")

    patch_path = plugin / "patches/0001-parent-prefork-stop-on-error.patch"
    with patch_path.open("rb") as patch_stream:
        checked = subprocess.run(
            ["patch", "--dry-run", "--silent", "-p1", "-d", str(frozen)],
            stdin=patch_stream,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    require(checked.returncode == 0,
            "fail-closed parent pre-fork patch no longer applies exactly")
    patch_text = patch_path.read_text()
    require("HOOK_STOP_WHEN_ERROR" in patch_text and
            "SendResponse(connection, &message->msgHeader, ret, 0)" in
            patch_text,
            "parent pre-fork patch does not reject before fork")
    patched_service = (plugin /
        "stock_host_patched/base/startup/appspawn/standard/appspawn_service.c"
    ).read_text()
    require(
        "AppSpawnHookExecute(STAGE_PARENT_PRE_FORK, HOOK_STOP_WHEN_ERROR" in
        patched_service and
        "SendResponse(connection, &message->msgHeader, ret, 0)" in
        patched_service and
        "AppSpawnHookExecute(STAGE_PARENT_PRE_FORK, 0," not in
        patched_service,
        "candidate stock-host service is not fail-closed before fork",
    )

    result = {
        "status": "PASS",
        "route": "A_stock_appspawn_child_processor",
        "stock_decoder": True,
        "stock_fork": True,
        "stock_stage20": True,
        "stock_stage31_stop_when_error": True,
        "stock_result_pipe": True,
        "plugin_security_operations": False,
        "competing_ace_child_processor_loaded": False,
        "required_parent_prefork_delta":
            "standard/appspawn_service.c: ProcessSpawnReqMsg honor stage20 error",
        "candidate_parent_prefork_fail_closed_source": True,
        "product_activation": False,
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
