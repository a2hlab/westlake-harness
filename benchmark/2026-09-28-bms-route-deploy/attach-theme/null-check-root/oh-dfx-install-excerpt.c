#define NSIG 64
#endif

static void DFX_InstallSignalHandler(void);
// preload by libc
void __attribute__((constructor)) InitHandler(void)
{
    DFX_InstallSignalHandler();
}

static void DFX_InstallSignalHandler(void)
{
    if (g_hasInit) {
        return;
    }

    SetKernelSnapshot(true);
    InitCallbackItems();
    struct signal_chain_action sigchain = {
        .sca_sigaction = DFX_SigchainHandler,
        .sca_mask = {},
        .sca_flags = 0,
    };

    for (size_t i = 0; i < sizeof(SIGCHAIN_DUMP_SIGNAL_LIST) / sizeof(SIGCHAIN_DUMP_SIGNAL_LIST[0]); i++) {
        int32_t signo = SIGCHAIN_DUMP_SIGNAL_LIST[i];
        if (signo == SIGLEAK_STACK) {
            InstallSigActionHandler(signo);
            continue;
        }
        sigfillset(&sigchain.sca_mask);
        // dump signal not mask crash signal
        for (size_t j = 0; j < sizeof(SIGCHAIN_CRASH_SIGNAL_LIST) / sizeof(SIGCHAIN_CRASH_SIGNAL_LIST[0]); j++) {
            sigdelset(&sigchain.sca_mask, SIGCHAIN_CRASH_SIGNAL_LIST[j]);
        }
        add_special_signal_handler(signo, &sigchain);
    }
    for (size_t i = 0; i < sizeof(SIGCHAIN_CRASH_SIGNAL_LIST) / sizeof(SIGCHAIN_CRASH_SIGNAL_LIST[0]); i++) {
        int32_t signo = SIGCHAIN_CRASH_SIGNAL_LIST[i];
        if (signo == SIGILL || signo == SIGSYS) {
            InstallSigActionHandler(signo);
        } else {
            sigfillset(&sigchain.sca_mask);
            add_special_handler_at_last(signo, &sigchain);
        }
        if (signo == SIGSEGV) {
            /*Sigaction registers sigsgev again to prevent
              the cppcrash file from not being generated when cash in other sigchain handler*/
            InstallSigActionHandler(signo);
        }
    }

    g_hasInit = TRUE;
