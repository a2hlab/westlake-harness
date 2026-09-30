/* Explicit six-package EGL facade. Window operations are supplied by the
 * existing U5 HWUI owner; no copied interposition or second HWUI instance.
 * ABI matches Khronos EGL (pointer handles, 32-bit EGLint/EGLBoolean). */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef void *Handle;
typedef unsigned Boolean;
typedef void (*Proc)(void);
typedef void *(*Resolver)(const char *);
static Resolver owner;
static Handle (*create_surface)(Handle,Handle,void *,const int *);
static Boolean (*destroy_surface)(Handle,Handle);
static Boolean (*swap)(Handle,Handle);
static Boolean (*damage)(Handle,Handle,const int *,int);
static Proc (*get_proc)(const char *);
__attribute__((visibility("default")))
int westlake_flutter_egl_bind(Resolver resolve) {
    if (!resolve || owner) return -1;
    create_surface=(void *)resolve("eglCreateWindowSurface");
    destroy_surface=(void *)resolve("eglDestroySurface");
    swap=(void *)resolve("eglSwapBuffers");
    damage=(void *)resolve("eglSwapBuffersWithDamageKHR");
    get_proc=(void *)resolve("eglGetProcAddress");
    if (!create_surface || !destroy_surface || !swap || !damage || !get_proc) return -1;
    owner=resolve;
    fprintf(stderr,"[N7-EGL] bound resident HWUI create=%p swap=%p platform destroy=%p\n",(void *)create_surface,(void *)swap,(void *)destroy_surface);
    return 0;
}
Handle eglCreateWindowSurface(Handle d,Handle c,void *w,const int *a) {
    if (!owner) return NULL;
    fprintf(stderr,"[N7-EGL] enter resident HWUI window=%p\n",w);
    Handle s=create_surface(d,c,w,a);
    fprintf(stderr,"[N7-EGL] resident HWUI surface=%p\n",s);
    return s;
}
Boolean eglDestroySurface(Handle d,Handle s) { return owner?destroy_surface(d,s):0; }
Boolean eglSwapBuffers(Handle d,Handle s) { return owner?swap(d,s):0; }
Boolean eglSwapBuffersWithDamageKHR(Handle d,Handle s,const int *r,int n) { return owner?damage(d,s,r,n):0; }
Proc eglGetProcAddress(const char *name) {
    if (!name || !owner) return NULL;
#define SELF(n) if (!strcmp(name,#n)) return (Proc)&n
    SELF(eglCreateWindowSurface); SELF(eglDestroySurface); SELF(eglSwapBuffers);
    SELF(eglSwapBuffersWithDamageKHR); SELF(eglGetProcAddress);
#undef SELF
    if (!strcmp(name,"eglSwapBuffersWithDamageEXT")) return (Proc)&eglSwapBuffersWithDamageKHR;
    Proc p=(Proc)owner(name);
    return p?p:get_proc(name);
}
/* Signatures from Khronos EGL 1.x, matching the six engines' direct imports.
 * No synthetic GL implementation: every result is returned by its U5 owner. */
#define FORWARD(ret,n,args,call,fail) ret n args { \
    ret (*f) args=owner?(void *)owner(#n):NULL; return f?f call:fail; }
FORWARD(Boolean,eglChooseConfig,(Handle d,const int *a,Handle *c,int n,int *out),(d,a,c,n,out),0)
FORWARD(Handle,eglCreateContext,(Handle d,Handle c,Handle share,const int *a),(d,c,share,a),NULL)
FORWARD(Handle,eglCreateImageKHR,(Handle d,Handle c,unsigned t,void *b,const int *a),(d,c,t,b,a),NULL)
FORWARD(Handle,eglCreatePbufferSurface,(Handle d,Handle c,const int *a),(d,c,a),NULL)
FORWARD(Boolean,eglDestroyContext,(Handle d,Handle c),(d,c),0)
FORWARD(Boolean,eglDestroyImageKHR,(Handle d,Handle i),(d,i),0)
FORWARD(Handle,eglGetCurrentContext,(void),(),NULL)
FORWARD(Handle,eglGetCurrentDisplay,(void),(),NULL)
FORWARD(Handle,eglGetCurrentSurface,(int w),(w),NULL)
FORWARD(Handle,eglGetDisplay,(void *d),(d),NULL)
FORWARD(int,eglGetError,(void),(),0x3001)
FORWARD(Boolean,eglInitialize,(Handle d,int *ma,int *mi),(d,ma,mi),0)
FORWARD(Boolean,eglMakeCurrent,(Handle d,Handle draw,Handle read,Handle c),(d,draw,read,c),0)
FORWARD(const char *,eglQueryString,(Handle d,int n),(d,n),NULL)
FORWARD(Boolean,eglQuerySurface,(Handle d,Handle s,int a,int *v),(d,s,a,v),0)
FORWARD(Boolean,eglTerminate,(Handle d),(d),0)
#undef FORWARD
