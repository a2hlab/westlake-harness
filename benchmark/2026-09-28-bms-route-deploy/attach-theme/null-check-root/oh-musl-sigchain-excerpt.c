/**
  * @brief This is a callback function, which is registered to the kernel
  * @param[in] signo, the value of the signal.
  * @param[in] siginfo, the information of the signal.
  * @param[in] ucontext_raw, the context of the signal.
  * @retval void
  */
static void signal_chain_handler(int signo, siginfo_t* siginfo, void* ucontext_raw)
{
    SIGCHAIN_PRINT_DEBUG("%{public}s signo: %{public}d", __func__, signo);
    /* First call special handler. */
    /* If a process crashes, the sigchain'll call the corresponding  handler */
    if (!get_handling_signal()) {
        for (int i = 0; i < SIGNAL_CHAIN_SPECIAL_ACTION_MAX; i++) {
            if (sig_chains[signo - 1].sca_special_actions[i].sca_sigaction == NULL) {
                continue;
            }
            /* The special handler might not return. */
            bool noreturn = (sig_chains[signo - 1].sca_special_actions[i].sca_flags &
                             SIGCHAIN_ALLOW_NORETURN);
            sigset_t previous_mask;
            sigchain_sigmask(SIG_SETMASK, &sig_chains[signo - 1].sca_special_actions[i].sca_mask,
                            &previous_mask);

            bool previous_value = get_handling_signal();
            if (!noreturn) {
                set_handling_signal(true);
            }
            SIGCHAIN_PRINT_ERROR("%{public}s call %{public}d rd sigchain action for signal: %{public}d", __func__, i, signo);
            if (sig_chains[signo - 1].sca_special_actions[i].sca_sigaction(signo,
                                                            siginfo, ucontext_raw)) {
                set_handling_signal(previous_value);
                SIGCHAIN_PRINT_ERROR("%{public}s call %{public}d rd sigchain action for signal: %{public}d directly return", __func__, i, signo);
                return;
            }

            sigchain_sigmask(SIG_SETMASK, &previous_mask, NULL);
            set_handling_signal(previous_value);
        }
    }
    /* Then Call the user's signal handler */
    int sa_flags = sig_chains[signo - 1].sig_action.sa_flags;
    ucontext_t* ucontext = (ucontext_t*)(ucontext_raw);

    sigset_t mask;
    sigorset(&mask, &ucontext->uc_sigmask, &sig_chains[signo - 1].sig_action.sa_mask);

    if (!(sa_flags & SA_NODEFER)) {
        sigaddset(&mask, signo);
    }

    sigchain_sigmask(SIG_SETMASK, &mask, NULL);

    if ((sa_flags & SA_SIGINFO)) {
        SIGCHAIN_PRINT_INFO("%{public}s call usr sigaction for signal:"
            "%{public}d sig_action.sa_sigaction=%{public}lx",
            __func__, signo, (unsigned long)sig_chains[signo - 1].sig_action.sa_sigaction);
        sig_chains[signo - 1].sig_action.sa_sigaction(signo, siginfo, ucontext_raw);
    } else {
        if (sig_chains[signo - 1].sig_action.sa_handler == SIG_IGN) {
            SIGCHAIN_PRINT_ERROR("%{public}s SIG_IGN handler for signal: %{public}d", __func__, signo);
            return;
        } else if (sig_chains[signo - 1].sig_action.sa_handler == SIG_DFL) {
            SIGCHAIN_PRINT_ERROR("%{public}s SIG_DFL handler for signal: %{public}d", __func__, signo);
            remove_all_special_handler(signo);
            if (__syscall(SYS_rt_tgsigqueueinfo, __syscall(SYS_getpid), __syscall(SYS_gettid), signo, siginfo) != 0) {
                SIGCHAIN_PRINT_ERROR("Failed to rethrow sig(%{public}d), errno(%{public}d).", signo, errno);
            } else {
                SIGCHAIN_PRINT_ERROR("pid(%{public}d) rethrow sig(%{public}d) success.", __syscall(SYS_getpid), signo);
            }
        } else {
            SIGCHAIN_PRINT_INFO("%{public}s call usr sa_handler: %{public}p for signal:"
                "%{public}d sig_action.sa_handler=%{public}lx",
                __func__, signo, (unsigned long)sig_chains[signo - 1].sig_action.sa_handler);
            sig_chains[signo - 1].sig_action.sa_handler(signo);
        }
    }

    return;
}

static void mark_signal_to_sigchain(int signo)
{
    SIGCHAIN_PRINT_INFO("%{public}s signo: %{public}d", __func__, signo);
    if (!sig_chains[signo - 1].marked) {
        sigchain_register(signo);
        sig_chains[signo - 1].marked = true;
    }
}

/**
  * @brief Set the action of the signal.
  * @param[in] signo, the value of the signal.
  * @param[in] new_sa, the new action of the signal.
  * @retval void
  */
static void setaction(int signo, const struct sigaction *restrict new_sa)
{
    SIGCHAIN_PRINT_DEBUG("%{public}s signo: %{public}d", __func__, signo);
    sig_chains[signo - 1].sig_action = *new_sa;
}

/**
  * @brief Get the action of the signal.
    }
}

/**
  * @brief This is an external interface, add the special handler at the last of sigchain chains.
  * @param[in] signo, the value of the signal.
  * @param[in] sa, the action with special handler.
  * @retval void
  */
void add_special_handler_at_last(int signo, struct signal_chain_action* sa)
{
    SIGCHAIN_PRINT_INFO("%{public}s signo: %{public}d", __func__, signo);
    if (signo <= 0 || signo >= _NSIG) {
        SIGCHAIN_PRINT_FATAL("%{public}s Invalid signal %{public}d", __func__, signo);
        return;
    }

    if (sig_chains[signo - 1].sca_special_actions[SIGNAL_CHAIN_SPECIAL_ACTION_MAX - 1].sca_sigaction == NULL) {
        sig_chains[signo - 1].sca_special_actions[SIGNAL_CHAIN_SPECIAL_ACTION_MAX - 1] = *sa;
        mark_signal_to_sigchain(signo);
        return;
    }

    SIGCHAIN_PRINT_FATAL("Add too many the special handlers at last!");
}

/**
  * @brief Intercept the signal and sigaction.
  * @param[in] signo, the value of the signal.
  * @param[in] sa, the new action with the signal handler.
  * @param[out] old, the old action with the signal handler.
  * @retval true if the signal if intercepted, or false.
  */
bool intercept_sigaction(int signo, const struct sigaction *restrict sa,
                         struct sigaction *restrict old)
{
    SIGCHAIN_PRINT_DEBUG("%{public}s signo: %{public}d", __func__, signo);
    if (signo <= 0 || signo >= _NSIG) {
        SIGCHAIN_PRINT_ERROR("%{public}s Invalid signal %{public}d", __func__, signo);
        return false;
    }

    if (ismarked(signo)) {
        struct sigaction saved_action = getaction(signo);

        if (sa != NULL) {
            setaction(signo, sa);
        }
        if (old != NULL) {
            *old = saved_action;
        }
        return true;
