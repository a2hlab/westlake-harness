"""Check ABI-prefix bounds, detailed failure propagation and per-attempt reset."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class ResultChannel(unittest.TestCase):
    def test_real_result_writer_and_mixed_abi_bounds(self):
        compiler = shutil.which('clang')
        self.assertIsNotNone(compiler)
        source = r'''
#define WLSCPL_TESTING
#include "sealed_child_provider_loader.c"
#include <assert.h>
int main(void) {
    _Static_assert(offsetof(WlscplLoadResultV1, last_stage) == 40, "V1 prefix moved");
    _Static_assert(sizeof(WlscplLoadResultV1) == 216, "unexpected V2 layout");
    WlscplLoadRequestV1 request = {0};
    WlscplLoadResultV1 result;
    request.abi_version = WLSCPL_ABI_VERSION;
    N11eReset();
    g_n11e_failure.stage = WLSCPL_STAGE_AFTER_OWNER_VERIFY;
    errno = ENOENT;
    char oversized[400]; memset(oversized, 'x', sizeof oversized); oversized[399] = 0;
    N11eFailure(WLSCPL_FAILB_EMIT_RESOLVE, 1, oversized, "fallback");
    SetResult(&request, &result, WLSCPL_ERROR_DLOPEN, 26, NULL);
    assert(result.abi_version == 2 && result.struct_size == sizeof result);
    assert(result.last_stage == 6 && result.fail_branch == 4);
    assert(result.fail_artifact_index == 1 && result.fail_errno == ENOENT);
    assert(strlen(result.fail_detail) == 159 && result.fail_detail[159] == 0);
    N11eReset();
    g_n11e_failure.branch = WLSCPL_FAILB_OWNER_PUBLISH_LATE;
    g_n11e_failure.index = 1;
    SetResult(&request, &result, WLSCPL_OK, 26, (void*)1);
    assert(result.last_stage == WLSCPL_STAGE_DONE && result.fail_branch == 6);
    assert(result.fail_artifact_index == 1);
    (void)dlopen("/definitely/absent/n11f-stale-error.so", RTLD_NOW);
    N11eFailure(WLSCPL_FAILB_ARTIFACT_DLOPEN, 0, "current call error", "fallback");
    SetResult(&request, &result, WLSCPL_ERROR_DLOPEN, 26, NULL);
    assert(strcmp(result.fail_detail, "current call error") == 0);
    N11eReset();
    SetResult(&request, &result, WLSCPL_OK, 26, (void*)1);
    assert(result.last_stage == WLSCPL_STAGE_DONE && result.fail_branch == 0);
    assert(result.fail_artifact_index == UINT32_MAX && result.fail_detail[0] == 0);
    struct { unsigned char prefix[40]; unsigned char canary[176]; } old;
    memset(&old, 0xa5, sizeof old);
    request.abi_version = 1;
    SetResult(&request, (WlscplLoadResultV1*)&old, WLSCPL_ERROR_INVALID_ARGUMENT, 0, NULL);
    for (size_t i=0; i<sizeof old.canary; ++i) assert(old.canary[i] == 0xa5);
    assert(((WlscplLoadResultV1*)&old)->abi_version == 2);
    assert(((WlscplLoadResultV1*)&old)->struct_size == 216);
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name)
            (directory/'test.c').write_text(source)
            subprocess.run([compiler, '-std=c11', '-D_GNU_SOURCE', '-I'+str(HERE/'include'),
                            '-I'+str(HERE/'src'), str(directory/'test.c'), '-o', str(directory/'test')], check=True)
            subprocess.run([str(directory/'test')], check=True)



if __name__ == '__main__':
    unittest.main()
