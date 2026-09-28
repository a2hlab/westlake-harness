#ifndef WESTLAKE_GENERATION_TOKEN
#error WESTLAKE_GENERATION_TOKEN is required
#endif

extern int runtime_redteam_missing_strong_provider(void);

__attribute__((used, section(".westlake_generation"), visibility("hidden")))
static const char kWestLakeGeneration[] = WESTLAKE_GENERATION_TOKEN;

__attribute__((visibility("default"), noinline)) int unresolved_consumer(void)
{
    return runtime_redteam_missing_strong_provider();
}
