#include <jni.h>
#include <native_image/native_image.h>
#include <vector>
#include <iostream>
#include <cassert>
#include <sstream>
#include <cerrno>
#include <unistd.h>
#include <sys/stat.h>
std::vector<std::string> events;
bool peer_exception=false,peer_find_failure=false;
int peer_exception_errno=0, provider_rc=0, provider_errno=71, ref_rc=0, unref_rc=0;
std::map<std::pair<jobject,jfieldID>,jlong> peer_fields;
void peer_event(const std::string& text){int saved=errno;events.push_back(text);errno=saved;}
int provider(const std::string& name){peer_event(name+":errno-in="+std::to_string(errno));errno=provider_errno;return provider_rc;}
extern "C" {
OH_NativeImage* OH_NativeImage_CreateWithSingleBufferMode(uint32_t,uint32_t,bool){return nullptr;}
OHNativeWindow* OH_NativeImage_AcquireNativeWindow(OH_NativeImage*){return nullptr;}
void OH_NativeImage_Destroy(OH_NativeImage**){peer_event("destroy-image");}
int32_t OH_ConsumerSurface_SetDefaultSize(OH_NativeImage*,int32_t,int32_t){return provider("size");}
int32_t OH_NativeImage_SetOnFrameAvailableListener(OH_NativeImage*,OH_OnFrameAvailableListener){return provider("listener");}
int32_t OH_NativeImage_UnsetOnFrameAvailableListener(OH_NativeImage*){return provider("unlisten");}
int32_t OH_NativeImage_UpdateSurfaceImage(OH_NativeImage*){return provider("update");}
int32_t OH_NativeImage_ReleaseTextImage(OH_NativeImage*){return provider("release-text");}
int32_t OH_NativeImage_DetachContext(OH_NativeImage*){return provider("detach");}
int32_t OH_NativeImage_AttachContext(OH_NativeImage*,uint32_t tex){return provider("attach:"+std::to_string(tex));}
int32_t OH_NativeImage_GetTransformMatrix(OH_NativeImage*,float*){return provider("matrix");}
int64_t OH_NativeImage_GetTimestamp(OH_NativeImage*){return provider("timestamp");}
int32_t OH_NativeImage_Release(OH_NativeImage*){return provider("release");}
int32_t OH_NativeWindow_NativeObjectReference(void* p){provider("ref:"+std::to_string(static_cast<OHNativeWindow*>(p)->id));return ref_rc;}
int32_t OH_NativeWindow_NativeObjectUnreference(void* p){provider("unref:"+std::to_string(static_cast<OHNativeWindow*>(p)->id));return unref_rc;}
int32_t OH_NativeWindow_NativeWindowHandleOpt(OHNativeWindow*,int,...){return provider("opt");}
}
// Include complete original/derived TUs without editing or extracting method bodies.
#include PEER_SURFACE_SOURCE
#include PEERER_TEXTURE_SOURCE

