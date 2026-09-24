# 最终语料清单 — 100 apps

SHA 为前 16 位，完整 SHA-256、原始标签、输入路径、技术栈证据和 ABI 状态见 [corpus100.json](corpus100.json)。全部输入身份与三阶段产物检查通过；JVM 仅指未打包 native，不能排除运行期下载代码。

| key | package | version | stack | ABI | SHA-256 前缀 | source |
|---|---|---|---|---|---|---|
| co-weibo | `com.sina.weibo` | 16.8.1 | flutter | arm64 | b88ec5013713d2d0 | commercial100-results spare; China top apps |
| mcdonalds | `com.mcdonalds.app` | 26.31.1 | android-jvm | arm64 | 065b0b34b2698eec | manifest app-inputs.lock (local-pins-main) |
| burgerking | `com.emn8.mobilem8.nativeapp.bk` | 7.82.0 | react-native | arm64 | 9c89d53266e01157 | manifest app-inputs.lock (local-pins-main) |
| subwaysurfers | `com.kiloo.subwaysurf` | 3.69.1 | unity-il2cpp | arm64 | a61d69d9922833af | manifest app-inputs.lock (local-pins-main) |
| firefox | `org.mozilla.firefox` | 156.0 | gecko | arm64 | 313626eef7c918f9 | manifest app-inputs.lock (local-pins-main) |
| vlc | `org.videolan.vlc` | 3.7.1 | native-engine | arm64 | c493c167de52724d | manifest app-inputs.lock (local-pins-main) |
| wikipedia | `org.wikipedia` | r/50606-r-2026-09-09 | android-jvm | arm64 | eba82a0f77940d8a | manifest app-inputs.lock (local-pins-main) |
| localsend | `org.localsend.localsend_app` | 1.18.2 | flutter | arm64 | 82ec3568fba2aa52 | manifest app-inputs.lock (local-pins-main) |
| ppsspp | `org.ppsspp.ppsspp` | 1.19.3 | native-engine | arm64 | 44e1ecb9268702fb | manifest app-inputs.lock (local-pins-main) |
| mindustry | `io.anuke.mindustry` | 8-fdroid-160.4 | libgdx/arc | arm64 | 96f8dacbd2de964a | manifest app-inputs.lock (local-pins-main) |
| termux | `com.termux` | 0.118.3 | android-jvm | arm64 | e6265a57eb5ca363 | manifest app-inputs.lock (local-pins-main) |
| ooniprobe | `org.openobservatory.ooniprobe` | 6.2.0 | android-jvm | arm64 | 7a5bc50be59ad5ed | manifest app-inputs.lock (local-pins-main) |
| anki | `com.ichi2.anki` | 2.24.1 | android-jvm | arm64 | f00faccb681117ac | manifest app-inputs.lock (local-pins-main) |
| antennapod | `de.danoeh.antennapod` | 3.12.2 | android-jvm | arm64 | 3f43a4337a693cdb | manifest app-inputs.lock (local-pins-main) |
| newpipe | `org.schabi.newpipe` | 0.29.1 | android-jvm | arm64 | 1d66d19eedbab969 | manifest app-inputs.lock (local-pins-main) |
| aegis | `com.beemdevelopment.aegis` | 3.4.3 | android-jvm | arm64 | 0eecec45de0da3ff | manifest app-inputs.lock (local-pins-main) |
| markor | `net.gsantner.markor` | 2.16.1 | android-jvm | JVM | 3f9f260dc3e32a12 | manifest app-inputs.lock (local-pins-main) |
| opencamera | `net.sourceforge.opencamera` | 1.56.2 | android-jvm | JVM | ca5672ca8c717455 | manifest app-inputs.lock (local-pins-main) |
| fd-k9 | `com.fsck.k9` | 23.0 | android-jvm | arm64 | 92cd3a81c7a8d066 | F-Droid (fdroid100 fetch) |
| fd-tusky | `com.keylesspalace.tusky` | 32.2 | android-jvm | arm64 | 3e8fcc49a80d4c30 | F-Droid (fdroid100 fetch) |
| fd-client | `com.nextcloud.client` | 35.0.0 | android-jvm | arm64 | 2d08059c9a0a94ef | F-Droid (fdroid100 fetch) |
| fd-gallery | `org.fossify.gallery` | 1.13.1 | android-jvm | arm64 | ae7e699599e81f70 | F-Droid (fdroid100 fetch) |
| fd-calendar | `org.fossify.calendar` | 1.10.3 | android-jvm | arm64 | 2acbd47fa2abc6dd | F-Droid (fdroid100 fetch) |
| fd-filemanager | `org.fossify.filemanager` | 1.6.1 | android-jvm | arm64 | 9e97d2faf55fb270 | F-Droid (fdroid100 fetch) |
| fd-com-amaze-filemanager | `com.amaze.filemanager` | 3.11.3 | android-jvm | arm64 | 35e0338dac1bf026 | F-Droid (fdroid100 fetch) |
| fd-feeder | `com.nononsenseapps.feeder` | 2.23.2 | android-jvm | arm64 | 0aa5eb094f94ca29 | F-Droid (fdroid100 fetch) |
| fd-catima | `me.hackerchick.catima` | 2.45.0 | android-jvm | arm64 | 4f01f40d06d82fc5 | F-Droid (fdroid100 fetch) |
| fd-uhabits | `org.isoron.uhabits` | 2.3.1 | android-jvm | JVM | 3903d3be3db0f162 | F-Droid (fdroid100 fetch) |
| fd-seal | `com.junkfood.seal` | 1.13.1-(F-Droid) | android-jvm | arm64 | 7070a3d4f0790469 | F-Droid (fdroid100 fetch) |
| fd-reader | `me.ash.reader` | 0.16.2 | android-jvm | arm64 | 78b1b8b9b6f6d18b | F-Droid (fdroid100 fetch) |
| fd-droidify | `com.looker.droidify` | 0.7.7 | android-jvm | arm64 | da3070f3f18bdbed | F-Droid (fdroid100 fetch) |
| fd-auxio | `org.oxycblt.auxio` | 4.1.5 | android-jvm | arm64 | c2053d36c28dbe74 | F-Droid (fdroid100 fetch) |
| fd-breezyweather | `org.breezyweather` | 6.2.2_freenet | android-jvm | arm64 | 1369d817d4264987 | F-Droid (fdroid100 fetch) |
| fd-etar | `ws.xsoh.etar` | 1.0.57 | android-jvm | JVM | dae01d93c8920aa6 | F-Droid (fdroid100 fetch) |
| fd-fluffychat | `chat.fluffy.fluffychat` | 2.9.5 | flutter | arm64 | edcdf6171c09ab39 | F-Droid (fdroid100 fetch) |
| fd-libre | `deckers.thibault.aves.libre` | 1.15.3 | flutter | arm64 | 25f986a8cae2c208 | F-Droid (fdroid100 fetch) |
| fd-saber | `com.adilhanney.saber` | 1.36.1 | flutter | arm64 | 5e2e3691288fdac7 | F-Droid (fdroid100 fetch) |
| fd-immich | `app.alextran.immich` | 3.2.2 | flutter | arm64 | 36b0d1368881ad63 | F-Droid (fdroid100 fetch) |
| fd-kitchenowl | `com.tombursch.kitchenowl` | 0.7.10 | flutter | arm64 | c7fbb7a62636fc74 | F-Droid (fdroid100 fetch) |
| fd-meet | `org.jitsi.meet` | 26.0.0 | react-native | arm64 | 72a89e53ca532b3a | F-Droid (fdroid100 fetch) |
| fd-tutanota | `de.tutao.tutanota` | 359.260904.0 | webview-hybrid | arm64 | 6e2b9cb23ddbdb1a | F-Droid (fdroid100 fetch) |
| fd-organicmaps | `app.organicmaps` | 2026.08.27-18-FDroid | native-engine | arm64 | c1fc03a8bad4dac3 | F-Droid (fdroid100 fetch) |
| fd-plus | `net.osmand.plus` | 5.3.10 | android-jvm | arm64 | 27f1eb82d288a993 | F-Droid (fdroid100 fetch) |
| fd-stk | `org.supertuxkart.stk` | 1.4 | native-engine | arm64 | 4a01fa9b566a694f | F-Droid (fdroid100 fetch) |
| fd-minetest | `net.minetest.minetest` | 5.17.0 | native-engine | arm64 | 87a136d408ed560d | F-Droid (fdroid100 fetch) |
| fd-app | `com.unciv.app` | 4.22.1 | libgdx/arc | arm64 | 0eb71e65786a7879 | F-Droid (fdroid100 fetch) |
| fd-shatteredpixeldungeon | `com.shatteredpixel.shatteredpixeldungeon` | 4.0.0 | libgdx/arc | arm64 | ed1b43d7312a70e8 | F-Droid (fdroid100 fetch) |
| fd-fennec_fdroid | `org.mozilla.fennec_fdroid` | 156.0.0 | gecko | arm64 | 27f2951376ca1085 | F-Droid (fdroid100 fetch) |
| fd-mpv | `is.xyz.mpv` | 2026-09-17-release | native-engine | arm64 | 5cba2237b20ba34b | F-Droid (fdroid100 fetch) |
| fd-im-vector-app | `im.vector.app` | 1.6.62 | react-native | arm64 | ff73751599211c70 | F-Droid (fdroid100 fetch) |
| fd-api | `com.termux.api` | 0.53.0 | android-jvm | JVM | 4497dbbf81906df5 | F-Droid (fdroid100 fetch) |
| fd-notes | `org.fossify.notes` | 1.7.0 | android-jvm | arm64 | 5a56e0e39cc488e1 | F-Droid (fdroid100 fetch) |
| fd-libretube | `com.github.libretube` | 32.1 | android-jvm | JVM | 792b1e37e7bd6a26 | F-Droid (fdroid100 fetch) |
| fd-com-kunzisoft-keepass-libre | `com.kunzisoft.keepass.libre` | 4.5.4 | android-jvm | arm64 | 862f87a30baef061 | F-Droid (fdroid100 fetch) |
| fd-noice | `com.github.ashutoshgngwr.noice` | 2.5.7 | android-jvm | JVM | 8e11b3136977e9f5 | F-Droid (fdroid100 fetch) |
| fd-tasks | `org.tasks` | 15.12 | android-jvm | arm64 | ed972cc1cec3456a | F-Droid (fdroid100 fetch) |
| fd-android | `net.thunderbird.android` | 23.0 | android-jvm | arm64 | 1e4a2e23a4bff8c8 | F-Droid (fdroid100 fetch) |
| fd-mobile | `org.jellyfin.mobile` | 2.7.3 | webview-hybrid | arm64 | f9f4b3ab46cc9434 | F-Droid (fdroid100 fetch) |
| fd-netguard | `eu.faircode.netguard` | 2.337 | android-jvm | arm64 | 158b4308da000629 | F-Droid (fdroid100 fetch) |
| fd-AppManager | `io.github.muntashirakon.AppManager` | 4.1.1 | android-jvm | arm64 | e1f6ba10812c7401 | F-Droid (fdroid100 fetch) |
| fd-binaryeye | `de.markusfisch.android.binaryeye` | 1.75.4 | android-jvm | arm64 | 428c26249c706bd7 | F-Droid (fdroid100 fetch) |
| fd-wifianalyzer | `com.vrem.wifianalyzer` | 3.3.1 | android-jvm | JVM | 282a06fcc5ce5d88 | F-Droid (fdroid100 fetch) |
| fd-fitness | `de.tadris.fitness` | 16.3 | android-jvm | arm64 | e1708c7c4256748a | F-Droid (fdroid100 fetch) |
| fd-musicplayer | `org.fossify.musicplayer` | 1.8.1 | android-jvm | arm64 | b5d0ce367544df1a | F-Droid (fdroid100 fetch) |
| co-music | `com.spotify.music` | 9.1.84.2231 | android-jvm | arm64 | 72ff1af9d79a3fa2 | Similarweb US top free 2026-09-21 ranks 11-51 |
| co-messenger | `org.telegram.messenger` | 12.10.3 | android-jvm | arm64 | 5195053f1fb5254a | Similarweb US top free 2026-09-21 ranks 11-51 |
| co-android | `com.walmart.android` | 26.36 | android-jvm | arm64 | dfb5fd78a27ba85b | Similarweb US top free 2026-09-21 ranks 11-51 |
| co-newsbreak | `com.particlenews.newsbreak` | 26.38.1 | android-jvm | arm64 | 89a9a7c9c966fa2d | Similarweb US top free 2026-09-21 ranks 11-51 |
| co-safetymapd | `com.life360.android.safetymapd` | 26.35.0 | android-jvm | arm64 | c5d6cbf14ca4f787 | Similarweb US top free 2026-09-21 ranks 11-51 |
| co-pinterest | `com.pinterest` | 14.25.0 | android-jvm | arm64 | a4e090458a22c7a6 | Similarweb US top free 2026-09-21 ranks 11-51 |
| co-TextNow | `com.enflick.android.TextNow` | 26.8.0.0 | android-jvm | arm64 | c59e0bff278a5724 | Similarweb US top free 2026-09-21 ranks 11-51 |
| co-barcelona | `com.instagram.barcelona` | 448.0.0.54.85 | react-native | arm64 | ab19acae0ad8a255 | Similarweb US top free 2026-09-21 ranks 11-51 |
| co-com-chase-sig-android | `com.chase.sig.android` | 4.662 | android-jvm | arm64 | 0ace6cfc9e083d6a | Similarweb US top free 2026-09-21 ranks 11-51 |
| co-ubercab | `com.ubercab` | 4.649.10000 | android-jvm | arm64 | 3c9eb324dc5837e5 | category pick (travel/food/pay/video/edu/work/create/shop/game) |
| co-booking | `com.booking` | 67.4.0.11 | android-jvm | arm64 | be7bc81cc247017e | category pick (travel/food/pay/video/edu/work/create/shop/game) |
| co-mediaclient | `com.netflix.mediaclient` | 9.84.0 build 3 74548 | android-jvm | arm64 | 5cda21c5edd2db8b | category pick (travel/food/pay/video/edu/work/create/shop/game) |
| co-duolingo | `com.duolingo` | 6.98.3 | unity-il2cpp | arm64 | 46eb6a035137e664 | category pick (travel/food/pay/video/edu/work/create/shop/game) |
| co-lvoverseas | `com.lemon.lvoverseas` | 19.7.0 | android-jvm | arm64 | 52afff43356fdd9d | category pick (travel/food/pay/video/edu/work/create/shop/game) |
| co-zzkko | `com.zzkko` | 15.4.2 | android-jvm | arm64 | 8d927c6535a10daa | category pick (travel/food/pay/video/edu/work/create/shop/game) |
| co-aliexpresshd | `com.alibaba.aliexpresshd` | 8.175.4 | android-jvm | arm64 | d8ea0b63aba68581 | category pick (travel/food/pay/video/edu/work/create/shop/game) |
| co-mobile | `com.ebay.mobile` | 6.140.0.1 | android-jvm | arm64 | eee911e868ad6109 | category pick (travel/food/pay/video/edu/work/create/shop/game) |
| co-client | `com.roblox.client` | 2.740.931 | native-engine | arm64 | 0a70a24d8237c593 | category pick (travel/food/pay/video/edu/work/create/shop/game) |
| co-frontpage | `com.reddit.frontpage` | 2026.37.0 | android-jvm | arm64 | 80ddd41678b0248a | Similarweb US top free 2026-09-21 ranks 11-51 |
| co-chatgpt | `com.openai.chatgpt` | 1.2026.244 | android-jvm | arm64 | 970536155b38d43f | Similarweb US top free 2026-09-21 ranks 11-51 |
| co-p2pmobile | `com.paypal.android.p2pmobile` | 10.12.0 | android-jvm | arm64 | e62db40e40b48623 | category pick (travel/food/pay/video/edu/work/create/shop/game) |
| co-videomeetings | `us.zoom.videomeetings` | 7.1.0.41065 | android-jvm | arm64 | 0b466b949b0d5436 | category pick (travel/food/pay/video/edu/work/create/shop/game) |
| co-teams | `com.microsoft.teams` | 1416/1.0.0.2026163804 | react-native | arm64 | ca830a2a4a5454e7 | category pick (travel/food/pay/video/edu/work/create/shop/game) |
| co-candycrushsaga | `com.king.candycrushsaga` | 1.337.0.2 | native-engine | arm64 | 4e131960c39afc07 | category pick (travel/food/pay/video/edu/work/create/shop/game) |
| co-mm | `com.tencent.mm` | 8.0.72 | flutter | arm64 | 2b3c613204361327 | China top apps |
| co-aweme | `com.ss.android.ugc.aweme` | 38.7.0 | android-jvm | arm64 | c400ae7596f5eeaa | China top apps |
| co-AlipayGphone | `com.eg.android.AlipayGphone` | 12.12.16.7200 | android-jvm | arm64 | 62d8b2c44615caed | China top apps |
| co-katana | `com.facebook.katana` | 575.0.0.45.73 | android-jvm | arm64 | 1229320e203ae996 | westlake-harness corpus/downloads.lock.json |
| co-orca | `com.facebook.orca` | 575.0.0.48.90 | android-jvm | arm64 | f48e1b4566408a9e | westlake-harness corpus/downloads.lock.json |
| co-com-instagram-android | `com.instagram.android` | 443.0.0.48.82 | android-jvm | arm64 | a88ad107e99ad23b | westlake-harness corpus/downloads.lock.json |
| co-shopping | `com.amazon.mShop.android.shopping` | 32.12.4.100 | react-native | arm64 | 93c0023c8c8eeed3 | westlake-harness corpus/downloads.lock.json |
| co-musically | `com.zhiliaoapp.musically` | 46.6.1 | android-jvm | arm64 | b26cfb6fc8597026 | westlake-harness corpus/downloads.lock.json |
| co-whatsapp | `com.whatsapp` | 2.26.31.77 | android-jvm | arm64 | 45a6f769fd0088ea | westlake-harness corpus/downloads.lock.json |
| co-cash | `com.squareup.cash` | 5.65.0 | android-jvm | arm64 | a2d753e51fb9abec | westlake-harness corpus/downloads.lock.json |
| co-discord | `com.discord` | 341.13 - Stable | react-native | arm64 | 62345b3197faa88a | westlake-harness corpus/downloads.lock.json |
| co-com-snapchat-android | `com.snapchat.android` | 14.20.0.50 | android-jvm | arm64 | ea05b7e17b1d062d | westlake-harness corpus/downloads.lock.json |
