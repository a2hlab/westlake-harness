#!/usr/bin/env python3
"""Generate review-only, single-source-file patches; never change source inputs."""
from pathlib import Path
import difflib, hashlib, json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OH = Path('/Users/zhaoyue/orca/adapter-local/oh-headers')
REL = Path('foundation/bundlemanager/bundle_framework/services/bundlemgr/src')
CANONICAL = ROOT/'bms/src/adapter/ohos_patches'/REL/'installd/installd_operator.cpp.patch'

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def current_function():
    # Extract the complete newly-added function from the checked-in patch.
    lines=CANONICAL.read_text().splitlines()
    first=lines.index('+bool InstalldOperator::ExtractApkNativeFiles(const ExtractParam &extractParam)')
    last=next(i for i in range(first+1,len(lines)) if lines[i].startswith('+// adapter project: APK_RESOURCES_HAP'))
    assert all(x.startswith('+') for x in lines[first:last])
    return '\n'.join(x[1:] for x in lines[first:last])+'\n'

def once(text, before, after):
    assert text.count(before)==1, f'expected one occurrence: {before[:100]}'
    return text.replace(before,after,1)

def candidate_function(original, exceptions):
    table='\n'.join('        {"%s", "%s", "%s", "%s"},' % (e['bundle'],e['abi'],e['filename'],e['sha256']) for e in exceptions)
    addition='''    // #77 review candidate. The table is generated from native-data-exceptions.json.
    // No generic .zip.so bypass: retain strict ELF checks for all other bytes.
    // Copy exact reviewed payloads intact, including an ARM32 artifact packaged in arm64.\n    // This is extraction compatibility, not permission/ability to load them as ARM64 DSOs.
    struct DataPayloadException {
        const char *bundle;
        const char *abi;
        const char *name;
        const char *sha256;
    };
    const DataPayloadException dataPayloadExceptions[] = {
'''+table+'''
    };
    auto checkPayload = [&](const std::string &path, const std::string &name) {
        if (checkElf(path)) {
            return true;
        }
        for (const auto &exception : dataPayloadExceptions) {
            if (bundleName == exception.bundle && extractParam.cpuAbi == exception.abi &&\n                name == exception.name && Sha256File(path) == exception.sha256) {
                LOG_I(BMS_TAG_INSTALLD, "accepted reviewed APK payload exception %{public}s", name.c_str());
                return true;
            }
        }
        return false;
    };
'''
    result=once(original,'    auto verifyOutput = [&checkElf](const std::string &path, const ZipEntry &entry) {',
                addition+'    auto verifyOutput = [&checkPayload](const std::string &path, const ZipEntry &entry,\n        const std::string &name) {')
    result=once(result,'static_cast<uint32_t>(crc) == entry.crc && checkElf(path);',
                'static_cast<uint32_t>(crc) == entry.crc && checkPayload(path, name);')
    result=once(result,'!verifyOutput(outputPath, entry)', '!verifyOutput(outputPath, entry, targetName)')
    result=once(result,'return failAndClean("CRC/ELF/owner/mode verification failed");',
                'return failAndClean("CRC/payload/owner/mode verification failed: " + targetName);')
    return result

def diff(before,after,rel):
    return ''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
                                       fromfile='a/'+str(rel),tofile='b/'+str(rel)))

def main():
    payloads=json.loads((HERE/'evidence/seal-payloads.json').read_text())
    inputs=json.loads((HERE/'evidence/inputs.json').read_text())
    for r in inputs: assert sha(r['path'])==r['sha256']
    exceptions=[{'bundle':'com.junkfood.seal','abi':'arm64-v8a',
        'filename':Path(e['entry']).name,'sha256':e['sha256'],'bytes':e['bytes'],
        'apk_sha256':inputs[0]['sha256'],'status':'draft','approved_by':None,
        'reason':'Packaged ZIP data consumed by app, not a loadable ELF DSO.',
        'evidence':'evidence/seal-payloads.json:'+str(next(i for i,l in enumerate((HERE/'evidence/seal-payloads.json').read_text().splitlines(),1) if e['entry'] in l))}
        for e in payloads if e['entry'].endswith('.zip.so')]
    toutiao=json.loads((HERE/'evidence/toutiao-payload.json').read_text())
    exceptions.append({'bundle':'com.ss.android.article.news','abi':'arm64-v8a',
        'filename':'libcvt.so','sha256':toutiao['sha256'],'bytes':toutiao['bytes'],
        'apk_sha256':inputs[2]['sha256'],'status':'draft','approved_by':None,
        'reason':'Preserve the exact ARM32 artifact as packaged, as prior raw extraction did. This does not enable ARM64 loading; consumer reachability is unknown.',
        'evidence':'evidence/toutiao-payload.json:2'})
    (HERE/'native-data-exceptions.json').write_text(json.dumps(exceptions,indent=2)+'\n')
    original=current_function();candidate=candidate_function(original,exceptions)
    # Baseline is the checked-in current function, including the existing EI_VERSION=0 exception.
    # Do NOT use the older OH headers copy as the complete native-function baseline.
    oldfile=(OH/REL/'installd/installd_operator.cpp').read_text()
    start=oldfile.index('bool InstalldOperator::ExtractApkNativeFiles(')
    end=oldfile.index('// adapter project: APK_RESOURCES_HAP',start)
    baseline=oldfile[:start]+original+oldfile[end:]
    updated=oldfile[:start]+candidate+oldfile[end:]
    (HERE/'patches/0002-native-exact-payloads.patch').write_text(
        diff(baseline,updated,REL/'installd/installd_operator.cpp'))
    manifest=(OH/REL/'base_bundle_installer.cpp').read_text()
    manifest_new=once(manifest,'constexpr int kJsonBufSize = 65536;',
        'constexpr int kJsonBufSize = 1024 * 1024;')
    (HERE/'patches/0001-reuse-manifest-1mib.patch').write_text(
        diff(manifest,manifest_new,REL/'base_bundle_installer.cpp'))
    (HERE/'evidence/patch-provenance.json').write_text(json.dumps({
        'canonical_native_patch':str(CANONICAL),'canonical_native_patch_sha256':sha(CANONICAL),
        'oh_source_root':str(OH),'old_manifest_source_sha256':sha(OH/REL/'base_bundle_installer.cpp'),
        'baseline_native_function_sha256':hashlib.sha256(original.encode()).hexdigest(),
        'candidate_native_function_sha256':hashlib.sha256(candidate.encode()).hexdigest(),
        'native_candidate_status':'draft for outer review, not installed',
        'manifest_rule':'Existing repository/real-work 1 MiB caller capacity; producer NUL-inclusive bound unchanged',
    },indent=2)+'\n')

if __name__=='__main__':main()
