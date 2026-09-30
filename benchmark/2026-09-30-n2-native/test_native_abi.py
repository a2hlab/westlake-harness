#!/usr/bin/env python3
"""Host behavior test, separate from target ELF/version/namespace verification."""
from pathlib import Path
import subprocess,tempfile
P=Path(__file__).resolve().parent
CODE=r'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
int* __errno_location(void){return &errno;}
int SystemReadParam(const char* name,char* value,uint32_t* size) {
    if(strcmp(name,"n2.long")!=0)return -1;
    assert(*size==92);memset(value,'x',91);value[91]=0;*size=91;return 0;
}
extern int* __errno(void);
extern int __system_property_get(const char*,char*);
extern void android_set_abort_message(const char*);
int main(void){
 struct {char value[92];char sentinel[16];} data;
 memset(&data,0x5a,sizeof(data));
 assert(__system_property_get("ro.build.version.sdk",data.value)==2);
 assert(strcmp(data.value,"34")==0);
 assert(__system_property_get("n2.missing.property",data.value)==0 && data.value[0]==0);
 assert(__system_property_get("n2.long",data.value)==91);
 for(int i=0;i<16;i++)assert(data.sentinel[i]==0x5a);
 errno=EIO;assert(__errno()==&errno && *__errno()==EIO);
 android_set_abort_message("n2-test");
 puts("PASS property fallback/92-byte boundary; errno TLS; abort-message callable");
}
'''
with tempfile.TemporaryDirectory() as td:
 c=Path(td)/'test.c';c.write_text(CODE);b=Path(td)/'test'
 subprocess.run(['cc','-D_GNU_SOURCE','-std=c11','-Wl,-export_dynamic',str(P/'src/native_abi.c'),str(c),'-o',str(b)],check=True)
 x=subprocess.run([str(b)],capture_output=True,text=True)
 (P/'abi-host-tests.txt').write_text(x.stdout+x.stderr)
 assert x.returncode==0,x.stderr
 print(x.stdout.strip())
