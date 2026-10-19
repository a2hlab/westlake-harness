    private boolean _supportProxy(String str, int i) {
        boolean z;
        boolean z2;
        int i2;
        ChangeQuickRedirect changeQuickRedirect2 = changeQuickRedirect;
        if (changeQuickRedirect2 != null) {
            C31U c31uM0 = DRm.m0(str, i, this, changeQuickRedirect2, false, 707201);
            if (c31uM0.a) {
                return c31uM0.e;
            }
        }
        if (TextUtils.isEmpty(str)) {
            return false;
        }
        String lowerCase = str.toLowerCase();
        if (lowerCase.startsWith("mdl://") || lowerCase.startsWith("http://127.0.0.1") || lowerCase.startsWith("http://localhost") || lowerCase.startsWith("file://") || lowerCase.startsWith(GrsUtils.SEPARATOR) || FormatProvider.FormatProviderHolder.isMpd(str)) {
            return false;
        }
        if (this.mEnableHLSProxy == 1 && ((i2 = this.mEnableCheckHLSProxyVVCtrl) == 0 || (i2 == 1 && i == 1))) {
            z = true;
        } else {
            z = false;
        }
        if (this.mEnableHls == 1 && (this.mSupportHls || (z && this.mHLSProxyValid))) {
            z2 = true;
        } else {
            z2 = false;
        }
        if (!z2 && FormatProvider.FormatProviderHolder.isM3u8(str)) {
            return false;
        }
        return true;
    }
