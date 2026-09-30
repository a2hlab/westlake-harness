# N6 candidate-bound exception proposal

**PENDING outer approval; none installed. No device writes.**

Counts: {'U5 baseline': 126, 'N6 new': 1, 'N5 traversal': 57}

For each app/process, compare five singleton-library `(device,inode)` counts and payload SHA sets with a same-board U5 sample. LocalSend U5 has two liblog inodes. Missing baselines are unknown, not accepted. Also record EGL/GLES/libc++ provider identities and wrapper dispatch evidence.

| Row | Class | Gate/kind | Object | Issue ID |
| --- | --- | --- | --- | --- |
| 1 | U5 baseline | N1/unknown | `host` | `c90b8c4a9b6cfd220fb8c94c00c4736cf7179be1cda51d5e5e6c7dbd4ae67182` |
| 2 | U5 baseline | N1/unknown | `runtime` | `417e4d0a6c9e69b9c24a91beabbf46036dfd0d36f497dab4f902309b63d14a31` |
| 3 | U5 baseline | N1/unknown | `runtime` | `972fc61d845c13a9cc44a497c38a97a43061981f253c9648f36eef05de1ed6ba` |
| 4 | U5 baseline | N1/unknown | `runtime` | `e985bc3de4b337523ec8a3aaa25dcc8dbe7d96ea0b14b93888048ca0e9a43ea8` |
| 5 | U5 baseline | N1/unknown | `runtime` | `7b37d89fc240396630d1984303815444b0e4cf8d8eaa19b7a06fd5d7322e9fb7` |
| 6 | U5 baseline | N1/unknown | `runtime` | `cce47b5e0333d31ddbd69c3357124451730e0f425e26a73a2be903e908cb9571` |
| 7 | U5 baseline | N1/unresolved_calls | `runtime` | `af5432e50b808a03468741193a30f44c3d7d3ac742ffee3571fe8458c33b8e8e` |
| 8 | U5 baseline | N1/unresolved_calls | `runtime` | `4fd8b3fed2bcd91da4eb9e41a00740e96123eb4f34862dbeb4032c6ea24f464a` |
| 9 | U5 baseline | N1/unresolved_calls | `runtime` | `d406213786318e7a4e1a75bad856ee6d59b8e089dd269435b5f9a88db668cbc2` |
| 10 | U5 baseline | N1/unresolved_calls | `runtime` | `4a8ad2f2ecffc9ebd26943f2224885fd202c5f5bcbb70493ddb80b9b6b9d86bf` |
| 11 | U5 baseline | N1/unresolved_calls | `runtime` | `e84e815d3dfe0ba510a24a60516670e209e61350f1971a32ca0990b7e4cb6675` |
| 12 | U5 baseline | N1/unresolved_calls | `runtime` | `1e7dec294923b143d2bdf7b322f47a26e35d8f0e7af9a9f084da4f445e90ae6f` |
| 13 | U5 baseline | N1/unresolved_calls | `runtime` | `e4379d4de98abc7d620dbf08414ef14dc0d89d10d51deb0923c397abf8145b53` |
| 14 | U5 baseline | N1/unresolved_calls | `runtime` | `22034e9c24e403748d2915813a15eeda33aa03678e3d8a73736acd2f48904253` |
| 15 | U5 baseline | N1/unresolved_calls | `runtime` | `4482215ef31f768fd76e4e327883ee7f44cdbe475628f44025577799ef9863f8` |
| 16 | U5 baseline | N1/unresolved_calls | `runtime` | `bc662d59925d3efde02bc3f875fb8b1e97d88d4084b728a3e01e1bbed7408848` |
| 17 | U5 baseline | N1/unresolved_calls | `runtime` | `93e85a4559a7a001c7df83a3d0c5a8060f14806b6ca0b18bef8611bbbe52aff1` |
| 18 | U5 baseline | N1/unresolved_calls | `runtime` | `a0547317f68271b48c4c9d98a9125635d961849e9c8ff2b751c18e612aac59df` |
| 19 | U5 baseline | N1/unresolved_calls | `runtime` | `ad89d90bdcea1b65ef5dd3c81c9a378847bd43eed3a89f759c75cbbad0134124` |
| 20 | U5 baseline | N1/unresolved_calls | `runtime` | `6ae930e27a8ffeff9e929d7dbcdc24c656840b048d99d336c75212c9d7b7d126` |
| 21 | U5 baseline | N1/unresolved_calls | `runtime` | `f8c4ea40661fc03ed09b9d2ac95c2f1d207b5288feb49553694b3827ea63b730` |
| 22 | U5 baseline | N1/unresolved_calls | `runtime` | `df4aa9135748a871085c26a3b0229ee7eee74372553f21abfcf1eceff7629e11` |
| 23 | U5 baseline | N1/unresolved_calls | `runtime` | `054405359baaa294cc4dc41f6bed0cfbfcf92ef3724f9afa6d644c3dd92202ce` |
| 24 | U5 baseline | N1/unresolved_calls | `runtime` | `9d1d0b684c44b2509f6216c625ebbf9b40d2d102f2d62a4095e6e9f6a512ef8f` |
| 25 | U5 baseline | N1/unresolved_calls | `runtime` | `45d1624479692e4e3b10d4df2cfe1976f2d949aaaaf1e2b2d13f81cb4a7a826c` |
| 26 | U5 baseline | N1/unresolved_calls | `runtime` | `4b1a954d37e5adc8c1d7536fdbaac038e2cc691b58bf5cd0f7bdadc8c5384fb0` |
| 27 | U5 baseline | N1/unresolved_calls | `runtime` | `c0db145d15333c0397b6c9953388fb5e9c48822e3f0d4a351990669fde63314e` |
| 28 | U5 baseline | N1/unresolved_calls | `runtime` | `37e3cbd05518e11e2ac2e0a454a54ae85a0159ceeeb638674922da49ac97096a` |
| 29 | U5 baseline | N2/unknown-effective-path | `domain->app_paths` | `953f42df9929daacdb847690004385ac12dc6f5e6cdecc650da3af11a1d6bbf9` |
| 30 | U5 baseline | N2/unknown-effective-path | `domain->app_permitted_paths` | `f297a4af790461bfcc33dbbf9404d00b1cb742ee4ee9c4d6f8114294fa46154f` |
| 31 | U5 baseline | N2/unknown-effective-path | `domain->selected_load_dir` | `6a91239ee69332b4c8e608225955ffa5c0932fc2bf29478a278d25652538d0de` |
| 32 | U5 baseline | N2/missing-dt-needed | `/system/android/lib64/westlake_flutter/libGLESv2.so -> libGLESv3.so` | `fa5c42453cea90e8929b33909dd5bb64c6b7212a1a494889c87068552d5ac286` |
| 33 | U5 baseline | N2/missing-dt-needed | `/system/android/lib64/westlake_flutter/libandroid.so -> libsurface.z.so` | `a26423046f8b645d897b846d6ff78cb61669cd54f196c6ce7963e777d00279f5` |
| 34 | N6 new | N2/missing-dt-needed | `/system/android/lib64/westlake_flutter/libwestlake_native_abi.so -> libc++.so` | `2f9fa05c3e887d6274b6e93cf3aa9b81c8be1979f01b3deaa8e5a42452bcc321` |
| 35 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_android_runtime.so -> libEGL.so` | `1c49c7744b0af1cdff3a6c76e09e281f1997ffbcb631bc9c32e919e5de013298` |
| 36 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_android_runtime.so -> libGLESv3.so` | `06d4be0cc9c5519d452e7a4248bd74f42ffcf95a8a8b05771865a02b31ced160` |
| 37 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_android_runtime.so -> libhitrace_ndk.z.so` | `d4899c2a86ae5b7bb3d4c80c1cc42b063b4845066ce3d37ac488a0fc6c30268b` |
| 38 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_android_runtime.so -> libbegetutil.z.so` | `797ee2615fc01c44adaa76985ec16b0169f55fe23e1489a5814ee763025373be` |
| 39 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_android_runtime.so -> libsurface.z.so` | `19d9de972d24a244992f1ee26b5b9f26aa8124e1dbe19badf72de65a8fdcefed` |
| 40 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_android_runtime.so -> libhilog.so` | `372f9a278d039a1f360df0f3e5cc321d12ae977ed6ff85b8439208f10686d207` |
| 41 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_android_runtime.so -> libc++.so` | `f1cf2d68dc3c9d1146edcb21c7877719a9e8c4af0640ea81d928bc872c9aa5ba` |
| 42 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libandroidfw.so -> libc++.so` | `37a72100e9db97d3d785e6b309f75aeb45ddcc345ad7388fd01627dcdf56268a` |
| 43 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libbase.so -> libc++.so` | `4e0236460e974d2ddcb1108b4fadbf833385bea7db5183b30488060dc156e0e1` |
| 44 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libutils.so -> libc++.so` | `30eccdfec3d7d09c6dd9bb4e52a669dccea4e82d77ddae2f9819f13beb523f9a` |
| 45 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libcutils.so -> libc++.so` | `e450a3f290e7dcd37a4b369a7d49d2e2bda14f2da81bc6820b4eddda1d2f9b6d` |
| 46 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libziparchive.so -> libc++.so` | `e22b17cdf7d5f237dc002c71f580370df768b75d4701ea4eedd626a08915f0d8` |
| 47 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libicuuc.so -> libc++.so` | `af303b25bbc929e3bd5fcfe767ae222cb1c82014d8ef991d3ff6cb270c48e332` |
| 48 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liblog.so -> libc++.so` | `a5b9e2f81e65f9535c655dcfb6fb36ff86bd06a48d0df7cf30b5f6889c2ab102` |
| 49 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liblog.so -> libhilog.so` | `c885a622c87d0ed802462a11f7cc552e070456fb6a1bbac6cfc54b386e4bb57b` |
| 50 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libbionic_compat.so -> libbegetutil.z.so` | `2993bbf114fa85c30d1debe9e0261df4cb2fee9b0e01b836ec0123551ba2a199` |
| 51 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libbionic_compat.so -> libc++.so` | `568b90413d441a080cb94542aa33702b3aa3be31c540c36e712858b9530d5759` |
| 52 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libc++.so` | `8573b73e198b57e1d7d9af5019297d962fed13dbd3aa2a33148578a0370c5840` |
| 53 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libhilog.so` | `d48e71cab815ead328ee985b490a03e7610c4d48650e39132f99b37c696c9703` |
| 54 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libutils.z.so` | `47b6f8c5ee81dea8789d052262690158845d8836c83fce86f22eaa522511ba0b` |
| 55 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libipc_single.z.so` | `2fb78cb901b1f7f7f14e6f348687904ea16755977ea7bca4adff073d80f216a6` |
| 56 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libsamgr_proxy.z.so` | `513432f67cbd88dca99a59e2e9d81e750988fe43a25ff116cd51410961aab1bc` |
| 57 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libability_manager.z.so` | `a1e3907e6418952959e43c1277c3a19adc0352fdb724e864f5fa99c223e1ac54` |
| 58 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libapp_manager.z.so` | `893edde943e4bccb7a446c445beac7c8c54ea8b27dfbdf2efe0b75d4a3e89e81` |
| 59 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libability_connect_callback_stub.z.so` | `cd0a2a693c062bc52066899a6e3b1a9412d2e903beacef5819d0e0738a4c2ba2` |
| 60 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libwm.z.so` | `a130e3e75db0b1ac8b0409b0d7aeb652d92f59abae6772dd60074f6e8ca52249` |
| 61 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libdm.z.so` | `4c6a8cbb59ba758bbce030f283f2ad93f047b7e02ab7c767b0ee5235c858fbdb` |
| 62 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> librender_service_client.z.so` | `1b97f1546680fc089e31c2b9cab75f8f4838bfeb2f22d054dcce990ced5fe057` |
| 63 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libskia_canvaskit.z.so` | `0c8f833ec5b58e1ec68be5354ca61cb43136039d24759edabbbeb9beebd79a4f` |
| 64 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libmmi-client.z.so` | `e4db05c1d461e43b3d83b0237c435bb024c2c6f88570b9737c08cfd1b0e29e39` |
| 65 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libsurface.z.so` | `ec50e4f9d96855e8745dcda5422bae1daf72bba5277d6f19a5f6fc261618fbb3` |
| 66 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libcesfwk_innerkits.z.so` | `73ac83a281a6ed6efefa3e094024f61fb1f1830a5fd01371724acdec4fcbba58` |
| 67 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libdatashare_consumer.z.so` | `ce952580dea042f0979a7749bff7e8d737c110f5a86097a19ce84040623f6928` |
| 68 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libappexecfwk_core.z.so` | `2d1a934e64d2611f00da623c2e3080149a3d8f94dc959a64d599a40671f021bb` |
| 69 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libappkit_native.z.so` | `7f5aa3dc8eaa2b36bbe9e4eda288b94f165d5e2023f92a6de5737dba0fe368dc` |
| 70 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libEGL.so` | `1bdfe73ab88db58feb3a2dab91470a3f8a99bf64f74facfcbb6d1b8342315eb8` |
| 71 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libwant.z.so` | `8bd9c2bdf05bba19c27be3ce282c88789b090afd9f59578f4b5aa6c9cb7c407e` |
| 72 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libzuri.z.so` | `245269cb96c5cd2d53b621bad859750f52af4490b3a5c9f90104aa1798bc59f5` |
| 73 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libconfiguration.z.so` | `4e3db1f0de531c9317bd7feb60539753df87543ca056ef624fd2cec18ee5838d` |
| 74 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libmission_info.z.so` | `98b7f6223ab96a646a6cd222ba2e919655d429af5a4577a9105153c07d796271` |
| 75 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> librender_service_base.z.so` | `c86644d7bd0db1061e20a0b8727180771e09ff2331f769e1b8ec1ae21486fa1f` |
| 76 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libscene_session.z.so` | `718b813ba64383eb177100e62978b45c17871d0026067db15c3b1154c7d65915` |
| 77 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libwindow_scene_common.z.so` | `4faabf4e3c86d721fe8fb3b9001474fe5f93b3185914f9c7390d83ad104c5a82` |
| 78 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libsession_manager.z.so` | `1d20a735a660c427b223d529823e3ddb55168062ff83d0186a24a9c29c6cf829` |
| 79 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libwmutil.z.so` | `94f76f5db810a3e46fe646e151c7460335e31cb163646a87be1f0f74c0b97ee5` |
| 80 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libeventhandler.z.so` | `9df52a5b2d85d891c87faa37b5fb661c9331e011aa1bcea86362aee996dd9a9c` |
| 81 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libhitrace_ndk.z.so` | `f3b75765676dae2b1d0f6a8e559ce35deb52f68db2dc8526ec023cb2856748ff` |
| 82 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so -> libsync_fence.z.so` | `40b127c073bb746c674fa01359a03ac6259264e4e182ab522d7cc068f4abe064` |
| 83 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libnativehelper.so -> libc++.so` | `03bc1b7c372ff9a122a0c8899b65fb72081bfa863457acef674d03a03e833733` |
| 84 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libnativeloader.so -> libc++.so` | `d589f48771709a08a26ed74be0860237f0b13e0a9d4819d87b95949da18b829d` |
| 85 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libappexecfwk_base.z.so -> libwant.z.so` | `5d292f28e8f212be33b86f237371de938ba9e75d18bc7f34fc9d503948f7f4d6` |
| 86 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libappexecfwk_base.z.so -> libutils.z.so` | `fdb8a6fc6dbf56b5daff191ea80498929c342a8cd07d9aaa9acdab2b0a66a6ca` |
| 87 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libappexecfwk_base.z.so -> libhilog.so` | `799d0830691129242d08c7ba1be614ad4b8d20941dc60ca1cac312f2dd21a69b` |
| 88 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libappexecfwk_base.z.so -> libipc_single.z.so` | `23bc59b215530bb1de11922c22e4307e0d2982ffb2bf593a89c75b4fa09280a5` |
| 89 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libappexecfwk_base.z.so -> libutd_client.z.so` | `1ef9ceb2f3b5b2cd0fd2fb080113c4e43e38247c277ce23d1556a5e5327a5c7e` |
| 90 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libappexecfwk_base.z.so -> libc++.so` | `309ef3a5cecb78f336419d1fb94e9b4d77f8c46685121dc8ea85ea7940ed62b1` |
| 91 | N5 traversal | N2/missing-dt-needed | `/system/android/lib64/libappexecfwk_base.z.so -> libclang_rt.ubsan_minimal.so` | `4245a74103723edf6012361edb8e84383f03cf10fd8d027da125250c1bebf578` |
| 92 | U5 baseline | N2/unknown-effective-path | `domain->app_paths` | `6958e4582fad193a82d027c028366dc30aa086e65944d7f7c1a2a9e37adb5eb0` |
| 93 | U5 baseline | N2/unknown-effective-path | `domain->app_permitted_paths` | `0c81645c756db35804f182bf92b77a1f5c406c43ab8e07cfcba71a408790bee4` |
| 94 | U5 baseline | N2/unknown-effective-path | `domain->selected_load_dir` | `0a093848bf531b5a65fa19563d2115a2f3835bd9bfd3066ce67151d07dc1ecf0` |
| 95 | U5 baseline | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libGLESv2.so -> libGLESv3.so` | `213f6e3919e25e11cd90ffd1020b8e2e633c34a0f2319287ba909c5c008dd906` |
| 96 | U5 baseline | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libGLESv2.so -> libc.so` | `281d7852ddd0af8efc7319c906b03b48a1e252f375e564e0bf1671e8526bcaab` |
| 97 | U5 baseline | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libandroid.so -> liboh_android_runtime.so` | `a28be66866b44a8dd08c3ec8fc4eaf92ee1569ab2343a8244d398ebee02ff083` |
| 98 | U5 baseline | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libandroid.so -> libsurface.z.so` | `8bc36c6a6db4ce2957e56ec2f5d514abe6167947fb47063359ec6bf99b3307c8` |
| 99 | U5 baseline | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libandroid.so -> libc.so` | `944283c6653e4b91738f02ea059927f74c3d21c047742af4f0016100ed65e47a` |
| 100 | U5 baseline | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libjnigraphics.so -> libc.so` | `f6eba56079be42a00fce01eb78e5678cd6f7f7759de1e04a119f9be23da0a76f` |
| 101 | U5 baseline | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libstdc++.so -> libc.so` | `6f950edba0626890bbf28fca42ef741e251b3571b32eb0cd9e0b090ed17220db` |
| 102 | U5 baseline | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libwestlake_native_abi.so -> libc.so` | `ee06dcf2cd6e85f193d368c474c41d1ff9c4af9e34b4437cd7576255af756866` |
| 103 | U5 baseline | N2/uncovered-library-directory | `/data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a` | `3fe0d4e05a595bf7547fa3e137578433963b347ee30637afd8fef5025fdd7ef7` |
| 104 | U5 baseline | N2/uncovered-library-directory | `/system/android/lib64` | `dfdad8b2f338452aa5efd35960f9c98a310858882ac75e0bd5ccd1e6937b61d2` |
| 105 | U5 baseline | N2/uncovered-library-directory | `/system/lib64` | `f237456c07758ca1e8366330c0faaf70c5c2917c723b205c913a2e3cb7d1db81` |
| 106 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/appdetailability` | `34f40a832ca53f6eca9ff3909193c91ebb2fa8ee9a253efa86129f9fabb42c4c` |
| 107 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/appspawn` | `44f73546d7b79d0bf5db5535d7bb221cd2e7c3e509b833eed08e7cb99f9e75af` |
| 108 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/appspawn/appspawn` | `efe92055500c47f9a193b74278b35eb4c52d643bc37b4fbaed6a970efc074fa4` |
| 109 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/appspawn/common` | `93b5a58cad6a808cf295047af7c3a7d9bd1488b8d57d4d0f3fa055fa436e9208` |
| 110 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/appspawn/nativespawn` | `41660eed4691d9cfe9a18def10e9a74ee626b4d342ead0fb028d825963b3f07b` |
| 111 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/appspawn/nwebspawn` | `759db59bbbc03a150ad7d83fac06f5ccd1b963bfcd12a4f10b5faef6f477d8dd` |
| 112 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/chipset-pub-sdk` | `254535dd873bd87f8de8a82e00ffc460d0b462018cdb5564daab0c3c62214b23` |
| 113 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/chipset-sdk` | `d40635b9896dec28b516d4c3fee252e16adb56020ac1b28e4e85c0ca3dcc4a00` |
| 114 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/chipset-sdk-sp` | `0081600e1cb0865d6b7f213ce93f6213ffd96152802b2c424e3196cfb00be9be` |
| 115 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/edm_plugin` | `3d28561f43874cd15653d102bd65b2fe3847ef44fa7f9d124e04bf981f52abb3` |
| 116 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/extensionability` | `55155cd8a5b13239580016e28332feaeddece12091f81c5bdae72fd6aaf235b8` |
| 117 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/graphics3d` | `6e9de071b9a4e6376215de57e5561f988532cf7520f787c7d4cd97359c29013e` |
| 118 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/init` | `4759f8df8493f6b585550f34ccd377860d03d825edfd37363b264c43a40608d0` |
| 119 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/init/autorun` | `2be02b4a5d54a1266e97d14906178e43972efdd272b8283648c63bd4f447b74d` |
| 120 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/init/reboot` | `8c136cc7c57bdf68f480e4265ab741d47ee24905a925935342a56cd7eee46122` |
| 121 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/media` | `170790ab252f8c07a1591ae7573f3039c1a3d9e32fa0adf8199a78a7d48ad82f` |
| 122 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/media/histreamer_plugins` | `a9aed5131aafa73006e7f7f8436f2ae6a529fd7d8432cee5197a3ea4c26908d7` |
| 123 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/media/media_plugins` | `fa09877896001f84f292097dcd4055b65184b4ec47838d7fb319d2864553d9bd` |
| 124 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module` | `1562c020366bdcac6c4aece49beeb98b8d8279c9d9d404f483afd91dc18c2dc3` |
| 125 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/ability` | `fa6cb69aaa3ff45493ef0eb59b645eba482a20609431daf181cec1c3fe0b7461` |
| 126 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/accessibility` | `95cbfb84b21e61f8ed438fb12663ba4864f132e5a9aca4bdfbe51c9e043d2c3c` |
| 127 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/account` | `d775f78c85c7e8e6957a15df0caf001321ed8e3c794f144153b2df691f9d208d` |
| 128 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/advertising` | `d023361ca3dea272c0db43708017264f20ea96337a02725f3ee5b63792b30b98` |
| 129 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/ai` | `9a693111c1ebeac4bcfd1ba04b131bc628c53149770a197abdb38288feeca5e8` |
| 130 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/animation` | `4937d03688bd909328c66d54d8c216226517ae4358f23d15a8bc4ccf455b23cf` |
| 131 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/app` | `d0b8211b59d0dfb64c7c88b81ea61e70ebf606f5a16e74178456857fee556581` |
| 132 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/app/ability` | `b3f4aeac82750bb3091ded4a77f520bac9e171db059f772f8f86f9812e2e944e` |
| 133 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/app/appstartup` | `91aa4a0a2d09ff7e420292f38d54d4cdf5ef426c9a30f2e7d164ead018d2b0d9` |
| 134 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/app/form` | `5d75fd6a42fd39a92133e15d6c871fc8d6a701ab6f5f413511c86c1d41596337` |
| 135 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/application` | `7aca5ff1a43a6641062c7bd656305ee0dcb64aabc47f09fc1262a3cda07c353b` |
| 136 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/arkts` | `7d4befcc74516ae42d9fc77c9952e62e82fda116fbdf3bc586dc8b8abdc39886` |
| 137 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/arkts/math` | `9ab6a929187a8e31f547362c130d6c637c1557867936f3152d0825b3ce1871f4` |
| 138 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/arkui` | `6daf650b3064c249b617070fb724dce1bf7638de4305d72d678fa196f4fe95fc` |
| 139 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/arkui/advanced` | `dfcf3b90ca07dc17d469eb35413373817f4ef2e3a6dc9cf5ef242adf4154c4cf` |
| 140 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/arkui/intelligence` | `f97de84c24fc4cd58c8737663b4d5c5adae1037350cfa0133fa681d79f778756` |
| 141 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/atomicservice` | `becbe477f69e90e8469e809893ec551c076dcb3500d00f136153cf31501da7bd` |
| 142 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/bluetooth` | `e0f7e961a88c6b7960be4a7fd9b94ae14d3018cd39bdae93b40a9a9d2e447caa` |
| 143 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/bundle` | `bcfff1cadb3cecc7712131f706955024935b6addec7e7e659f795ae1bae1f559` |
| 144 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/continuation` | `46ba2804da531a4549f81a8914e46e8fc46f7fb698ef0ee80ee82952ab032252` |
| 145 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/customization` | `a8ab3b6d1539879930f096941a3ee3ac3a8f248195c97d128472b2ed6f8311a6` |
| 146 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/data` | `5b28d65f7375be6e5853b013e0faa9e81a68cb7154038d215a3034921edf0afc` |
| 147 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/devicestatus` | `c2bedf256cb51d164828661eef60c1be2d5679ec36ede86d92cc0cda6632afe3` |
| 148 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/distributedhardware` | `4bce3d6517fdc6e563658a84c3f21a384581fc15d3786b73eae1d9f23ac42a3c` |
| 149 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/distributedsched` | `08ded0e641dd1e6f5c75682ac31c268765ffbb02562a3d8e60ac252daf60e8ec` |
| 150 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/driver` | `63d22d77537f57edcda78dcacfbf22a19522164b59dcbc431614fc3116c65c73` |
| 151 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/enterprise` | `91b7875eec1d8ab6e7b0b2b2f03a94a86a805b9c20469119b6b20792ea15ab9f` |
| 152 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/events` | `dc37bc76e53a1ba78b8573e7aca9ddcb5d16a0649041996eb8cd7cad4ae243b1` |
| 153 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/file` | `752c5d8569407c72d3e466b4571ab2b68cd89d7a16f91feb96c81cef96c28e38` |
| 154 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/filemanagement` | `4886913f958f16ccf7a409395825b204aff3764d86d932f72985c9d5c726d401` |
| 155 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/fusionconnectivity` | `8f97b30a2b7bcbd9a57cb270df3e156d337de421356433c5ae2c2f8eec96cd79` |
| 156 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/graphics` | `f80741fd59203bcb708e6b4fb5f455fdf805784c95627c13fc457c4a995508d5` |
| 157 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/hiviewdfx` | `6914d9d1f08d44ae1ce4d895e2c2fac4ce23f0d8213404a7ae1285cbeb81bb3b` |
| 158 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/identifier` | `81bc8a60b79efdf403126b4dd123538df92e36a83d27dcc32a46806e58c2a96d` |
| 159 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/inputmethod` | `8f2bc11019dde78ab832c8bfd88c97d9452aa8a72c5dbb37c9c3a4b16852da4d` |
| 160 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/multimedia` | `8b3fed79d60ef000c4f6c0e8565a3bd6fbb6e20cf9eff07b6cd43cacc7a0cf75` |
| 161 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/multimodalawareness` | `32138f950a9adf9821ddd22e8ed762794f59f02e4a6277c3830ebd8908038e2f` |
| 162 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/multimodalinput` | `c15e18b39dbffc762c263d188e1fd4ce3a29aee7e75710ee8b93933c47887300` |
| 163 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/net` | `41af7529579d9d0fb5fc20db8aefa5d3aa675683fa0520b773ad52cd6998a401` |
| 164 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/request` | `6d20377ef880e7fbcb5a14e508fa97714468586011ee5409e052b26fdc852506` |
| 165 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/resourceschedule` | `6d95717f71ec673a737fe05a2994053cbdb7a7d29602f900d02efcb15b8ea363` |
| 166 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/security` | `d4f6fc8dd541d25c1c8707b164420be837f217d408e941d5d945d2ea01791d72` |
| 167 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/selectioninput` | `407313b78c7b8b05e63f73378ca37849da4b0bfd5d2c80584e860e5decfea1d8` |
| 168 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/telephony` | `5699cb242702f7499e0f01ab3cc0314f9bbf2ec4dd571f2ed89b6243d682f553` |
| 169 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/test` | `fb1b1d3dd250562e1e1a369134d33593db99520c7c5c67e9343921b3b403db73` |
| 170 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/usbmanager` | `9a21d097aab71ed66eabcaaa5411d879031ba60756e503ec44dcf1c0560d9f64` |
| 171 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/useriam` | `e326c21cf9c22576098836ad85b4f77d085b10d65db55ec087c97a55b3668204` |
| 172 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/util` | `1be802deabf88ec009aed97ee5ca4549ca18a4df9c0dee12aaa810cbbd5373ed` |
| 173 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/web` | `7d5ed281cdef7b99083801d5d1b88281dc773eb84b95a194231ef02e398597f2` |
| 174 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/module/window` | `25dca7f7ab18204cf2c44208441e5c7256e8c84b66031d2ff5de11bbbc01fc04` |
| 175 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/ndk` | `d9c9eb11b338b2a3a3adbcf3cb9c80ec95e16ca3c9ee28dc559f5d7181675e26` |
| 176 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/platformsdk` | `3efed74aac02036d38eaec2eaa70e9694b0a7b2349f6e648651e4ad9742b5937` |
| 177 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/seccomp` | `f4cda727c7b40758f5e94c7c6ac376874691f2b915f22e6292ca75b560eef3e7` |
| 178 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/westlake/route-a/74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac` | `b80446ce24cf30f8b7a45521188cc1c2390a8e83f9f8d30579258e4b0af75e2d` |
| 179 | U5 baseline | N2/uncovered-library-directory | `/system/lib64/westlake/route-a/74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d` | `71668046f4c05f577b283b90a417b6cec8abe9bf14bceedc357ab123a7fcad0c` |
| 180 | U5 baseline | N2/uncovered-library-directory | `/vendor/lib64` | `b17322a0d8e097b1035c960b1d05a5fd092000d8135d4b8d58de91fd48b8648d` |
| 181 | U5 baseline | N2/uncovered-library-directory | `/vendor/lib64/chipsetsdk` | `08fcaaa293dc002617dc822db6da1cb8db0c2a06abba216d39d2344b4f511a06` |
| 182 | U5 baseline | N2/uncovered-library-directory | `/vendor/lib64/hw` | `1d968a8906321051ca4c0f60685d922454d34e4886fdcbb6eeb17333b1cf4ddd` |
| 183 | U5 baseline | N2/uncovered-library-directory | `/vendor/lib64/passthrough` | `7e05beb43c65c0133f2294217602a255653b28b8b8861a2c97f0d675940af490` |
| 184 | U5 baseline | N2/uncovered-library-directory | `/vendor/lib64/passthrough/indirect` | `5c9f87c69258f6ea02013b9ec6c9ff2cfa814dafc4b3d5e6af31e2f5df605119` |
