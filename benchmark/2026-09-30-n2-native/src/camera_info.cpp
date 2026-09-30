/* Camera1 metadata projected from OH6.1's actual camera list. No capture HAL
 * or synthetic camera: errors stay errors and an empty list returns zero.
 * AOSP14 android_hardware_Camera_getCameraInfo supplies field/error semantics;
 * OH SDK headers in oh-camera pin the platform ABI. */
#include <jni.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include "oh-camera/camera.h"
#include "oh-camera/camera_device.h"

namespace android {
namespace {
struct CameraOps {
    void* handle;
    Camera_ErrorCode (*create)(Camera_Manager**);
    Camera_ErrorCode (*destroy)(Camera_Manager*);
    Camera_ErrorCode (*list)(Camera_Manager*,Camera_Device**,uint32_t*);
    Camera_ErrorCode (*free_list)(Camera_Manager*,Camera_Device*,uint32_t);
    Camera_ErrorCode (*orientation)(Camera_Device*,uint32_t*);
    bool ready;
};
CameraOps ops{};
pthread_once_t once=PTHREAD_ONCE_INIT;
void loadOps() {
    ops.handle=dlopen("/system/lib64/ndk/libohcamera.so",RTLD_NOW|RTLD_LOCAL);
    if (!ops.handle) { fprintf(stderr,"[N2-Camera] backend unavailable: %s\n",dlerror());return; }
#define LOOKUP(member,name) ops.member=reinterpret_cast<decltype(ops.member)>(dlsym(ops.handle,name))
    LOOKUP(create,"OH_Camera_GetCameraManager");
    LOOKUP(destroy,"OH_Camera_DeleteCameraManager");
    LOOKUP(list,"OH_CameraManager_GetSupportedCameras");
    LOOKUP(free_list,"OH_CameraManager_DeleteSupportedCameras");
    LOOKUP(orientation,"OH_CameraDevice_GetCameraOrientation");
#undef LOOKUP
    ops.ready=ops.create && ops.destroy && ops.list && ops.free_list && ops.orientation;
}
void fail(JNIEnv* env,const char* message) {
    jclass c=env->FindClass("java/lang/RuntimeException");
    if(c) {env->ThrowNew(c,message);env->DeleteLocalRef(c);}
}
struct CameraList {
    Camera_Manager* manager=nullptr;Camera_Device* devices=nullptr;uint32_t count=0;
    ~CameraList(){if(devices) ops.free_list(manager,devices,count);if(manager) ops.destroy(manager);}
    bool get(JNIEnv* env) {
        pthread_once(&once,loadOps);
        if(!ops.ready){fail(env,"Camera backend unavailable");return false;}
        if(ops.create(&manager)!=CAMERA_OK || !manager){fail(env,"Camera manager unavailable");return false;}
        if(ops.list(manager,&devices,&count)!=CAMERA_OK){fail(env,"Fail to enumerate cameras");return false;}
        if(count && !devices){fail(env,"Invalid camera list");return false;}
        fprintf(stderr,"[N2-Camera] actual supported cameras=%u\n",count);return true;
    }
};
jint number(JNIEnv* env,jclass) {CameraList list;return list.get(env)?static_cast<jint>(list.count):0;}
void info(JNIEnv* env,jclass,jint cameraId,jboolean overrideToPortrait,jobject out) {
    CameraList list;if(!list.get(env))return;
    if(cameraId<0 || static_cast<uint32_t>(cameraId)>=list.count){fail(env,"Unknown camera ID");return;}
    if(!out){fail(env,"Null camera info");return;}
    Camera_Device* device=&list.devices[cameraId];uint32_t orientation=0;
    if(ops.orientation(device,&orientation)!=CAMERA_OK){fail(env,"Fail to get camera info");return;}
    if(overrideToPortrait){fail(env,"Portrait camera override is not supported");return;}
    if(device->cameraPosition!=CAMERA_POSITION_BACK && device->cameraPosition!=CAMERA_POSITION_FRONT){fail(env,"Unsupported camera position");return;}
    jclass c=env->GetObjectClass(out);
    jfieldID facing=env->GetFieldID(c,"facing","I"), rotation=env->GetFieldID(c,"orientation","I"),sound=env->GetFieldID(c,"canDisableShutterSound","Z");
    if(!env->ExceptionCheck()) {
        env->SetIntField(out,facing,device->cameraPosition==CAMERA_POSITION_FRONT?1:0);
        env->SetIntField(out,rotation,static_cast<jint>(orientation));
        // Capture/shutter controls are not implemented; never advertise suppression.
        env->SetBooleanField(out,sound,JNI_FALSE);
    }
    env->DeleteLocalRef(c);
}
}
int register_n2_Camera(JNIEnv* env) {
    jclass c=env->FindClass("android/hardware/Camera");if(!c)return -1;
    JNINativeMethod methods[]={
        {"getNumberOfCameras","()I",reinterpret_cast<void*>(number)},
        {"_getCameraInfo","(IZLandroid/hardware/Camera$CameraInfo;)V",reinterpret_cast<void*>(info)}
    };
    int rc=env->RegisterNatives(c,methods,2);env->DeleteLocalRef(c);
    fprintf(stderr,"[N2-Camera] metadata registration=%d\n",rc);return rc;
}
}
