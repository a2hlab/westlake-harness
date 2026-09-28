#ifndef WESTLAKE_GENERATION_TOKEN
#error WESTLAKE_GENERATION_TOKEN is required
#endif

#ifndef WESTLAKE_ANCHOR
#define WESTLAKE_ANCHOR westlake_default_anchor
#endif

__attribute__((used, section(".westlake_generation"), visibility("hidden")))
static const char kWestLakeGeneration[] = WESTLAKE_GENERATION_TOKEN;

__attribute__((visibility("default"), noinline)) int WESTLAKE_ANCHOR(void)
{
    return 17;
}
