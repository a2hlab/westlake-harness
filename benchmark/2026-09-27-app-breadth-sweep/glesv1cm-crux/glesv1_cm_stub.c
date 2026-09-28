/* glesv1_cm_stub.c — minimal libGLESv1_CM.so for OH (which ships only GLESv2/v3).
 *
 * WHY: libSDL2.so (SuperTuxKart & other SDL2 apps) DT_NEEDEDs libGLESv1_CM.so AND is linked
 * BIND_NOW (eager). OH has no libGLESv1_CM.so → load fails ("Error loading shared library
 * libGLESv1_CM.so"). A symlink to libGLESv2.so does NOT help: BIND_NOW forces immediate
 * resolution of the GLESv1-only fixed-function symbols SDL2 references, which libGLESv2 does
 * not export → "cannot locate symbol glMatrixMode".
 *
 * This stub exports EXACTLY the 14 GLESv1/OES symbols libSDL2.so references as UND (found via
 * `readelf --dyn-syms libSDL2.so | awk '$7=="UND"'`), so BIND_NOW resolves and libSDL2 loads.
 * Modern SuperTuxKart uses the GLES3 render path, so these fixed-function entry points are
 * never CALLED at runtime → the no-op bodies never execute. Each stub logs on first call so
 * the child stderr reveals immediately IF the app actually uses fixed-function (→ would then
 * need real impls / gl4es, not just a stub).
 *
 * Keep this stub MINIMAL: export ONLY these 14. The core GLES2 symbols SDL2 uses (glClear,
 * glDrawArrays, glCreateShader, …) must resolve from the REAL libGLESv2.so (also DT_NEEDED),
 * so we must NOT shadow them here.
 */
#include <stdio.h>
#include <stdatomic.h>

typedef unsigned int GLenum;
typedef unsigned int GLuint;
typedef int GLint;
typedef int GLsizei;
typedef float GLfloat;

static atomic_int g_hit = 0;
static void note(const char *fn) {
    /* one line the first time ANY fixed-function stub is hit — proves the app uses ES1 */
    if (atomic_fetch_add(&g_hit, 1) < 32)
        fprintf(stderr, "[glesv1_cm_stub] CALLED %s (app uses ES1 fixed-function — stub insufficient, needs real impl/gl4es)\n", fn);
}

#define STUB0(name)                 void name(void){ note(#name); }
#define STUB1(name, t1)             void name(t1 a){ (void)a; note(#name); }
#define STUB2(name, t1, t2)         void name(t1 a, t2 b){ (void)a;(void)b; note(#name); }
#define STUB3(name, t1, t2, t3)     void name(t1 a, t2 b, t3 c){ (void)a;(void)b;(void)c; note(#name); }
#define STUB4(name, t1, t2, t3, t4) void name(t1 a, t2 b, t3 c, t4 d){ (void)a;(void)b;(void)c;(void)d; note(#name); }

/* ---- GLESv1-only fixed-function (10) ---- */
STUB1(glMatrixMode, GLenum)
STUB4(glColor4f, GLfloat, GLfloat, GLfloat, GLfloat)
STUB1(glEnableClientState, GLenum)
STUB1(glDisableClientState, GLenum)
STUB0(glLoadIdentity)
void glOrthof(GLfloat l, GLfloat r, GLfloat b, GLfloat t, GLfloat n, GLfloat f){ (void)l;(void)r;(void)b;(void)t;(void)n;(void)f; note("glOrthof"); }
STUB4(glColorPointer, GLint, GLenum, GLsizei, const void*)
STUB4(glTexCoordPointer, GLint, GLenum, GLsizei, const void*)
STUB3(glTexEnvf, GLenum, GLenum, GLfloat)
STUB4(glVertexPointer, GLint, GLenum, GLsizei, const void*)

/* ---- OES extension entry points SDL2 references (4) ---- */
STUB2(glBindFramebufferOES, GLenum, GLuint)
STUB2(glGenFramebuffersOES, GLsizei, GLuint*)
STUB1(glBlendEquationOES, GLenum)
void glDrawTexfOES(GLfloat x, GLfloat y, GLfloat z, GLfloat w, GLfloat h){ (void)x;(void)y;(void)z;(void)w;(void)h; note("glDrawTexfOES"); }
