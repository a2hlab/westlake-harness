// Host fixture prelude only. The tested lambdas are extracted unchanged from the candidate.
// ELF header layout follows the ELF ABI (64/52 bytes); no OH service code is simulated.
#include <cstdint>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>
#include <iostream>
#include <sys/stat.h>
#include <zlib.h>
#include <CommonCrypto/CommonDigest.h>
#define EI_NIDENT 16
#define EI_CLASS 4
#define EI_DATA 5
#define EI_VERSION 6
#define ELFMAG "\177ELF"
#define SELFMAG 4
#define ELFDATA2LSB 1
#define ELFCLASS64 2
#define ELFCLASS32 1
#define EV_CURRENT 1
#define ET_DYN 3
#define EM_AARCH64 183
#define EM_ARM 40
#define BUFFER_SIZE 4096
#define LOG_I(...) ((void)0)
struct Elf64_Ehdr {
    unsigned char e_ident[16];
    uint16_t e_type,e_machine;
    uint32_t e_version;
    uint64_t e_entry,e_phoff,e_shoff;
    uint32_t e_flags;
    uint16_t e_ehsize,e_phentsize,e_phnum,e_shentsize,e_shnum,e_shstrndx;
};
struct Elf32_Ehdr {
    unsigned char e_ident[16];
    uint16_t e_type,e_machine;
    uint32_t e_version,e_entry,e_phoff,e_shoff,e_flags;
    uint16_t e_ehsize,e_phentsize,e_phnum,e_shentsize,e_shnum,e_shstrndx;
};
static_assert(sizeof(Elf64_Ehdr)==64 && sizeof(Elf32_Ehdr)==52, "ELF ABI");
std::string Sha256File(const std::string &path)
{
    std::ifstream in(path,std::ios::binary); if(!in)return "";
    CC_SHA256_CTX ctx; CC_SHA256_Init(&ctx);
    char b[4096];
    while(in.read(b,sizeof(b)) || in.gcount()>0)CC_SHA256_Update(&ctx,b,(CC_LONG)in.gcount());
    if(in.bad())return "";
    unsigned char hash[CC_SHA256_DIGEST_LENGTH];CC_SHA256_Final(hash,&ctx);
    const char hex[]="0123456789abcdef";std::string out;
    for(auto v:hash){out+=hex[v>>4];out+=hex[v&15];}return out;
}
// Mac fixtures cannot chown root. Override only uid/gid from CLI; real lstat still
// supplies file type, mode, size and symlink status. This is not an OH ownership test.
int fixtureUid=0,fixtureGid=0;
int fixture_lstat(const char *path, struct stat *st)
{
    int ret=::lstat(path,st);
    if(!ret){st->st_uid=fixtureUid;st->st_gid=fixtureGid;}
    return ret;
}
#define lstat fixture_lstat
int main(int argc,char **argv)
{
    if(argc!=10)return 3;
    const std::string mode=argv[1],path=argv[2],name=argv[3],bundleName=argv[4];
    struct {std::string cpuAbi;} extractParam{argv[5]};
    struct ZipEntry {uint64_t uncompressedSize;uint32_t crc;};
    ZipEntry entry{std::stoull(argv[6]),(uint32_t)std::stoul(argv[7])};
    fixtureUid=std::stoi(argv[8]);fixtureGid=std::stoi(argv[9]);
