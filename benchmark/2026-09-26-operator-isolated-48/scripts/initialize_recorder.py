"""Initialize passive directory descriptor during handler registration; inherit across fork.
No handler ordering, masks, callback return, context or rethrow changes.
"""
import pathlib,json,hashlib,subprocess
w=pathlib.Path.home()/'a2hlab/ws';o=w/'out-isolated48-recorder';root=pathlib.Path(__file__).resolve().parents[1]
s=(w/'out-crash42/recorder/sigchain_musl_diag.cc').read_text()
a=s.index('  // Existing post-fork child entry, outside signal context. No constructor capture.')
b=s.index('  if (g_ohos_native_chain) return;',a)
old=s[a:b]
helper='''static bool crash42_initialized;
static void crash42_prepare_directory() {
  if (crash42_initialized) return;
  const char* dir = getenv("WESTLAKE_CRASH42_DIR");
  if (dir == nullptr) return;
  int saved = errno;
  if (wl_crash_snapshot_init(dir) == 0) {
    crash42_initialized = true;
    static const char ok[] = "[CRASH42] directory ready before fork\\n";
    ssize_t n = write(2, ok, sizeof(ok)-1); (void)n;
  } else {
    static const char failed[] = "[CRASH42] directory init failed\\n";
    ssize_t n = write(2, failed, sizeof(failed)-1); (void)n;
  }
  errno = saved;
}

'''
s=s.replace('void SigchainStartReassert() {',helper+'void SigchainStartReassert() {',1).replace(old,'  crash42_prepare_directory();\n',1)
s=s.replace('void AddSpecialSignalHandlerFn(int signal, void* sa) {','void AddSpecialSignalHandlerFn(int signal, void* sa) {\n  crash42_prepare_directory();',1)
p=o/'sigchain_initialized.cc';p.write_text(s)
sdk=w/'toolchains/ohos-sdk/native'
cmd=[str(sdk/'llvm/bin/clang++'),'--target=aarch64-linux-ohos','--sysroot='+str(sdk/'sysroot'),'-std=c++17','-O2','-g','-fPIC','-Wall','-Wextra','-Werror','-I'+str(root/'native'),'-c',str(p),'-o',str(o/'sigchain-initialized.o')]
subprocess.run(cmd,check=True)
r=json.loads((o/'relink.json').read_text());cmd=r['command'];cmd=[str(o/'sigchain-initialized.o') if x==str(w/'out-crash42/recorder/art/sigchain.o') else x for x in cmd];cmd[cmd.index('-o')+1]=str(o/'libart-initialized.so');subprocess.run(cmd,check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r.update(candidate_sha256=sha(o/'libart-initialized.so'),initialized_source_sha256=sha(p),command=cmd)
(o/'initialized-relink.json').write_text(json.dumps(r,indent=2));print(r['candidate_sha256'])
(root/'native/sigchain_initialized.cc').write_text(s)
