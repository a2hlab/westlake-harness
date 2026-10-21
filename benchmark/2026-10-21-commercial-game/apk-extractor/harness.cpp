#include "zip_file.h"
#include <iostream>
int main(int argc,char**argv){if(argc!=2)return 64; OHOS::AppExecFwk::ZipFile z(argv[1],false);bool ok=z.Open();std::cout<<"{\"open\":"<<(ok?"true":"false")<<",\"entries\":"<<z.GetAllEntries().size()<<"}\n";return ok?0:2;}
