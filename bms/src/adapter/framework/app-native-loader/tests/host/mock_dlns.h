#ifndef WESTLAKE_ANL_HOST_TEST_MOCK_DLNS_H
#define WESTLAKE_ANL_HOST_TEST_MOCK_DLNS_H

#include "oh_dlns_abi.h"

typedef struct MockDlnsState {
    int init_calls;
    int create_calls;
    int inherit_calls;
    int separated_calls;
    int permitted_calls;
    int allowed_calls;
    int dlopen_calls;
    int dlclose_calls;
    int dlsym_calls;
    int bridge_install_calls;
    int bridge_install_create_calls;
    int last_create_flags;
    int last_dlopen_mode;
    int create_flags[4];
    char last_dlopen_file[512];
    char last_dlsym_symbol[128];
    void* last_dlclose_handle;
    char last_inherited_libs[512];
    char last_allowed_libs[512];
} MockDlnsState;

void MockDlnsReset(void);
const MockDlnsState* MockDlnsGet(void);
void MockDlnsSetBridgeSymbolAvailable(bool available);
void MockDlnsSetBridgeInstallResult(int result);
void MockDlnsSetDlopenFailure(const char* error_text);

#endif
