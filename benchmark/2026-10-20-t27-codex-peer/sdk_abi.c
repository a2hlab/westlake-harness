#include <stddef.h>
#include <stdbool.h>
#include <native_buffer/native_buffer.h>
_Static_assert(sizeof(OH_NativeBuffer_Config)==20,"Config size");
_Static_assert(offsetof(OH_NativeBuffer_Config,width)==0,"width");
_Static_assert(offsetof(OH_NativeBuffer_Config,height)==4,"height");
_Static_assert(offsetof(OH_NativeBuffer_Config,format)==8,"format");
_Static_assert(offsetof(OH_NativeBuffer_Config,usage)==12,"usage");
_Static_assert(offsetof(OH_NativeBuffer_Config,stride)==16,"stride");
typedef void (*getcfg)(OH_NativeBuffer*,OH_NativeBuffer_Config*);
typedef int32_t (*fromnwb)(OHNativeWindowBuffer*,OH_NativeBuffer**);
_Static_assert(__builtin_types_compatible_p(__typeof__(&OH_NativeBuffer_GetConfig),getcfg),"GetConfig signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&OH_NativeBuffer_FromNativeWindowBuffer),fromnwb),"FromNativeWindowBuffer signature");
int t27_sdk_abi_proved(void){return sizeof(OH_NativeBuffer_Config);}
