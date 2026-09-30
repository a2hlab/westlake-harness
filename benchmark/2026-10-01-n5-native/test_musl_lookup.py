"""Compile unchanged OH musl lookup functions; this is not a full-loader/device test."""
from pathlib import Path
import subprocess,tempfile,gzip
HERE=Path(__file__).resolve().parent
source=gzip.decompress((HERE/'source-evidence/oh61-dynlink.c.gz').read_bytes()).decode();ns=gzip.decompress((HERE/'source-evidence/oh61-namespace.c.gz').read_bytes()).decode()
def extract(text,start):
 pos=text.index(start);brace=text.index('{',pos);depth=1;i=brace+1
 while depth:
  depth += (text[i]=='{')-(text[i]=='}');i+=1
 return text[pos:i]
functions='\n'.join([extract(ns,'bool is_sharable('),*[extract(source,s) for s in ['static struct dso *search_dso_by_name(', 'static struct dso *search_dso_by_fstat(', 'static inline int app_has_same_name_so(', 'static struct dso *find_library_by_name(', 'UT_STATIC struct dso *find_library_by_fstat(']]])
header=r'''
#include <assert.h>
#include <stdbool.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#define LD_LOGD(...) ((void)0)
#define UT_STATIC static
#define LOCAL_NS_PREFERED 1
#define ALLOW_ALL_SHARED_LIBS "*"
#define PATH_MAX 4096
struct dso {const char *name,*shortname; dev_t dev; ino_t ino; uint64_t file_offset;};
typedef struct ns ns_t;
typedef struct {size_t num; const char **strs;} strlist;
typedef struct {ns_t *inherited_ns; strlist *shared_libs;} ns_inherit;
typedef struct {size_t num; ns_inherit **inherits;} inherits;
typedef struct {size_t num; struct dso **dsos;} dsos;
struct ns {int flag;const char *lib_paths,*ns_name;dsos *ns_dsos;inherits *ns_inherits;};
static int path_open(const char *name,const char *path,char *buf,size_t size){snprintf(buf,size,"%s/%s",path,name);return open(buf,O_RDONLY);}
'''
main=r'''
int main(int argc,char **argv){
 char filename[4096];snprintf(filename,sizeof filename,"%s/liboh_android_runtime.so",argv[1]);
 int fd=open(filename,O_CREAT|O_RDWR,0600);assert(fd>=0);struct stat st;assert(fstat(fd,&st)==0);close(fd);
 struct dso resident={.name=filename,.shortname=NULL,.dev=st.st_dev,.ino=st.st_ino};struct dso *owner_items[]={&resident};
 dsos owner_dsos={1,owner_items},empty={0,NULL};ns_t owner={.ns_dsos=&owner_dsos,.ns_name="owner"};
 const char *names[]={"liboh_android_runtime.so"};strlist shared={1,names};ns_inherit edge={&owner,&shared};ns_inherit *edges[]={&edge};inherits direct={1,edges};
 ns_t app={.flag=LOCAL_NS_PREFERED,.lib_paths="/missing",.ns_dsos=&empty,.ns_inherits=&direct,.ns_name="app"};
 assert(find_library_by_name(names[0],&app,true)==NULL); // absolute-loaded object has no shortname
 assert(find_library_by_fstat(&st,&app,true,0)==&resident); // direct inherited inode reuse
 assert(find_library_by_fstat(&st,&app,false,0)==NULL); // no invented global reuse
 resident.shortname=names[0];assert(find_library_by_name(names[0],&app,true)==&resident);
 app.lib_paths=argv[1];assert(find_library_by_name(names[0],&app,true)==NULL); // LOCAL_NS_PREFERED requires file check
 assert(find_library_by_fstat(&st,&app,true,0)==&resident); // still returns same object after opening actual file
 st.st_ino++;assert(find_library_by_fstat(&st,&app,true,0)==NULL); // same basename is not identity proof
 puts("PASS unchanged OH musl: inherited basename and inode reuse; local preference; no-inherit/different-inode negatives");
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'probe.c').write_text(header+functions+main)
 subprocess.run(['cc','-std=c11','-D_DARWIN_C_SOURCE',str(p/'probe.c'),'-o',str(p/'probe')],check=True)
 subprocess.run([str(p/'probe'),td],check=True)
