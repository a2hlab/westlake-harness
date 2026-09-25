# NATIVE-TARGETS-19: 100 语料 app 的 Android-ABI / 网络翻译目标推导(离线)

方法:`native_targets.py`(commit a379e32)——对每个 app `lib/arm64-v8a/*.so` 的未定义符号,nm 比对 `libwebview_bionic_shim.so` 实际导出(本表 shim 符号数 73)+ 规定族前缀(android_fdsan_*/__android_log_*/__system_property_*)与核心符号(__sF/__errno/__register_atfork 等);命中=bionic-only → native target;导入 getaddrinfo/freeaddrinfo/gethostbyname*/getnameinfo 且已是 native target → net target;DT_NEEDED 闭包传播。

语料对齐:app-inputs 共 110 目录,语料 100(表列 100);另 10 个非语料目录略。

| app | native 数 | net 数 | net 目标 | 命中符号样例(首个 native 目标) |
|---|---|---|---|---|
| aegis | 1 | 0 | — | libimage_processing_util_jni.so: ANativeWindow_lock, ANativeWindow_unlockAndPost, __androi |
| anki | 1 | 1 | librsdroid.so | librsdroid.so: __android_log_buf_write, __android_log_write, dlopen |
| antennapod | 1 | 1 | libconscrypt_jni.so | libconscrypt_jni.so: __android_log_print, android_set_abort_message, dlopen |
| burgerking | 34 | 1 | librsa_bridge.so | libNitroMmkv.so: fflush, fprintf, fwrite |
| co-AlipayGphone | 187 | 8 | libBifrost.so, libijkffmpeg4x.so, libmfproducts4x.so, libmyjsi_2.12.260429103028.so, libopenssl.so, libtnet-4.0.0.so, libxriver-core.so, libzrtc.so | libACMemPool.so: __emutls_get_address, fflush, fprintf |
| co-TextNow | 21 | 3 | liblinphone.so, libmediastreamer2.so, libortp.so | libandroidx.graphics.path.so: __system_property_get |
| co-aliexpresshd | 21 | 2 | libaidcnetdetect.so, libtnet-4.0.0.so | libAPSE_5.0.6.so: dlopen, __errno, fclose |
| co-android | 20 | 4 | libImageWatermark.so, libcrashlytics-common.so, libfilament-utils-jni.so, libsqlcipher.so | libAudioWatermark.so: __android_log_print, android_set_abort_message, dlopen |
| co-aweme | 245 | 19 | libCoreCpt.so, libLogTransport.so, libStreamCore.so, libavframework.so, libavmdlv2.so, libbat.so, libbyterts.so, libcllamaengine-android.so, libliveplayer2.so, liblivestrategy.so, liblynxdebugrouter.so, libnativeserver.so, librtclive.so, libsscronet.so, libttcrypto.so, libttffmpeg.so, libttvesdk.so, libvcn.so, libvctfo.so | libAGFX.so: sigaction, sigemptyset, __system_property_get |
| co-barcelona | 67 | 2 | libmsysmerged.so, libstartup.so | libMDCoreDGWServiceHandleMCFBridgejni.so: __register_atfork |
| co-booking | 15 | 2 | libBaiduMapSDK_map_v7_6_3.so, libconscrypt_jni.so | libBaiduMapSDK_base_v7_6_3.so: __android_log_vprint, _ctype_, dlopen |
| co-candycrushsaga | 3 | 1 | libcandycrushsaga.so | libapplovin-native-crash-reporter.so: __android_log_print, android_set_abort_message, __er |
| co-cash | 22 | 0 | — | libFaceIad.so: android_set_abort_message, fflush, fprintf |
| co-chatgpt | 11 | 1 | liblkjingle_peerconnection_so.so | libandroidx.graphics.path.so: __system_property_get |
| co-client | 11 | 2 | libbacktrace-native.so, libroblox.so | libbacktrace-native.so: __android_log_buf_write, __android_log_print, __android_log_vprint |
| co-com-chase-sig-android | 17 | 2 | libBarcodeScannerLib.so, libzcloud.so | libBarcodeScannerLib.so: __android_log_print, __errno, fclose |
| co-com-instagram-android | 13 | 0 | — | libandroidx.graphics.path.so: __system_property_get |
| co-com-snapchat-android | 22 | 1 | libclient.so | libGWP-ASan.so: __errno, fprintf, fputs |
| co-discord | 42 | 2 | libdiscord.so, liblibdiscore-rn-jsi-module.so | libNitroModules.so: fflush, fprintf, fwrite |
| co-duolingo | 29 | 2 | libil2cpp.so, libunity.so | libUberchordAudio.so: __android_log_print, android_set_abort_message, __errno |
| co-frontpage | 4 | 1 | libcronet.143.0.7445.0.so | libandroidx.graphics.path.so: __system_property_get |
| co-katana | 14 | 0 | — | libachilles-jni.so: __register_atfork |
| co-lvoverseas | 154 | 5 | libpreload.so, libsscronet.so, libttcrypto.so, libttffmpeg.so, libvcn.so | libAGFX.so: sigaction, sigemptyset, __system_property_get |
| co-mediaclient | 10 | 1 | libcronet.151.0.7922.83.so | libandroidx.graphics.path.so: __system_property_get |
| co-messenger | 2 | 1 | libtmessages.49.so | liblanguage_id_l2c_jni.so: __android_log_vprint, __android_log_write, android_set_abort_me |
| co-mm | 132 | 12 | libAdvanceP2P.so, libDownloadProxy.so, libTPThirdParties-master.so, libcronet.119.0.6045.214.so, libcrypto.so, libflutter.so, libmarscomm.so, libmmnode.so, libowl.so, libvoipComm.so, libwechatmm.so, libxffmpeg.so | libAdvanceP2P.so: __android_log_print, __cmsg_nxthdr, __emutls_get_address |
| co-mobile | 4 | 1 | libnative-lib.so | libTMXProfiling-6.3-81-jni.so: __android_log_print, android_set_abort_message, dlopen |
| co-music | 9 | 2 | libcrashlytics-common.so, liborbit-jni-spotify.so | libandroidx.graphics.path.so: __register_atfork, __system_property_get |
| co-musically | 175 | 8 | libavmdlbase.so, liblyrax.so, libpreload.so, libsscronet.so, libttcrypto.so, libttffmpeg.so, libvcn.so, libvctfo.so | libAGFX.so: sigaction, sigemptyset, __system_property_get |
| co-newsbreak | 18 | 2 | libavformat.so, libcrashlytics-common.so | libandroidx.graphics.path.so: __system_property_get |
| co-orca | 11 | 0 | — | libandroidx.graphics.path.so: __system_property_get |
| co-p2pmobile | 4 | 0 | — | liba8cf.so: dlopen, __errno, fclose |
| co-pinterest | 11 | 1 | libcronet.143.0.7445.0.so | libandroidx.graphics.path.so: __system_property_get |
| co-safetymapd | 9 | 0 | — | libandroidx.graphics.path.so: __system_property_get |
| co-shopping | 78 | 0 | — | libA9VSAndroidNativeCodec.so: __android_log_print, android_set_abort_message, __errno |
| co-teams | 33 | 4 | libRtmMediaManagerDyn.so, libcrashpad_handler.so, libcrashpad_handler_trampoline.so, libskypert.so | libMicrosoft.AugLoop.Client.Jni.so: __emutls_get_address, __errno, __system_property_get |
| co-ubercab | 14 | 2 | libse.so, libtwilio_voice_android_so.so | libandroidx.graphics.path.so: __system_property_get |
| co-videomeetings | 118 | 12 | libavformat_zm.so, libcrypto_sb.so, libcurl.so, libssl_sb.so, libzMsgAppCommon.so, libzNetDiagnostic.so, libzPTApp.so, libzSipSdk.so, libzVideoApp.so, libzoom_tp.so, libzoombase_crypto_shared.so, libzoombase_shared.so | libAndroidCameraBridge.so: fflush, fprintf, fwrite |
| co-weibo | 71 | 15 | libMortredRtc.so, libWBLivePublisher.so, libagora-core.so, libagora-ffmpeg.so, libagora-rtc-sdk.so, libcronet.131.0.6778.103.so, libecdnvod_jni.so, libffmpeg.so, libflutter.so, libhttpdns.so, libst_mobile.so, libtnet-4.0.0.so, libwlog.so, libydetssdk.so, libzk.so | libCtaApiLib.so: __android_log_print, _ctype_, fputc |
| co-whatsapp | 2 | 0 | — | libsuperpack.so: android_dlopen_ext, __android_log_print, dlopen |
| co-zzkko | 20 | 1 | libsmsdk.so | libTMXProfiling-7.6-46-jni.so: __android_log_print, android_set_abort_message, _ctype_ |
| fd-AppManager | 3 | 0 | — | libam.so: android_set_abort_message, __errno, fflush |
| fd-android | 4 | 0 | — | libandroidx.graphics.path.so: __system_property_get |
| fd-api | 0 | 0 | — |  |
| fd-app | 0 | 0 | — |  |
| fd-auxio | 2 | 0 | — | libffmpegJNI.so: __android_log_print, __errno, fprintf |
| fd-binaryeye | 2 | 0 | — | libimage_processing_util_jni.so: ANativeWindow_lock, ANativeWindow_unlockAndPost, __androi |
| fd-breezyweather | 3 | 0 | — | libandroidx.graphics.path.so: __system_property_get |
| fd-calendar | 1 | 0 | — | libandroidx.graphics.path.so: __system_property_get |
| fd-catima | 1 | 0 | — | libandroidx.graphics.path.so: __system_property_get |
| fd-client | 6 | 1 | libcrypto.so | libandroidx.graphics.path.so: __system_property_get |
| fd-com-amaze-filemanager | 1 | 0 | — | librootoperations.so: __android_log_write, __errno, fflush |
| fd-com-kunzisoft-keepass-libre | 0 | 0 | — |  |
| fd-droidify | 4 | 0 | — | libandroidx.graphics.path.so: __system_property_get |
| fd-etar | 0 | 0 | — |  |
| fd-feeder | 2 | 1 | libgojni.so | libandroidx.graphics.path.so: __system_property_get |
| fd-fennec_fdroid | 15 | 3 | libmegazord.so, libnss3.so, libxul.so | libandroidx.graphics.path.so: __system_property_get |
| fd-filemanager | 1 | 0 | — | libandroidx.graphics.path.so: __system_property_get |
| fd-fitness | 2 | 0 | — | libandroidx.graphics.path.so: __system_property_get |
| fd-fluffychat | 7 | 4 | libflutter.so, libjingle_peerconnection_so.so, libsqlcipher.so, libwebcrypto.so | libImaging.so: fprintf, fwrite, getenv |
| fd-gallery | 12 | 0 | — | libNativeImageProcessor.so: __register_atfork |
| fd-im-vector-app | 21 | 2 | libjingle_peerconnection_so.so, librealm-jni.so | libc++_shared.so: android_set_abort_message, __errno, fclose |
| fd-immich | 8 | 2 | libcronet.143.0.7445.0.so, libflutter.so | libandroidx.graphics.path.so: __system_property_get |
| fd-kitchenowl | 2 | 1 | libflutter.so | libdatastore_shared_counter.so: __errno, __system_property_get |
| fd-libre | 9 | 2 | libflutter.so, libmpv.so | libdartjni.so: __android_log_print |
| fd-libretube | 0 | 0 | — |  |
| fd-meet | 13 | 1 | libjingle_peerconnection_so.so | libc++_shared.so: android_set_abort_message, __errno, fclose |
| fd-minetest | 2 | 1 | libluanti.so | libc++_shared.so: android_set_abort_message, __errno, fclose |
| fd-mobile | 2 | 0 | — | libandroidx.graphics.path.so: __system_property_get |
| fd-mpv | 10 | 2 | libavformat.so, libmpv.so | libavcodec.so: dlopen, __errno, fclose |
| fd-musicplayer | 1 | 0 | — | libandroidx.graphics.path.so: __system_property_get |
| fd-netguard | 1 | 1 | libnetguard.so | libnetguard.so: __android_log_print, __errno, fclose |
| fd-noice | 0 | 0 | — |  |
| fd-notes | 1 | 0 | — | libandroidx.graphics.path.so: __system_property_get |
| fd-organicmaps | 1 | 0 | — | liborganicmaps.so: android_set_abort_message, dlopen, __errno |
| fd-plus | 6 | 1 | libQt5Network.so | libOsmAndCoreWithJNI.so: __android_log_vprint, android_set_abort_message, dlopen |
| fd-reader | 2 | 0 | — | libandroidx.graphics.path.so: __system_property_get |
| fd-saber | 5 | 1 | libflutter.so | libdatastore_shared_counter.so: __errno, __system_property_get |
| fd-seal | 6 | 1 | libaria2c.so | libandroidx.graphics.path.so: __system_property_get |
| fd-shatteredpixeldungeon | 1 | 0 | — | libgdx-freetype.so: fclose, fopen, fread |
| fd-stk | 2 | 1 | libmain.so | libSDL2.so: __android_log_print, __android_log_write, android_set_abort_message |
| fd-tasks | 4 | 0 | — | libandroidx.graphics.path.so: __system_property_get |
| fd-tusky | 4 | 1 | libconscrypt_jni.so | libandroidx.graphics.path.so: __system_property_get |
| fd-tutanota | 6 | 1 | libconscrypt_jni.so | libconscrypt_jni.so: __android_log_print, android_set_abort_message, dlopen |
| fd-uhabits | 0 | 0 | — |  |
| fd-wifianalyzer | 0 | 0 | — |  |
| firefox | 18 | 5 | libcrashhelper.so, libcrashtools.so, libmegazord.so, libnss3.so, libxul.so | libandroidx.graphics.path.so: __system_property_get |
| localsend | 4 | 2 | libflutter.so, librust_lib_localsend_app.so | libdartjni.so: __android_log_print |
| markor | 0 | 0 | — |  |
| mcdonalds | 10 | 4 | libakamaibmp.so, libpanorenderer.so, librealm-jni.so, librealmc.so | libakamaibmp.so: __android_log_print, android_set_abort_message, dlopen |
| mindustry | 2 | 0 | — | libarc-freetype.so: fclose, fopen, fread |
| newpipe | 1 | 0 | — | libandroidx.graphics.path.so: __system_property_get |
| ooniprobe | 5 | 2 | libgojni.so, libuniffi_ooniprobe.so | libandroidx.graphics.path.so: __system_property_get |
| opencamera | 0 | 0 | — |  |
| ppsspp | 2 | 1 | libppsspp_jni.so | libhook_impl.so: android_dlopen_ext, __android_log_print, android_set_abort_message |
| subwaysurfers | 15 | 3 | libcrashlytics-common.so, libil2cpp.so, libunity.so | libFirebaseCppApp-12_10_1.so: __android_log_vprint, android_set_abort_message, __errno |
| termux | 2 | 0 | — | libtermux-bootstrap.so: __register_atfork |
| toutiao | 124 | 9 | libCoreCpt.so, liblivestrategy.so, libmffmpeg.so, libsscronet.so, libtnet-3.1.14.so, libtraceroute-lib.so, libttcrypto.so, libvcn.so, libvctfo.so | libByteVC1_dec.so: __android_log_print |
| vlc | 4 | 1 | libvlc.so | libc++_shared.so: android_set_abort_message, __errno, fclose |
| wikipedia | 2 | 0 | — | libandroidx.graphics.path.so: __system_property_get |

## verify2 首阻塞为 native-symbols 的 app 覆盖

| app | 首阻塞 identity | 推导出 native 目标 | 目标数 |
|---|---|---|---|
| burgerking | _ZNSt6__ndk119__shared_weak_count14__release_weakEv | 是 | 34 |
| co-TextNow | __system_property_read | 是 | 21 |
| co-candycrushsaga | AConfiguration_delete | 是 | 3 |
| co-com-chase-sig-android | android_get_device_api_level | 是 | 17 |
| co-com-snapchat-android | __assert | 是 | 22 |
| co-weibo | _ZNSt6__ndk16chrono12steady_clock3nowEv | 是 | 71 |
| co-zzkko | _ZNSt6__ndk112basic_stringIcNS_11char_traitsIcEENS_9allocato | 是 | 20 |
| fd-immich | ATrace_beginSection | 是 | 8 |

覆盖:8/8 个 native-symbols 首阻塞 app 被推导出非空 native 目标。
