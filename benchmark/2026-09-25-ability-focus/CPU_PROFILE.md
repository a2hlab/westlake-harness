# CPU self-time profiles

On-CPU task-clock periods only. Kernel time is included. These separate runs are excluded from queueMs cohorts. Consent profiles cover ~10 seconds starting immediately after the consent command; they are equal observation windows, not equal completed work. Unresolved executable samples remain explicit.

## OH consent

Sampled CPU: **1610.0 ms**. Raw report: `cpu-consent-2/report-main.txt`.

| Self % | CPU ms | DSO | Symbol |
|---:|---:|---|---|
| 20.34 | 327.5 | libart.so | art_quick_lock_object |
| 11.96 | 192.5 | libart.so | art::Monitor::MonitorEnter(art::Thread*, art::ObjPtr<art::mirror::Object>, bool) |
| 5.90 | 95.0 | id.article.news | id.article.news@0x3a1e1844 |
| 4.19 | 67.5 | id.article.news | id.article.news@0x3600bc88 |
| 2.48 | 40.0 | [kernel.kallsyms] | rwsem_spin_on_owner |
| 1.55 | 25.0 | libart.so | art::DexFile::FindTypeId(std::__h::basic_string_view<char, std::__h::char_traits<char>>) const |
| 1.55 | 25.0 | [kernel.kallsyms] | finish_task_switch |
| 1.40 | 22.5 | libart.so | art::DexFile::FindClassDef(art::dex::TypeIndex) const |
| 1.24 | 20.0 | libart.so | art::verifier::impl::(anonymous namespace)::MethodVerifier<false>::VerifyInvocationArgs(art::Instruction const*, art::verifier::MethodType, bool) |
| 1.09 | 17.5 | id.article.news | id.article.news@0x3a2134e0 |
| 1.09 | 17.5 | libart.so | art::ResolvedTypeMatchesDexType(art::ObjPtr<art::mirror::Class>, art::DexFile const&, art::dex::TypeIndex) |
| 1.09 | 17.5 | [kernel.kallsyms] | handle_mm_fault |
| 0.93 | 15.0 | libart.so | art::verifier::impl::(anonymous namespace)::MethodVerifier<false>::CodeFlowVerifyInstruction(unsigned int*) |
| 0.78 | 12.5 | id.article.news | id.article.news@0x360007e8 |
| 0.78 | 12.5 | [kernel.kallsyms] | smp_call_function_many_cond.llvm.1770886491869863892 |
| 0.78 | 12.5 | [kernel.kallsyms] | unwind_frame |
| 0.78 | 12.5 | libart.so | art::verifier::RegTypeCache::FindClass(art::ObjPtr<art::mirror::Class>, bool) const |
| 0.78 | 12.5 | id.article.news | id.article.news@0x36000a7c |
| 0.62 | 10.0 | [kernel.kallsyms] | el0_svc_common.llvm.16863548047879419796 |
| 0.62 | 10.0 | id.article.news | id.article.news@0x3a210f10 |

## Android consent

Sampled CPU: **2837.5 ms**. Raw report: `android-reference/cpu-1/report-main.txt`.

| Self % | CPU ms | DSO | Symbol |
|---:|---:|---|---|
| 9.34 | 265.0 | libhwui.so | neon::bilerp_clamp_8888(SkRasterPipelineStage*, unsigned long, unsigned long, std::byte*, float vector[4], float vector[4], float vector[4], float vector[4], float vector[4], float vector[4], float vector[4], float vector[4]) (.__uniq.171973291814702829445853707239222793327) |
| 5.64 | 160.0 | libart.so | NterpGetMethod |
| 4.49 | 127.5 | libart.so | art::mirror::Class::FindClassMethod(art::ObjPtr<art::mirror::DexCache>, unsigned int, art::PointerSize) |
| 3.52 | 100.0 | libart.so | nterp_helper |
| 3.17 | 90.0 | [kernel.kallsyms] | _raw_spin_unlock_irqrestore |
| 2.11 | 60.0 | [kernel.kallsyms] | el0_svc_common.llvm.9240720064732868026 |
| 1.50 | 42.5 | libart.so | nterp_op_invoke_virtual |
| 1.50 | 42.5 | [kernel.kallsyms] | _raw_spin_unlock_irq |
| 1.32 | 37.5 | libart.so | art::InternTable::InternStrong(unsigned int, char const*) |
| 1.15 | 32.5 | libart.so | art::ClassLinker::FindClass(art::Thread*, char const*, unsigned long, art::Handle<art::mirror::ClassLoader>) |
| 1.15 | 32.5 | [kernel.kallsyms] | local_daif_restore |
| 1.06 | 30.0 | libart.so | NterpGetInstanceFieldOffset |
| 1.06 | 30.0 | [kernel.kallsyms] | unwind_frame |
| 0.97 | 27.5 | libhwui.so | neon::store_8888(SkRasterPipelineStage*, unsigned long, unsigned long, std::byte*, float vector[4], float vector[4], float vector[4], float vector[4], float vector[4], float vector[4], float vector[4], float vector[4]) (.__uniq.171973291814702829445853707239222793327) |
| 0.97 | 27.5 | [kernel.kallsyms] | do_handle_mm_fault |
| 0.88 | 25.0 | libhwui.so | neon::load_8888_dst(SkRasterPipelineStage*, unsigned long, unsigned long, std::byte*, float vector[4], float vector[4], float vector[4], float vector[4], float vector[4], float vector[4], float vector[4], float vector[4]) (.__uniq.171973291814702829445853707239222793327) |
| 0.88 | 25.0 | [kernel.kallsyms] | __handle_mm_fault |
| 0.79 | 22.5 | libart.so | NterpGetShorty |
| 0.79 | 22.5 | libdexfile.so | art::TypeLookupTable::Lookup(std::__1::basic_string_view<char, std::__1::char_traits<char>>, unsigned int) const |
| 0.70 | 20.0 | libart.so | NterpGetClass |

