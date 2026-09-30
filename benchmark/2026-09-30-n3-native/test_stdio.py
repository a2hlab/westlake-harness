"""Exercise copied stdio adapter as a DSO, including real FILE* pass-through."""
from pathlib import Path
import subprocess,tempfile
P=Path(__file__).resolve().parent
code=r'''
#include <stdio.h>
#include <dlfcn.h>
#include <assert.h>
#include <string.h>
int main(int argc,char**argv){
 void*h=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);assert(h);
 void*s=dlsym(h,"__sF");assert(s);
 int(*puts_fn)(const char*,FILE*)=dlsym(h,"fputs");
 int(*flush_fn)(FILE*)=dlsym(h,"fflush");
 size_t(*write_fn)(const void*,size_t,size_t,FILE*)=dlsym(h,"fwrite");
 size_t(*read_fn)(void*,size_t,size_t,FILE*)=dlsym(h,"fread");
 int(*seek_fn)(FILE*,long,int)=dlsym(h,"fseek");
 int(*close_fn)(FILE*)=dlsym(h,"fclose");
 assert(puts_fn("N3 legacy stderr translated\n",(FILE*)((char*)s+304))>=0);
 assert(flush_fn((FILE*)((char*)s+304))==0);
 FILE*f=tmpfile();assert(f);assert(write_fn("actual",1,6,f)==6);assert(seek_fn(f,0,SEEK_SET)==0);char b[8]={0};assert(read_fn(b,1,6,f)==6);assert(!strcmp(b,"actual"));assert(close_fn(f)==0);
 puts("PASS copied stdio: legacy stderr sentinel and ordinary FILE round-trip");
}
'''
with tempfile.TemporaryDirectory() as td:
 t=Path(td);(t/'probe.c').write_text(code)
 subprocess.run(['cc','-dynamiclib','-fno-builtin',str(P/'src/bionic_stdio_compat.c'),'-o',str(t/'shim.dylib')],check=True)
 subprocess.run(['cc',str(t/'probe.c'),'-o',str(t/'probe')],check=True)
 x=subprocess.run([str(t/'probe'),str(t/'shim.dylib')],capture_output=True,text=True);assert x.returncode==0,x.stderr
 (P/'stdio-tests.txt').write_text(x.stdout+x.stderr);print(x.stdout.strip())
