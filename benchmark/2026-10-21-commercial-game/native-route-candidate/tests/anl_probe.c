#include "app_native_loader.c"
#include <assert.h>
static int creates,opens;
static char seen_shared[4096],seen_search[16384];
static int ready(void* p){(void)p;return 1;}
static int create(Dl_namespace*b,const char*bn,const char*bs,const char*bp,const char*ss,const char*boot,const WlpbHostOpsV1*ops,void**h,Dl_namespace*a,const char*an,const char*as,const char*ap){
 (void)bs;(void)bp;(void)boot;(void)ops;(void)h;(void)ap;
 creates++;snprintf(a->name,sizeof(a->name),"%s",an);if(b)snprintf(b->name,sizeof(b->name),"%s",bn);
 snprintf(seen_search,sizeof(seen_search),"%s",as);snprintf(seen_shared,sizeof(seen_shared),"%s",ss);return 0;
}
static void* open_ns(Dl_namespace*n,const char*p,int flags){(void)n;(void)p;assert(!(flags&RTLD_GLOBAL));opens++;return (void*)1;}
static const char* native[]={"com.ichi2.anki","com.unciv.app","app.organicmaps","com.nextcloud.client","com.mcdonalds.app","io.anuke.mindustry","com.emn8.mobilem8.nativeapp.bk","im.vector.app","org.mozilla.firefox","org.mozilla.fennec_fdroid","org.videolan.vlc","org.ppsspp.ppsspp","com.shatteredpixel.shatteredpixeldungeon"};
static const char* flutter[]={"chat.fluffy.fluffychat","app.alextran.immich","com.tombursch.kitchenowl","deckers.thibault.aves.libre","com.adilhanney.saber","org.localsend.localsend_app"};
static const char* negative[]={"evil.com.miHoYo.Yuanshen","com.miHoYo.Yuanshen.evil","com.mihoyo.Yuanshen","com.miHoYo.yuanshen","com.DefaultCompany.ZigZag"};
static const char* shared="libc.so:libdl.so:libm.so:libEGL.so:libGLESv3.so:libsurface.z.so:liboh_android_runtime.so:libbionic_compat.so:liblog.so:libc++.so:libwestlake_bionic_pthread_bridge.so";
static void one(const char*root,const char*pkg,int kind,int input){
 char file[4096],dir[4096],generic[4096],expected[4096];
 snprintf(dir,sizeof(dir),"%s/%s",root,pkg);snprintf(generic,sizeof(generic),"%s/common/libnative.so",root);
 snprintf(file,sizeof(file),"%s/%s",dir,kind==2?"libflutter.so":"libnative.so");
 const char*path=input==0?file:generic;
 if(kind==2)path=file;
 AnlDomainConfig cfg={.app_search_paths=input==1?dir:root,.app_permitted_paths=input==2?dir:root,.bridge_search_paths=root,.bridge_permitted_paths=root,.bridge_shared_sonames="liblog.so"};
 AnlDomain*d=NULL;int old=creates;assert(ANL_CreateDomain(&cfg,&d)==0);assert(creates==old+1);
 assert(ANL_Dlopen(d,path,RTLD_NOW));assert(creates==old+(kind?2:1));
 if(kind){
  assert(strstr(seen_search,kind==2?"/westlake_flutter:":"/westlake_native:"));
  snprintf(expected,sizeof(expected),"%s%s",shared,kind==3?":libmediandk.so":"");assert(strcmp(seen_shared,expected)==0);
 }
 int c=creates,o=opens;assert(ANL_Dlopen(d,path,RTLD_NOW));assert(creates==c);assert(opens==o+1);
 c=creates;o=opens;assert(!ANL_Dlopen(d,path,RTLD_NOW|RTLD_GLOBAL));assert(!ANL_Dlopen(d,"/outside/no-file.so",RTLD_NOW));assert(creates==c&&opens==o);
 ANL_ReleaseDomainHandle(d);
}
int main(int argc,char**argv){
 assert(argc==2);AnlRuntimeGateV1 g={0};g.abi_version=ANL_RUNTIME_GATE_ABI_VERSION;g.struct_size=sizeof(g);g.verify_current_thread_ready=ready;
 g.namespace_host_ops=(AnlNamespaceHostOpsV1){.abi_version=ANL_NAMESPACE_HOST_OPS_ABI_VERSION,.struct_size=sizeof(AnlNamespaceHostOpsV1),.runtime_generation=1,.create_configured_namespaces=create,.open_namespace=open_ns};assert(ANL_InstallRuntimeGate(&g)==0);
 for(int i=0;i<13;i++)one(argv[1],native[i],1,0);
 for(int i=0;i<6;i++)one(argv[1],flutter[i],2,0);
 for(int i=0;i<5;i++)for(int input=0;input<3;input++)one(argv[1],negative[i],0,input);
 for(int input=0;input<3;input++)one(argv[1],"com.miHoYo.Yuanshen",CANDIDATE?3:0,input);
 printf("PASS actual ANL 37 domain cases; exact shared strings; load/search/permitted; reuse; GLOBAL/outside rejects\n");return 0;
}
