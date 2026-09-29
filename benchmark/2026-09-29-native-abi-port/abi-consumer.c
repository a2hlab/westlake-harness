extern int *bionic_errno(void);
__asm__(".symver bionic_errno,__errno@LIBC");
extern char bionic_sf[];
__asm__(".symver bionic_sf,__sF@LIBC");
extern int __android_log_buf_write(int,int,const char*,const char*);
int verify_app_abi(void) { return *bionic_errno()+bionic_sf[0]+__android_log_buf_write(0,4,"b87","ABI consumer"); }