## OH detail main

Sampled CPU: **2662.5 ms**. Raw report: `cpu-detail-1/report-main.txt`.

| Self % | CPU ms | DSO | Symbol |
|---:|---:|---|---|
| 18.69 | 497.5 | [kernel.kallsyms] | rwsem_spin_on_owner |
| 5.07 | 135.0 | [kernel.kallsyms] | _raw_spin_unlock_irqrestore |
| 2.54 | 67.5 | [kernel.kallsyms] | el0_svc_common.llvm.16863548047879419796 |
| 1.97 | 52.5 | libart.so | art::mirror::Class::FindClassMethod(art::ObjPtr<art::mirror::DexCache>, unsigned int, art::PointerSize) |
| 1.78 | 47.5 | libart.so | art::verifier::impl::(anonymous namespace)::MethodVerifier<false>::VerifyInvocationArgs(art::Instruction const*, art::verifier::MethodType, bool) |
| 1.78 | 47.5 | libart.so | art::verifier::impl::(anonymous namespace)::MethodVerifier<false>::CodeFlowVerifyInstruction(unsigned int*) |
| 1.69 | 45.0 | libart.so | art::mirror::Class::DescriptorEquals(char const*) |
| 1.50 | 40.0 | [kernel.kallsyms] | finish_task_switch |
| 1.50 | 40.0 | [kernel.kallsyms] | unwind_frame |
| 1.41 | 37.5 | libart.so | art::verifier::RegTypeCache::FindClass(art::ObjPtr<art::mirror::Class>, bool) const |
| 1.41 | 37.5 | libart.so | art::DexFile::FindTypeId(std::__h::basic_string_view<char, std::__h::char_traits<char>>) const |
| 1.31 | 35.0 | [kernel.kallsyms] | smp_call_function_many_cond.llvm.1770886491869863892 |
| 1.31 | 35.0 | libart.so | art::verifier::impl::(anonymous namespace)::MethodVerifier<false>::Verify() |
| 1.03 | 27.5 | ld-musl-aarch64.so.1 | /system/lib/ld-musl-aarch64.so.1+0x97f1c |
| 1.03 | 27.5 | ld-musl-aarch64.so.1 | strcmp |
| 1.03 | 27.5 | libart.so | art::DexFile::FindClassDef(art::dex::TypeIndex) const |
| 0.94 | 25.0 | libart.so | art::ResolvedTypeMatchesDexType(art::ObjPtr<art::mirror::Class>, art::DexFile const&, art::dex::TypeIndex) |
| 0.94 | 25.0 | libart.so | art::ComputeModifiedUtf8Hash(char const*) |
| 0.75 | 20.0 | libart.so | art::TypeLookupTable::Lookup(std::__h::basic_string_view<char, std::__h::char_traits<char>>, unsigned int) const |
| 0.75 | 20.0 | libart.so | art::ClassLinker::ResolveType(art::dex::TypeIndex, art::ArtMethod*) |

## OH detail RenderThread

Sampled CPU: **130.0 ms**. Raw report: `cpu-detail-1/report-render.txt`.