using namespace android;
JNIEnv env;
OH_NativeImage image{1};
OHNativeWindow first{1},second{2};
jobject object=reinterpret_cast<jobject>(11), view=reinterpret_cast<jobject>(12);
void reset(OhSurfaceTextureState& state){
 events.clear();peer_fields.clear();peer_exception=false;peer_find_failure=false;peer_exception_errno=0;
 provider_rc=0;provider_errno=71;ref_rc=0;unref_rc=0;state.image=&image;state.nativeWindow=&second;
 state.magic=kSurfaceTextureMagic;state.released=false;state.detached=false;state.texName=7;
 gFields.surfaceTexture=reinterpret_cast<jfieldID>(1);gFields.producer=reinterpret_cast<jfieldID>(2);
 gTextureViewNativeWindow=reinterpret_cast<jfieldID>(3);
 peer_fields[{object,gFields.surfaceTexture}]=reinterpret_cast<jlong>(&state);
 errno=37;
}
void output(const std::string& name,int result,OhSurfaceTextureState& state){
 int saved=errno;auto value=peer_fields[{view,gTextureViewNativeWindow}];
 int window=value?reinterpret_cast<OHNativeWindow*>(value)->id:0;
 std::cout<<"{\"case\":\""<<name<<"\",\"return\":"<<result<<",\"errno\":"<<saved
 <<",\"exception\":"<<peer_exception<<",\"detached\":"<<state.detached
 <<",\"tex\":"<<state.texName<<",\"window\":"<<window<<",\"events\":[";
 for(size_t i=0;i<events.size();++i){if(i)std::cout<<",";std::cout<<"\""<<events[i]<<"\"";}
 std::cout<<"]}\n";
}
void identity(OhSurfaceTextureState& state){
 int saved=errno;struct stat st{};assert(fstat(2,&st)==0 && S_ISREG(st.st_mode));
 fprintf(stderr,"[PEER-IDENTITY] state=%p image=%p first=%p second=%p pid=%x regular=1 stderr_dev=%llx stderr_ino=%llx\n",
         static_cast<void*>(&state),static_cast<void*>(&image),static_cast<void*>(&first),static_cast<void*>(&second),
         static_cast<unsigned>(getpid()),static_cast<unsigned long long>(st.st_dev),static_cast<unsigned long long>(st.st_ino));
 fflush(stderr);errno=saved;
}
int main(int argc,char** argv){
 std::string selected=argc==3&&std::string(argv[1])=="--case"?argv[2]:"";
 int executed=0;
 OhSurfaceTextureState state;
 for(const auto* op:{"attach","detach","update"}){
  for(const auto* variant:{"ok","error","null-object","null-state","bad-magic","null-image","released","exception-find-fails","exception-errno"}){
   std::string v=variant,o=op;
   if(!selected.empty()&&selected!=o+"/"+v)continue;
   ++executed;reset(state);jobject arg=object;
   if(v=="error"||v=="exception-find-fails"||v=="exception-errno")provider_rc=-23;
   if(v=="null-object")arg=nullptr;
   if(v=="null-state")peer_fields[{object,gFields.surfaceTexture}]=0;
   if(v=="bad-magic")state.magic=0;
   if(v=="null-image")state.image=nullptr;
   if(v=="released")state.released=true;
   if(v=="exception-find-fails")peer_find_failure=true;
   if(v=="exception-errno")peer_exception_errno=81;
   identity(state);int result=0;
   if(o=="attach")result=SurfaceTexture_nativeAttachToGLContext(&env,arg,42);
   if(o=="detach")result=SurfaceTexture_nativeDetachFromGLContext(&env,arg);
   if(o=="update")SurfaceTexture_nativeUpdateTexImage(&env,arg);
   bool invalid=v=="null-object"||v=="null-state"||v=="bad-magic"||v=="null-image";
   if(o!="update")assert(result==(invalid?-1:provider_rc));
   if(o=="attach")assert(state.texName==(!invalid&&provider_rc==0?42:7));
   if(o=="detach")assert(state.detached==(!invalid&&provider_rc==0));
   output(o+"/"+v,result,state);
  }
 }
 for(const auto* variant:{"different","alias","old-null","new-null","both-null","released","invalid-state","null-object","ref-unref-error","existing-exception","destroy","destroy-null","field-unset"}){
  std::string v=variant;
  if(!selected.empty()&&selected!="producer/"+v)continue;
  ++executed;reset(state);jobject arg=object;
  peer_fields[{view,gTextureViewNativeWindow}]=reinterpret_cast<jlong>(&first);
  if(v=="alias")state.nativeWindow=&first;
  if(v=="old-null"||v=="both-null"||v=="destroy-null")peer_fields[{view,gTextureViewNativeWindow}]=0;
  if(v=="new-null"||v=="both-null")state.nativeWindow=nullptr;
  if(v=="released")state.released=true;
  if(v=="invalid-state")state.magic=0;
  if(v=="null-object")arg=nullptr;
  if(v=="ref-unref-error"){provider_rc=-29;ref_rc=-29;unref_rc=-31;}
  if(v=="existing-exception")peer_exception=true;
  if(v=="field-unset")gTextureViewNativeWindow=nullptr;
  identity(state);
  if(v=="destroy"||v=="destroy-null"||v=="field-unset")TextureView_nDestroyNativeWindow(&env,view);
  else TextureView_nCreateNativeWindow(&env,view,arg);
  output("producer/"+v,0,state);
 }
 assert(executed==(selected.empty()?40:1));
 return 0;
}
