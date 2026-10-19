// evidence_id: ev_613021e9f9d245810ef69a868b905502bfaaae069fd9c6b42095b6df6edfa961
// class: X.C4cC  method: w1  descriptor: (Ljava/lang/String;Ljava/util/Map;)V  overload_count: 1
// provider: JADX headless 0.7.1  APK sha256 a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395
// NOTE: static decompile; display/overload names are engine-local aliases; APK never executed.

    private void w1(String str, java.util.Map<String, String> map) throws IOException {
        String str2;
        ChangeQuickRedirect changeQuickRedirect = wd;
        if (changeQuickRedirect != null && DRm.V0(str, map, this, changeQuickRedirect, false, 708513).a) {
            return;
        }
        if (this.Ob == 1) {
            StringBuilder sb = StringBuilderOpt.get();
            sb.append("setDatasource before url:");
            sb.append(str);
            A4(StringBuilderOpt.release(sb));
        }
        String strN0 = N0(str, map);
        if (this.x6) {
            strN0 = TTHelper.buildHttpsUrl(strN0);
        }
        if (this.Ob == 1) {
            StringBuilder sb2 = StringBuilderOpt.get();
            sb2.append("setDatasource after url:");
            sb2.append(strN0);
            A4(StringBuilderOpt.release(sb2));
        }
        Qjn qjn = this.O3;
        if (qjn != null) {
            qjn.o1(this.v1);
        }
        if (!this.M) {
            long jCurrentTimeMillis = System.currentTimeMillis();
            Qjn qjn2 = this.O3;
            if (qjn2 != null) {
                this.aa = qjn2.x0();
            } else {
                this.aa = TTHelper.genTrackID(C4kY.f, jCurrentTimeMillis);
            }
            if (!TextUtils.isEmpty(this.aa)) {
                map.put("X-Tt-Traceid", this.aa);
                ((ConcurrentHashMap) this.w3).put("X-Tt-Traceid", this.aa);
                if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
                    TTVideoEngineLog.i(g(), StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "X-Tt-Traceid:"), this.aa)));
                }
            }
            if (!TextUtils.isEmpty(this.Zc)) {
                map.put("X-Tt-GroupId", this.Zc);
                this.O3.setStringOption(156, this.Zc);
                if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
                    TTVideoEngineLog.i(g(), StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "X-Tt-GroupId:"), this.Zc)));
                }
            }
            int i = this.U7;
            if (!this.u && i != 0) {
                ((ConcurrentHashMap) this.w3).put("X-Tt-Fapi", String.valueOf(i));
                ((ConcurrentHashMap) this.w3).put("Engine-ID", String.valueOf(this.Wa));
                this.O3.setIntOption(34, i);
            }
            int iD = d(857, this.Ja);
            int i2 = TTVideoEngine.sABRSpeedPredictInputType;
            if (i2 == 1) {
                if (TTVideoEngineLog.isPredicateLoglevelTurnOn(1)) {
                    TTVideoEngineLog.d(g(), StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "HEADER_IS_SPEEDTEST single data, interval:"), TTVideoEngine.sTestSpeedInterval)));
                }
                ((ConcurrentHashMap) this.w3).put("X-SpeedTest-TimeInternal", String.valueOf(TTVideoEngine.sTestSpeedInterval));
            } else if (i2 == 0 && this.Ia > 0 && iD > 0) {
                if (TTVideoEngineLog.isPredicateLoglevelTurnOn(1)) {
                    TTVideoEngineLog.d(g(), StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "enableNetLevel, interval: "), iD)));
                }
                ((ConcurrentHashMap) this.w3).put("X-SpeedTest-TimeInternal", String.valueOf(iD));
            }
            java.util.Map<String, String> map2 = this.w3;
            if (TextUtils.isEmpty(this.a)) {
                str2 = DitoNode.LOAD_STRATEGY_DEFAULT;
            } else {
                str2 = this.a;
            }
            ((ConcurrentHashMap) map2).put("X-Tt-Tag", str2);
            int intOption = this.jc;
            if (this.J0 > 0) {
                intOption = this.H0.getIntOption(801);
                if (intOption == 1) {
                    intOption = 0;
                } else if (intOption == 0) {
                    intOption = 1;
                }
            }
            if (intOption == 0 || intOption == 1) {
                ((ConcurrentHashMap) this.w3).put("X-Tt-VdpIo", String.valueOf(intOption));
            }
            if (!TextUtils.isEmpty(this.b)) {
                ((ConcurrentHashMap) this.w3).put("X-Tt-SubTag", this.b);
            }
        }
        if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
            String strG = g();
            StringBuilder sb3 = StringBuilderOpt.get();
            sb3.append("setDataSource X-Tt-Traceid:");
            sb3.append(map.get("X-Tt-Traceid"));
            TTVideoEngineLog.i(strG, StringBuilderOpt.release(sb3));
        }
        MediaPlayer mediaPlayer = this.d;
        if (mediaPlayer != null && mediaPlayer.getPlayerType() == 0 && d(SystemAttrMapping.enabled, this.Z4 ? 1 : 0) != 0) {
            map.clear();
        }
        if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
            TTVideoEngineLog.i(g(), StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "setDataSource:"), strN0)));
        }
        this.d.setDataSource(this.c, android.net.Uri.parse(strN0), map);
    }
