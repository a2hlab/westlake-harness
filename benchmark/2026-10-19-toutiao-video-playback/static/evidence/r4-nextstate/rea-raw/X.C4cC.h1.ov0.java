// evidence_id: ev_74f1b74ea842af0b37a80f476474a85d9c751f7b27e4804b3b0eb914967b0584
// class: X.C4cC  method: h1  descriptor: (Z)V  overload_count: 1
// provider: JADX headless 0.7.1  APK sha256 a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395
// NOTE: static decompile; display/overload names are engine-local aliases; APK never executed.

    /* JADX WARN: Code duplicated, block: B:57:0x00fd  */
    public void h1(boolean z) throws Throwable {
        TTAVPreloaderItem tTAVPreloaderItem;
        int i;
        MediaPlayer mediaPlayer;
        String str;
        String str2;
        ChangeQuickRedirect changeQuickRedirect;
        ChangeQuickRedirect changeQuickRedirect2 = wd;
        boolean z2 = false;
        if (changeQuickRedirect2 != null && DRm.J1(z, this, changeQuickRedirect2, false, 708379).a) {
            return;
        }
        if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
            TTVideoEngineLog.i(g(), StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "_play, mState:"), this.k), ", byPlay:"), z), ", this:"), this)));
        }
        this.L = true;
        this.K = false;
        if (z && (((changeQuickRedirect = wd) == null || !DRm.z0(this, changeQuickRedirect, false, 708480).a) && !this.u3)) {
            this.U0 = new C4dx(this.Uc, C4eU.d, C4eU.e);
            DataLoaderHelper.getDataLoader().setTestSpeedListener(this.U0);
            this.u3 = true;
            this.O3.setIntOption(17, TTVideoEngine.sTestSpeedSampleInterval);
            this.O3.setIntOption(18, TTVideoEngine.sIsReportTestSpeedInfo);
            this.O3.setIntOption(19, TTVideoEngine.sReportSpeedInfoMaxWindowSize);
            this.O3.n2(TTVideoEngine.sNetSpeedAbrPredictType);
        }
        S0();
        Qjn qjn = this.O3;
        if (qjn != null) {
            if (z) {
                qjn.T1(64);
                if (this.U3 < 0) {
                    this.U3 = SystemClock.elapsedRealtime();
                    if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
                        String strG = g();
                        StringBuilder sb = StringBuilderOpt.get();
                        sb.append("mPlayStartTime:");
                        sb.append(this.U3);
                        sb.append(", curT:");
                        sb.append(System.currentTimeMillis());
                        TTVideoEngineLog.i(strG, StringBuilderOpt.release(sb));
                    }
                }
            } else {
                qjn.setIntOption(31, 1);
                this.O3.T1(65);
            }
            this.O3.O0(z);
        }
        int i2 = this.k;
        if (i2 != 0) {
            if (i2 != 1) {
                if (i2 != 3) {
                    if (i2 != 4) {
                        return;
                    }
                } else {
                    ChangeQuickRedirect changeQuickRedirect3 = wd;
                    if (changeQuickRedirect3 != null && DRm.z0(this, changeQuickRedirect3, false, 708432).a) {
                        return;
                    }
                    ChangeQuickRedirect changeQuickRedirect4 = C4cD.O0;
                    if (changeQuickRedirect4 != null) {
                        C31U c31uZ0 = DRm.z0(this, changeQuickRedirect4, false, 708639);
                        if (c31uZ0.a) {
                            z2 = c31uZ0.e;
                        } else {
                            i = this.l;
                            if (((i != 0 || i == 3) && !this.M) || ((mediaPlayer = this.d) != null && mediaPlayer.getPlayerType() == 0 && !this.M)) {
                                z2 = true;
                            }
                        }
                    } else {
                        i = this.l;
                        if (i != 0) {
                        }
                        z2 = true;
                    }
                    if (z2) {
                        if (this.A || this.u || this.c5 != null || this.f5 != null) {
                            V0(this.v3);
                            if (this.A) {
                                str = this.B;
                            } else {
                                str = this.v;
                            }
                            C1(str, this.w3);
                            return;
                        }
                        if (this.F4) {
                            long jCurrentTimeMillis = System.currentTimeMillis() / 1000;
                            long j = this.G4.mUrlTime;
                            if (j > 0 && jCurrentTimeMillis - j > 2400) {
                                M0();
                            }
                            V0(this.G4.mVideoID);
                            C1(this.G4.mUrl, this.w3);
                            return;
                        }
                        if (this.O4) {
                            V0(this.v3);
                            C1(this.P4.playURL, this.w3);
                            return;
                        }
                        V0(this.v3);
                        java.util.Map<String, C4d2> map = this.h4;
                        if (map != null) {
                            C4d2 c4d2 = (C4d2) ((HashMap) map).get(this.P7.a);
                            if (c4d2 != null) {
                                c4d2.b = "FromCache";
                                ((HashMap) this.h4).put(this.P7.a, c4d2);
                                N1();
                            }
                        }
                        C4d6 c4d6 = this.P7;
                        if (c4d6.c) {
                            str2 = c4d6.b;
                        } else {
                            str2 = c4d6.a;
                        }
                        i1(str2, this.w3);
                        return;
                    }
                    if (TTVideoEngineLog.isPredicateLoglevelTurnOn(1)) {
                        TTVideoEngineLog.d(g(), StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "_replayOrResume state:"), this.l), ", playtime:"), this.R)));
                    }
                    if (this.V || (this.l == 0 && this.R == 0)) {
                        v1();
                        u1();
                        V0(this.v3);
                        java.util.Map<String, String> map2 = this.w3;
                        MediaPlayer mediaPlayer2 = this.d;
                        if (map2 != null && mediaPlayer2 != null) {
                            ConcurrentHashMap concurrentHashMap = (ConcurrentHashMap) map2;
                            concurrentHashMap.put("X-Tt-Traceid", this.aa);
                            StringBuilder sb2 = new StringBuilder();
                            for (java.util.Map.Entry entry : concurrentHashMap.entrySet()) {
                                sb2.append((String) entry.getKey());
                                sb2.append(": ");
                                sb2.append((String) entry.getValue());
                                sb2.append("\r\n");
                            }
                            this.d.setStringOption(20, sb2.toString());
                        }
                        C4cg c4cg = this.j0;
                        if (c4cg != null) {
                            c4cg.d();
                        }
                    }
                    r1();
                    return;
                }
            } else if (this.J3 == null) {
                if (!this.l5) {
                    k1();
                    return;
                }
                return;
            } else {
                if (this.F4 && (tTAVPreloaderItem = this.G4) != null) {
                    V0(tTAVPreloaderItem.mVideoID);
                } else {
                    V0(this.v3);
                }
                e1(this.J3);
                return;
            }
        }
        k1();
    }
