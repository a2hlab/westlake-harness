#!/usr/bin/env python3
"""Explicit source-only successor; never edits the pinned donor files."""
import argparse,hashlib,json,difflib
from pathlib import Path
SELF=Path(__file__).resolve().parent

def derive(main):
 out=SELF/'derived';out.mkdir(exist_ok=True);pins=[]
 def put(rel,name,fn=lambda s:s):
  p=main/rel;s=p.read_text();v=fn(s);(out/name).write_text(v)
  pins.append({'source':rel,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'successor':name,'sha256':hashlib.sha256(v.encode()).hexdigest()})
  (out/(name+'.diff')).write_text(''.join(difflib.unified_diff(s.splitlines(True),v.splitlines(True),fromfile=rel,tofile='T26/derived/'+name)))
 r14='benchmark/2026-10-19-toutiao-video-playback/candidate-r14-offline/'
 r20='benchmark/2026-10-20-t20-provider-link-slice/'
 r25='benchmark/2026-10-20-t25-geometry/'
 r23='benchmark/2026-10-20-t23-egl-import/'
 r15='benchmark/2026-10-19-toutiao-video-playback/candidate-r15-provider-offline/'
 put(r15+'provider_adapter.c','provider_adapter.c')
 put(r15+'provider_adapter.h','provider_adapter.h',lambda s:s.replace('../candidate-r14-offline/window_module.h','window_module.h'))
 def window(s):
  s=s.replace('#include "window_module.h"','#include "window_module.h"\n#include "yv12.h"\n#include "observation.h"')
  s=s.replace('struct slot { enum state state;','struct slot { struct r26_token token; enum state state;')
  s=s.replace('struct r14_module { pthread_mutex_t mutex;','struct r14_module { struct r26_context *extension; pthread_mutex_t mutex;')
  s=s.replace('static int negative(', 'void r14_attach_yv12(struct r14_module *m,struct r26_context *extension) { m->extension=extension; }\nstatic int negative(')
  s=s.replace('struct r14_report r={0};int rc=-EINVAL,idx=-1,fd=-1,mapped=0;', 'struct r26_token token={0};int claimed=0;struct r14_report r={0};int rc=-EINVAL,idx=-1,fd=-1,mapped=0;')
  needle='rc=o->unwrap(o->ctx,wrapper,&oh);if(rc || !oh){rc=rc?negative(rc):-ENODEV;goto done;}'
  s=s.replace(needle,needle+'\n if(m->extension){rc=r26_lock_begin(m->extension,wrapper,oh,&token);if(rc)goto done;claimed=1;}')
  s=s.replace('r.map_called=1;r.map_rc=', 'wl_r27_cpu(token.generation,oh,buffer,native);\n r.map_called=1;r.map_rc=')
  s=s.replace('struct r14_rect rect={0,0,(int32_t)h.width,(int32_t)h.height};','struct r14_rect rect={0,0,(int32_t)h.width,(int32_t)h.height};\n if(m->extension){rc=r26_prepare(m->extension,token,&h,&answer);if(rc)goto fail;}\n wl_r27_output(token.generation,native,&answer); /* prepared, not published */')
  s=s.replace('s->buffer=buffer;s->native=native;', 's->token=token;s->buffer=buffer;s->native=native;')
  s=s.replace('done:\n r.primary=rc;', 'done:\n if(rc && claimed)(void)r26_finish(m->extension,token,r.retained);\n r.primary=rc;')
  old='const struct r14_ops *o=&m->ops;r=copy.report;r.unmap_called=1;r.unmap_rc=o->unmap(o->ctx,copy.native);\n int rc=r.unmap_rc?negative(r.unmap_rc):0;\n if(!rc){r.flush_called=1;r.flush_rc=o->flush(o->ctx,copy.oh,copy.buffer,-1,&copy.rect);if(r.flush_rc)rc=negative(r.flush_rc);}\n r.primary=rc;complete(m,idx,&r,rc==0);if(report)*report=r;return rc;'
  new='''const struct r14_ops *o=&m->ops;r=copy.report;
 int conversion=m->extension?r26_before_unmap(m->extension,copy.token):0;
 r.unmap_called=1;r.unmap_rc=o->unmap(o->ctx,copy.native);
 int rc=conversion?conversion:(r.unmap_rc?negative(r.unmap_rc):0);
 if(conversion && !r.unmap_rc){r.abort_called=1;r.abort_rc=o->abort(o->ctx,copy.oh,copy.buffer);}
 if(!rc){r.flush_called=1;r.flush_rc=o->flush(o->ctx,copy.oh,copy.buffer,-1,&copy.rect);if(r.flush_rc)rc=negative(r.flush_rc);}
 if(m->extension)(void)r26_finish(m->extension,copy.token,rc!=0);
 r.primary=rc;complete(m,idx,&r,rc==0);if(report)*report=r;return rc;'''
  assert old in s;s=s.replace(old,new);return s
 put(r14+'window_module.c','window_module.c',window)
 put(r14+'window_module.h','window_module.h',lambda s:s.replace('#endif','struct r26_context;\nvoid r14_attach_yv12(struct r14_module *,struct r26_context *);\n#endif'))
 put(r20+'entry.c','entry.c',lambda s:s.replace('#include "entry.h"','#include "entry.h"\n#include "wiring.h"').replace('*out=c;return 0;','r14_attach_yv12(c->module,wl_r26_cache());*out=c;return 0;'))
 put(r20+'entry.h','entry.h')
 def geometry(s):
  s=s.replace('#include "geometry.h"','#include "geometry.h"\n#include "wiring.h"')
  s=s.replace('case 0x32315659:return 11','case 0x32315659:return 12')
  s=s.replace('static struct r25_ops ops;','static struct r25_ops ops;\nstatic struct r26_context *cache;')
  s=s.replace('opt};bind_error=0;', 'opt};\n struct r26_owner owner={ops.acquire,ops.get,ops.release};bind_error=r26_create(&owner,NULL,&cache);')
  point='static int32_t dispatch('
  s=s.replace(point,'''int wl_r26_gate(void *caller){pthread_once(&once,bind_once);return bind_error?bind_error:(admitted_caller(caller)?0:-EXDEV);}
struct r26_context *wl_r26_cache(void){return cache;}
'''+point)
  s=s.replace('struct r25_report r;int rc=r25_apply(&ops,w,width,height,format,&r);','''struct r26_token token;int rc=r26_geometry_begin(cache,w,&token);if(rc)return rc;
 struct r25_report r;rc=r25_apply(&ops,w,width,height,format,&r);
 int cleanup=r26_geometry_end(cache,token,format,rc,r.release_called && r.release_rc!=1);if(!rc && cleanup)rc=cleanup;''')
  return s
 put(r25+'geometry.c','geometry.c',geometry);put(r25+'geometry.h','geometry.h')
 def pair(s):
  s=s.replace('#include "entry.h"','#include "entry.h"\n#include "wiring.h"\n#include "observation.h"')
  s=s.replace('if(!player_caller(caller))return original_lock_refusal();','if(!player_caller(caller))return original_lock_refusal();\n int route=wl_r26_gate(caller);if(route)return fail(route);')
  s=s.replace('if(!player_caller(caller))return fail(-ENODEV);','if(!player_caller(caller))return fail(-ENODEV);\n int route=wl_r26_gate(caller);if(route)return fail(route);')
  s=s.replace('const struct r20_owner own={NULL,unwrap};', 'wl_r27_bind_cpu(owner_handle,provider_base);\n const struct r20_owner own={NULL,unwrap};')
  s=s.replace('if(!rc && owner_release(window)!=1)rc=-EPROTO;', 'if(!rc && owner_release(window)!=1){(void)r26_poison(wl_r26_cache(),window);rc=-EPROTO;}')
  return s
 put(r20+'shim/pair.c','pair.c',pair)
 def egl(s):
  s=s.replace('#include "egl_import.h"','#include "egl_import.h"\n#include "observation.h"')
  s=s.replace('void *window=platform.create_buffer((void*)buffer);pthread_mutex_unlock(&provider_lock);','void *window=platform.create_buffer((void*)buffer);pthread_mutex_unlock(&provider_lock);if(window)wl_r27_import((void*)buffer,window,index,generation);')
  s=s.replace('image=platform.impl[selected].create_image(display,context,OH_BUFFER,buffer,attribs);','image=wl_r27_create(index,generation,(void*)platform.impl[selected].create_image,display,context,OH_BUFFER,buffer,attribs);')
  return s
 def platform(s):
  s=s.replace('#include "egl_import.h"','#include "egl_import.h"\n#include "observation.h"')
  s=s.replace('p->create_buffer=(void*(*)(void*))create;', 'wl_r27_bind_import(h,surface_base);\n p->create_buffer=(void*(*)(void*))create;')
  return s
 put(r23+'egl_import.c','egl_import.c',egl)
 put(r23+'egl_import.h','egl_import.h')
 put(r23+'platform.c','platform.c',platform)
 put(r23+'exact_binding.h','exact_binding.h')
 (SELF/'derivation-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source-repo',type=Path,required=True);a=p.parse_args();derive(a.source_repo.resolve())
