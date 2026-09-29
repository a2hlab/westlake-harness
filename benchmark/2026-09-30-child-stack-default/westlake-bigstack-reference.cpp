    // Step 8: Launch the Android ActivityThread event loop
    LOGI("Launching ActivityThread for %s", msg.procName.c_str());
    // WESTLAKE (arm64 board, 2026-07-21) — run it on a BIG-STACK pthread.
    //
    // musl reports only __default_stacksize (128 KB) from pthread_getattr_np() for the
    // INITIAL thread, regardless of the real 8 MB rlimit stack.  ART's Thread::InitStackHwm
    // believes it, so anything deep on the child's main thread dies with
    //   "java.lang.StackOverflowError: stack size 124KB"   (128 KB - guard)
    // — observed killing android.graphics.Typeface.<clinit> on its font-mmap path
    // (MappedByteBuffer/DirectByteBuffer), which then leaves sDefaultTypeface null and
    // fails ensureBindApplication.  Patching the ELF PT_GNU_STACK and `ulimit -s` both
    // failed to move it (OHOS musl doesn't raise __default_stacksize from either).
    // A pthread created with an explicit stacksize DOES get an honest attr, so run the
    // whole ActivityThread/Looper on one.  It never returns, so just join it.
    {
        struct LaunchCtx {
            const SpawnMsg* msg; AppSpawnXRuntime* runtime;
        };
        static LaunchCtx ctx{&msg, runtime};   // enclosing fn is static: no `this`
        pthread_attr_t attr;
        pthread_attr_init(&attr);
        // §565: THIS is the stack ART reports as "stack size 8182KB" when the JIT starts
        // executing compiled frames -- it is an explicitly-sized pthread, not the process main
        // thread, which is why -Xss and RLIMIT_STACK (16 MB here) both had no effect.
        // ★codex's reading is the key one: ART turns the guard-page fault into StackOverflowError
        // by writing art_quick_throw_stack_overflow into the saved PC, so a CLEAN Java exception is
        // proof the handler and sigreturn worked -- the overflow is REAL, not spurious. Compiled
        // frames simply need more stack than the interpreter did.
        size_t javaStackMb = 8;
        if (const char* v = getenv("APPSPAWNX_JAVA_STACK_MB"); v && *v) {
            long m = strtol(v, nullptr, 10);
            if (m >= 1 && m <= 512) javaStackMb = (size_t)m;
        }
        fprintf(stderr, "[CM-BIGSTACK] java thread stack = %zu MB\n", javaStackMb); fflush(stderr);
        pthread_attr_setstacksize(&attr, javaStackMb * 1024 * 1024);
        pthread_t javaTid;
        int prc = pthread_create(&javaTid, &attr, [](void* a) -> void* {
            auto* c = static_cast<LaunchCtx*>(a);
            wl_prioritize_activity_thread();
            JNIEnv* tenv = nullptr;
            JavaVM* vm = c->runtime->getJavaVM();
            if (vm != nullptr && vm->AttachCurrentThread(&tenv, nullptr) != JNI_OK) {
                fprintf(stderr, "[CM-BIGSTACK] AttachCurrentThread FAILED\n"); fflush(stderr);
                return nullptr;
            }
            size_t ss = 0; pthread_attr_t ga;
            if (pthread_getattr_np(pthread_self(), &ga) == 0) {
                pthread_attr_getstacksize(&ga, &ss); pthread_attr_destroy(&ga);
            }
            fprintf(stderr, "[CM-BIGSTACK] ActivityThread on dedicated pthread, stack=%zu bytes\n", ss);
            fflush(stderr);
            ChildMain::launchActivityThread(tenv, *c->msg, c->runtime);
            return nullptr;
        }, &ctx);
        pthread_attr_destroy(&attr);
        if (prc == 0) {
            // The fork child starts out attached to ART and therefore registered as a
            // runnable mutator.  Once ActivityThread has moved to javaTid, this thread
            // does nothing but block forever in pthread_join().  Leaving it attached
            // makes a stop-the-world GC wait for a checkpoint that this native joiner
            // can never run; a cold Toutiao launch then deadlocks in
            // Heap::WaitForGcToCompleteLocked while registering an app dex file.
            // Detaching is the JNI-defined way to remove this otherwise-unused thread
            // from ART's mutator list.  No JNI state is used after a successful spawn.
            JavaVM* vm = runtime->getJavaVM();
            jint detachRc = vm != nullptr ? vm->DetachCurrentThread() : JNI_ERR;
            fprintf(stderr,
                    "[CM-BIGSTACK] launcher DetachCurrentThread before join rc=%d\n",
                    static_cast<int>(detachRc));
            fflush(stderr);
            pthread_join(javaTid, nullptr);
        } else {
            fprintf(stderr, "[CM-BIGSTACK] pthread_create failed (%d) — falling back to main thread\n", prc);
            fflush(stderr);
            wl_prioritize_activity_thread();
            launchActivityThread(env, msg, runtime);
        }
    }

    // Should never reach here – launchActivityThread enters an infinite loop
    LOGE("launchActivityThread returned unexpectedly – exiting");
    fprintf(stderr, "[CM-EXIT] launchActivityThread RETURNED — child_main:_exit(1)\n"); fflush(stderr);
    _exit(1);
}

// ---------------------------------------------------------------------------
