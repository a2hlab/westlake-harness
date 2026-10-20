#pragma once
#include <cstdint>
#include <map>
#include <string>
#include <cerrno>
using jint=int32_t; using jlong=int64_t; using jboolean=uint8_t; using jfloat=float;
using jobject=void*; using jclass=void*; using jfieldID=void*; using jmethodID=void*; using jfloatArray=void*;
constexpr jint JNI_OK=0, JNI_VERSION_1_6=0x10006;
constexpr jboolean JNI_TRUE=1,JNI_FALSE=0;
struct JNINativeMethod { const char* name; const char* signature; void* fnPtr; };
struct JavaVMAttachArgs { jint version; char* name; jobject group; };
struct JNIEnv;
void peer_event(const std::string&);
extern bool peer_exception;
extern bool peer_find_failure;
extern int peer_exception_errno;
extern std::map<std::pair<jobject,jfieldID>,jlong> peer_fields;
struct JavaVM {
 jint GetEnv(void**,jint){return -1;}
 jint AttachCurrentThreadAsDaemon(JNIEnv**,JavaVMAttachArgs*){return -1;}
 jint DetachCurrentThread(){return 0;}
};
struct JNIEnv {
 jlong GetLongField(jobject obj,jfieldID id){peer_event("get:"+std::to_string(reinterpret_cast<uintptr_t>(id)));return peer_fields[{obj,id}];}
 void SetLongField(jobject obj,jfieldID id,jlong value){peer_event("set:"+std::to_string(reinterpret_cast<uintptr_t>(id))+":"+(value?"nonzero":"zero"));peer_fields[{obj,id}]=value;}
 jclass FindClass(const char* name){peer_event(std::string("find:")+name);if(peer_exception_errno)errno=peer_exception_errno;return peer_find_failure?nullptr:reinterpret_cast<jclass>(100);}
 jint ThrowNew(jclass,const char* message){peer_event(std::string("throw:")+message);peer_exception=true;if(peer_exception_errno)errno=peer_exception_errno+1;return 0;}
 void DeleteLocalRef(jobject){peer_event("delete-local");if(peer_exception_errno)errno=peer_exception_errno+2;}
 jboolean ExceptionCheck(){peer_event("exception-check");return peer_exception;}
 void ExceptionClear(){peer_event("exception-clear");peer_exception=false;}
 void ExceptionDescribe(){peer_event("exception-describe");}
 jfieldID GetFieldID(jclass,const char*,const char*){return reinterpret_cast<jfieldID>(1);}
 jmethodID GetStaticMethodID(jclass,const char*,const char*){return reinterpret_cast<jmethodID>(1);}
 void CallStaticVoidMethod(jclass,jmethodID,jobject){}
 jint RegisterNatives(jclass,const JNINativeMethod*,jint){return 0;}
 jint GetJavaVM(JavaVM**){return -1;}
 jobject NewGlobalRef(jobject o){return o;}
 void DeleteGlobalRef(jobject){}
 jclass GetObjectClass(jobject){return reinterpret_cast<jclass>(100);}
 jint GetArrayLength(jfloatArray){return 16;}
 void SetFloatArrayRegion(jfloatArray,jint,jint,const jfloat*){}
};
