/* Actual production TU; names changed only to avoid host libc interposition. */
#define _GNU_SOURCE 1
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <locale.h>
#ifdef __APPLE__
#include <xlocale.h>
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define _ctype_ g30_ctype
#define strtoll_l g30_strtoll_l
#define strtoull_l g30_strtoull_l
#include G30_SOURCE
#undef _ctype_
#undef strtoll_l
#undef strtoull_l
static unsigned classifications, conversions;
static unsigned classify(int c) {
    unsigned f=0;
    if (c<0 || c>127) return 0;
    if (c<32 || c==127) f|=32;
    if (c==' ' || (c>=9 && c<=13)) f|=8;
    if (c==' ') f|=128;
    if (c>='A'&&c<='Z') f|=1;
    if (c>='a'&&c<='z') f|=2;
    if (c>='0'&&c<='9') f|=4;
    /* Bionic legacy table: digit classification is N; X flags A-F/a-f. */
    if ((c>='A'&&c<='F')||(c>='a'&&c<='f')) f|=64;
    if (c>=33 && c<=126 && !(f&(1|2|4))) f|=16;
    return f;
}
static void signed_case(const char *s,int base,long long want,size_t used,int err,locale_t loc) {
    char *e=NULL;errno=19;long long v=g30_strtoll_l(s,&e,base,loc);
    int got_errno=errno; char *reference_end=NULL; errno=19;
    (void)strtoll(s,&reference_end,base); int reference_errno=errno;
    if(got_errno!=err) fprintf(stderr,"errno observation signed input=[%s] got=%d original=%d old_expectation=%d\n",s,got_errno,reference_errno,err);
    assert(v==want);assert(e==s+used);assert(e==reference_end);assert(got_errno==reference_errno);if(err==ERANGE)assert(got_errno==ERANGE);conversions++;
}
static void unsigned_case(const char *s,int base,unsigned long long want,size_t used,int err,locale_t loc) {
    char *e=NULL;errno=19;unsigned long long v=g30_strtoull_l(s,&e,base,loc);
    int got_errno=errno; char *reference_end=NULL; errno=19;
    (void)strtoull(s,&reference_end,base); int reference_errno=errno;
    if(got_errno!=err) fprintf(stderr,"errno observation unsigned input=[%s] got=%d original=%d old_expectation=%d\n",s,got_errno,reference_errno,err);
    assert(v==want);assert(e==s+used);assert(e==reference_end);assert(got_errno==reference_errno);if(err==ERANGE)assert(got_errno==ERANGE);conversions++;
}
static void cases(locale_t loc) {
    signed_case("9223372036854775807!",10,LLONG_MAX,19,19,loc);
    signed_case("-9223372036854775808!",10,LLONG_MIN,20,19,loc);
    signed_case("9223372036854775808!",10,LLONG_MAX,19,ERANGE,loc);
    signed_case("-9223372036854775809!",10,LLONG_MIN,20,ERANGE,loc);
    signed_case("  +42tail",10,42,5,19,loc);
    signed_case("-0x2a!",0,-42,5,19,loc);
    signed_case("077!",0,63,3,19,loc);
    signed_case("101!",2,5,3,19,loc);
    signed_case("z!",36,35,1,19,loc);
    signed_case("",10,0,0,19,loc);
    signed_case(" +x",10,0,0,19,loc);
    unsigned_case("18446744073709551615!",10,ULLONG_MAX,20,19,loc);
    unsigned_case("18446744073709551616!",10,ULLONG_MAX,20,ERANGE,loc);
    unsigned_case("-1!",10,ULLONG_MAX,2,19,loc);
    unsigned_case("+0xff!",0,255,5,19,loc);
    unsigned_case("010!",0,8,3,19,loc);
    unsigned_case("101!",2,5,3,19,loc);
    unsigned_case("z!",36,35,1,19,loc);
    unsigned_case("",10,0,0,19,loc);
    unsigned_case("-x",10,0,0,19,loc);
    errno=19;assert(g30_strtoll_l("-42",NULL,10,loc)==-42&&errno==19);conversions++;
    errno=19;assert(g30_strtoull_l("42",NULL,10,loc)==42&&errno==19);conversions++;
    /* Invalid-base/edge behavior is delegated exactly, not normalized. */
    const char *texts[]={"123","0x","  -","0129"};int bases[]={1,37,0,8};
    for(size_t i=0;i<4;i++) {
        char *a=(char*)texts[i], *b=a;errno=19;long long va=strtoll(texts[i],&a,bases[i]);int ea=errno;
        errno=19;long long vb=g30_strtoll_l(texts[i],&b,bases[i],loc);assert(va==vb&&a==b&&errno==ea);conversions++;
        a=(char*)texts[i];b=a;errno=19;unsigned long long ua=strtoull(texts[i],&a,bases[i]);ea=errno;
        errno=19;unsigned long long ub=g30_strtoull_l(texts[i],&b,bases[i],loc);assert(ua==ub&&a==b&&errno==ea);conversions++;
    }
}
int main(void) {
    _Static_assert(sizeof(g30_ctype)==8,"host must model 64-bit pointer ABI");
    assert(g30_ctype==kBionicCtypeTable);
    for(int c=-1;c<=255;c++){assert((unsigned char)g30_ctype[c+1]==classify(c));classifications++;}
    locale_t c=newlocale(LC_ALL_MASK,"C",(locale_t)0);assert(c);
    locale_t posix=newlocale(LC_ALL_MASK,"POSIX",(locale_t)0);assert(posix);
    cases(c);cases(posix);cases((locale_t)0);freelocale(c);freelocale(posix);
    printf("PASS classifications=%u integer_cases=%u actual_TU=1 locales=C,POSIX,ignored-null\n",classifications,conversions);
    return 0;
}
