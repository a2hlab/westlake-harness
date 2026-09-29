"""Apply the reviewed R155 protocol groups to the retained-provider build tree."""
from pathlib import Path
import re,hashlib,json
R=Path.cwd();W=R/'bms/src/.work/b6-real-work';S=R/'bms/src/adapter/framework/appspawn-x';P=W/'adapter/framework/appspawn-x/security_specialization/stock_child_plugin';O=Path.home()/'orca/.bridge-payload/appspawn-x-src/appspawn-x/security_specialization/stock_child_plugin';T=Path(__file__).resolve().parents[1]
receipts=[]
def write(p,s,origin):
 old=p.read_bytes();p.write_text(s);receipts.append({'path':str(p.relative_to(W)),'before_sha256':hashlib.sha256(old).hexdigest(),'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'origin':origin})
def block(s,name):
 m=re.search(r'(?m)^[\w \t*:]+\b'+re.escape(name)+r'\([^;]*?\)\s*\{',s);assert m,name
 start=m.start();a=m.end()-1;n=1;i=a+1
 while n:
  n+=(s[i]=='{')-(s[i]=='}');i+=1
 return start,i,s[start:i]
def replace(s,name,new):
 a,z,_=block(s,name);return s[:a]+new+s[z:]
# G1 service registry preserves its V1 nonnull contract and two-output getter.
for name in ['src/host_runtime_services.c','include/host_runtime_services.h']:
 write(P/name,(S/'security_specialization/stock_child_plugin'/name).read_text(),'repository two-output V1 service registry')
h=P/'src/westlake_stock_host_main.c';text=h.read_text();ref=(S/'security_specialization/stock_child_plugin/src/westlake_stock_host_main.c').read_text();text=replace(text,'InstallPluginHostServices',block(ref,'InstallPluginHostServices')[2])
text=re.sub(r'^static pid_t g_stock_host_parent_pid;\n','',text,flags=re.M);text=re.sub(r'^static WlascInheritAndroidRuntimeV1 g_inherit_android_runtime;\n','',text,flags=re.M)
write(h,text,'repository host V1 service installer; retain task50 namespace fix and current verified-open code')
# G2 V1 child/manifest/hook lifecycle, with live R155 reply completion retained.
current=(P/'src/westlake_android_child_plugin.c').read_text();reply=block(current,'CompleteStockChildReply')[2]
text=(O/'src/westlake_android_child_plugin.c').read_text();pos=text.index('static int WestlakeRunAndroidChild(');text=text[:pos]+reply+'\n\n'+text[pos:]
needle='    if (LoadSealedProviderAfterHooks(&request, &receipt) != 0) {';assert needle in text
text=text.replace(needle,'    if (CompleteStockChildReply(content, client) != 0) return -1;\n\n'+needle)
needle='    WLASC_GATE_MARKER("WLCGATE:LSP:INVOKE_PROVIDER");';assert needle in text
text=text.replace(needle,'''    child_services.open_sealed_exact = WLSCPL_OpenPreparedNamespace;
    child_services.create_configured_namespaces = g_stock_host_services.create_configured_namespaces;
    child_services.open_namespace = g_stock_host_services.open_namespace;
'''+needle)
write(P/'src/westlake_android_child_plugin.c',text,'old payload V1 child plus reviewed three callbacks and stock reply completion')
for name in ['include/sealed_child_provider_loader.h','src/sealed_child_provider_loader.c','include/westlake_child_hook_table_v1.h','src/child_hook_table_v1.c']:
 write(P/name,(O/name).read_text(),'old payload V1 production source')
p=P/'include/sealed_child_provider_loader.h';text=p.read_text().replace('/* Build-generated, immutable', 'void *WLSCPL_OpenPreparedNamespace(const char *absolute_path, int flags);\n\n/* Build-generated, immutable');write(p,text,'R155 exported canonical sealed-open callback')
p=P/'src/sealed_child_provider_loader.c';text=p.read_text();text=text.replace('    static Dl_namespace closure_namespace;\n    static int namespace_prepared;\n','')
pos=text.index('static void *RealOpenLocalNow(')
text=text[:pos]+'''static Dl_namespace closure_namespace;
static int namespace_prepared;

void *WLSCPL_OpenPreparedNamespace(const char *absolute_path, int flags)
{
    const char prefix[] = "/system/android/lib64/";
    if (namespace_prepared != 1 || !AbsoluteCanonicalForm(absolute_path) ||
        strncmp(absolute_path, prefix, sizeof(prefix) - 1U) != 0 ||
        absolute_path[sizeof(prefix) - 1U] == '\\0' ||
        (flags & (RTLD_NOW | RTLD_GLOBAL)) != RTLD_NOW) return NULL;
    return dlopen(absolute_path, flags);
}

'''+text[pos:]
text=text.replace('!ExactLowerHex(artifact->build_id_hex, 40U) ||\n            !HexHasNonzeroDigit(artifact->build_id_hex, 40U)', '(!ExactLowerHex(artifact->build_id_hex, 40U) && !ExactLowerHex(artifact->build_id_hex, 32U)) ||\n            !HexHasNonzeroDigit(artifact->build_id_hex, strlen(artifact->build_id_hex))')
write(p,text,'R155 sealed-open 0x31f0 admission and shared prepared state; retain 16/20-byte build IDs')
# Generate the V1 records using actual provider hashes. Keep current metadata generation.
p=P/'build_target_in_container.sh';text=p.read_text();old=(O/p.name).read_text();a=old.index('generate_sealed_manifest()');z=old.index('\nbuild_pass()',a);part=old[a:z].replace('len(build_ids[0]) != 40','len(build_ids[0]) not in (32, 40)')
a=text.index('generate_sealed_manifest()');z=text.index('\nbuild_pass()',a);text=text[:a]+part+text[z:];write(p,text,'old payload V1 manifest emitter; retain current build and identity metadata')
# G1/G3 provider: validated direct sequence and old environment/stack, with runtime callbacks.
p=P/'src/westlake_android_runtime_provider.cpp';text=(O/'src/westlake_android_runtime_provider.cpp').read_text()
text=text.replace('#include "runtime_loader_phase.h"','#include "runtime_loader_phase.h"\nextern "C" int WLNL_InstallSealedOpenV1(WlascOpenSealedExactV1);')
text=text.replace('context->runtime->startVm()','context->runtime->startVm(false)')
text=text.replace('    return WLAR_HostServicesGetPthreadBridgeOps(\n               &gHostServicesRegistry, &gate.pthread_bridge_ops) == 0 &&', '    return WLAR_HostServicesGetNamespaceCallbacks(\n               &gHostServicesRegistry, &gate.create_configured_namespaces, &gate.open_namespace) == 0 &&\n           WLAR_HostServicesGetPthreadBridgeOps(\n               &gHostServicesRegistry, &gate.pthread_bridge_ops) == 0 &&')
text=text.replace('ProviderGeneration(), kProviderGenerationSha, services) != 0) {','ProviderGeneration(), kProviderGenerationSha, services) != 0 ||\n        WLNL_InstallSealedOpenV1(services->open_sealed_exact) != 0) {')
text=text.replace('    if (context == nullptr || !SetRequiredEnvironment() ||','    struct rlimit previousStack{};\n    if (context == nullptr || getrlimit(RLIMIT_STACK, &previousStack) != 0 || !SetRequiredEnvironment() ||')
write(p,text,'old payload validated direct sequence plus RESTORE-PLAN G1/G3 gaps')
# Drop retired public V2/inheritance exports (identity checks are retained).
for name in ['westlake_android_child_plugin.map','westlake_android_runtime_provider.map']:
 p=P/name;text=p.read_text();text='\n'.join(l for l in text.splitlines() if 'WLSCPL_InheritAndroidRuntimeV1' not in l and 'WLAR_PrepareA02PrerequisiteBundleV2' not in l)+'\n';write(p,text,'remove retired V2/inheritance exports')
(T/'source-edits.json').write_text(json.dumps(receipts,indent=2)+'\n')
print('restored source groups',len(receipts))
