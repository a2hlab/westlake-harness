// evidence_id: ev_a630a4a3874c7cb688ec2c0f24958a3b7c4c47b033e256a9596d3043f8cb848b
// class: X.C4cC  method: O0  descriptor: (Ljava/lang/String;Ljava/util/Map;Ljava/util/List;)Ljava/lang/String;  overload_count: 1
// provider: JADX headless 0.7.1  APK sha256 a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395
// NOTE: static decompile; display/overload names are engine-local aliases; APK never executed.

    /* JADX WARN: Code duplicated, block: B:70:0x0166  */
    /* JADX WARN: Code duplicated, block: B:74:0x0172  */
    /* JADX WARN: Code duplicated, block: B:85:0x0195  */
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
    private String O0(String str, java.util.Map<String, String> map, List<VideoInfo> list) {
        boolean z;
        String strReplaceAll;
        boolean z2;
        boolean z3;
        String host;
        String videoRefStr;
        boolean z4;
        String videoRefStr2;
        int i;
        java.util.Map<String, String> map2 = map;
        ChangeQuickRedirect changeQuickRedirect = wd;
        if (changeQuickRedirect != null) {
            C31U c31uZ0 = DRm.Z0(str, map2, list, this, changeQuickRedirect, false, 708496);
            if (c31uZ0.a) {
                return (String) c31uZ0.b;
            }
        }
        if (this.J0 > 0) {
            if (this.H0.getIntOption(33) == 1) {
                z = true;
            } else {
                z = false;
            }
        } else {
            z = this.Z0;
        }
        if (z && !TextUtils.isEmpty(str) && !str.startsWith("mem://bash") && !str.startsWith("mem://hls")) {
            if (this.Ob == 1) {
                StringBuilder sb = StringBuilderOpt.get();
                sb.append("brian is support bash:");
                sb.append(Y3(this.J3));
                A4(StringBuilderOpt.release(sb));
            }
            if (Y3(this.J3)) {
                if (list != null) {
                    videoRefStr2 = VideoRef.VideoListToBashString(list);
                } else {
                    videoRefStr2 = this.J3.getVideoRefStr(8);
                }
                Object[] objArr = new Object[4];
                objArr[0] = ((HashMap) this.g4).get(this.X3);
                objArr[1] = Integer.valueOf(d(313, this.y6 ? 1 : 0));
                if (this.J3.hasFormat(IVideoModel.Format.DASH)) {
                    i = 1;
                } else {
                    i = 2;
                }
                objArr[2] = Integer.valueOf(i);
                objArr[3] = videoRefStr2.replaceAll("\\\\/", GrsUtils.SEPARATOR);
                strReplaceAll = String.format("mem://bash/url_index:%d/check_hijack:%d/segment_format:%d/%s", objArr);
                z2 = true;
            } else {
                if (d(493, this.b1 ? 1 : 0) == 1) {
                    ChangeQuickRedirect changeQuickRedirect2 = wd;
                    if (changeQuickRedirect2 != null) {
                        C31U c31uN0 = DRm.N0(str, this, changeQuickRedirect2, false, 708601);
                        if (c31uN0.a) {
                            z4 = c31uN0.e;
                        } else if (!TextUtils.isEmpty(str) || !X3(2)) {
                            z4 = false;
                        } else {
                            String lowerCase = str.toLowerCase();
                            if (lowerCase.startsWith("file://") || lowerCase.startsWith(GrsUtils.SEPARATOR) || FormatProvider.FormatProviderHolder.isM3u8(str) || FormatProvider.FormatProviderHolder.isMpd(str)) {
                                z4 = false;
                            } else {
                                z4 = true;
                            }
                        }
                    } else if (!TextUtils.isEmpty(str)) {
                        z4 = false;
                    } else {
                        z4 = false;
                    }
                    if (z4) {
                        strReplaceAll = String.format("mem://bash/url_index:0/segment_format:%d/{\"dynamic_video\":{\"dynamic_video_list\":[{\"main_url\":\"%s\"}]}}", 2, str);
                    } else {
                        strReplaceAll = str;
                    }
                } else {
                    strReplaceAll = str;
                }
                z2 = false;
            }
        } else {
            strReplaceAll = str;
            z2 = false;
        }
        if (this.J0 > 0) {
            if (this.H0.getIntOption(671) == 1) {
                z3 = true;
            } else {
                z3 = false;
            }
        } else {
            z3 = this.a1;
        }
        if (z3 && !TextUtils.isEmpty(strReplaceAll) && !strReplaceAll.startsWith("mem://bash") && !strReplaceAll.startsWith("mem://hls") && Z3(this.J3)) {
            if (list != null) {
                videoRefStr = VideoRef.VideoListToBashString(list);
            } else {
                videoRefStr = this.J3.getVideoRefStr(8);
            }
            strReplaceAll = String.format("mem://hls/url_index:%d/%s", ((HashMap) this.g4).get(this.X3), videoRefStr.replaceAll("\\\\/", GrsUtils.SEPARATOR));
            z2 = true;
        }
        if (z2 && !TextUtils.isEmpty(strReplaceAll) && map2 != null && map2.containsKey(HttpHeaders.HOST)) {
            String string = map2.get(HttpHeaders.HOST).toString();
            try {
                host = new java.net.URI(str).getHost();
            } catch (URISyntaxException e) {
                if (TTVideoEngineLog.isPredicateLoglevelTurnOn(1)) {
                    TTVideoEngineLog.d(e);
                }
                host = null;
            }
            if (!TextUtils.isEmpty(string) && !TextUtils.isEmpty(host)) {
                strReplaceAll = strReplaceAll.replaceAll(string.trim(), host);
            }
        }
        if (d(302, this.w1) == 1) {
            if (map2 == null) {
                map2 = new HashMap<>();
            }
            map2.remove("X-Tt-CDN");
            map2.put("X-Tt-CDN", "0");
        }
        this.O3.A1(strReplaceAll.startsWith("mem://bash") ? 1 : 0);
        return strReplaceAll;
    }
