extern int wl_r20_pair_lock(void*,void*,void*,void*);
extern int wl_r20_pair_unlock(void*,void*);
int ANativeWindow_lock(void* window, void* outBuffer, void* inOutDirtyBounds)
{
    return wl_r20_pair_lock(window,outBuffer,inOutDirtyBounds,__builtin_return_address(0));
}
int ANativeWindow_unlockAndPost(void* window)
{
    return wl_r20_pair_unlock(window,__builtin_return_address(0));
}
