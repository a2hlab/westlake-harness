// evidence_id: ev_75c7dd45e87e187f9c6f13ab59fac08f1092e4dc98919d36a7f49524b805c76a
// class: X.C4cC  method: d1  descriptor: (Ljava/lang/String;)V  overload_count: 1
// provider: JADX headless 0.7.1  APK sha256 a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395
// NOTE: static decompile; display/overload names are engine-local aliases; APK never executed.

    private void d1(String str) {
        int i;
        boolean z;
        int i2;
        IVideoModel iVideoModel;
        ChangeQuickRedirect changeQuickRedirect = wd;
        boolean z2 = false;
        if (changeQuickRedirect != null && DRm.N0(str, this, changeQuickRedirect, false, 708390).a) {
            return;
        }
        if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
            TTVideoEngineLog.i(g(), StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "hostnameURL:"), str)));
        }
        if (this.I) {
            TTVideoEngineLog.w(g(), "_parseDNS should stop");
            return;
        }
        this.k = 2;
        Qjn qjn = this.O3;
        if (qjn != null) {
            qjn.r1(System.currentTimeMillis(), 0);
        }
        try {
            C4eY c4eY = new C4eY(this.c, new java.net.URL(str).getHost(), getNetClientSetByUser());
            this.S3 = c4eY;
            c4eY.d = new C4eX(this) { // from class: X.4cP
                public static ChangeQuickRedirect b;
                public final WeakReference<C4cC> a;
                public volatile transient Object robustFieldMap;

                @Override // X.C4eX
                public void onCancelled() {
                    ChangeQuickRedirect changeQuickRedirect2 = b;
                    if (changeQuickRedirect2 != null && DRm.z0(this, changeQuickRedirect2, false, 708105).a) {
                        return;
                    }
                    TTVideoEngineLog.i(C4cD.h(this.a.get()), "dns cancelled");
                }

                {
                    ChangeQuickRedirect changeQuickRedirect2 = b;
                    if (changeQuickRedirect2 != null && DRm.N0(this, this, changeQuickRedirect2, false, 708108).a) {
                        return;
                    }
                    this.a = new WeakReference<>(this);
                }

                @Override // X.C4eX
                public void onRetry(Error error) {
                    ChangeQuickRedirect changeQuickRedirect2 = b;
                    if ((changeQuickRedirect2 != null && DRm.N0(error, this, changeQuickRedirect2, false, 708106).a) || error != null) {
                        return;
                    }
                    C4cC c4cC = this.a.get();
                    if (TTVideoEngineLog.isPredicateLoglevelTurnOn(6)) {
                        String strH = C4cD.h(c4cC);
                        StringBuilder sb = StringBuilderOpt.get();
                        sb.append("fetcher should retry, error:");
                        sb.append(error.toString());
                        TTVideoEngineLog.e(strH, StringBuilderOpt.release(sb));
                    }
                    if (c4cC == null) {
                        return;
                    }
                    c4cC.O3.f(error);
                }

                @Override // X.C4eX
                public void onCompletion(JSONObject jSONObject, Error error) throws Throwable {
                    C4cC c4cC;
                    String strOptString;
                    ChangeQuickRedirect changeQuickRedirect2 = b;
                    if ((changeQuickRedirect2 != null && DRm.V0(jSONObject, error, this, changeQuickRedirect2, false, 708107).a) || (c4cC = this.a.get()) == null) {
                        return;
                    }
                    if (c4cC.I) {
                        TTVideoEngineLog.w(C4cD.h(c4cC), "MyDNSCompletionListener should stop");
                        return;
                    }
                    if (error != null) {
                        if (TTVideoEngineLog.isPredicateLoglevelTurnOn(6)) {
                            String strH = C4cD.h(c4cC);
                            StringBuilder sb = StringBuilderOpt.get();
                            sb.append("dns failed:");
                            sb.append(error.toString());
                            TTVideoEngineLog.e(strH, StringBuilderOpt.release(sb));
                        }
                        c4cC.k4(error);
                        return;
                    }
                    if (jSONObject != null) {
                        strOptString = jSONObject.optString("ip");
                        long jOptLong = jSONObject.optLong(CrashHianalyticsData.TIME);
                        String strOptString2 = jSONObject.optString("dns_type");
                        if (c4cC.O3 != null) {
                            c4cC.O3.i(jOptLong);
                            c4cC.O3.setStringOption(86, strOptString2);
                        }
                    } else {
                        strOptString = null;
                    }
                    if (TextUtils.isEmpty(strOptString)) {
                        c4cC.k4(new Error("", -9997, "DNS result empty"));
                        TTVideoEngineLog.e(C4cD.h(c4cC), "dns parse empty");
                    } else {
                        C4cC.c3(c4cC, strOptString);
                    }
                }
            };
            if (this.F0 != 0) {
                this.S3.h();
            }
            C4eY c4eY2 = this.S3;
            if (this.g5) {
                i = 1;
            } else {
                i = 0;
            }
            if (d(18, i) == 1) {
                z = true;
            } else {
                z = false;
            }
            c4eY2.n = z;
            int iD = d(19, this.h5);
            if (iD > 0) {
                this.S3.p = iD;
            }
            if (this.u6) {
                i2 = 1;
            } else {
                i2 = 0;
            }
            if (d(403, i2) == 1) {
                z2 = true;
            }
            if (z2 && (iVideoModel = this.J3) != null) {
                C4eY c4eY3 = this.S3;
                c4eY3.o = z2;
                c4eY3.g(iVideoModel.getDnsInfo(), Long.valueOf(this.J3.getVideoRefLong(216)));
            }
            this.S3.start();
        } catch (Exception e) {
            if (TTVideoEngineLog.isPredicateLoglevelTurnOn(1)) {
                TTVideoEngineLog.d(e);
            }
        }
    }
