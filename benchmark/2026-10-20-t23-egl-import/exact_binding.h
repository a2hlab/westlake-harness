#ifndef WL_R23_EXACT_BINDING_H
#define WL_R23_EXACT_BINDING_H
/* Exact a11c ELF metadata only: no application/window object offsets.
 * Relocation subject SHA and full LLVM receipt are recorded in donor-index.json.
 * Outer admission must independently hash the mapped hwui and surface files. */
struct r23_ehdr {unsigned char ident[16];uint16_t type,machine;uint32_t version;uint64_t entry,phoff,shoff;uint32_t flags;uint16_t ehsize,phsize,phnum,shsize,shnum,shstr;};
struct r23_phdr {uint32_t type,flags;uint64_t off,vaddr,paddr,filesz,memsz,align;};
_Static_assert(sizeof(struct r23_ehdr)==64,"ELF64 header");
_Static_assert(sizeof(struct r23_phdr)==56,"ELF64 program header");
static int r23_readable_slot(void *base,uintptr_t offset){
 const struct r23_ehdr*e=base;
 if(memcmp(e->ident,"\177ELF\2\1\1",7) || e->type!=3 || e->machine!=183 || e->ehsize!=64 || e->phsize!=56 || !e->phnum || e->phnum>64 || e->phoff<64 || e->phoff>4096 || e->phoff+(uint64_t)e->phnum*56>4096)return 0;
 const struct r23_phdr*p=(const void*)((const unsigned char*)base+e->phoff);
 for(unsigned i=0;i<e->phnum;i++)if(p[i].type==1 && (p[i].flags&4) && offset>=p[i].vaddr && p[i].memsz>=8 && offset-p[i].vaddr<=p[i].memsz-8)return 1;
 return 0;
}
static int r23_exact_consumer(void *handle,uintptr_t *hwui,void **provider){
 if(!handle)return 0;
 const char *name="_ZN7android29ASurfaceTexture_dequeueBufferEP15ASurfaceTexturePiP19android_dataspace_tP16AHdrMetadataTypeP25android_cta861_3_metadataP26android_smpte2086_metadataPfPjPbPFibPPvSF_S2_SE_EPFiiSE_ESE_P5ARect";
 void *dequeue=dlsym(handle,name);Dl_info owner={0},source={0};
 if(!dequeue || !dladdr(dequeue,&owner) || !owner.dli_fbase || !owner.dli_fname || strcmp(owner.dli_fname,"/data/local/tmp/asx/libhwui.so"))return 0;
 *hwui=(uintptr_t)owner.dli_fbase;
 if((uintptr_t)dequeue-*hwui!=0x80a9c0 || !r23_readable_slot(owner.dli_fbase,0x841850))return 0;
 void *convert=__atomic_load_n((void**)((unsigned char*)owner.dli_fbase+0x841850),__ATOMIC_ACQUIRE);
 if(!convert || convert!=dlsym(handle,"OH_NativeBuffer_FromNativeWindowBuffer") || !dladdr(convert,&source) || !source.dli_fbase || !source.dli_fname || strcmp(leaf(source.dli_fname),"libsurface.z.so") || (uintptr_t)convert-(uintptr_t)source.dli_fbase!=0x64be0)return 0;
 *provider=source.dli_fbase;
 fprintf(stderr,"[WL-R23-BIND] consumer_base=%p convert_slot=%p convert=%p provider_base=%p\n",owner.dli_fbase,(void*)(*hwui+0x841850),convert,source.dli_fbase);return 1;
}
#endif
