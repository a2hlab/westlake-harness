// evidence_id: ev_1123629e811fe713877127548b886f8ae9ecac556b9b6aa1b44ce910b10dffec
// class: X.C4cC  method: a1  descriptor: (Ljava/lang/String;)V  overload_count: 1
// provider: JADX headless 0.7.1  APK sha256 a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395
// NOTE: static decompile; display/overload names are engine-local aliases; APK never executed.

    private void a1(String str) {
        String str2;
        VideoInfo videoInfo;
        String str3;
        ChangeQuickRedirect changeQuickRedirect = wd;
        int iIntValue = 0;
        if (changeQuickRedirect != null && DRm.N0(str, this, changeQuickRedirect, false, 708282).a) {
            return;
        }
        if (TextUtils.isEmpty(str)) {
            TTVideoEngineLog.d(g(), "log first url . url is null");
            return;
        }
        String[] strArrAllVideoURLs = null;
        if (this.Q4) {
            this.Q4 = false;
            String str4 = "";
            if (str.startsWith("mem://bash") && (videoInfo = this.e4) != null) {
                if (this.Pc) {
                    if (videoInfo.getMediatype() == VideoRef.TYPE_VIDEO) {
                        str2 = (String) ((HashMap) this.k4).get(Integer.valueOf(this.e4.getValueInt(42)));
                        if (!TextUtils.isEmpty(str2)) {
                            if (this.Ob == 1) {
                                StringBuilder sb = StringBuilderOpt.get();
                                sb.append("parse first video url: ");
                                sb.append(str2);
                                A4(StringBuilderOpt.release(sb));
                            }
                        } else {
                            str2 = str;
                        }
                        int videoRefInt = this.a3;
                        if (videoRefInt == -1) {
                            videoRefInt = this.J3.getVideoRefInt(230);
                        }
                        str3 = (String) ((HashMap) this.k4).get(Integer.valueOf(videoRefInt));
                        if (!TextUtils.isEmpty(str3)) {
                            if (this.Ob == 1) {
                                StringBuilder sb2 = StringBuilderOpt.get();
                                sb2.append("parse first audio url: ");
                                sb2.append(str3);
                                A4(StringBuilderOpt.release(sb2));
                            }
                            str4 = str3;
                        }
                    } else {
                        if (this.e4.getMediatype() == VideoRef.TYPE_AUDIO) {
                            String str5 = (String) ((HashMap) this.k4).get(Integer.valueOf(this.e4.getValueInt(42)));
                            if (!TextUtils.isEmpty(str5)) {
                                str4 = str5;
                            }
                        }
                        str2 = str;
                    }
                } else if (videoInfo.getMediatype() == VideoRef.TYPE_VIDEO) {
                    if (this.Ob == 1) {
                        StringBuilder sb3 = StringBuilderOpt.get();
                        sb3.append("brian parse first url, resolution:");
                        sb3.append(q1(this.X3));
                        A4(StringBuilderOpt.release(sb3));
                    }
                    str2 = (String) ((HashMap) this.i4).get(this.X3);
                    if (str2 == null || str2.isEmpty()) {
                        str2 = str;
                    }
                    for (java.util.Map.Entry entry : ((HashMap) this.j4).entrySet()) {
                        if (iIntValue == 0) {
                            try {
                                iIntValue = ((Integer) entry.getKey()).intValue();
                            } catch (Exception e) {
                                if (TTVideoEngineLog.isPredicateLoglevelTurnOn(1)) {
                                    TTVideoEngineLog.d(g(), e.getMessage());
                                }
                            }
                        } else if (iIntValue > ((Integer) entry.getKey()).intValue()) {
                            iIntValue = ((Integer) entry.getKey()).intValue();
                        }
                    }
                    if (iIntValue > 0) {
                        str3 = (String) ((HashMap) this.j4).get(Integer.valueOf(iIntValue));
                        str4 = str3;
                    }
                } else {
                    if (this.e4.getMediatype() == VideoRef.TYPE_AUDIO) {
                        str4 = (String) ((HashMap) this.j4).get(Integer.valueOf(this.e4.getValueInt(3)));
                    }
                    str2 = str;
                }
            } else {
                str2 = str;
            }
            this.O3.P1(str2, str4);
            Qjn qjn = this.O3;
            if (!TextUtils.isEmpty(this.ad)) {
                str2 = this.ad;
            }
            qjn.A0(str2);
            this.ad = null;
        }
        VideoInfo videoInfo2 = this.e4;
        if (videoInfo2 != null) {
            strArrAllVideoURLs = videoInfo2.getValueStrArr(16);
        } else {
            IVideoModel iVideoModel = this.J3;
            if (iVideoModel != null) {
                strArrAllVideoURLs = iVideoModel.allVideoURLs(this.X3, this.o6);
            }
        }
        if (strArrAllVideoURLs != null && strArrAllVideoURLs.length > 0) {
            int iIntValue2 = ((Integer) ((HashMap) this.g4).get(this.X3)).intValue();
            if (iIntValue2 < strArrAllVideoURLs.length) {
                this.O3.l1(strArrAllVideoURLs[iIntValue2]);
                if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
                    TTVideoEngineLog.i(g(), StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "find curUrl:"), strArrAllVideoURLs[iIntValue2])));
                    return;
                }
                return;
            }
            this.O3.l1(str);
            if (!TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
                return;
            }
            TTVideoEngineLog.i(g(), StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "set curUrl:"), str)));
            return;
        }
        this.O3.l1(str);
        if (!TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
            return;
        }
        TTVideoEngineLog.i(g(), StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "set curUrl:"), str)));
    }
