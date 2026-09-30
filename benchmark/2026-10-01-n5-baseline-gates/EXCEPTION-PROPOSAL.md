# Native baseline exception proposal

Status: **PENDING outer review; no entries installed, no N5 device deployment.**

Every row below is separately bound to a package manifest, complete sidecar input hash and strict issue ID in `exception-proposal.json`. Approval of a group must explicitly enumerate its rows. Baseline evidence: `benchmark/2026-10-01-u5-sweep/{results.json,facts-all.txt}`; outer signed 24 own-UI outcomes. This is bounded test eligibility, not proof that unresolved initialization or namespace visibility is safe.

N5-only edges are 57 newly traversed dependencies of unchanged U5 library bytes. All 57 dependency basenames exist in the read-only device snapshot. The strict checker does not follow direct inheritance or change owner while traversing a dependency. Physical existence therefore does not discharge its visibility finding. Owner reuse / one initialization remains the device experiment, with U5 rollback required.

## Per-object decisions requested

| Row | Package | Relation | Gate/kind | Object | Strict issue ID |
| --- | --- | --- | --- | --- | --- |
| 1 | U5 | shared | N1/unknown | `host / {'function': 'main', 'namespace': 'default', 'library': None, 'target_expression': 'plugin_path', 'evidence': {'source': 'n4-host.c', 'line': 629, 'text': 'plugin_handle = dlopen(plugin_path, RTLD_NOW / RTLD_NOLOAD);'}, ` | `7e9e027e97d7c7ccd0c82f4fc14b65b0eb1f5070aa52d00b1469d4a66412a89b` |
| 2 | U5 | shared | N1/unknown | `runtime / {'class_name': 'com/google/android/gles_jni/EGLConfigImpl', 'operation': 'GetMethodID', 'sequence': 73, 'evidence': {'source': 'egl.cpp', 'line': 103, 'text': 'jmethodID configCtor = env->GetMethodID(configClass, "<init>` | `396ac0a189470bbdf8a2652a37c6e8c775432e69d4b52762d114493a04e6e660` |
| 3 | U5 | shared | N1/unknown | `runtime / {'class_name': 'com/google/android/gles_jni/EGLConfigImpl', 'operation': 'GetFieldID', 'sequence': 74, 'evidence': {'source': 'egl.cpp', 'line': 105, 'text': 'jfieldID configField = env->GetFieldID(configClass, "mEGLConf` | `6919c18528a8a49ceecc2da96cdea17bc425a55f8bd6cbdf9b07a36de9949e90` |
| 4 | U5 | shared | N1/unknown | `runtime / {'class_name': 'com/google/android/gles_jni/EGLDisplayImpl', 'operation': 'GetFieldID', 'sequence': 76, 'evidence': {'source': 'egl.cpp', 'line': 109, 'text': 'jfieldID displayField = env->GetFieldID(displayClass, "mEGLD` | `598c76e98e981393130074905f1d368f43e6bd245bb3696e11fc0809c18c8d91` |
| 5 | U5 | shared | N1/unknown | `runtime / {'class_name': 'com/google/android/gles_jni/EGLContextImpl', 'operation': 'GetFieldID', 'sequence': 78, 'evidence': {'source': 'egl.cpp', 'line': 113, 'text': 'jfieldID contextField = env->GetFieldID(contextClass, "mEGLC` | `aa56e5df236969a8f98202cc5958f4a7270845fbf96c000ecc7e48a4b43d44c1` |
| 6 | U5 | shared | N1/unknown | `runtime / {'class_name': 'com/google/android/gles_jni/EGLSurfaceImpl', 'operation': 'GetFieldID', 'sequence': 80, 'evidence': {'source': 'egl.cpp', 'line': 117, 'text': 'jfieldID surfaceField = env->GetFieldID(surfaceClass, "mEGLS` | `d4cdfee1a504b00059ae672c5732480a7196cfe7e1d2e388b98ad35fbb5f1fb8` |
| 7 | U5 | shared | N1/unresolved_calls | `runtime / ExceptionCheck` | `3af8a88ef8632e6872763d84f547bc2519f11155ffd06d25e0632f9fad67b6da` |
| 8 | U5 | shared | N1/unresolved_calls | `runtime / ExceptionClear` | `a6c12c464d740e7ae9afe5f5dbb5e6e258d292cf3879181b9f55f698251ea81d` |
| 9 | U5 | shared | N1/unresolved_calls | `runtime / ExceptionDescribe` | `9f3921d86629d7272f5577e89ccf95e5e5116e2b05f1985618667563a75334da` |
| 10 | U5 | shared | N1/unresolved_calls | `runtime / GetJavaVM` | `32964444b4049c3bd820cc7d94c50410ddcfc3dfbf93c2dc8b00641dce349738` |
| 11 | U5 | shared | N1/unresolved_calls | `runtime / HiLogPrint` | `e738de13af3ac541e463b55cdd76ece7da65fdeab41c55825816c9d7a323f24b` |
| 12 | U5 | shared | N1/unresolved_calls | `runtime / NELEM` | `15b71da794eb05986a232403b7d878f5e68f0bb9128141c788c60ecd58200854` |
| 13 | U5 | shared | N1/unresolved_calls | `runtime / NewGlobalRef` | `bb96948ad779961df67d8c92e87413c23a233c8766977dc4f9410d680dae97d9` |
| 14 | U5 | shared | N1/unresolved_calls | `runtime / PopLocalFrame` | `3a3e68f9935d1012311189575790479afeaf11ac937c98c04f4c70f3916c27c7` |
| 15 | U5 | shared | N1/unresolved_calls | `runtime / PushLocalFrame` | `b536fbd022f72535c034faf4a322b59ebb19845aa04b4234a1439b22af28f9ff` |
| 16 | U5 | shared | N1/unresolved_calls | `runtime / dlerror` | `bea49c20de5b0ad7d99448630e805ba0d53c59618d6e2b449c4c01904d54ad3b` |
| 17 | U5 | shared | N1/unresolved_calls | `runtime / dlopen` | `60c3cdf1a06d6743a625b760180bd53ca9dc663243e00c312db6652e7ff6540e` |
| 18 | U5 | shared | N1/unresolved_calls | `runtime / dlsym` | `aeb64620e37364e23482594a062a1c21d4c691c9f28e07c2e461f4a9abcaad52` |
| 19 | U5 | shared | N1/unresolved_calls | `runtime / fn` | `35c75632215778bcaa3a8b4b4d383209fa168ad36e9d84509622cea455820ddc` |
| 20 | U5 | shared | N1/unresolved_calls | `runtime / fprintf` | `0086e5ef8ac94125462a119d3b7a17ba79cf8f26e4e5604ed90cfc35fd11caf2` |
| 21 | U5 | shared | N1/unresolved_calls | `runtime / int` | `a7ef09e3ac932e89f8a48685e287d71b56d693fdd14622fd0f5693fbb89e7b75` |
| 22 | U5 | shared | N1/unresolved_calls | `runtime / jint` | `5d611dbf210418ccd6fee5743a834b03d53a337b583180cfaceb68f3aa1c26e0` |
| 23 | U5 | shared | N1/unresolved_calls | `runtime / jniThrowException` | `f24338308a573c6eb582e3f9b9cc3706c2ef3d7d807a8aa3c16b406138b49b58` |
| 24 | U5 | shared | N1/unresolved_calls | `runtime / memcpy` | `fb41e11fe6253fcdda2b9f8b6295d44a89b51da7c7af16e47e83a7658b1ffb09` |
| 25 | U5 | shared | N1/unresolved_calls | `runtime / onload` | `926ae03babbb99a92943ffa6f3906ae773c9a608cfc5c8dc128eed8251d943f5` |
| 26 | U5 | shared | N1/unresolved_calls | `runtime / proc` | `8e2aec1027ef92f4d95a22232bafb774277dd1ea7a3859fa1045cc2bcb83f185` |
| 27 | U5 | shared | N1/unresolved_calls | `runtime / register_android_graphics_compat_shim` | `d4adcf809de8cadf8b5f554a83a15fcb69701e6d31db5d4962a7692e7db2d34b` |
| 28 | U5 | shared | N1/unresolved_calls | `runtime / register_n2_Camera` | `f9efcadf6d22b1c71614fb08aabfbdc2feee8b677a9c869d04feb6ac59eb29b9` |
| 29 | U5 | shared | N2/unknown-effective-path | `domain->app_paths` | `76f387288d66d1d4b386c47631aff396a2a406e515b32ac039c1dce7c705e365` |
| 30 | U5 | shared | N2/unknown-effective-path | `domain->app_permitted_paths` | `ba02a5b7b1502ce7dbd909497fc466cd739c31f1b82d03f47d0142e666f6cf22` |
| 31 | U5 | shared | N2/unknown-effective-path | `domain->selected_load_dir` | `6112ada21a95d6b99daaf6bbccc52a649240257b20cbc3a3d1e2ff47a90a8b82` |
| 32 | U5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_flutter/libGLESv2.so → libGLESv3.so` | `af4809dfe69674a4c1f71a175b29f5da44a85bb4664d7e21a1978a967a6fd86b` |
| 33 | U5 | u5-only | N2/missing-dt-needed | `/system/android/lib64/westlake_flutter/libGLESv2.so → libc.so` | `0eff577495506fc7f503ac3d0dc16e438c2b321887773f42dc68d8ac72ef1edc` |
| 34 | U5 | u5-only | N2/missing-dt-needed | `/system/android/lib64/westlake_flutter/libandroid.so → liboh_android_runtime.so` | `3d83561b7f3a340f4d9da554d2d0d99c2af7ec776f8f5d0c17dda1376b5f55c8` |
| 35 | U5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_flutter/libandroid.so → libsurface.z.so` | `5c0ab47c5698bde0770e323a8d15be28e474f274140643baa8cd2f75b5f84e2f` |
| 36 | U5 | u5-only | N2/missing-dt-needed | `/system/android/lib64/westlake_flutter/libandroid.so → libc.so` | `f7a4b422be62d400ec09f8cf9e1db133ba0a67c1b0608838da1dcb41a64138f7` |
| 37 | U5 | u5-only | N2/missing-dt-needed | `/system/android/lib64/westlake_flutter/libjnigraphics.so → libc.so` | `387660a25bc25cf28b3a5e195f106b974b4e2306276fd15dae27a137336cc670` |
| 38 | U5 | u5-only | N2/missing-dt-needed | `/system/android/lib64/westlake_flutter/libwestlake_native_abi.so → libc.so` | `c19c1cb3e0235cb109692a9ee0161dac8afa114ac3fc030069dc718499feff24` |
| 39 | U5 | shared | N2/unknown-effective-path | `domain->app_paths` | `f9cb0289bce13e2bd3d042027c62a57fc22b3c76f3320f4615740e9cb530ee52` |
| 40 | U5 | shared | N2/unknown-effective-path | `domain->app_permitted_paths` | `cdc0dfd217df84883741273aa4b37625305a314886557adf0aa41c0d51ec1c33` |
| 41 | U5 | shared | N2/unknown-effective-path | `domain->selected_load_dir` | `9f20fec64bb0f2ee6a43abf01a30a53c5a231ce044894d573e138c931ce54524` |
| 42 | U5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libGLESv2.so → libGLESv3.so` | `534b0d6f308f0ef1141634634120b583fbe6b51dbe6c59704480901a6455315a` |
| 43 | U5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libGLESv2.so → libc.so` | `7118b11faa38fb85747494e3716a1bdc6e4284f4ee5d53fca0c8030746b24ea6` |
| 44 | U5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libandroid.so → liboh_android_runtime.so` | `97a4db41c8e6fb932e755db7fd0175c4637c2206a5b49183696b8fc05a34e887` |
| 45 | U5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libandroid.so → libsurface.z.so` | `53e664e9ced6c84449cbfdca92a99e9e72aa9ccb707e0c3619d512793a904f0d` |
| 46 | U5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libandroid.so → libc.so` | `183a8f9d60527a2a7e17945c56eac7d83b6cfcc36fc4a9fba25740b5f454275b` |
| 47 | U5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libjnigraphics.so → libc.so` | `ea2f7e8c4e0d7ad44c6a8f8e4a8419f7ba36b45893f9eefb4758074419376bc6` |
| 48 | U5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libstdc++.so → libc.so` | `177946fdf38ca67747cecf1845b9d8a14b4ceccfb3327814c23a88af246240b2` |
| 49 | U5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libwestlake_native_abi.so → libc.so` | `55e1b24667c331ebc94f40807fb1b891c737f5dbb642398c5c00ae9f08a653a3` |
| 50 | U5 | shared | N2/uncovered-library-directory | `/data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a` | `43ba1d71a08000ff1024a87bac78d4c42c788d81c46b1942bf9779301ff3d721` |
| 51 | U5 | shared | N2/uncovered-library-directory | `/system/android/lib64` | `46c97145051c29a4952a7a8582b54f8ce75845bd1ab00785be0d637777c8e365` |
| 52 | U5 | shared | N2/uncovered-library-directory | `/system/lib64` | `f24799d789e5f1a4e1efe2403ac36f5fe2e82b602d5078db256b55e69c04e35d` |
| 53 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/appdetailability` | `cfe7b46d8e116e3b10d7fc398ab1c9240b1b3cde2eb54521233a91b56522fb80` |
| 54 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/appspawn` | `feee067becbd3bb4d037f7afc201c9ca16509496808bf3f71d4fa11f9993b6a5` |
| 55 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/appspawn/appspawn` | `6d1a007c0f2e5027f42ad893df216397a286057d9451e007b842bcfcec920cdb` |
| 56 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/appspawn/common` | `e5eaf4783d7b77fd8db4f52e4798c28340e90df7cac25628f9d1c50d4ed0382c` |
| 57 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/appspawn/nativespawn` | `37e2ebae65d6820469f3a6b21821f360151aa802266bb7e267c631fd3d6d4d72` |
| 58 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/appspawn/nwebspawn` | `f041883bfba82635e3a3df60d43e1a557ab8dbea021832c6da7cc56eddf4f3f2` |
| 59 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/chipset-pub-sdk` | `47b760d42300c6458ba4c1501735865a8856e2554b2988581172c3e08eea3dfe` |
| 60 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/chipset-sdk` | `19816d7ccd1d53c8fc6161a5eadcedf510907f1f18eb5db9a8e6846268312a85` |
| 61 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/chipset-sdk-sp` | `072477ab85718691e8f54dc4fc69f07978ad80efbf36e46eb991742ba6bcada4` |
| 62 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/edm_plugin` | `a490b5800ba5b4034ca10a84cccf28270ec1e52867c3e88368d499b6440834c5` |
| 63 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/extensionability` | `2fc6be06a0f27933a42368f86a2bdc7b13d7de2d1d74fb6e4c6c8327b2b61bad` |
| 64 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/graphics3d` | `c85c07969cfe4e8b01d181ff24c1daba3d2d51cb3cd6da595c52c886ecbe4189` |
| 65 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/init` | `159498770edf0e0a54d66ee3ed3a2fc8e954f4dedc8e7230042ed9804b1026dc` |
| 66 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/init/autorun` | `ecd3a81df33e2953af8c58f466142e9020618cefac27b1eb0da700fcbbde5f6e` |
| 67 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/init/reboot` | `9a1e715df85a2aa4101b9ad9b1f0a1daf84bf7b0229eb6faf864ecbe287be2d2` |
| 68 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/media` | `e0e2b4d0ad2f56abc67173fc2ad45208cad5a343afd17cb3b5295fe09758036c` |
| 69 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/media/histreamer_plugins` | `eb823ec1503329ffcc8224d1be46e553616f5bf3a46ae1aea7bbb7f6b9e110d5` |
| 70 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/media/media_plugins` | `c800f8710a86d037a946d7cdaea5443b7c25e03ec98eaf6df86afc7614edd6e4` |
| 71 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module` | `07b4f9483e1106553cc10ff66803898b7ef00ca63839fb46b1d2bbad7e4ab831` |
| 72 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/ability` | `46c24c4cac287605cd0cc9a4287eeb98545aaf304ba8de7b74a43be816be8c50` |
| 73 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/accessibility` | `e5319cb5ceb92a8c34ad1ae95a835e03da460a8ae12a3e50582f1d6d9375eefe` |
| 74 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/account` | `b1abcd0f94d4fecfc535aa0587e8a0fb8f3d85a788adbcd3e881b1d5df92324b` |
| 75 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/advertising` | `74f20e131d80999e3fb85b51eb8696a6834cf781eb185f7357c1212f952dd249` |
| 76 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/ai` | `ada1b4431c87e9d470666976f7bc85a84bef4e2055603bebdd11cb82afb6505a` |
| 77 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/animation` | `9e56724175ccc6422da3862dc84526621177a72ad0405699fcba549048116d5b` |
| 78 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/app` | `363c28152e177970d1121c6a198bb18b1164b606a73be07ac6a708fb8c25d9a7` |
| 79 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/app/ability` | `af8590c08c0249cc99e84de0a657364c3231be7b8ed235607e728d52e63cb7ef` |
| 80 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/app/appstartup` | `6a8bc649d567ad7b21eb425810fabd7623beaa28100f7e50bf46ae4e5c5f4866` |
| 81 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/app/form` | `5d32043f31d850d1241e91b35084072f65a2da8af210c4ffe89fdfec6f375718` |
| 82 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/application` | `e42b55a28846f88c004c9d2109bae62794aa8c7134d9bbf36401883645a0f9bd` |
| 83 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/arkts` | `22154c1e37b71b3222a755a3347d559a85fe5c4d9004f9cdf3265c3bd8d4dff9` |
| 84 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/arkts/math` | `5dee27188d3bddea9ddd65aeb2232cda8cf888da398dab2867810e736bf7139c` |
| 85 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/arkui` | `5ad4e743cda004ed17af95aaef64c0d805dec07a69a761023458d4676b963b9d` |
| 86 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/arkui/advanced` | `ef7104e86c7f96a10e99bcd4a4bb4d2d6ec2cef7948ef1169e29073a223037ca` |
| 87 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/arkui/intelligence` | `38e102827d5c080ac517ea109dd010a82abf9bb1f4bf08f6ab205de868256aa9` |
| 88 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/atomicservice` | `381e039f7497b024437f034eecdac5339d3e28eb683de2d4da685e2c8877d454` |
| 89 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/bluetooth` | `f76f413a00a5b7325b406836f4a7e7e9c9dd7537ee5a74cf9c29ca9a7921df71` |
| 90 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/bundle` | `c978526c450effb344d8a93e6b4d1f046d554ff7cdc51624436c496a62b4c4a5` |
| 91 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/continuation` | `650995bb0639fb6c32be63a7c0531441ab1778a49fb0247874e0e6f0eb91ce50` |
| 92 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/customization` | `727d73d942a362f060765acfba9a50a1fdbe1fd3063f9e22b312509069c74283` |
| 93 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/data` | `feb9c7732e86c489bf17bef6cb67f1083352ed793b7bb2169b76776cdae61b50` |
| 94 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/devicestatus` | `3e4c00d55cd3cdf16b55f044edf58367a648019d62581c85f5e6acf350e25b45` |
| 95 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/distributedhardware` | `09c908223a90788b7629ed245743cf01b9299fa1ef8ca2e80b5be2858b209248` |
| 96 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/distributedsched` | `3df0c06099e1e947f8c7dc1d66dd0e7a155cb2c4a6bbd02e1063b6ee6b263568` |
| 97 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/driver` | `44cd3f322c23c6f1988d1e6a5b12cbd413bb09fad2e0354916ee179e3bc10f56` |
| 98 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/enterprise` | `5df405f1d020234735ac1981beeb2f3a28db5b6be9c13016f818b2f06c1b543a` |
| 99 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/events` | `9fa35af66e864e961bcb38194e21ed2f425a7bcc98ec160b9b8aaad3584002bc` |
| 100 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/file` | `fe637498da9cd65c052f266e5c4a0cc7be9b14d241710c2df6f1ccd38052e297` |
| 101 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/filemanagement` | `281f96fa44737b5ae7af2cb04a8374ec42fb93c5251c6fb86fc438b1da14f9d4` |
| 102 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/fusionconnectivity` | `82a0a0ee5b728a43ca6b73891e466cadd51629c7318a7d378d7876c73428513f` |
| 103 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/graphics` | `67d03e9d6846b47987c7c7dbc73a80e7325465217cd50b5677256f320d211af0` |
| 104 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/hiviewdfx` | `51e3875bee29b5e0cbfe0a8589688294d8018ed69f0ffa646523fdf930f2112f` |
| 105 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/identifier` | `d071518dc4dd6e159639a648f2acecf8ef0a53f158dd784fea6c7084ba529d2a` |
| 106 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/inputmethod` | `c2a4590d43f57f282c12dd153cf64ffadadab7b3cdcdc2842b5099854aa394e3` |
| 107 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/multimedia` | `35d23823e26cd99ef00c864f80b3b96d3cf2db41ec007c1dee06b0bd3a96800f` |
| 108 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/multimodalawareness` | `453fc99c079b1f51a77b5603125ba88d63b85eeaf573e6177d5551f1f55c5d08` |
| 109 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/multimodalinput` | `907eb293761a4d15d081654ed908d5a71b7af3795c09d716cf0b34732791ba1a` |
| 110 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/net` | `3d477726fb519d519620377aa6be50f5f234b5ac4ab6cae56a415338f881ee9c` |
| 111 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/request` | `0ec325772044897bc7f7c071fa76d9519025a335d7658b5d9c04341d7beb7c03` |
| 112 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/resourceschedule` | `48497b2642c91f5d24b7835ced37cd89f70b45e9962eaf46dfb6e7427362f603` |
| 113 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/security` | `bcc0cf0d6512ceb5adfe1d32fe25bf5d27f47cc084a32f6736b024a31b93bb7e` |
| 114 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/selectioninput` | `531c92f4454b1e6720290be1890a0ba7c1c40476bd0f924beb9d9123951c6d48` |
| 115 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/telephony` | `7db39fd89caca27a2953f9e1c262e2a196d90e3563a01c1f7b53d7db66376466` |
| 116 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/test` | `c61948019081aa17f42fb50374a0bd8ad139d44c194ac8e137e8d19ee8799267` |
| 117 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/usbmanager` | `f34db28dbc0de678396a61ab4e503640e72d1f654ac0b5f5facb3a3bf46c5fe4` |
| 118 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/useriam` | `6ea765b0ad634bd71561147044173bd75df691bf4c86189f5aea251055d98cab` |
| 119 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/util` | `c6d4b7f0ea75142ac3923692dbbc5b113184c8fda5a55d01b9a426a1f6f8a177` |
| 120 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/web` | `a793909fd373af4b35060ab0517edcb163cc9710713dbc1f8c0a90eb9bf4af1b` |
| 121 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/module/window` | `1e13647566043b56ab34175ce0876bf2f764e5a67bb6f9e4ad1e64a183a19df1` |
| 122 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/ndk` | `e47ca92236fe4a935ec1c60829bbc4274cf3db81409c3860edec3fe51df38721` |
| 123 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/platformsdk` | `94570b1aa869da01b71353503d743538142ea093648331d23b325d3373a11295` |
| 124 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/seccomp` | `47eeecb5fca012769f43e41d2a25d518dde013e69d63a89e36a2acecc4f1562a` |
| 125 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/westlake/route-a/74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac` | `e5d3b1d62b78ec0544555e8aa10400fea00a08867b0a4679db1ef568063fcbf6` |
| 126 | U5 | shared | N2/uncovered-library-directory | `/system/lib64/westlake/route-a/74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d` | `678d36090a080f52bafa41853c1479cfb43714e3eb1e6913dcd3b62cacce3dfa` |
| 127 | U5 | shared | N2/uncovered-library-directory | `/vendor/lib64` | `f738f87f2ce2109cda709c2a6b422cebd99f266483f505cab8828e5c87056965` |
| 128 | U5 | shared | N2/uncovered-library-directory | `/vendor/lib64/chipsetsdk` | `6c2f02ed8e83b23b154a1191e78a8b69e79013c10617e88e70115f1ed98f8b9f` |
| 129 | U5 | shared | N2/uncovered-library-directory | `/vendor/lib64/hw` | `736ea1a793978987b69c15707e68757ec5df1840d9f5fcc5106823022ba08725` |
| 130 | U5 | shared | N2/uncovered-library-directory | `/vendor/lib64/passthrough` | `1bdd08a54ee2b82d0e8cdf9914944b782f6f61ecb28a5761510259e45e698966` |
| 131 | U5 | shared | N2/uncovered-library-directory | `/vendor/lib64/passthrough/indirect` | `d2f5a814147a187f6a179090e3b7139d8c11e30eac6cc417ee2351166fda1ddc` |
| 132 | N5 | shared | N1/unknown | `host / {'function': 'main', 'namespace': 'default', 'library': None, 'target_expression': 'plugin_path', 'evidence': {'source': 'n4-host.c', 'line': 629, 'text': 'plugin_handle = dlopen(plugin_path, RTLD_NOW / RTLD_NOLOAD);'}, ` | `d676eb75c39c8d1eb05b4ed47ebe68eee63dac5435446e558e8524f9e3958648` |
| 133 | N5 | shared | N1/unknown | `runtime / {'class_name': 'com/google/android/gles_jni/EGLConfigImpl', 'operation': 'GetMethodID', 'sequence': 73, 'evidence': {'source': 'egl.cpp', 'line': 103, 'text': 'jmethodID configCtor = env->GetMethodID(configClass, "<init>` | `b0ffb1429d6ff93050a2fc2e3a22c330f32781cda31a3d873ce64c94dfb656c5` |
| 134 | N5 | shared | N1/unknown | `runtime / {'class_name': 'com/google/android/gles_jni/EGLConfigImpl', 'operation': 'GetFieldID', 'sequence': 74, 'evidence': {'source': 'egl.cpp', 'line': 105, 'text': 'jfieldID configField = env->GetFieldID(configClass, "mEGLConf` | `d04b438b97b99a8ff8024561a01c63b90c0531a2fef514fe9f902ab1e1a9ea96` |
| 135 | N5 | shared | N1/unknown | `runtime / {'class_name': 'com/google/android/gles_jni/EGLDisplayImpl', 'operation': 'GetFieldID', 'sequence': 76, 'evidence': {'source': 'egl.cpp', 'line': 109, 'text': 'jfieldID displayField = env->GetFieldID(displayClass, "mEGLD` | `826f2201943569908506af069c4324ca2ee9a36f0983c4782575ec60fa580b87` |
| 136 | N5 | shared | N1/unknown | `runtime / {'class_name': 'com/google/android/gles_jni/EGLContextImpl', 'operation': 'GetFieldID', 'sequence': 78, 'evidence': {'source': 'egl.cpp', 'line': 113, 'text': 'jfieldID contextField = env->GetFieldID(contextClass, "mEGLC` | `a5f66fcc2f87ca2e635e4bc1e31c1067caa7b95ae273f8b45c163671eaa7d021` |
| 137 | N5 | shared | N1/unknown | `runtime / {'class_name': 'com/google/android/gles_jni/EGLSurfaceImpl', 'operation': 'GetFieldID', 'sequence': 80, 'evidence': {'source': 'egl.cpp', 'line': 117, 'text': 'jfieldID surfaceField = env->GetFieldID(surfaceClass, "mEGLS` | `89d8106ef31c139f773b4da055fb5d3bb8dbcfed331421966ab62d4be421f604` |
| 138 | N5 | shared | N1/unresolved_calls | `runtime / ExceptionCheck` | `35818da065e45a6e0ea9aebc769caa291bb28df53f06890c70fcda8c70390bfd` |
| 139 | N5 | shared | N1/unresolved_calls | `runtime / ExceptionClear` | `f93c1181d919be609b82ff6e4d78ee3276341841e68a12ef152739bc667c46a9` |
| 140 | N5 | shared | N1/unresolved_calls | `runtime / ExceptionDescribe` | `131d4debc3410602c071e1899ad63eec68bf4501fde8967b2bc09b78f52d09bb` |
| 141 | N5 | shared | N1/unresolved_calls | `runtime / GetJavaVM` | `0a60effc4924d7db34ff90016fecd95d51a86f49f1ce3caf2fc92778c9043d52` |
| 142 | N5 | shared | N1/unresolved_calls | `runtime / HiLogPrint` | `a291c2c7bd930a9e1628892521a92c0415bb8826cc97836ea06c3a30143d3a1d` |
| 143 | N5 | shared | N1/unresolved_calls | `runtime / NELEM` | `c006faf7904a18602b74bac6ddca46d15f1e8006ad056b539f5319696aa42270` |
| 144 | N5 | shared | N1/unresolved_calls | `runtime / NewGlobalRef` | `a141de37655fcae7e1027d84f5798144ef9ce9415038796ec2898b5c57d49270` |
| 145 | N5 | shared | N1/unresolved_calls | `runtime / PopLocalFrame` | `f84252e4887a3696884b1654cefbf4a3a24c72e54fb9284291c501ae555a6276` |
| 146 | N5 | shared | N1/unresolved_calls | `runtime / PushLocalFrame` | `d107293e08044f0b99245bc2f3c80454d2331fde88f6190e390fd4601127292a` |
| 147 | N5 | shared | N1/unresolved_calls | `runtime / dlerror` | `fa605bc4371c269a0f9ac6de9aecce212f59b6c57be3a393b5239b56b4572b88` |
| 148 | N5 | shared | N1/unresolved_calls | `runtime / dlopen` | `b9b76ef27ee0caa1a1b964ce3f56d2ba62373ce6c0e8f23e7da4ce9194ff0f9e` |
| 149 | N5 | shared | N1/unresolved_calls | `runtime / dlsym` | `5e8d95a184a35a4dad6ab6640fcf99c2ec55c1823917fc2a417b6bf03bfc8fc9` |
| 150 | N5 | shared | N1/unresolved_calls | `runtime / fn` | `3f37efebbd40e92e2b209101d33b7a89f276930b695993fbb38ef2b166239ee3` |
| 151 | N5 | shared | N1/unresolved_calls | `runtime / fprintf` | `65c34e5c5997c3365b156824d9d3f191ae1727d2839f03d16cb1ca62e591b4e3` |
| 152 | N5 | shared | N1/unresolved_calls | `runtime / int` | `578d24d606ee12684caa6a4ff832d37da12e26344481ccbecec17ea0292cb467` |
| 153 | N5 | shared | N1/unresolved_calls | `runtime / jint` | `127dd31d8743fa3255457bded568b25c04f893a6692672b934750c217e5df159` |
| 154 | N5 | shared | N1/unresolved_calls | `runtime / jniThrowException` | `d3f2d2d9c4c717b6d92e4b367a6f76474a2babbe48c7a8dd93a8891cc9911c1f` |
| 155 | N5 | shared | N1/unresolved_calls | `runtime / memcpy` | `a735400507d2cf87f29b6b84ac072b9cf2dfcdfd31c4a7f9fb1329351be8ee0f` |
| 156 | N5 | shared | N1/unresolved_calls | `runtime / onload` | `ed61f630de879cc7f5c2d1a5c769fab4eb9d0aa50c9a326efd77cb8b30bc101a` |
| 157 | N5 | shared | N1/unresolved_calls | `runtime / proc` | `6a9becf2591764e58e4efac86bb1821c1c0bc9ee0292db34c21fabddaf1d2c24` |
| 158 | N5 | shared | N1/unresolved_calls | `runtime / register_android_graphics_compat_shim` | `e61fb51db521779f1441459bfebc5dff9df8bd627939f3d3a99aa00e84918952` |
| 159 | N5 | shared | N1/unresolved_calls | `runtime / register_n2_Camera` | `cc44fae673b17fd718a13514a169d7ed9cf7e62f8008b018b8254b7e8614c3b3` |
| 160 | N5 | shared | N2/unknown-effective-path | `domain->app_paths` | `d39395508517c2daa1740e4d5ef0c8fa4a871dee82d4030ceea1949dfe1ab668` |
| 161 | N5 | shared | N2/unknown-effective-path | `domain->app_permitted_paths` | `1bbb56bb3d4ca26230f348394517d7c03bcf845eeb07ee4f40167523f417dc70` |
| 162 | N5 | shared | N2/unknown-effective-path | `domain->selected_load_dir` | `70a30b05a53188c1b4dd1c4b929db0e717b92f62e372b33a82c4fc619d0ff04c` |
| 163 | N5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_flutter/libGLESv2.so → libGLESv3.so` | `3386669a30ea8b9026cf10fa8c5e8d25e413c0bd85c85bdcc6fbecd27b81ba1d` |
| 164 | N5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_flutter/libandroid.so → libsurface.z.so` | `30d58809f5429dd310c6b73342c49613c5b68621b37820ba3321eff22268d757` |
| 165 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_android_runtime.so → libEGL.so` | `bf00f9d608908571187bc13057a6d75132b669eac8f443a5c6cc49f43f9914e1` |
| 166 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_android_runtime.so → libGLESv3.so` | `9a0f203db6dcbe197d2015b8bb30b9810268dca4021b05b8d5ce9ea582aa694d` |
| 167 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_android_runtime.so → libhitrace_ndk.z.so` | `aaa5633957ebd9372ceab80ad90f2a8052f9c8ae50c0303191732ec679247a2e` |
| 168 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_android_runtime.so → libbegetutil.z.so` | `529f0999977b2af200c3c9f4d8655a30a9aed8fe1cc0bc3641c2b8b60f4a2648` |
| 169 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_android_runtime.so → libsurface.z.so` | `12b17a7bd355896c182b4d1007c570d428ed60ff3869499a3d8a8f238a97601c` |
| 170 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_android_runtime.so → libhilog.so` | `5770d01c6a710e6e019aae98153f76792c37f6c17c2dc2eb0a38fb410bee320d` |
| 171 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_android_runtime.so → libc++.so` | `f783dc4a8dea7073e52505d816bf9bf9bb3b472c8545b5d0ba63a0f54b68e6b9` |
| 172 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libandroidfw.so → libc++.so` | `984278d732b9adea45e1ecc275034e80244b1c4452aa192907e1238d57d03239` |
| 173 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libbase.so → libc++.so` | `617a7af5f6f60bf4232aa8ebff5996d3a93ff3d0aebad39cc9dd9b053b659fa6` |
| 174 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libutils.so → libc++.so` | `87cda5bf332d4706c96be1149efcdbad2123b1b06404904a02165b27dd661e3b` |
| 175 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libcutils.so → libc++.so` | `8aa114b1a32537daf323850da1592fa3df732c296ab4ea9d82f1fcd7fc9b3dda` |
| 176 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libziparchive.so → libc++.so` | `b507543741bcaef658b5629ecacc5e7987a1658503d5777dfa11bbc62c6cbc56` |
| 177 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libicuuc.so → libc++.so` | `04ce95842930e601f1c082b48f21d34c1e1fa8623949fbcd5452bb6aac8d5513` |
| 178 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liblog.so → libc++.so` | `88076dd85cd3617c6082b0dc51c6759175282e6272e5ce0444f199a094f03043` |
| 179 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liblog.so → libhilog.so` | `168f99d4938c07c47a5dd77f2b47042ec5e813f5ed0044b4e66d51508aa78008` |
| 180 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libbionic_compat.so → libbegetutil.z.so` | `ff4343ad367b59bb90692bc941c6c2056965781703a93488e9c3db2be329f89f` |
| 181 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libbionic_compat.so → libc++.so` | `56e60eae270edbc01b39c391751ba5c5ba2e5357f53227a440a4ae9994bc070d` |
| 182 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libc++.so` | `e0a1d4d15c8ef43d733c85a3c80281494cda72094fcf2dc47ab82f8d5d3fccbe` |
| 183 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libhilog.so` | `19f1f79803588043bf1b3c2b5033602b7134173585fff8eefd34917cb40fed28` |
| 184 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libutils.z.so` | `0a5af73a6b301e251250b9b836ea920d3cc75549cf7aca1268589948594e2c89` |
| 185 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libipc_single.z.so` | `135a079c9e22d2656c4f68ad41f45577b59e9fae1afeb44438d1069507f143b7` |
| 186 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libsamgr_proxy.z.so` | `54184a5f9948d700be482ae1dcd1f21a9e136681dd4974936ae0976f34cc33b3` |
| 187 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libability_manager.z.so` | `05492a9c43a47df591e84e4668c274c89baf2c94bc3a650ce3b32a24ab787f1c` |
| 188 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libapp_manager.z.so` | `e5bbf02cb1ead6b016a9d8e25cebb42a7419010f60031e96d1c408e6084b615f` |
| 189 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libability_connect_callback_stub.z.so` | `9ed72862f539ce9cf809a4e7a3ececa961aacaa976285cc498220a36dc849c4c` |
| 190 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libwm.z.so` | `16d6cd76bc562a15aac8d556853d48bd4c56084f7efbc1920e85eeae1fd2c36e` |
| 191 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libdm.z.so` | `37b05e6e53bfb3b0727b46c29b56639c5905532e808e099bb4c8ec134900428c` |
| 192 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → librender_service_client.z.so` | `c631bd97caf36aabb6e929b604790962fb7e96606332bac32c73067a1f0a4812` |
| 193 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libskia_canvaskit.z.so` | `9f0a110464681222f72403da4140c607f0ea554fb7e0161c77b6b4b96f91b764` |
| 194 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libmmi-client.z.so` | `27b85168967e4adc0dd49aafea5b4235d7fefed83e743cf787fc54e8be5773ad` |
| 195 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libsurface.z.so` | `8fc6870f48ee9f57fc78814b4e850be980fd0aedc6c1a7cd574b4f2a867e5161` |
| 196 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libcesfwk_innerkits.z.so` | `e06ba08081bb14cda66429c82701c31691a16d8bc1b1c220a2329db82034c73f` |
| 197 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libdatashare_consumer.z.so` | `42eaf1ced1ca0640fce66ecd42efcf7f5362f5fe074f9b2fbe0a692111cd8136` |
| 198 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libappexecfwk_core.z.so` | `58101c8989e6d3ea0e329a2bf40d925fcee5c5d340d5cde7b7abe095bcde0440` |
| 199 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libappkit_native.z.so` | `f550441bfce47b26c6511f31ec7cdc0d1c8fe7a6079c99bb5888f896dbf4fe34` |
| 200 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libEGL.so` | `ab5cc5714ad089d23d70f60fc1ffe15bf10f135ea295d707e848a71997ff4229` |
| 201 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libwant.z.so` | `6426f194d04f9b70eecdbc9477924be378c1a52cc90fbd6b47a5c5931218487b` |
| 202 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libzuri.z.so` | `2ae742b3ef5cc2c437dea9ddf2c6026b0326381324f0939b1d05c7857a4cb89c` |
| 203 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libconfiguration.z.so` | `d3850339483da45d3ca710e27a6dd220499f04d73ad261ce493c4226c1926fac` |
| 204 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libmission_info.z.so` | `111517a298a08831f1c4d40f6e22d278766cb3891387c7b61196a0db89d7852f` |
| 205 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → librender_service_base.z.so` | `76225c383f2fee77963f21178e443b5a9205cfaf5521191cb1d337ac98cc4bed` |
| 206 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libscene_session.z.so` | `d19b9fd2c58b9076a60be3c691f91825e91aa26b372941c930ecda5dbc26fe7c` |
| 207 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libwindow_scene_common.z.so` | `d4d477299e1fe25a216a7196c27ac4d2f652a13a8904c9f6d8d0cf7fe48d8e86` |
| 208 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libsession_manager.z.so` | `eb84b3a948fda464f9b82a5bb93e51e1bbc1ce913fc84759bd32f5a207f40bbb` |
| 209 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libwmutil.z.so` | `5c11545bad5b0fa81a3bee035aa18c3f38147a879d1e6b893ed3715aa25173aa` |
| 210 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libeventhandler.z.so` | `329ac6f467424d0d572aebf87ecb9a3a65c135a43cb6dea4bb56a5da2b85cb85` |
| 211 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libhitrace_ndk.z.so` | `50562b83794acd3f6d10d712db119713bd1d0afd292d2c031b318e1896632d79` |
| 212 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/liboh_adapter_bridge.so → libsync_fence.z.so` | `2f1ef88ef995fd9d22160712b54d140ec9e1514ae3b92eba033f11458d5ee760` |
| 213 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libnativehelper.so → libc++.so` | `ca8035e68984a71225f7b95a6e58639eef0405bcfd75bddfb95e766cb9b27362` |
| 214 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libnativeloader.so → libc++.so` | `c37cc9307d8fe11fa5ccf06de1d20e853a566bdd3b5f39f6a8db601aee15e18c` |
| 215 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libappexecfwk_base.z.so → libwant.z.so` | `2f2181bb066a633f5b3f12d99bc306ced3b1c9f626e184b6ef30b9e953bc8b2f` |
| 216 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libappexecfwk_base.z.so → libutils.z.so` | `6bcd6a32191387a96991bc036e440cbe3cde2f9bb19286c4d434f4e87b9d233e` |
| 217 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libappexecfwk_base.z.so → libhilog.so` | `67589999fbdedf0f6aa339e32d3df8e5b8f65cc002399f70c9c1544bb29a3930` |
| 218 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libappexecfwk_base.z.so → libipc_single.z.so` | `3d2ab92eec4c9ab6f29f933ef8923ebd89fe243953b605c3497d6880e578a471` |
| 219 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libappexecfwk_base.z.so → libutd_client.z.so` | `56ee5ce56f8ef4bba1acf92fea5c635800291af66d44db1640b163566223ca8d` |
| 220 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libappexecfwk_base.z.so → libc++.so` | `8c43fac97582e40ebdcaff3cc989273fec84cc991420b4bff1bcc97197a8d170` |
| 221 | N5 | n5-only | N2/missing-dt-needed | `/system/android/lib64/libappexecfwk_base.z.so → libclang_rt.ubsan_minimal.so` | `fbac769c7c37b848390d874048cfe75266cd40926c4f7cadd4ed55f399081dd7` |
| 222 | N5 | shared | N2/unknown-effective-path | `domain->app_paths` | `e76bd833ce713f1f953e9295ca4d45effef7986d73bb89be7a4657242fbb7768` |
| 223 | N5 | shared | N2/unknown-effective-path | `domain->app_permitted_paths` | `fd5d8a1d24ab3d486d08c798285100bddee8d6c34ced98744d07da0d4b302111` |
| 224 | N5 | shared | N2/unknown-effective-path | `domain->selected_load_dir` | `f1de48e36e6455a597dbeb0a1253948afd37906cb8111358e577ac54a41e5e3f` |
| 225 | N5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libGLESv2.so → libGLESv3.so` | `847754fa95ce0d9acc8740d9f22efb6f390eaf41fc0e893384f8477ca04792f6` |
| 226 | N5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libGLESv2.so → libc.so` | `185b0e4d8f5c8d3b1104d55298b237352e8a888a25fa400bd855a4c2a8fbbd14` |
| 227 | N5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libandroid.so → liboh_android_runtime.so` | `1f6172ed4dc76769a379d59d6c149e856af829bfb079379f2220e463a42975c6` |
| 228 | N5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libandroid.so → libsurface.z.so` | `8ea20f506e60b860a8cc1cdb1a112312658fa159ab05d2332414c6bb104b7c78` |
| 229 | N5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libandroid.so → libc.so` | `a83fe6ebd006920ae2825f060ee5fc13378e35fcb4950b625e2110d2041d1464` |
| 230 | N5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libjnigraphics.so → libc.so` | `9c120b6e4ea2afb7220ad5aaacf339837f9f2610095375dd4298606c959f1bf4` |
| 231 | N5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libstdc++.so → libc.so` | `430d6acbfd56328218dca6826b9636a20168b5011a76c2088686c93e7debd5fa` |
| 232 | N5 | shared | N2/missing-dt-needed | `/system/android/lib64/westlake_native/libwestlake_native_abi.so → libc.so` | `733614c08cfd4a8d573435282bbbc668dc539ae18785079e1a3721383fa33af3` |
| 233 | N5 | shared | N2/uncovered-library-directory | `/data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a` | `7e69ba9e84f44372de3dac0a1bf91ecbbbda4738e28b704f1e7748bda2efee34` |
| 234 | N5 | shared | N2/uncovered-library-directory | `/system/android/lib64` | `a80aaa429289e0cb290c58407fc9c5fe088495969b7d8b1ef31df334e8f53115` |
| 235 | N5 | shared | N2/uncovered-library-directory | `/system/lib64` | `78b19e4bcfdf1572fce328e78e9639a7504320178a48ef0a330d316b48845834` |
| 236 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/appdetailability` | `a7982c675fcf2d1e54818c7d7836a51288d882f557938d4b8f01506dc86d1ca7` |
| 237 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/appspawn` | `4b8f21f91717141e746bd815144a7e250e100fe92b449c062d3d00502b214e68` |
| 238 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/appspawn/appspawn` | `b373a88613de4cd7131cb8582b911f54619d1de946e06a53350c7dbd5d2cbe28` |
| 239 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/appspawn/common` | `cbb936e4040367305adfdfe452ece8e9e4750bcc8e4ee29910e161135040d08a` |
| 240 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/appspawn/nativespawn` | `fd274051808ab1b8a94ab88891551b3c85574f4ba7fa08008162e1d8c135e2ef` |
| 241 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/appspawn/nwebspawn` | `e1cb22021e6835b161767b53226fe39d5f72ee76795a0389fa9020a7eb791862` |
| 242 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/chipset-pub-sdk` | `1081b667d2fe3b9df27b5ac5e703e43f41a1990a38a5e5230703e718e52f3eb6` |
| 243 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/chipset-sdk` | `bdf066ec8db41ed24ee00f5c0fe04f3c1c6d5a828a75ee5e148402e6808516cc` |
| 244 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/chipset-sdk-sp` | `ae5f691d10a72cb32b71551ad501ef686d385f9ede0dbdb4fc73ca6fba7349c7` |
| 245 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/edm_plugin` | `2e2617a96c0b553be78ccdb13c53154bbe459e69601c25f72ce2357c0eb4c341` |
| 246 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/extensionability` | `ca82b479ed833b68a3ce4391698abeb6e3c13364d2408cc66926080ce5de7d65` |
| 247 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/graphics3d` | `cfc09c3b0aaeda6cd5820a80d8de12cd4db67979f5e94ebf0ec145ec2a0eb307` |
| 248 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/init` | `010690d2914f48861727ebc0a99110dea9bf61b1a027e8bc4b6248f2a6d8b7b3` |
| 249 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/init/autorun` | `5057e1721a8d805502276321e4fe3cf86b70e876c44befb99ba166e89dfbf478` |
| 250 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/init/reboot` | `5befb4e2f5d962f2b6d9bdc124264c7f7a297a427b2b0d4edc8c6875c154d08f` |
| 251 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/media` | `8e29b36507e2015d0b41f746db81765b55a6da9567068079ff449ef2c562515c` |
| 252 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/media/histreamer_plugins` | `43415525f3315cf0d72793885e5fc6dde228241ecf34951ad9251cb03452da7b` |
| 253 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/media/media_plugins` | `d8ea6ab25255d8d7ff45f78f2b8d6cc2a02d5b66c2243ce3ae9c8162afeb7705` |
| 254 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module` | `770a805a33d2610d76c8fd0c31cde3848a6075c97fe9c8a00f311507dd2e7df3` |
| 255 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/ability` | `75648e734c5ac237a8211e7c8684a1e21e49acbe7e7a518835b408f1b494cb3c` |
| 256 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/accessibility` | `5d2cbe76e7ae6e3601e6d5d59f728ae61b9d08c89556fee992e2ac10db4541c0` |
| 257 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/account` | `22b678f153a3581b4a9018134b1be74cb9f2839c0183154015b49bae988569e9` |
| 258 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/advertising` | `a8de2b422e6cb94f94dc04c2698a491d97df8c615e349b8e0e11b9afcfa89ddf` |
| 259 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/ai` | `a4bbc7efaf5ae007ab91406e15686817457157b83daa523b0fea409639e9e599` |
| 260 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/animation` | `1a9bb80729160732d7e1a50b4aabdeb403445661114fb98fbc622d49a8b73608` |
| 261 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/app` | `375581d012c761f6720a0f2b0d459909ab896785b0aafe7369d28b2a4b8d2af8` |
| 262 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/app/ability` | `a5a9135b51138e637970e9afdaed911d6508367d6c6174f2cb1480a50b674a16` |
| 263 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/app/appstartup` | `a8cf44ea372d72a477f88fb0b7a7d0fa11a822ef74f326a0e7e8dc15ab1e6636` |
| 264 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/app/form` | `2143b836bd008a461e6dad8b5ce81b6ca0fa7d6249da6ebe72749ec29b576b22` |
| 265 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/application` | `4ba6a4dc068260c111ccaffd1b2c9e9b848de62474458094d15d5ac118fbc3ac` |
| 266 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/arkts` | `22e3cf9b687da43f91b40045462f95cf8a9f16695568f646788e175ccc9be766` |
| 267 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/arkts/math` | `e590fe41a09f11dc4c133a0cea1cdb62350fe6c94b485890d9ecc882abb0c69f` |
| 268 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/arkui` | `fd1355e887b373c03eb2647547434d421bd548b89c807eec8af12a34382cc338` |
| 269 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/arkui/advanced` | `964d74411e7d6b25a11b1b8e88b49c2f442cb1306fa002c1b32bf75b0d743dd5` |
| 270 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/arkui/intelligence` | `298bc3168fbf620e14dbb03f9f4fd380f992127083417be19dbdfd1a8e5370d6` |
| 271 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/atomicservice` | `60c39d4ed60c42c1c9103979f30a6610c6f2eae05918b32c3f282a1c78f981b5` |
| 272 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/bluetooth` | `60be500bebd9cb7255f1ce0923728d567b67d88d4fae319e76dced4b010c3bb7` |
| 273 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/bundle` | `fdd3a2aded7aca23557214203ef7fd0274537b46202f5714f5944fc963caae65` |
| 274 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/continuation` | `7e389914ce385c2f746dbbb9e9a57e61b919abfc83301854ba1a27093df3d24e` |
| 275 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/customization` | `5d9b3b08451c6b06ebcc6a14170d058742afcdb999f8456aa67e5a35796ffe5f` |
| 276 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/data` | `7f83b161b95137c4a1202f1a19cbd29f9048c9a5296ef51716be4d187865e9df` |
| 277 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/devicestatus` | `378fc0d6ecdcb59e5af70ff878d2f7b7dd9f26f774d51e06a04755dfdcec4ca4` |
| 278 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/distributedhardware` | `cac5f96f37d2d3c4964cfe2e4d4dec3b343a09b87a33d96c63c20ca0cffbbe2d` |
| 279 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/distributedsched` | `f094ac95b3ee5da195bfd67701eb2d7a6183f6a4f3624f281c65e9a2e2bfdf8c` |
| 280 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/driver` | `e87461579e3a5466f0321b7c024a3a1d2d7c3b40bcc08d47c003ef9b097427e2` |
| 281 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/enterprise` | `ca9433fed6fa9ca35bb713076d6201d048d5a93dd515f13507979567d32d2180` |
| 282 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/events` | `759c60e75e2fec6ab5123e1d56a7bf7780600b5a0d141880928ff0c7348e418f` |
| 283 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/file` | `017ba67f659227f126348ee25ce226768008453d03443c97aec9ba06ffec1c4d` |
| 284 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/filemanagement` | `2aca6429a07135a0a656ed76e11186e8f811fe5786c335a266fa13304dc28d7d` |
| 285 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/fusionconnectivity` | `b83d7b50439da5cba78895324d577d2e9765cc508676a893e7635817e55d7740` |
| 286 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/graphics` | `b3f21b0623a1c5a1a5de9ed1a7d360c026c32f05e6d473784cdfb1b31dcf8413` |
| 287 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/hiviewdfx` | `4d9949e523fc19df209b42db296bf184103d00c7db74ad0028d481bf03e51406` |
| 288 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/identifier` | `f08835df05ba4bacaa991b9984373811b86414ad80850b120848431ac24c8fe4` |
| 289 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/inputmethod` | `b71a22b1c96048ff0f55634b5a4c51fd155c78c0047024af5f54bf69f5e4cf27` |
| 290 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/multimedia` | `dc2ab70b0c84c2875fd9c3bf2a617b9028c14127e3e74caff197eef32686f6e1` |
| 291 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/multimodalawareness` | `7c40f39a24ffe1ecd7a0b5d6bff1b4739c1f8217371452c687c056efed29844b` |
| 292 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/multimodalinput` | `3f0a03d5a459e11f69cbdaba9cc74adcab720229675321647562f61cf7c08886` |
| 293 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/net` | `3d602753ba4317cf61e0f826dc617e69dc2b4b7ba8f59ac4722153dc506b0a2c` |
| 294 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/request` | `6c3f1a622aba98c76686be91a9fe72e94a682d66a18d133a224467d3bd2a2c10` |
| 295 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/resourceschedule` | `8a8496007c85d8ec381793f64774d0e864370bd099d8302845bec089b172b829` |
| 296 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/security` | `b7cea22ffbfcf73bb16760f185356dc485f9f08c296dc129b2dcfaea7c8a31a3` |
| 297 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/selectioninput` | `d0915d2133acec93708ef7aa1f9f303000d658d0ab010427c72707f6467fb6e5` |
| 298 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/telephony` | `c15d7a7cd00fa1953ae2101eef4f084c1906d6dfcf678454102929116c699373` |
| 299 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/test` | `862420dd823b3fb5a5d0770ad04dabfba898d3ef01dcd1b1805bb569e0aafaf4` |
| 300 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/usbmanager` | `a34a45a514c93e62e844c0417fe12dbdf18317bb780a2238567c8a0777cbe120` |
| 301 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/useriam` | `9385c9a8c889221dc33edc8643c0e31a459fa5711e5c6b7a174a2f6293492b72` |
| 302 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/util` | `32ea0375603b854f96c6a5a9602296411667430d25ead2f92bedd0a480f710cf` |
| 303 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/web` | `152b869b4a3eafdce00344ab22952e0d5c252b3b726c8fb801417660834ef4b3` |
| 304 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/module/window` | `a9b49555df163dc33d68509f5faef4d7acfa0d7cbe25d335cf50ef2c4521ce8e` |
| 305 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/ndk` | `f5786f11f875ffe9bad5608139d85dc963b3fa9167e90b722b1fc260745fd5df` |
| 306 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/platformsdk` | `42e6478e4b2e4c77ddc0c1cfbc4d8dd174df0de54628d93f2d95ce36543bfc91` |
| 307 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/seccomp` | `8cf63ddeb1aca03cc9d1f798048cedfb6c023cbd188b04ebfba60e35565c1e0b` |
| 308 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/westlake/route-a/74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac` | `8c4c4a4b490102776519a6a7ee00e73ff6ce35640c5fb7ed7eac6b6e1cc52fd6` |
| 309 | N5 | shared | N2/uncovered-library-directory | `/system/lib64/westlake/route-a/74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d` | `6f71e8d91df3db85c5f1ef8e2298c2dfeb6ac476b163ba4128168bf835eafd6b` |
| 310 | N5 | shared | N2/uncovered-library-directory | `/vendor/lib64` | `027df2ee13441234ef8a9b5c8c548d08882c60d3d080004950e29760c60a7181` |
| 311 | N5 | shared | N2/uncovered-library-directory | `/vendor/lib64/chipsetsdk` | `f004d7d4e6234c19be3d3e60df121f56b27fbc2a58b84c2a6fa22550621a5827` |
| 312 | N5 | shared | N2/uncovered-library-directory | `/vendor/lib64/hw` | `883d947c6093e331b6e4b9bc5161964fe2b1cc0492f22c1fd229fc03548c7cc1` |
| 313 | N5 | shared | N2/uncovered-library-directory | `/vendor/lib64/passthrough` | `41c439e40f9d2a0c89695838abeebbc7003825710d222c7bf6d837cd7e073988` |
| 314 | N5 | shared | N2/uncovered-library-directory | `/vendor/lib64/passthrough/indirect` | `1979eca0125ef8096bd6b9378cb80b1000592d3296a0ff1e773c90a00aba7a2c` |