| Self % | CPU ms | DSO | Symbol |
|---:|---:|---|---|
| 15.38 | 20.0 | [kernel.kallsyms] | unwind_frame |
| 13.46 | 17.5 | [kernel.kallsyms] | copy_page_range |
| 9.62 | 12.5 | [kernel.kallsyms] | rwsem_spin_on_owner |
| 5.77 | 7.5 | [kernel.kallsyms] | arch_counter_get_cntpct.de8fdf0bd5357f6d08de61689e9881d7 |
| 5.77 | 7.5 | [kernel.kallsyms] | _raw_spin_unlock_irqrestore |
| 5.77 | 7.5 | [kernel.kallsyms] | walk_stackframe |
| 5.77 | 7.5 | [kernel.kallsyms] | save_return_addr.e0fae712d22d8aaf509295c68aa45426 |
| 3.85 | 5.0 | [kernel.kallsyms] | sched_clock |
| 3.85 | 5.0 | [kernel.kallsyms] | vm_normal_page |
| 3.85 | 5.0 | [kernel.kallsyms] | call_rcu |
| 3.85 | 5.0 | [kernel.kallsyms] | kmem_cache_alloc |
| 1.92 | 2.5 | [kernel.kallsyms] | preempt_count_add |
| 1.92 | 2.5 | [kernel.kallsyms] | handle_mm_fault |
| 1.92 | 2.5 | [kernel.kallsyms] | el0_svc_common.llvm.16863548047879419796 |
| 1.92 | 2.5 | [kernel.kallsyms] | do_notify_resume |
| 1.92 | 2.5 | [kernel.kallsyms] | stop_preemptoff_timing |
| 1.92 | 2.5 | [kernel.kallsyms] | preempt_count_sub |
| 1.92 | 2.5 | [kernel.kallsyms] | tracer_preempt_off |
| 1.92 | 2.5 | [kernel.kallsyms] | start_backtrace |
| 1.92 | 2.5 | [kernel.kallsyms] | _raw_spin_unlock_irq |

## Consent-window decomposition

OH/Android sampled main-thread CPU = 1610.0/2837.5 = **0.567×**. This is not the 665ms DOWN dispatch ratio and cannot be used to explain it causally: the window includes different executed work, waiting and runtime states. Off-CPU waiting is absent from a self CPU report.

| Category | OH CPU ms | Android CPU ms | OH contribution / Android total |
|---|---:|---:|---:|
| ART other | 105.0 | 180.0 | 0.037× |
| GC | 17.5 | 27.5 | 0.006× |
| JIT compiler/cache | 7.5 | 0.0 | 0.003× |
| JIT zygote executable mapping (unsymbolized) | 145.0 | 0.0 | 0.051× |
| OH libraries | 10.0 | 0.0 | 0.004× |
| WebView native | 0.0 | 32.5 | 0.000× |
| anonymous executable mapping (unsymbolized) | 252.5 | 0.0 | 0.089× |
| class loading/verification/resolution | 227.5 | 275.0 | 0.080× |
| compiled managed code | 0.0 | 260.0 | 0.000× |
| graphics | 0.0 | 415.0 | 0.000× |
| kernel other | 185.0 | 500.0 | 0.065× |
| libc | 42.5 | 65.0 | 0.015× |
| locks/synchronization | 592.5 | 172.5 | 0.209× |
| nterp | 20.0 | 547.5 | 0.007× |
| other / unresolved | 2.5 | 362.5 | 0.001× |
| westlake bridge/runtime | 2.5 | 0.0 | 0.001× |

## Observed DOWN dispatch factor (not a causal attribution)

Android reference DOWN mean = (3.710+5.273+5.240)/3 = 4.741ms. Idle OH article-target cold a4/a5/a7 DOWN mean = (124+111+207)/3 = 147.333ms. The old busy trace-2 value 665ms is 140.3× the Android mean; arithmetically this is 4.51× (busy/idle OH) times 31.08× (idle OH/Android). These are different trials and states, with diagnostic overhead and different hardware; they do not identify which subsystem caused either factor. CPU-category contributions above describe a separate consent window, not the DOWN event.

Both runs contain direct nterp leaf samples. No ExecuteSwitchImplCpp leaf sample in a limited profile does not prove it never executes. OH zygote-JIT and anonymous executable ranges are classified from that run’s maps; anonymous code is not given invented Java method names.

Endpoint /proc main-thread stat field39: OH CPU2 before / CPU7 after; Android CPU5 before / CPU4 after. These are last-executed CPU IDs, not continuous residency. Matching clock-frequency samples were not captured, so no frequency-normalized factor is claimed.
