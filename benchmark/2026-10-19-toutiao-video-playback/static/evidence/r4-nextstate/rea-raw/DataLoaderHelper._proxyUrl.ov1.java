    public String _proxyUrl(String str, String str2, long j, String[] strArr, Resolution resolution, String str3, VideoInfo videoInfo, String str4, String str5, boolean z, boolean z2, String str6, long j2, String[] strArr2, int i, String str7, boolean z3, int i2, int i3) {
        int i4;
        boolean z4;
        int i5;
        boolean z5;
        boolean z6;
        boolean zD;
        int i6;
        boolean z7 = z;
        ChangeQuickRedirect changeQuickRedirect2 = changeQuickRedirect;
        if (changeQuickRedirect2 != null) {
            i4 = i3;
            C31U c31uR1 = DRm.R1(new Object[]{str, str2, new Long(j), strArr, resolution, str3, videoInfo, str4, str5, new Byte(z7 ? (byte) 1 : (byte) 0), new Byte(z2 ? (byte) 1 : (byte) 0), str6, new Long(j2), strArr2, new Integer(i), str7, new Byte(z3 ? (byte) 1 : (byte) 0), new Integer(i2), new Integer(i4)}, this, changeQuickRedirect2, false, 707209);
            if (c31uR1.a) {
                return (String) c31uR1.b;
            }
        } else {
            i4 = i3;
        }
        if (this.mState != 0) {
            this.mInvalidCode = IVideoEventLogger.MdlInvalidCode.StateError.ordinal();
            return null;
        }
        if (TextUtils.isEmpty(str) || strArr == null || strArr.length < 1) {
            this.mInvalidCode = IVideoEventLogger.MdlInvalidCode.ParamsWrong.ordinal();
            return null;
        }
        String[] strArr3 = (String[]) strArr.clone();
        for (int i7 = 0; i7 < strArr3.length; i7++) {
            if (!_supportProxy(strArr3[i7], i4)) {
                this.mInvalidCode = IVideoEventLogger.MdlInvalidCode.ProxyNotSupport.ordinal();
                TTVideoEngineLog.d("DataLoaderHelper", "not support");
                return strArr3[i7];
            }
        }
        if (this.mInnerDataLoader == null) {
            TTVideoEngineLog.e("DataLoaderHelper", "start mdl first");
            this.mInvalidCode = IVideoEventLogger.MdlInvalidCode.StateError.ordinal();
            return null;
        }
        if (this.mEnableHls == 1) {
            if (z2 || FormatProvider.FormatProviderHolder.isM3u8(strArr3[0])) {
                z4 = true;
            } else {
                z4 = false;
            }
            if (z4) {
                z7 = true;
            }
        } else {
            z4 = false;
        }
        this.mInvalidCode = IVideoEventLogger.MdlInvalidCode.StateError.ordinal();
        this.mLock.c(1);
        try {
            String localAddr = "";
            if (this.mCloseLocalServer) {
                if (!this.mInnerDataLoader.isRunning()) {
                    TTVideoEngineLog.e("DataLoaderHelper", "dataloader is not running");
                    this.mLock.f(1);
                    return null;
                }
            } else {
                localAddr = this.mInnerDataLoader.getLocalAddr();
                if (TextUtils.isEmpty(localAddr)) {
                    TTVideoEngineLog.e("DataLoaderHelper", "local host error");
                    this.mLock.f(1);
                    return null;
                }
            }
            if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
                TTVideoEngineLog.i("DataLoaderHelper", StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "proxy url, mInvalidMdlProcotol: "), this.mInvalidMdlProcotol)));
            }
            boolean z8 = this.mEnableMdlProtocol;
            if (!this.mCloseLocalServer && this.mForbidNativeMDLForOriUrl && !TTHelper.isTranscodeUrlList(strArr3)) {
                TTVideoEngineLog.i("DataLoaderHelper", "url not transcode, not use native mdl");
                z8 = false;
            }
            if (z7 || this.mInvalidMdlProcotol || !z8) {
                z5 = true;
            } else {
                z5 = false;
            }
            if (this.mCloseLocalServer && z5) {
                TTVideoEngineLog.e("DataLoaderHelper", "use local server but local server closed");
                this.mLock.f(1);
                return null;
            }
            String strProxyQuery = proxyQuery(str, str2, 0L, j, strArr3, str4, str5, z4, str6, i, i2);
            if (TextUtils.isEmpty(strProxyQuery)) {
                this.mLock.f(1);
                return null;
            }
            i5 = 1;
            try {
                StringBuffer stringBuffer = new StringBuffer();
                int i8 = this.mMdlDataSourceId;
                this.mMdlDataSourceId = i8 + 1;
                if (this.mEnableHLSProxy == 1 && ((i6 = this.mEnableCheckHLSProxyVVCtrl) == 0 || (i6 == 1 && i3 == 1))) {
                    z6 = true;
                } else {
                    z6 = false;
                }
                if (z4 && z6) {
                    zD = this.mDataLoaderHelperAdapter.d(stringBuffer);
                } else {
                    zD = false;
                }
                if (z5) {
                    stringBuffer.append("http://");
                    stringBuffer.append(localAddr);
                    stringBuffer.append(GrsUtils.SEPARATOR);
                    stringBuffer.append(i8);
                } else {
                    stringBuffer.append("mdl://");
                    stringBuffer.append("id");
                    stringBuffer.append(i8);
                    stringBuffer.append(GrsUtils.SEPARATOR);
                }
                stringBuffer.append(strProxyQuery);
                StringBuffer stringBuffer2 = new StringBuffer();
                stringBuffer2.append(strProxyQuery);
                String auth = this.mInnerDataLoader.getAuth(strProxyQuery);
                if (!TextUtils.isEmpty(auth)) {
                    stringBuffer.append("&ah=");
                    stringBuffer.append(auth);
                    stringBuffer2.append("&ah=");
                }
                if (zD) {
                    NrF nrF = new NrF();
                    if (videoInfo == null) {
                        if (strArr2 != null) {
                            nrF.a = strArr2;
                        }
                    } else {
                        nrF.a = videoInfo.mURLExpires;
                    }
                    nrF.b = str7;
                    nrF.c = z3;
                    String strA = nrF.a();
                    if (!TextUtils.isEmpty(strA)) {
                        stringBuffer.append("&hlsproxyQuery=");
                        stringBuffer.append(strA);
                    }
                }
                String string = stringBuffer.toString();
                if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
                    TTVideoEngineLog.i("DataLoaderHelper", StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "_proxyUrl: "), string)));
                }
                this.mLock.f(1);
                Nr6 nr6H = this.mAllPlayTasks.h(str2);
                if (nr6H == null) {
                    nr6H = new Nr6();
                }
                NrB nrBB = nr6H.b(str);
                if (nrBB != null) {
                    nrBB.a = str;
                    nr6H.a = str2;
                    nrBB.b = string;
                    nrBB.c = resolution;
                    nrBB.d = str3;
                    nrBB.e = videoInfo;
                    nrBB.f = strArr3;
                    nrBB.n = str4;
                    nrBB.h = str5;
                    nrBB.g = strArr2;
                    this.mAllPlayTasks.d(nr6H);
                }
                this.mInvalidCode = IVideoEventLogger.MdlInvalidCode.None.ordinal();
                return string;
            } catch (Throwable th) {
                th = th;
                this.mLock.f(i5);
                throw th;
            }
        } catch (Throwable th2) {
            th = th2;
            i5 = 1;
        }
    }
