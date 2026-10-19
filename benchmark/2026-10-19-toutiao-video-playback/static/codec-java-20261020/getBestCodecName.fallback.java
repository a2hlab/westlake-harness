    public java.lang.String getBestCodecName(java.lang.String r18) {
            r17 = this;
            r3 = r17
            com.bytedance.hotfix.base.ChangeQuickRedirect r2 = com.ss.ttm.player.AJMediaCodec.changeQuickRedirect
            r1 = 0
            r10 = r18
            if (r2 == 0) goto L19
            r0 = 705926(0xac586, float:9.89213E-40)
            X.31U r1 = X.C34166DRm.N0(r10, r3, r2, r1, r0)
            boolean r0 = r1.a
            if (r0 == 0) goto L19
            java.lang.Object r0 = r1.b
            java.lang.String r0 = (java.lang.String) r0
            return r0
        L19:
            int r1 = com.ss.ttm.utils.Util.SDK_INT
            r0 = 16
            r4 = 0
            if (r1 >= r0) goto L28
            java.lang.String r1 = "JAJMediaCodec"
            java.lang.String r0 = "API < 16"
            com.ss.ttm.utils.AVLogger.Error(r1, r3, r0)
            return r4
        L28:
            boolean r0 = android.text.TextUtils.isEmpty(r10)
            if (r0 == 0) goto L36
            java.lang.String r1 = "JAJMediaCodec"
            java.lang.String r0 = "codecType is empty"
            com.ss.ttm.utils.AVLogger.Error(r1, r3, r0)
            return r4
        L36:
            java.lang.String r0 = "video/hevc"
            boolean r0 = r10.equals(r0)
            if (r0 == 0) goto L5e
            boolean r0 = com.ss.ttm.player.AJMediaCodec.mIsByteVC1Blocklist
            if (r0 == 0) goto L5e
            int r0 = com.ss.ttm.player.AJMediaCodec.mIsByteVC1BlocklistEnable
            if (r0 <= 0) goto L5e
            java.lang.String r2 = "JAJMediaCodec"
            java.lang.StringBuilder r1 = com.ss.android.article.news.launch.codeopt.StringBuilderOpt.get()
            java.lang.String r0 = "the device is hw decoder blocklist,"
            r1.append(r0)
            java.lang.String r0 = com.ss.ttm.utils.Util.HARDWARE
            r1.append(r0)
            java.lang.String r0 = com.ss.android.article.news.launch.codeopt.StringBuilderOpt.release(r1)
            com.ss.ttm.utils.AVLogger.Warn(r2, r3, r0)
            return r4
        L5e:
            java.lang.StringBuilder r1 = com.ss.android.article.news.launch.codeopt.StringBuilderOpt.get()
            java.lang.String r0 = "detect hardware codec by codecType = "
            r1.append(r0)
            r1.append(r10)
            java.lang.String r0 = " downgradeSw = "
            r1.append(r0)
            int r0 = r3.mDowngradeSw
            r1.append(r0)
            com.ss.android.article.news.launch.codeopt.StringBuilderOpt.release(r1)
            java.util.ArrayList r4 = new java.util.ArrayList
            r4.<init>()
            java.util.ArrayList r16 = new java.util.ArrayList
            r16.<init>()
            java.lang.Object r15 = com.ss.ttm.player.AJMediaCodec.mCodecListLock
            monitor-enter(r15)
            java.lang.String r0 = "video/"
            boolean r0 = r10.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L9a
            int r0 = r3.mDowngradeSw     // Catch: java.lang.Throwable -> L3b7
            if (r0 != 0) goto L9a
            java.util.ArrayList<android.media.MediaCodecInfo> r1 = com.ss.ttm.player.AJMediaCodec.mVideoHWDecoderCodecs     // Catch: java.lang.Throwable -> L3b7
            boolean r0 = r1.isEmpty()     // Catch: java.lang.Throwable -> L3b7
            if (r0 != 0) goto L9a
            r16 = r1
        L9a:
            java.lang.String r0 = "video/"
            boolean r0 = r10.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            r1 = 1
            if (r0 == 0) goto Lb1
            int r0 = r3.mDowngradeSw     // Catch: java.lang.Throwable -> L3b7
            if (r0 != r1) goto Lb1
            java.util.ArrayList<android.media.MediaCodecInfo> r2 = com.ss.ttm.player.AJMediaCodec.mVideoSWDecoderCodecs     // Catch: java.lang.Throwable -> L3b7
            boolean r0 = r2.isEmpty()     // Catch: java.lang.Throwable -> L3b7
            if (r0 != 0) goto Lb1
            r16 = r2
        Lb1:
            java.lang.String r0 = "audio/"
            boolean r0 = r10.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto Lc3
            java.util.ArrayList<android.media.MediaCodecInfo> r2 = com.ss.ttm.player.AJMediaCodec.mAudioSWDecoderCodecs     // Catch: java.lang.Throwable -> L3b7
            boolean r0 = r2.isEmpty()     // Catch: java.lang.Throwable -> L3b7
            if (r0 != 0) goto Lc3
            r16 = r2
        Lc3:
            boolean r0 = r16.isEmpty()     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto Ld0
            boolean r0 = r3.mEnableCacheCodecAsync     // Catch: java.lang.Throwable -> L3b7
            java.util.ArrayList r9 = com.ss.ttm.player.MediacodecBlockManager.getCodecs(r0)     // Catch: java.lang.Throwable -> L3b7
            goto Ld2
        Ld0:
            r9 = r16
        Ld2:
            if (r9 == 0) goto Lda
            boolean r0 = r9.isEmpty()     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto Ldd
        Lda:
            monitor-exit(r15)     // Catch: java.lang.Throwable -> L3b7
            r0 = 0
            return r0
        Ldd:
            int r8 = r9.size()     // Catch: java.lang.Throwable -> L3b7
            r7 = 0
        Le2:
            if (r7 >= r8) goto L24e
            java.lang.Object r12 = r9.get(r7)     // Catch: java.lang.Throwable -> L3b7
            android.media.MediaCodecInfo r12 = (android.media.MediaCodecInfo) r12     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r11 = r12.getName()     // Catch: java.lang.Throwable -> L3b7
            java.lang.StringBuilder r2 = com.ss.android.article.news.launch.codeopt.StringBuilderOpt.get()     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = "found codec name : "
            r2.append(r0)     // Catch: java.lang.Throwable -> L3b7
            r2.append(r11)     // Catch: java.lang.Throwable -> L3b7
            com.ss.android.article.news.launch.codeopt.StringBuilderOpt.release(r2)     // Catch: java.lang.Throwable -> L3b7
            boolean r0 = r12.isEncoder()     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L105
            goto L247
        L105:
            java.lang.String r0 = "OMX.google"
            boolean r0 = r11.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 != 0) goto L115
            java.lang.String r0 = "c2.android"
            boolean r0 = r11.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L123
        L115:
            java.lang.String r0 = "video/"
            boolean r0 = r10.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L139
            int r0 = r3.mDowngradeSw     // Catch: java.lang.Throwable -> L3b7
            if (r0 != 0) goto L139
            goto L247
        L123:
            java.lang.String r0 = "audio/"
            boolean r0 = r10.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 != 0) goto L247
            java.lang.String r0 = "video/"
            boolean r0 = r10.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L139
            int r0 = r3.mDowngradeSw     // Catch: java.lang.Throwable -> L3b7
            if (r0 != r1) goto L139
            goto L247
        L139:
            java.lang.String[] r6 = r12.getSupportedTypes()     // Catch: java.lang.Throwable -> L3b7
            if (r6 != 0) goto L141
            goto L247
        L141:
            int r5 = r6.length     // Catch: java.lang.Throwable -> L3b7
            r2 = 0
        L143:
            if (r2 >= r5) goto L247
            r13 = r6[r2]     // Catch: java.lang.Throwable -> L3b7
            boolean r0 = android.text.TextUtils.isEmpty(r13)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L14f
            goto L240
        L14f:
            boolean r0 = r16.isEmpty()     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L16e
            java.lang.String r0 = "video/"
            boolean r0 = r10.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L16e
            java.lang.String r0 = "video/"
            boolean r0 = r13.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L16e
            int r0 = r3.mDowngradeSw     // Catch: java.lang.Throwable -> L3b7
            if (r0 != r1) goto L191
            java.util.ArrayList<android.media.MediaCodecInfo> r0 = com.ss.ttm.player.AJMediaCodec.mVideoSWDecoderCodecs     // Catch: java.lang.Throwable -> L3b7
            r0.add(r12)     // Catch: java.lang.Throwable -> L3b7
        L16e:
            boolean r0 = r16.isEmpty()     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L189
            java.lang.String r0 = "audio/"
            boolean r0 = r10.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L189
            java.lang.String r0 = "audio/"
            boolean r0 = r13.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L189
            java.util.ArrayList<android.media.MediaCodecInfo> r0 = com.ss.ttm.player.AJMediaCodec.mAudioSWDecoderCodecs     // Catch: java.lang.Throwable -> L3b7
            r0.add(r12)     // Catch: java.lang.Throwable -> L3b7
        L189:
            boolean r0 = r13.equalsIgnoreCase(r10)     // Catch: java.lang.Throwable -> L3b7
            if (r0 != 0) goto L197
            goto L240
        L191:
            java.util.ArrayList<android.media.MediaCodecInfo> r0 = com.ss.ttm.player.AJMediaCodec.mVideoHWDecoderCodecs     // Catch: java.lang.Throwable -> L3b7
            r0.add(r12)     // Catch: java.lang.Throwable -> L3b7
            goto L16e
        L197:
            java.lang.StringBuilder r1 = com.ss.android.article.news.launch.codeopt.StringBuilderOpt.get()     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = "codec type : "
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            r1.append(r13)     // Catch: java.lang.Throwable -> L3b7
            com.ss.android.article.news.launch.codeopt.StringBuilderOpt.release(r1)     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = "OMX."
            boolean r0 = r11.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 != 0) goto L1b6
            java.lang.String r0 = "c2."
            boolean r0 = r11.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L240
        L1b6:
            java.lang.String r0 = "OMX.pv"
            boolean r0 = r11.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 != 0) goto L240
            java.lang.String r0 = "OMX.ittiam"
            boolean r0 = r11.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 != 0) goto L240
            java.lang.String r0 = "ffmpeg"
            boolean r0 = r11.contains(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 != 0) goto L240
            java.lang.String r0 = "avcodec"
            boolean r0 = r11.contains(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 != 0) goto L240
            java.lang.String r0 = "secure"
            boolean r0 = r11.contains(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L1df
            goto L240
        L1df:
            java.lang.String r0 = "OMX.MTK."
            boolean r0 = r11.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L1ee
            int r1 = com.ss.ttm.utils.Util.SDK_INT     // Catch: java.lang.Throwable -> L3b7
            r0 = 18
            if (r1 >= r0) goto L1ee
            goto L240
        L1ee:
            boolean r0 = codecNeedsFlushWorkaround(r11)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L1f5
            goto L240
        L1f5:
            int r0 = r3.mEnableUseCodec2     // Catch: java.lang.Throwable -> L3b7
            com.ss.ttm.player.AJMediaCodecRank r14 = com.ss.ttm.player.AJMediaCodecRank.setupRank(r12, r10, r0)     // Catch: java.lang.Throwable -> L3b7
            if (r14 != 0) goto L1fe
            goto L240
        L1fe:
            java.lang.StringBuilder r1 = com.ss.android.article.news.launch.codeopt.StringBuilderOpt.get()     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = "codec : "
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            android.media.MediaCodecInfo r0 = r14.mMediaCodecInfo     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = r0.getName()     // Catch: java.lang.Throwable -> L3b7
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = ",  rank : "
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            int r0 = r14.mRank     // Catch: java.lang.Throwable -> L3b7
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            com.ss.android.article.news.launch.codeopt.StringBuilderOpt.release(r1)     // Catch: java.lang.Throwable -> L3b7
            int r13 = r14.mRank     // Catch: java.lang.Throwable -> L3b7
            r0 = 40
            if (r13 != r0) goto L231
            int r1 = com.ss.ttm.utils.Util.SDK_INT     // Catch: java.lang.Throwable -> L3b7
            r0 = 21
            if (r1 >= r0) goto L231
            java.lang.String r1 = "JAJMediaCodec"
            java.lang.String r0 = "skip vendor mediacodec api impl ambiguous"
            com.ss.ttm.utils.AVLogger.Warn(r1, r3, r0)     // Catch: java.lang.Throwable -> L3b7
            goto L240
        L231:
            r0 = 20
            if (r13 != r0) goto L23d
            java.lang.String r1 = "JAJMediaCodec"
            java.lang.String r0 = "skip vendor software codec"
            com.ss.ttm.utils.AVLogger.Warn(r1, r3, r0)     // Catch: java.lang.Throwable -> L3b7
            goto L240
        L23d:
            r4.add(r14)     // Catch: java.lang.Throwable -> L3b7
        L240:
            int r2 = r2 + 1
            r0 = 0
            r0 = 0
            r1 = 1
            goto L143
        L247:
            int r7 = r7 + 1
            r0 = 0
            r0 = 0
            r1 = 1
            goto Le2
        L24e:
            boolean r0 = r4.isEmpty()     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L257
            monitor-exit(r15)     // Catch: java.lang.Throwable -> L3b7
            r0 = 0
            return r0
        L257:
            r0 = 0
            java.lang.Object r5 = r4.get(r0)     // Catch: java.lang.Throwable -> L3b7
            com.ss.ttm.player.AJMediaCodecRank r5 = (com.ss.ttm.player.AJMediaCodecRank) r5     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r2 = "JAJMediaCodec"
            java.lang.StringBuilder r1 = com.ss.android.article.news.launch.codeopt.StringBuilderOpt.get()     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = "decoderType:"
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            int r0 = r3.mDecoderType     // Catch: java.lang.Throwable -> L3b7
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = ", lowLatencyType:"
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            int r0 = r3.mLowLatencyType     // Catch: java.lang.Throwable -> L3b7
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = com.ss.android.article.news.launch.codeopt.StringBuilderOpt.release(r1)     // Catch: java.lang.Throwable -> L3b7
            com.ss.ttm.utils.AVLogger.InfoTrackLife(r2, r3, r0)     // Catch: java.lang.Throwable -> L3b7
            java.util.Iterator r10 = r4.iterator()     // Catch: java.lang.Throwable -> L3b7
            r4 = 0
        L284:
            boolean r0 = r10.hasNext()     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L38b
            java.lang.Object r6 = r10.next()     // Catch: java.lang.Throwable -> L3b7
            com.ss.ttm.player.AJMediaCodecRank r6 = (com.ss.ttm.player.AJMediaCodecRank) r6     // Catch: java.lang.Throwable -> L3b7
            int r1 = r3.mDecoderType     // Catch: java.lang.Throwable -> L3b7
            if (r1 > 0) goto L29c
            int r0 = r3.mLowLatencyType     // Catch: java.lang.Throwable -> L3b7
            if (r0 <= 0) goto L299
            goto L29c
        L299:
            r0 = 1
            goto L382
        L29c:
            r9 = -1
            if (r1 <= 0) goto L2a1
            r8 = -1
            goto L2a2
        L2a1:
            r8 = 0
        L2a2:
            int r0 = r3.mLowLatencyType     // Catch: java.lang.Throwable -> L3b7
            if (r0 <= 0) goto L2b9
        L2a6:
            android.media.MediaCodecInfo r0 = r6.mMediaCodecInfo     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r1 = r0.getName()     // Catch: java.lang.Throwable -> L3b7
            java.util.Locale r0 = java.util.Locale.US     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r7 = r1.toLowerCase(r0)     // Catch: java.lang.Throwable -> L3b7
            int r1 = r3.mDecoderType     // Catch: java.lang.Throwable -> L3b7
            r2 = 2
            r0 = 1
            if (r1 == r0) goto L2c7
            goto L2bb
        L2b9:
            r9 = 0
            goto L2a6
        L2bb:
            if (r1 == r2) goto L2be
            goto L2d0
        L2be:
            java.lang.String r0 = "c2"
            boolean r0 = r7.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L2d0
            goto L2cf
        L2c7:
            java.lang.String r0 = "omx"
            boolean r0 = r7.startsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L2d0
        L2cf:
            r8 = 1
        L2d0:
            int r1 = r3.mLowLatencyType     // Catch: java.lang.Throwable -> L3b7
            r0 = 1
            if (r1 == r0) goto L2f9
            if (r1 == r2) goto L2ee
            r0 = 3
            if (r1 == r0) goto L2db
            goto L302
        L2db:
            android.media.MediaCodecInfo r1 = r6.mMediaCodecInfo     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = r6.mCodecType     // Catch: java.lang.Throwable -> L3b7
            boolean r0 = com.ss.ttm.player.MediaCodecHelper.decoderSupportsAndroidRLowLatency(r1, r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 != 0) goto L301
            java.lang.String r0 = "low_latency"
            boolean r0 = r7.endsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L302
            goto L301
        L2ee:
            android.media.MediaCodecInfo r1 = r6.mMediaCodecInfo     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = r6.mCodecType     // Catch: java.lang.Throwable -> L3b7
            boolean r0 = com.ss.ttm.player.MediaCodecHelper.decoderSupportsAndroidRLowLatency(r1, r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L302
            goto L301
        L2f9:
            java.lang.String r0 = "low_latency"
            boolean r0 = r7.endsWith(r0)     // Catch: java.lang.Throwable -> L3b7
            if (r0 == 0) goto L302
        L301:
            r9 = 1
        L302:
            java.lang.String r2 = "JAJMediaCodec"
            java.lang.StringBuilder r1 = com.ss.android.article.news.launch.codeopt.StringBuilderOpt.get()     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = "name:"
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            r1.append(r7)     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = ", decoderTypeMatch:"
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            r1.append(r8)     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = ", lowLatencyMatch:"
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            r1.append(r9)     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = com.ss.android.article.news.launch.codeopt.StringBuilderOpt.release(r1)     // Catch: java.lang.Throwable -> L3b7
            com.ss.ttm.utils.AVLogger.InfoTrackLife(r2, r3, r0)     // Catch: java.lang.Throwable -> L3b7
            if (r8 > 0) goto L32b
            if (r9 <= 0) goto L382
        L32b:
            if (r4 == 0) goto L331
            if (r8 <= 0) goto L333
            if (r9 <= 0) goto L333
        L331:
            r4 = r6
            goto L367
        L333:
            int r1 = r6.mRank     // Catch: java.lang.Throwable -> L3b7
            int r0 = r4.mRank     // Catch: java.lang.Throwable -> L3b7
            if (r1 <= r0) goto L367
            java.lang.String r2 = "JAJMediaCodec"
            java.lang.StringBuilder r1 = com.ss.android.article.news.launch.codeopt.StringBuilderOpt.get()     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = "update specify codec name:"
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            r1.append(r7)     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = ", rank:"
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            int r0 = r6.mRank     // Catch: java.lang.Throwable -> L3b7
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = ", specify codec:"
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            android.media.MediaCodecInfo r0 = r6.mMediaCodecInfo     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = r0.getName()     // Catch: java.lang.Throwable -> L3b7
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = com.ss.android.article.news.launch.codeopt.StringBuilderOpt.release(r1)     // Catch: java.lang.Throwable -> L3b7
            com.ss.ttm.utils.AVLogger.InfoTrackLife(r2, r3, r0)     // Catch: java.lang.Throwable -> L3b7
            goto L331
        L367:
            java.lang.String r2 = "JAJMediaCodec"
            java.lang.StringBuilder r1 = com.ss.android.article.news.launch.codeopt.StringBuilderOpt.get()     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = "find specify codec:"
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            android.media.MediaCodecInfo r0 = r4.mMediaCodecInfo     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = r0.getName()     // Catch: java.lang.Throwable -> L3b7
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = com.ss.android.article.news.launch.codeopt.StringBuilderOpt.release(r1)     // Catch: java.lang.Throwable -> L3b7
            com.ss.ttm.utils.AVLogger.InfoTrackLife(r2, r3, r0)     // Catch: java.lang.Throwable -> L3b7
        L382:
            int r1 = r6.mRank     // Catch: java.lang.Throwable -> L3b7
            int r0 = r5.mRank     // Catch: java.lang.Throwable -> L3b7
            if (r1 <= r0) goto L284
            r5 = r6
            goto L284
        L38b:
            if (r4 == 0) goto L3a9
            java.lang.String r2 = "JAJMediaCodec"
            java.lang.StringBuilder r1 = com.ss.android.article.news.launch.codeopt.StringBuilderOpt.get()     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = "use specify codec:"
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            android.media.MediaCodecInfo r0 = r4.mMediaCodecInfo     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = r0.getName()     // Catch: java.lang.Throwable -> L3b7
            r1.append(r0)     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = com.ss.android.article.news.launch.codeopt.StringBuilderOpt.release(r1)     // Catch: java.lang.Throwable -> L3b7
            com.ss.ttm.utils.AVLogger.InfoTrackLife(r2, r3, r0)     // Catch: java.lang.Throwable -> L3b7
            r5 = r4
        L3a9:
            android.media.MediaCodecInfo r1 = r5.mMediaCodecInfo     // Catch: java.lang.Throwable -> L3b7
            r3.mCodecInfo = r1     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = r5.mCodecType     // Catch: java.lang.Throwable -> L3b7
            r3.mCodecType = r0     // Catch: java.lang.Throwable -> L3b7
            java.lang.String r0 = r1.getName()     // Catch: java.lang.Throwable -> L3b7
            monitor-exit(r15)     // Catch: java.lang.Throwable -> L3b7
            return r0
        L3b7:
            r0 = move-exception
            monitor-exit(r15)     // Catch: java.lang.Throwable -> L3b7
            throw r0
    }

    @com.ss.ttm.player.CalledByNative
    public int getChannelCount() {
