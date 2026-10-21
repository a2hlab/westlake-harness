int main(void){
 const char* native[]={"com.ichi2.anki","com.unciv.app","app.organicmaps","com.nextcloud.client","com.mcdonalds.app","io.anuke.mindustry","com.emn8.mobilem8.nativeapp.bk","im.vector.app","org.mozilla.firefox","org.mozilla.fennec_fdroid","org.videolan.vlc","org.ppsspp.ppsspp","com.shatteredpixel.shatteredpixeldungeon","com.miHoYo.Yuanshen"};
 const char* flutter[]={"chat.fluffy.fluffychat","app.alextran.immich","com.tombursch.kitchenowl","deckers.thibault.aves.libre","com.adilhanney.saber","org.localsend.localsend_app"};
 const char* negative[]={"evil.com.miHoYo.Yuanshen","com.miHoYo.Yuanshen.evil","com.mihoyo.Yuanshen","com.miHoYo.yuanshen","com.DefaultCompany.ZigZag"};
 Dl_namespace a,b;void*h=NULL;char an[128],bn[128],path[1024];snprintf(an,sizeof(an),"westlake.anl.app.%ld.1",(long)getpid());snprintf(bn,sizeof(bn),"westlake.anl.bridge.%ld.1",(long)getpid());
 for(int kind=0;kind<3;kind++)for(int i=0;i<(kind==0?14:kind==1?6:5);i++){
 const char*pkg=kind==0?native[i]:kind==1?flutter[i]:negative[i];
 assert(native_cluster_path(pkg)==(kind==0&&(i<13||CANDIDATE)));assert(flutter_package_path(pkg)==(kind==1));
 for(int private=0;private<2;private++){
 snprintf(path,sizeof(path),"%s/data/app/%s/lib",private?(kind==1?"/system/android/lib64/westlake_flutter:":"/system/android/lib64/westlake_native:"):"",pkg);
 inherits=abi_calls=runtime_calls=audio_calls=0;int expected=private&&(kind==1||(kind==0&&(i<13||CANDIDATE)));
 const char*share=(kind==0&&i==13&&CANDIDATE)?"liblog.so:libmediandk.so":"liblog.so";
 assert(StockCreateConfiguredNamespaces(&b,bn,"/runtime","/runtime",share,NULL,NULL,&h,&a,an,path,"/app")==0);
 assert(abi_calls==expected);assert(inherits==(expected?3:1));assert(strcmp(libs[inherits-1],share)==0);assert(strcmp(owners[inherits-1],bn)==0);
 if(expected){assert(strcmp(owners[0],"default")==0);assert(strcmp(owners[1],"westlake.sealed.child")==0);assert(!strstr(libs[0],"libmediandk.so"));assert(!strstr(libs[1],"libmediandk.so"));}
 if(kind==0&&i==13){assert(runtime_calls==0&&audio_calls==0);}
 int before=open_calls;assert(!StockOpenNamespace(&a,"libx.so",RTLD_NOW|RTLD_GLOBAL));assert(open_calls==before);assert(StockOpenNamespace(&a,"libx.so",RTLD_NOW));
 }
 }
 int before=open_calls;assert(StockCreateConfiguredNamespaces(&b,bn,"/runtime","/runtime","liblog.so",NULL,NULL,&h,&a,"foreign.app",path,"/app")==EINVAL);assert(before==open_calls);
 strcpy(a.name,"foreign.app");assert(!StockOpenNamespace(&a,"libx.so",RTLD_NOW));
 failure=1;assert(StockCreateConfiguredNamespaces(&b,bn,"/runtime","/runtime","liblog.so",NULL,NULL,&h,&a,an,"/system/android/lib64/westlake_native:/data/app/org.mozilla.firefox/lib","/app")==EPERM);
 puts("PASS actual host 50 route cases; private-root boundary; bridge mediation; GLOBAL/foreign/owner failure rejects");return 0;
}
