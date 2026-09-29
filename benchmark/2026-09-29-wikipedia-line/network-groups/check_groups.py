#!/usr/bin/env python3
"""Compile the actual candidate helper against a minimal stock-message fixture."""
from pathlib import Path
import subprocess,tempfile
p=Path(__file__).resolve().parent
s=(p/'appspawn_service.c').read_text()
start=s.index('static int WestlakeAddInetGroup(')
end=s.index('\nstatic void ProcessSpawnReqMsg(',start)
pre='''#include <stdint.h>
#include <stddef.h>
#include <assert.h>
#include <sys/types.h>
#define APP_MAX_GIDS 64
#define APPSPAWN_MSG_INVALID 22
#define APPSPAWN_LOGI(...) ((void)0)
#define APPSPAWN_LOGE(...) ((void)0)
#define TLV_DAC_INFO 1
#define TLV_INTERNET_INFO 2
typedef struct { unsigned uid; uint32_t gidCount; gid_t gidTable[APP_MAX_GIDS]; } AppSpawnMsgDacInfo;
typedef struct { unsigned char setAllowInternet, allowInternet; } AppSpawnMsgInternetInfo;
typedef struct { AppSpawnMsgDacInfo *dac; AppSpawnMsgInternetInfo *internet; } AppSpawningCtx;
static void *GetAppProperty(AppSpawningCtx *p,int key) { return key==TLV_DAC_INFO ? (void*)p->dac : (void*)p->internet; }
'''
post='''
int main(void) {
 AppSpawnMsgDacInfo d={.uid=20010099,.gidCount=1,.gidTable={3099}};
 AppSpawnMsgInternetInfo net={1,0}; AppSpawningCtx p={&d,&net};
 assert(WestlakeAddInetGroup(&p)==0 && d.gidCount==2 && d.gidTable[0]==3099 && d.gidTable[1]==3003);
 assert(net.setAllowInternet==1 && net.allowInternet==0); /* explicit OH deny unchanged */
 assert(WestlakeAddInetGroup(&p)==0 && d.gidCount==2); /* idempotent */
 d.gidCount=0;p.internet=NULL;assert(WestlakeAddInetGroup(&p)==0 && d.gidCount==1 && d.gidTable[0]==3003);
 for(unsigned i=0;i<APP_MAX_GIDS;i++)d.gidTable[i]=4000+i;
 d.gidCount=APP_MAX_GIDS;assert(WestlakeAddInetGroup(&p)==APPSPAWN_MSG_INVALID && d.gidCount==APP_MAX_GIDS);
 d.gidTable[APP_MAX_GIDS-1]=3003;assert(WestlakeAddInetGroup(&p)==0 && d.gidCount==APP_MAX_GIDS);
 d.gidCount=APP_MAX_GIDS+1;assert(WestlakeAddInetGroup(&p)==APPSPAWN_MSG_INVALID);
 p.dac=NULL;assert(WestlakeAddInetGroup(&p)==APPSPAWN_MSG_INVALID);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as t:
 c=Path(t)/'groups.c';exe=Path(t)/'groups';c.write_text(pre+s[start:end]+post)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Wno-unused-variable','-Werror',str(c),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('PASS: preserve/append, OH deny unchanged, duplicate, empty, full reject, full existing, corrupt count, missing DAC')
