"""VM only: rebuild one C object and relink one WebView shim (#36)."""
import pathlib,json,subprocess,shlex,hashlib
ws=pathlib.Path.home()/'a2hlab/ws';src=ws/'westlake-ability38/framework/webview-shim/webview_bionic_shim.c';old=ws/'out-sp20/webview-shims'
out=ws/'out-ability38/webview-gles-order';out.mkdir(parents=True,exist_ok=True)
original=(old/'src/framework/webview-shim/webview_bionic_shim.c').read_text();s=src.read_text()
start=s.index('    if (basename != NULL && strcmp(basename, "libGLESv2.so") == 0 &&')
end=s.index('    return real_dlopen(actual_filename, flags);',start)
block=s[start:end]
if s==original:
 s=s[:start]+s[end:]
 target='    /*\n     * OH names several NDK libraries'
 assert target in s
 s=s.replace(target,'    /* Translate GLES before the bare-name probe can return the Android NDK\n     * facade. That facade does not see OH platform EGL thread hooks. */\n'+block+target,1)
 src.write_text(s)
else:
 assert s.index('strcmp(basename, "libGLESv2.so")')<s.index('void *plain = real_dlopen(actual_filename, flags);')
commands=json.loads((old/'artifacts.json').read_text())['commands']
results=[]
for index in (0,2):
 cmd=shlex.split(commands[index])
 for i,arg in enumerate(cmd):
  if arg.endswith('/src/framework/webview-shim/webview_bionic_shim.c'):cmd[i]=str(src)
  elif arg.endswith('/obj/webview_bionic_shim.c.o'):cmd[i]=str(out/'webview_bionic_shim.c.o')
  elif i>0 and cmd[i-1]=='-o':cmd[i]=str(out/'libwebview_bionic_shim.so')
 log=out/f'build-{index}.log'
 with log.open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 results.append(cmd)
lib=out/'libwebview_bionic_shim.so';meta={'commands':results,'rebuilt_objects':1,'relinked_libraries':1,'sha256':hashlib.sha256(lib.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'old_source_sha256':hashlib.sha256(original.encode()).hexdigest(),'reused_asm_sha256':hashlib.sha256((old/'obj/webview_setjmp_arm64.S.o').read_bytes()).hexdigest()}
(out/'build.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta,indent=2))
