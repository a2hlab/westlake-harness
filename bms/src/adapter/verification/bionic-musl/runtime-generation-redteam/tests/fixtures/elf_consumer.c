#ifndef WESTLAKE_GENERATION_TOKEN
#error WESTLAKE_GENERATION_TOKEN is required
#endif

extern int shadow_value(void);

__attribute__((used, section(".westlake_generation"), visibility("hidden")))
static const char kWestLakeGeneration[] = WESTLAKE_GENERATION_TOKEN;

__attribute__((visibility("default"), noinline)) int consume_shadow(void)
{
    return shadow_value();
}
