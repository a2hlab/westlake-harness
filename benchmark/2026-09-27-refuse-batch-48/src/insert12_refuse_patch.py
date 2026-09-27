import sys
f=sys.argv[1]; s=open(f).read()
add='''    /* #48 A.22 security-batch: byte-security / RASP libs, ALL needed_by=0 (dlopen-only,
     * verified via APK-wide reverse DT_NEEDED across 138 libs). EXCLUDES libsscronet.so
     * (network engine, r1 feed-essential, 4 dependents) and libttcrypto.so (HTTPS/TLS core,
     * 15 dependents incl ttboringssl/sscronet). Tests whether the residual whole-heap smash
     * comes from these libs writing Bionic-layout metadata; feed-essentiality checked by the A/B. */
    "libEncryptor.so",
    "libencrypt.so",
    "libgecko_encrypt.so",
    "libropaencrypt.so",
    "liblynxsecurity.so",
    "libjato.so",
    "libmetasec_ml.so",
    "libmonitorcollector-lib.so",
    "libgodzilla-lib.so",
    "libgodzilla-memsponge.so",
    "libgodzilla-sysopt.so",
    "libsysoptimizer.so",
'''
i=s.index('g_refused_libraries[] = {'); j=s.index('\n};', i)
s2=s[:j]+'\n'+add.rstrip('\n')+s[j:]
assert s2.count('g_refused_libraries[] = {')==1 and s2!=s
open(f,'w').write(s2); print("appended 12 (preserving delivery 3-lib block)")
