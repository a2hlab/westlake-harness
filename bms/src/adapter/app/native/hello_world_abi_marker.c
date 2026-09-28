/*
 * AArch64-only APK ABI marker.
 *
 * HelloWorld is Java-only, but the L02.A01 game-min admission contract is
 * deliberately pinned to arm64-v8a. This inert DSO makes that architecture
 * declaration a real ELF fact without adding a runtime load dependency.
 */
__attribute__((visibility("default")))
int westlake_hello_world_abi_marker(void)
{
    return 64;
}
