// evidence_id: ev_19085dc9f7185b7f9718d9360bad7c84ba746d08699fff6d524a544d2a3de881
// class: X.C4cC  method: a0  descriptor: (Lcom/ss/ttvideoengine/model/IVideoModel;Lcom/ss/ttvideoengine/utils/Error;)V  overload_count: 1
// provider: JADX headless 0.7.1  APK sha256 a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395
// NOTE: static decompile; display/overload names are engine-local aliases; APK never executed.

    /* JADX WARN: Multi-variable type inference failed */
    /* JADX WARN: Type inference failed for: r1v57 */
    /* JADX WARN: Type inference failed for: r1v58, types: [boolean, int] */
    /* JADX WARN: Type inference failed for: r1v599 */
    /* JADX WARN: Type inference failed for: r1v600 */
    /* JADX WARN: Type inference failed for: r1v89 */
    /* JADX WARN: Type inference fix 'apply assigned field type' failed
    java.lang.UnsupportedOperationException: ArgType.getObject(), call class: class jadx.core.dex.instructions.args.ArgType$UnknownArg
    	at jadx.core.dex.instructions.args.ArgType.getObject(ArgType.java:596)
    	at jadx.core.dex.attributes.nodes.ClassTypeVarsAttr.getTypeVarsMapFor(ClassTypeVarsAttr.java:35)
    	at jadx.core.dex.nodes.utils.TypeUtils.replaceClassGenerics(TypeUtils.java:177)
    	at jadx.core.dex.visitors.typeinference.FixTypesVisitor.insertExplicitUseCast(FixTypesVisitor.java:397)
    	at jadx.core.dex.visitors.typeinference.FixTypesVisitor.tryFieldTypeWithNewCasts(FixTypesVisitor.java:359)
    	at jadx.core.dex.visitors.typeinference.FixTypesVisitor.applyFieldType(FixTypesVisitor.java:309)
    	at jadx.core.dex.visitors.typeinference.FixTypesVisitor.visit(FixTypesVisitor.java:94)
     */
    public void a0(IVideoModel iVideoModel, Error error) throws Throwable {
        int i;
        int i2;
        boolean z;
        Error error2;
        int i3;
        ?? r1;
        int i4;
        VideoInfo videoInfo;
        int i5;
        String strCacheFilePath;
        int i6;
        boolean z2;
        VideoInfo videoInfo2;
        String str;
        ABRResultElement aBRResultElement;
        java.util.Map<String, String> map;
        IGearStrategyListener iGearStrategyListener;
        Object obj;
        String strStringMapGetString;
        int iStringMapGetInt;
        int iStringMapGetInt2;
        int iStringMapGetInt3;
        int iStringMapGetInt4;
        int iStringMapGetInt5;
        int iStringMapGetInt6;
        int iStringMapGetInt7;
        int iStringMapGetInt8;
        Object value;
        IVideoInfo videoInfoByBitrate;
        boolean z3;
        float predictSpeed;
        float averageDownloadSpeed;
        float lastPredictConfidence;
        float averageDownloadSpeed2;
        long jLongValue;
        long jLongValue2;
        long jLongValue3;
        Object value2;
        boolean z4;
        ChangeQuickRedirect changeQuickRedirect = wd;
        IVideoModel iVideoModel2 = iVideoModel;
        if (changeQuickRedirect != null && DRm.V0(iVideoModel2, error, this, changeQuickRedirect, false, 708545).a) {
            iVideoModel2 = iVideoModel2;
            return;
        }
        iVideoModel2 = iVideoModel2;
        if (iVideoModel2 == null) {
            k4(new Error("kTTVideoErrorDomainFetchingInfo", -9997, "_parseIPAddress:VideoModel is empty"));
            return;
        }
        if (this.I) {
            TTVideoEngineLog.w(g(), "_doParseIPAddress should stop");
            return;
        }
        int iD = d(34, this.x4);
        if (iD == 2 && this.f == 2 && !R0()) {
            return;
        }
        IVideoModel iVideoModel3 = this.J3;
        if (iVideoModel3 != null) {
            String dynamicType = iVideoModel3.getDynamicType();
            if (!TextUtils.isEmpty(dynamicType) && dynamicType.equals("segment_base") && this.N3 == 3) {
                this.Z0 = true;
                this.H0.setIntOption(33, 1);
            }
        }
        if (this.j6.b == 0) {
            SRStrategyConfig sRStrategyConfig = new SRStrategyConfig();
            sRStrategyConfig.setMaxWidth(this.Y5).setMaxHeight(this.Z5);
            int i7 = iVideoModel2.hasFormat(IVideoModel.Format.DASH) ? 2 : 0;
            if (iVideoModel2.hasFormat(IVideoModel.Format.MP4)) {
                i7 |= 1;
            }
            sRStrategyConfig.setCurrentVideoFormatType(i7);
            sRStrategyConfig.setCurrentDuration(iVideoModel2.getVideoRefInt(3));
            List<VideoInfo> videoInfoList = iVideoModel2.getVideoInfoList();
            if (videoInfoList != null && videoInfoList.size() > 0) {
                Iterator<VideoInfo> it = videoInfoList.iterator();
                while (true) {
                    if (it.hasNext()) {
                        String valueStr = it.next().getValueStr(7);
                        if (valueStr != null && valueStr.toLowerCase().contains("hdr")) {
                            z4 = true;
                            break;
                        }
                    } else {
                        z4 = false;
                        break;
                    }
                }
            } else {
                z4 = false;
                break;
            }
            sRStrategyConfig.setIsHdr(z4);
            this.j6.g(sRStrategyConfig);
        }
        int iD2 = d(419, this.s7);
        int iD3 = d(583, this.y8);
        if (!this.W) {
            if (this.E8 > 0 && this.C8 == 0 && iD3 == 0) {
                long jCurrentTimeMillis = System.currentTimeMillis();
                IABRModule iABRModuleB = C4cR.c().b(iVideoModel2.getVideoRefStr(2));
                if (iABRModuleB == null) {
                    iABRModuleB = C4cR.c().a();
                    if (iABRModuleB == null) {
                        iABRModuleB = new DefaultABRModule();
                        z3 = false;
                    } else {
                        z3 = true;
                    }
                    r4(iABRModuleB, iVideoModel2);
                } else {
                    z3 = true;
                }
                Resolution resolution = this.Y3;
                if (resolution != Resolution.Auto && (resolution != null || this.p6 != null)) {
                    VideoInfo videoInfo3 = iVideoModel2.getVideoInfo(resolution, this.p6, true);
                    if (videoInfo3 != null) {
                        long valueInt = videoInfo3.getValueInt(3);
                        iABRModuleB.setLongOptionForKey(22, valueInt);
                        this.h8 = valueInt;
                    }
                } else {
                    this.h8 = -1L;
                    iABRModuleB.setLongOptionForKey(22, -1L);
                }
                Resolution resolutionValueOf = Resolution.valueOf(d(544, this.T8));
                String strE = e(545, this.U8);
                if (resolutionValueOf != Resolution.Undefine || !TextUtils.isEmpty(strE)) {
                    HashMap map2 = new HashMap();
                    map2.put(32, strE);
                    VideoInfo videoInfo4 = iVideoModel2.getVideoInfo(resolutionValueOf, (java.util.Map<Integer, String>) map2, false);
                    if (videoInfo4 != null) {
                        long valueInt2 = videoInfo4.getValueInt(3);
                        iABRModuleB.setLongOptionForKey(33, valueInt2);
                        this.i8 = valueInt2;
                    }
                } else {
                    this.i8 = -1L;
                    iABRModuleB.setLongOptionForKey(33, -1L);
                }
                q4(iABRModuleB, iVideoModel2);
                iABRModuleB.setIntOptionForKey(14, 1);
                DefaultSpeedPredictor defaultSpeedPredictor = C4eU.e;
                float f = 0.0f;
                if (defaultSpeedPredictor != null) {
                    java.util.Map<String, String> downloadSpeed = defaultSpeedPredictor.getDownloadSpeed(VideoRef.TYPE_VIDEO);
                    if (downloadSpeed != null && downloadSpeed.get("download_speed") != null) {
                        f = Float.parseFloat(downloadSpeed.get("download_speed"));
                    }
                    predictSpeed = C4eU.e.getPredictSpeed(0);
                    lastPredictConfidence = C4eU.e.getLastPredictConfidence();
                    averageDownloadSpeed2 = C4eU.e.getAverageDownloadSpeed(VideoRef.TYPE_VIDEO, 1, true);
                    averageDownloadSpeed = C4eU.e.getAverageDownloadSpeed(VideoRef.TYPE_VIDEO, this.K8, false);
                } else {
                    predictSpeed = 0.0f;
                    averageDownloadSpeed = 0.0f;
                    lastPredictConfidence = 0.0f;
                    averageDownloadSpeed2 = 0.0f;
                }
                iABRModuleB.setFloatOptionForKey(25, f);
                iABRModuleB.setFloatOptionForKey(23, predictSpeed);
                iABRModuleB.setFloatOptionForKey(24, lastPredictConfidence);
                iABRModuleB.setFloatOptionForKey(27, averageDownloadSpeed2);
                iABRModuleB.setFloatOptionForKey(28, averageDownloadSpeed);
                iABRModuleB.setIntOptionForKey(21, TTNetWorkListener.i().a);
                TTVideoEngine.getHARInfo();
                iABRModuleB.setIntOptionForKey(39, (this.j6.c() && d(571, this.O8) == 1) ? 1 : 0);
                boolean z5 = this.j6.c;
                iABRModuleB.setIntOptionForKey(40, z5 ? 1 : 0);
                iABRModuleB.setSRBenchmarkMap(this.j6.f);
                this.j6.f("srs", Integer.valueOf(z5 ? 1 : 0));
                iABRModuleB.setStringOptionForKey(75, this.a);
                iABRModuleB.setStringOptionForKey(76, this.b);
                this.q8 = iABRModuleB.getVersion();
                ABRResult aBRResultOnceSelect = iABRModuleB.onceSelect(d(573, this.J8), 1);
                if (iABRModuleB.getLongOption(79, 0L) > 0) {
                    HashMap map3 = new HashMap();
                    map3.put("cap_adaptive_bitrate", Arrays.asList("origin_audio_review_status", "item_category_0"));
                    this.O3.W(map3);
                }
                if (iABRModuleB.getLongOption(80, 0L) > 0) {
                    HashMap map4 = new HashMap();
                    map4.put("per_adaptive_bitrate", Arrays.asList("score", "enter_full_screen"));
                    this.O3.W(map4);
                }
                java.util.Map<String, Object> aBRResult = GearStrategy.parseABRResult(aBRResultOnceSelect);
                if (aBRResult != null) {
                    Object obj2 = aBRResult.get("video_bitrate");
                    jLongValue = obj2 != null ? ((Long) obj2).longValue() : 0L;
                    Object obj3 = aBRResult.get("audio_bitrate");
                    jLongValue3 = obj3 != null ? ((Long) obj3).longValue() : 0L;
                    Object obj4 = aBRResult.get("video_bitrarte_origin");
                    jLongValue2 = obj4 != null ? ((Long) obj4).longValue() : 0L;
                    Object obj5 = aBRResult.get("downgrade_type");
                    if (obj5 != null) {
                        this.a4 = ((Integer) obj5).intValue();
                    }
                } else {
                    jLongValue = 0;
                    jLongValue2 = 0;
                    jLongValue3 = 0;
                }
                C4cS c4cS = this.z8;
                if (c4cS != null && c4cS.a != null) {
                    HashMap map5 = new HashMap();
                    StringBuilder sb = StringBuilderOpt.get();
                    sb.append("");
                    sb.append(jLongValue);
                    map5.put("video_bitrate", StringBuilderOpt.release(sb));
                    StringBuilder sb2 = StringBuilderOpt.get();
                    sb2.append("");
                    sb2.append(jLongValue2);
                    map5.put("video_bitrarte_origin", StringBuilderOpt.release(sb2));
                    C4cS c4cS2 = this.z8;
                    c4cS2.a.onAfterSelect(iVideoModel2, map5, 1, c4cS2.b);
                }
                if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
                    String strG = g();
                    StringBuilder sb3 = StringBuilderOpt.get();
                    sb3.append("[GearStrategy]parseABRResult: videoBitrate=");
                    sb3.append(jLongValue);
                    sb3.append(" audioBitrate=");
                    sb3.append(jLongValue3);
                    sb3.append(" bitrateOrigin=");
                    sb3.append(jLongValue2);
                    sb3.append(" downgradeType=");
                    sb3.append(this.a4);
                    TTVideoEngineLog.i(strG, StringBuilderOpt.release(sb3));
                }
                C4dm c4dm = this.j6;
                if (c4dm.b == 0) {
                    if (1 == this.a4) {
                        this.d6 = true;
                        this.J5 = 1;
                        this.Va = 0;
                        SRStrategyConfig sRStrategyConfig2 = c4dm.a;
                        if (sRStrategyConfig2 != null && (value2 = sRStrategyConfig2.getValue(1, null)) != null) {
                            setEffect((Bundle) value2);
                        }
                    } else {
                        this.d6 = false;
                        this.J5 = 0;
                        this.Va = c4dm.d;
                    }
                }
                long j = jLongValue + jLongValue3;
                this.W3 = j;
                this.f8 = j;
                this.j8 = iABRModuleB.getLongOption(15, -1L);
                this.k8 = iABRModuleB.getLongOption(44, -1L);
                this.l8 = iABRModuleB.getFloatOption(16, -1.0f);
                this.m8 = iABRModuleB.getFloatOption(17, -1.0f);
                this.n8 = iABRModuleB.getFloatOption(18, -1.0f);
                this.t8 = iABRModuleB.getStringOption(74, "");
                this.u8 = iABRModuleB.getStringOption(77, "");
                this.d8 = ABRConfig.getSwitchModel();
                this.e8 = ABRConfig.getStartupModel();
                if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
                    TTVideoEngineLog.i(g(), StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "[SelectorLog] standalong abr startup bitrate="), j), " bitrateShiftFrom="), jLongValue2), " fromPool="), z3)));
                }
                List<VideoInfo> videoInfoList2 = iVideoModel2.getVideoInfoList();
                if (j > 0 && videoInfoList2 != null) {
                    Resolution resolution2 = this.X3;
                    HashMap map6 = new HashMap();
                    for (VideoInfo videoInfo5 : videoInfoList2) {
                        if (videoInfo5 != null && videoInfo5.getMediatype() != VideoRef.TYPE_AUDIO && videoInfo5.getResolution() != null) {
                            long valueInt3 = videoInfo5.getValueInt(3);
                            if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
                                StringBuilder sb4 = StringBuilderOpt.get();
                                sb4.append("resolution=");
                                sb4.append(videoInfo5.getResolution().toString(VideoRef.TYPE_VIDEO));
                                sb4.append(", resolutionBitRate =");
                                sb4.append(valueInt3);
                                TTVideoEngineLog.i("SelectorLog", StringBuilderOpt.release(sb4));
                            }
                            if (valueInt3 == j) {
                                resolution2 = videoInfo5.getResolution();
                                if (!TextUtils.isEmpty(videoInfo5.getValueStr(32))) {
                                    map6.put(32, videoInfo5.getValueStr(32));
                                }
                            }
                            if (jLongValue2 > 0 && valueInt3 == jLongValue2) {
                                this.b4 = videoInfo5.getResolution();
                                this.c4 = videoInfo5.getValueStr(32);
                            }
                        }
                    }
                    this.X3 = resolution2;
                    if (map6.size() > 0) {
                        this.o6 = map6;
                    }
                }
                if (z3) {
                    C4cR.c().d(iABRModuleB);
                } else {
                    iABRModuleB.release();
                }
                long jCurrentTimeMillis2 = System.currentTimeMillis();
                ((HashMap) this.A8).put("vbitrate", Long.valueOf(jLongValue));
                ((HashMap) this.A8).put("vbitrateo", Long.valueOf(jLongValue2));
                ((HashMap) this.A8).put("abitrate", Long.valueOf(jLongValue3));
                ((HashMap) this.A8).put("downgrade", Integer.valueOf(this.a4));
                ((HashMap) this.A8).put("begin", Long.valueOf(jCurrentTimeMillis));
                ((HashMap) this.A8).put("end", Long.valueOf(jCurrentTimeMillis2));
            } else if (iD3 > 0 && this.C8 == 0) {
                long jCurrentTimeMillis3 = System.currentTimeMillis();
                if (this.z8 == null) {
                    this.z8 = new C4cS();
                }
                this.z8.k(4, iD3);
                this.z8.o(28, this.a);
                this.z8.o(29, this.b);
                this.z8.k(24, d(334, this.d9));
                this.z8.k(25, d(335, this.e9));
                this.z8.k(26, this.f9);
                this.z8.k(27, this.g9);
                this.z8.k(23, d(584, this.G9 ? 1 : 0));
                this.z8.k(12, d(571, this.O8));
                this.z8.k(13, this.j6.c() ? 1 : 0);
                boolean z6 = this.j6.c;
                this.z8.k(14, z6 ? 1 : 0);
                this.z8.m(15, this.j6.f);
                GearStrategy.getSrSupportBitrate(iVideoModel2, this.j6, this.z8);
                C4cS c4cS3 = this.z8;
                if (c4cS3 != null) {
                    IGearStrategyListener iGearStrategyListener2 = c4cS3.a;
                    obj = c4cS3.b;
                    map = c4cS3.e;
                    iGearStrategyListener = iGearStrategyListener2;
                } else {
                    map = null;
                    iGearStrategyListener = null;
                    obj = null;
                }
                if (iGearStrategyListener != null) {
                    iGearStrategyListener.onBeforeSelect(iVideoModel2, map, 1, obj);
                }
                java.util.Map<String, String> mapSelect = GearStrategy.select(iVideoModel2, 1, this.z8);
                if (iGearStrategyListener != null) {
                    iGearStrategyListener.onAfterSelect(iVideoModel2, mapSelect, 1, obj);
                }
                if (mapSelect != null) {
                    iStringMapGetInt2 = GearStrategy.stringMapGetInt(mapSelect, "video_bitrate", 0);
                    iStringMapGetInt3 = GearStrategy.stringMapGetInt(mapSelect, "video_bitrarte_origin", 0);
                    iStringMapGetInt4 = GearStrategy.stringMapGetInt(mapSelect, "audio_bitrate", 0);
                    iStringMapGetInt5 = GearStrategy.stringMapGetInt(mapSelect, "error_code", 0);
                    iStringMapGetInt = GearStrategy.stringMapGetInt(mapSelect, "strategy_type", -1);
                    iStringMapGetInt7 = GearStrategy.stringMapGetInt(mapSelect, "strategy_module", -1);
                    iStringMapGetInt8 = GearStrategy.stringMapGetInt(mapSelect, "expected_bitrate", -1);
                    iStringMapGetInt6 = GearStrategy.stringMapGetInt(mapSelect, "bdowngrade_bitrate", -1);
                    strStringMapGetString = GearStrategy.stringMapGetString(mapSelect, "extra_info", "");
                    this.a4 = GearStrategy.stringMapGetInt(mapSelect, "downgrade_type", this.a4);
                    this.o8 = GearStrategy.stringMapGetFloat(mapSelect, "user_quality_sen", this.o8);
                    this.p8 = GearStrategy.stringMapGetInt(mapSelect, "user_enter_fullscreen", this.p8);
                    this.j8 = GearStrategy.stringMapGetLong(mapSelect, "max_cache_bitrate", this.j8);
                    this.k8 = GearStrategy.stringMapGetLong(mapSelect, "bitrate_before_fit_screen", this.k8);
                    this.l8 = GearStrategy.stringMapGetFloat(mapSelect, "startup_speed", this.l8);
                    this.m8 = GearStrategy.stringMapGetFloat(mapSelect, "predict_speed", this.m8);
                    this.n8 = GearStrategy.stringMapGetFloat(mapSelect, "average_speed", this.n8);
                    this.q8 = GearStrategy.stringMapGetString(mapSelect, "abr_ver", this.q8);
                    this.t8 = GearStrategy.stringMapGetString(mapSelect, "sr_info", this.t8);
                    this.u8 = GearStrategy.stringMapGetString(mapSelect, "startup_info", this.u8);
                } else {
                    strStringMapGetString = "";
                    iStringMapGetInt = -1;
                    iStringMapGetInt2 = 0;
                    iStringMapGetInt3 = 0;
                    iStringMapGetInt4 = 0;
                    iStringMapGetInt5 = 0;
                    iStringMapGetInt6 = -1;
                    iStringMapGetInt7 = -1;
                    iStringMapGetInt8 = -1;
                }
                long j2 = iStringMapGetInt2;
                this.W3 = j2;
                this.f8 = j2;
                this.d8 = GearStrategy.getGlobalConfig().c(44);
                this.e8 = GearStrategy.getGlobalConfig().c(46);
                if (iStringMapGetInt2 > 0) {
                    IVideoInfo videoInfoByBitrate2 = GearStrategy.getVideoInfoByBitrate(iVideoModel2, iStringMapGetInt2, EngineGlobalConfig.getInstance().getEnableUseRealBitrate());
                    if (videoInfoByBitrate2 != null) {
                        this.X3 = videoInfoByBitrate2.getResolution();
                        this.o6 = C4cO.c(videoInfoByBitrate2);
                    }
                } else {
                    if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
                        TTVideoEngineLog.i(g(), StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "[GearStrategy] gear strategy videoBitrate <=0 findBestResolution mBestResolutionType="), iD2)));
                    }
                    this.O3.setIntOption(a.n, iStringMapGetInt5);
                    this.X3 = TTVideoEngine.findBestResolution(iVideoModel2, this.X3, iD2, null);
                }
                if (iStringMapGetInt3 > 0 && iStringMapGetInt3 != iStringMapGetInt2 && (videoInfoByBitrate = GearStrategy.getVideoInfoByBitrate(iVideoModel2, iStringMapGetInt3, EngineGlobalConfig.getInstance().getEnableUseRealBitrate())) != null) {
                    this.b4 = videoInfoByBitrate.getResolution();
                    this.c4 = videoInfoByBitrate.getValueStr(32);
                }
                this.h8 = iStringMapGetInt8;
                this.i8 = iStringMapGetInt6;
                C4dm c4dm2 = this.j6;
                if (c4dm2.b == 0) {
                    if (1 == this.a4) {
                        this.d6 = true;
                        this.J5 = 1;
                        this.Va = 0;
                        SRStrategyConfig sRStrategyConfig3 = c4dm2.a;
                        if (sRStrategyConfig3 != null && (value = sRStrategyConfig3.getValue(1, null)) != null) {
                            setEffect((Bundle) value);
                        }
                    } else {
                        this.d6 = false;
                        this.J5 = 0;
                        this.Va = c4dm2.d;
                    }
                }
                this.j6.f("srs", Integer.valueOf(z6 ? 1 : 0));
                long jCurrentTimeMillis4 = System.currentTimeMillis();
                ((HashMap) this.A8).put("vbitrate", Integer.valueOf(iStringMapGetInt2));
                ((HashMap) this.A8).put("vbitrateo", Integer.valueOf(iStringMapGetInt3));
                ((HashMap) this.A8).put("abitrate", Integer.valueOf(iStringMapGetInt4));
                ((HashMap) this.A8).put("downgrade", Integer.valueOf(this.a4));
                ((HashMap) this.A8).put(PrivateApiReportHelper.BRANCH_ERROR, Integer.valueOf(iStringMapGetInt5));
                ((HashMap) this.A8).put("stype", Integer.valueOf(iStringMapGetInt));
                ((HashMap) this.A8).put("smodule", Integer.valueOf(iStringMapGetInt7));
                if (!TextUtils.isEmpty(strStringMapGetString)) {
                    ((HashMap) this.A8).put(MiPushMessage.KEY_EXTRA, strStringMapGetString);
                }
                ((HashMap) this.A8).put("begin", Long.valueOf(jCurrentTimeMillis3));
                ((HashMap) this.A8).put("end", Long.valueOf(jCurrentTimeMillis4));
                if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
                    TTVideoEngineLog.i(g(), StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "[GearStrategy] gear strategy startup mGearStrategyEnabled="), iD3), " videoBitrate="), iStringMapGetInt2), " videoBitrateOrigin="), iStringMapGetInt3), " audioBitrate="), iStringMapGetInt4), " downgrade="), this.a4), " strategyType="), iStringMapGetInt), " strategyModule="), iStringMapGetInt7), " selectErrorCode="), iStringMapGetInt5)));
                }
            } else if (this.C8 > 0) {
                if (this.B8 == null && a4(this.J3)) {
                    this.B8 = Q0(iVideoModel2);
                }
                if (this.B8 != null && this.C8 > 0 && d(503, this.H8) == 0) {
                    q4(this.B8, this.J3);
                    this.B8.setLongOptionForKey(26, this.F8);
                    this.q8 = this.B8.getVersion();
                    ABRResult aBRResultOnceSelect2 = this.B8.onceSelect(d(573, this.J8), 1);
                    if (this.B8.getLongOption(79, 0L) > 0) {
                        HashMap map7 = new HashMap();
                        map7.put("cap_adaptive_bitrate", Arrays.asList("origin_audio_review_status", "item_category_0"));
                        this.O3.W(map7);
                    }
                    if (this.B8.getLongOption(80, 0L) > 0) {
                        HashMap map8 = new HashMap();
                        map8.put("per_adaptive_bitrate", Arrays.asList("score", "enter_full_screen"));
                        this.O3.W(map8);
                    }
                    this.j8 = this.B8.getLongOption(15, -1L);
                    this.k8 = this.B8.getLongOption(44, -1L);
                    this.l8 = this.B8.getFloatOption(16, -1.0f);
                    this.m8 = this.B8.getFloatOption(17, -1.0f);
                    this.n8 = this.B8.getFloatOption(18, -1.0f);
                    this.t8 = this.B8.getStringOption(74, "");
                    this.u8 = this.B8.getStringOption(77, "");
                    this.d8 = ABRConfig.getSwitchModel();
                    this.e8 = ABRConfig.getStartupModel();
                    if (aBRResultOnceSelect2 != null && (aBRResultElement = aBRResultOnceSelect2.get(0)) != null) {
                        long bitrate = aBRResultElement.getBitrate();
                        this.f8 = bitrate;
                        this.W3 = bitrate;
                        this.g8 = bitrate;
                        if (TTVideoEngineLog.isPredicateLoglevelTurnOn(1)) {
                            TTVideoEngineLog.d(g(), StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "[ABR] predict start bitrate:"), bitrate), " bps")));
                        }
                        VideoInfo videoInfoA = C4cO.a(iVideoModel2, bitrate);
                        java.util.Map<Integer, String> mapC = C4cO.c(videoInfoA);
                        if (videoInfoA != null) {
                            this.X3 = videoInfoA.getResolution();
                            this.o6 = mapC;
                        }
                    }
                }
            } else if (this.v8 == 1) {
                this.O3.R1();
                HashMap map9 = new HashMap();
                VideoInfo videoInfoA2 = C4cl.a(this.J3, 1, this.w8, map9);
                if (videoInfoA2 != null) {
                    this.x8 = map9;
                    this.X3 = videoInfoA2.getResolution();
                    this.o6 = C4cO.c(videoInfoA2);
                }
            } else {
                this.X3 = TTVideoEngine.findBestResolution(iVideoModel2, this.X3, iD2, null);
            }
        }
        if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
            String strG2 = g();
            StringBuilder sb5 = StringBuilderOpt.get();
            sb5.append("find best resolution type: ");
            sb5.append(iD2);
            sb5.append(" resolution: ");
            sb5.append(q1(this.X3));
            sb5.append(" abr standalong:");
            sb5.append(this.E8);
            TTVideoEngineLog.i(strG2, StringBuilderOpt.release(sb5));
        }
        java.util.Map<Integer, String> map10 = this.o6;
        if (map10 != null && map10.containsKey(32) && TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
            String strG3 = g();
            StringBuilder sb6 = StringBuilderOpt.get();
            sb6.append("find quality:");
            sb6.append(this.o6.get(32));
            TTVideoEngineLog.i(strG3, StringBuilderOpt.release(sb6));
        }
        String[] codecs = iVideoModel2.getCodecs();
        if (codecs != null || codecs.length > 0) {
            this.X0 = "h264";
            for (String str2 : codecs) {
                if (!TextUtils.isEmpty(str2) && str2.equals("bytevc2")) {
                    if (this.J0 > 0) {
                        this.H0.setStringOption(1000, "bytevc2");
                        break;
                    } else {
                        this.X0 = "bytevc2";
                        break;
                    }
                }
                if (!TextUtils.isEmpty(str2) && str2.equals("bytevc1")) {
                    if (this.J0 > 0) {
                        this.H0.setStringOption(1000, "bytevc1");
                    } else {
                        this.X0 = "bytevc1";
                    }
                }
            }
        }
        String[] strArrAllVideoURLs = iVideoModel2.allVideoURLs(this.X3, this.o6);
        Resolution[] allResolutions = Resolution.getAllResolutions();
        if (this.Ob == 1) {
            StringBuilder sb7 = StringBuilderOpt.get();
            sb7.append("brian show all urls:");
            sb7.append(Arrays.toString(strArrAllVideoURLs));
            A4(StringBuilderOpt.release(sb7));
        }
        VideoInfo videoInfo6 = iVideoModel2.getVideoInfo(this.X3, this.o6);
        if (videoInfo6 != null) {
            SRStrategyConfig sRStrategyConfig4 = new SRStrategyConfig();
            sRStrategyConfig4.setCurrentWidth(videoInfo6.getValueInt(1)).setCurrentHeight(videoInfo6.getValueInt(2));
            this.j6.g(sRStrategyConfig4);
        }
        if (this.O3 != null) {
            this.j6.f("sfr", Integer.valueOf(this.Va));
            this.j6.f("sut", Integer.valueOf(this.d6 ? 1 : 0));
            this.j6.f("so", Integer.valueOf(this.J5));
            C4dm c4dm3 = this.j6;
            c4dm3.f("sm", Integer.valueOf(c4dm3.b));
            JSONArray mediaInfoJson = GearStrategy.getMediaInfoJson(iVideoModel2, d(584, this.G9 ? 1 : 0));
            if (mediaInfoJson != null) {
                ((HashMap) this.A8).put("minfo", mediaInfoJson);
            }
            i = 2;
            this.O3.j2(GearStrategy.getPreloadInfo(iVideoModel2.getVideoRefStr(2), this.f8));
        } else {
            i = 2;
        }
        if (TTVideoEngineLog.isPredicateLoglevelTurnOn(i)) {
            String strG4 = g();
            StringBuilder sb8 = StringBuilderOpt.get();
            sb8.append("[SRLog] got video info mUseSRTexture=");
            sb8.append(this.d6);
            sb8.append(" mTextureSrOpen=");
            sb8.append(this.J5);
            sb8.append(" mSRNotUseReason=");
            sb8.append(this.Va);
            sb8.append(" config=");
            sb8.append(this.j6.a());
            TTVideoEngineLog.i(strG4, StringBuilderOpt.release(sb8));
        }
        if (videoInfo6 != null && this.f8 < 0) {
            this.f8 = videoInfo6.getValueInt(3);
        }
        if (TextUtils.isEmpty(this.s8)) {
            if (!TextUtils.isEmpty(null)) {
                this.s8 = null;
            } else {
                this.s8 = q1(this.X3);
            }
        }
        if (U0(videoInfo6, iVideoModel2)) {
            videoInfo6 = null;
            strArrAllVideoURLs = null;
        }
        if (allResolutions.length > 0) {
            int length = allResolutions.length - 1;
            for (int i8 = 0; i8 < allResolutions.length; i8++) {
                if (allResolutions[i8].getIndex() == this.X3.getIndex()) {
                    length = i8;
                    break;
                }
            }
            int length2 = length;
            z = false;
            do {
                if (strArrAllVideoURLs == null || strArrAllVideoURLs.length == 0) {
                    Resolution resolution3 = allResolutions[length2];
                    strArrAllVideoURLs = iVideoModel2.allVideoURLs(resolution3, null);
                    if (strArrAllVideoURLs != null && strArrAllVideoURLs.length != 0) {
                        videoInfo6 = iVideoModel2.getVideoInfo(resolution3, (java.util.Map<Integer, String>) null);
                        if (!U0(videoInfo6, iVideoModel2)) {
                            this.X3 = resolution3;
                        } else {
                            videoInfo6 = null;
                            z = true;
                            strArrAllVideoURLs = null;
                        }
                    }
                    i2 = 1;
                    length2 = ((length2 + allResolutions.length) - 1) % allResolutions.length;
                }
                i2 = 1;
                break;
            } while (length2 != length);
        } else {
            i2 = 1;
            z = false;
        }
        if (this.Ob == i2) {
            StringBuilder sb9 = StringBuilderOpt.get();
            sb9.append("currentResolution:");
            sb9.append(q1(this.X3));
            sb9.append(", quality_desc:");
            java.util.Map<Integer, String> map11 = this.o6;
            if (map11 != null) {
                str = map11.get(32);
            } else {
                str = -1;
            }
            sb9.append(str);
            sb9.append(", tmpInfo resolution:");
            sb9.append(videoInfo6 != null ? q1(videoInfo6.getResolution()) : "null");
            A4(StringBuilderOpt.release(sb9));
        }
        this.e4 = videoInfo6;
        C4dS.a().getClass();
        this.O3.d0(q1(this.X3), "");
        this.ea = iVideoModel2.getVideoRefStr(221);
        this.ga = iVideoModel2.getVideoRefStr(241);
        this.ha = iVideoModel2.getVideoRefLong(243);
        this.N6 = iVideoModel2.getVideoRefInt(242);
        String videoRefStr = iVideoModel2.getVideoRefStr(235);
        this.fa = videoRefStr;
        if (TextUtils.isEmpty(videoRefStr) && (videoInfo2 = this.e4) != null) {
            this.fa = videoInfo2.getValueStr(43);
        }
        if (this.B8 != null && this.C8 > 0 && a4(this.J3) && this.n0 && this.X4) {
            this.B8.start(TTVideoEngine.sABRAlgorithmType, d(500, this.G8));
            this.O3.Q1(1);
        } else {
            this.O3.Q1(0);
        }
        this.O3.h(d(525, this.X8));
        this.O3.n2(TTVideoEngine.sNetSpeedAbrPredictType);
        this.O3.setIntOption(91, this.E8);
        this.O3.setIntOption(InternetDomainName.MAX_PARTS, iD3);
        v1();
        VideoInfo videoInfo7 = this.e4;
        if (videoInfo7 != null) {
            this.q6 = videoInfo7.getValueStr(18);
            this.r6 = this.e4.getValueStr(32);
            this.X3 = this.e4.getResolution();
            this.s6 = this.e4.getValueInt(41);
            if (this.b4 == null) {
                this.b4 = this.X3;
                this.c4 = this.r6;
            }
            this.O3.m1(this.r6);
            if (this.J0 > 0) {
                i6 = 1;
                z2 = this.H0.getIntOption(33) == 1;
            } else {
                i6 = 1;
                z2 = this.Z0;
            }
            if (z2 && Y3(iVideoModel2)) {
                strArrAllVideoURLs = this.e4.getValueStrArr(16);
                if (this.Ob == i6) {
                    StringBuilder sb10 = StringBuilderOpt.get();
                    sb10.append("enable bash show urls:");
                    sb10.append(Arrays.toString(strArrAllVideoURLs));
                    A4(StringBuilderOpt.release(sb10));
                }
            }
        }
        int iIntValue = ((Integer) ((HashMap) this.g4).get(this.X3)).intValue();
        if (strArrAllVideoURLs != null && strArrAllVideoURLs.length != 0) {
            if (strArrAllVideoURLs.length <= iIntValue) {
                error2 = new Error("kTTVideoErrorDomainFetchingInfo", -9996);
            } else {
                error2 = TextUtils.isEmpty(strArrAllVideoURLs[iIntValue]) ? new Error("kTTVideoErrorDomainFetchingInfo", -9967) : null;
            }
        } else if (z) {
            error2 = new Error("kTTVideoErrorDomainFetchingInfo", -9959);
        } else {
            error2 = new Error("kTTVideoErrorDomainFetchingInfo", -9997);
        }
        if (error2 != null) {
            k4(error2);
            return;
        }
        int i9 = d(403, this.u6 ? 1 : 0) == 1 ? 1 : 0;
        if (d(160, this.m5) > 0 && DataLoaderHelper.getDataLoader().isRunning() && iD != 2) {
            p1();
            String strO0 = null;
            String strN0 = N0(strArrAllVideoURLs[iIntValue], null);
            if (this.Ob == 1) {
                StringBuilder sb11 = StringBuilderOpt.get();
                sb11.append("brian show _generatePlayUrl:");
                sb11.append(strN0);
                A4(StringBuilderOpt.release(sb11));
            }
            if (TextUtils.isEmpty(strN0)) {
                k4(new Error("kTTVideoErrorDomainFetchingInfo", -9967));
                return;
            }
            if (i9 != 0) {
                DataLoaderHelper.getDataLoader().updateDnsInfo(iVideoModel2.getDnsInfo(), iVideoModel2.getVideoRefLong(216));
            }
            ArrayList<VideoInfo> arrayList = new ArrayList();
            if (iVideoModel2.hasFormat(IVideoModel.Format.DASH)) {
                if (strN0.startsWith("mem://bash") && iVideoModel2.hasData()) {
                    arrayList.addAll(iVideoModel2.getVideoInfoList());
                }
            } else if (iVideoModel2.hasFormat(IVideoModel.Format.HLS) && strN0.startsWith("mem://hls") && iVideoModel2.hasData()) {
                arrayList.addAll(iVideoModel2.getVideoInfoList());
            } else if (strN0.startsWith("mem://bash") && iVideoModel2.hasData()) {
                arrayList.addAll(iVideoModel2.getVideoInfoList());
            } else {
                arrayList.add(this.e4);
            }
            ArrayList arrayList2 = new ArrayList();
            for (VideoInfo videoInfo8 : arrayList) {
                if (this.I) {
                    TTVideoEngineLog.w(g(), "_doParseIPAddress should stop");
                    return;
                }
                if (videoInfo8 != null) {
                    String strA = C4dL.a(videoInfo8);
                    String valueStr2 = videoInfo8.getValueStr(5);
                    String videoRefStr2 = iVideoModel2.getVideoRefStr(2);
                    String valueStr3 = videoInfo8.getValueStr(15);
                    CacheFilePathListener cacheFilePathListener = this.E3;
                    if (cacheFilePathListener != null) {
                        strCacheFilePath = cacheFilePathListener.cacheFilePath(videoRefStr2, videoInfo8);
                        i5 = 16;
                    } else {
                        i5 = 16;
                        strCacheFilePath = null;
                    }
                    String[] valueStrArr = videoInfo8.getValueStrArr(i5);
                    if (valueStrArr != null && valueStrArr.length > 0) {
                        VideoInfo videoInfoCopyInfo = videoInfo8.copyInfo();
                        String[] strArrG3 = G3((String[]) valueStrArr.clone(), videoRefStr2);
                        if (this.x6) {
                            for (int i10 = 0; i10 < strArrG3.length; i10++) {
                                strArrG3[i10] = TTHelper.buildHttpsUrl(strArrG3[i10]);
                            }
                        }
                        if (iIntValue == 1 && this.ed && strN0.startsWith("mem://bash") && strArrG3.length > 1) {
                            String str3 = strArrG3[0];
                            strArrG3[0] = strArrG3[1];
                            strArrG3[1] = str3;
                        }
                        String strB1 = b1(valueStr3, videoRefStr2, d(161, this.q5), strArrG3, this.X3, valueStr2, videoInfo8, strCacheFilePath, strA, 0L, null, -1);
                        if (!((ArrayList) this.ja).contains(valueStr3)) {
                            ((ArrayList) this.ja).add(valueStr3);
                        }
                        if (!TextUtils.isEmpty(strB1)) {
                            videoInfoCopyInfo.setValue(16, new String[]{strB1, strB1});
                            if (strN0.startsWith("mem://bash") || strN0.startsWith("mem://hls")) {
                                if (videoInfo8.getMediatype() == VideoRef.TYPE_VIDEO) {
                                    if (this.Ob == 1) {
                                        StringBuilder sb12 = StringBuilderOpt.get();
                                        sb12.append("dashVideoUrlMap put res:");
                                        sb12.append(videoInfo8.getResolution());
                                        sb12.append(", url:");
                                        sb12.append(strB1);
                                        A4(StringBuilderOpt.release(sb12));
                                    }
                                    ((HashMap) this.i4).put(videoInfo8.getResolution(), strB1);
                                } else {
                                    if (videoInfo8.getMediatype() == VideoRef.TYPE_AUDIO) {
                                        ((HashMap) this.j4).put(Integer.valueOf(videoInfo8.getValueInt(3)), strB1);
                                    }
                                    ((HashMap) this.k4).put(Integer.valueOf(videoInfo8.getValueInt(42)), strB1);
                                    strO0 = strN0;
                                }
                                ((HashMap) this.k4).put(Integer.valueOf(videoInfo8.getValueInt(42)), strB1);
                                strO0 = strN0;
                            }
                            arrayList2.add(videoInfoCopyInfo);
                            strO0 = strB1;
                        }
                        strB1 = strO0;
                        arrayList2.add(videoInfoCopyInfo);
                        strO0 = strB1;
                    }
                }
            }
            i3 = 2;
            r1 = 0;
            i4 = 3;
            if ((strN0.startsWith("mem://bash") || strN0.startsWith("mem://hls")) && arrayList2.size() > 0) {
                strO0 = O0(strArrAllVideoURLs[iIntValue], null, arrayList2);
            }
            if (!TextUtils.isEmpty(strO0)) {
                if (this.Ob == 1) {
                    StringBuilder sb13 = StringBuilderOpt.get();
                    sb13.append("show proxyUrl:");
                    sb13.append(strO0);
                    A4(StringBuilderOpt.release(sb13));
                }
                C4d6 c4d6 = this.P7;
                c4d6.a = strO0;
                c4d6.c = false;
                this.O3.g2((strO0.startsWith("mem://bash") || strO0.startsWith("mem://hls")) ? (String) ((HashMap) this.i4).get(this.X3) : strO0);
                ConcurrentHashMap concurrentHashMap = (ConcurrentHashMap) this.w3;
                concurrentHashMap.remove(HttpHeaders.HOST);
                i1(strO0, concurrentHashMap);
                return;
            }
        } else {
            i3 = 2;
            r1 = 0;
            r1 = 0;
            r1 = 0;
            i4 = 3;
            if (iD != 2) {
                if (d(160, this.m5) == 0) {
                    this.O3.setIntOption(174, IVideoEventLogger.MdlInvalidCode.OptionNotSet.ordinal());
                } else {
                    this.O3.setIntOption(174, IVideoEventLogger.MdlInvalidCode.StateError.ordinal());
                    d4();
                }
            }
        }
        int i11 = this.f;
        if (i11 == i4 || i11 == 4) {
            for (int i12 = 0; i12 < strArrAllVideoURLs.length; i12++) {
                strArrAllVideoURLs[i12] = TTHelper.buildHttpUrl(strArrAllVideoURLs[i12]);
            }
        }
        if (TTVideoEngineLog.isPredicateLoglevelTurnOn(i3)) {
            String strG5 = g();
            StringBuilder sb14 = StringBuilderOpt.get();
            sb14.append("current resolution:");
            sb14.append(q1(this.X3));
            sb14.append(", urls:");
            sb14.append(TextUtils.join(Constants.ACCEPT_TIME_SEPARATOR_SP, strArrAllVideoURLs));
            sb14.append(", index:");
            sb14.append(iIntValue);
            TTVideoEngineLog.i(strG5, StringBuilderOpt.release(sb14));
        }
        if (d(r1, this.V0) == 0 && (videoInfo = this.e4) != null) {
            this.V0 = videoInfo.getValueInt(13);
            this.H0.setIntOption(r1, this.e4.getValueInt(13));
        }
        C4d6 c4d7 = this.P7;
        String str4 = strArrAllVideoURLs[iIntValue];
        c4d7.a = str4;
        c4d7.c = r1;
        if (str4 == null) {
            k4(new Error("kTTVideoErrorDomainFetchingInfo", -9967, "mURLInfo.hostURL is empty"));
            return;
        }
        ((HashMap) this.h4).put(str4, new C4d2(this, "", "", d(18, this.g5 ? 1 : 0), i9, iIntValue == 0 ? "main" : "backup"));
        N1();
        if (iD == i3 && this.f == i3 && this.Oa != null) {
            int iProcessToken = this.Oa.processToken(C4kY.b, this.v3, this.e4.getValueStr(36));
            if (iProcessToken == -1001) {
                k4(new Error("kTTVideoErrorDomainIntertrustDRM", -9937));
                return;
            } else {
                if (iProcessToken == -1) {
                    k4(new Error("kTTVideoErrorDomainIntertrustDRM", -9934));
                    return;
                }
                return;
            }
        }
        if (O1(r1)) {
            i1(this.P7.a, this.w3);
        } else {
            d1(this.P7.a);
        }
    }
