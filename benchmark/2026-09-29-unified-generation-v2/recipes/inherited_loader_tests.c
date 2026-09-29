/* R155 0x3b1c..0x3cf0: all three inherited members must be mapped, verified,
 * and skipped by the local dlopen loop. Wrong SHA never gets that exemption. */
static bool InheritedMembers(void)
{
    const char *names[] = {"libwestlake_thread_guard_registry.so", "libbionic_compat.so", "liblzma.so"};
    const char *paths[] = {"/system/lib64/libwestlake_thread_guard_registry.so", "/system/android/lib64/libbionic_compat.so", "/system/android/lib64/liblzma.so"};
    for (int n=0; n<3; ++n) {
        for (int mode=0; mode<4; ++mode) {
            WlscplArtifactV1 a[3]; WlscplManifestV1 m; WlscplLoadRequestV1 r;
            WlscplLoaderV1 l={0}; WlscplLoadResultV1 result; TestContext c;
            BuildValid(a,&m,&r,&c);a[0].absolute_path=paths[n];strcpy(a[0].soname,names[n]);
            c.mapped_at = mode==1 ? -1 : 0;
            if (mode==2) c.verify_fail_at=0;
            if (mode==3) strcpy(a[0].soname,"wrong.so");
            WlscplError rc=Load(&l,&r,&result,&c);
            if (mode==0) {
                if (rc!=WLSCPL_OK || c.verify_calls!=3 || c.open_calls!=2 || l.handle_count!=2 || result.provider_handle!=l.handles[1]) return false;
            } else if (rc!=(mode==2?WLSCPL_ERROR_ARTIFACT_IDENTITY:WLSCPL_ERROR_PREMATURE_MAPPING) || c.open_calls!=0) return false;
        }
    }
    return true;
}
