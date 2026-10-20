#include <stdio.h>
#include <string.h>
#include "observe29c.h"
int main(void) {
 struct r29c_record r; memset(&r,0,sizeof(r));
 r.phase=R29C_PRODUCER_DESTROY; r.wrapper=0x123; r.oh=0x123;
 r.valid=R29C_OH|R29C_OLDWIN|R29C_UNREFRC;
 r.old_window=0x123; r.called=r.unref_called=r.unref_rc_valid=1; r.transition=1;
 r.call=1; r29c_observe(&r); r.call=2; r29c_observe(&r);
 r.call=3; r.unref_rc=-31; r29c_observe(&r);
 r.call=4; r29c_observe(&r);
 struct r29c_stats s; r29c_stats_read(&s);
 printf("writes=%llu first_limit=%u eligible=%llu\n",(unsigned long long)s.writes,s.first_limit,(unsigned long long)s.eligible);
 return 0;
}
