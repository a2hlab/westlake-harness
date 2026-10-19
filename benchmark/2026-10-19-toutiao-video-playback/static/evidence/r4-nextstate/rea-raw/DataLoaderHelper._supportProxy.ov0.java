    private boolean _supportProxy(String str) {
        ChangeQuickRedirect changeQuickRedirect2 = changeQuickRedirect;
        if (changeQuickRedirect2 != null) {
            C31U c31uN0 = DRm.N0(str, this, changeQuickRedirect2, false, 707306);
            if (c31uN0.a) {
                return c31uN0.e;
            }
        }
        return _supportProxy(str, 0);
    }
