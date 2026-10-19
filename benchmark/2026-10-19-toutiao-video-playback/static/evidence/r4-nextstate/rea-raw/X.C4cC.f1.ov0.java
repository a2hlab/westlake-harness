// evidence_id: ev_a8556c9d54c6f3a91c7e755b37e53a20dce4ed9be56e1703fa85854ee8d7eb9b
// class: X.C4cC  method: f1  descriptor: (Lcom/ss/ttvideoengine/model/IVideoModel;Lcom/ss/ttvideoengine/utils/Error;)V  overload_count: 1
// provider: JADX headless 0.7.1  APK sha256 a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395
// NOTE: static decompile; display/overload names are engine-local aliases; APK never executed.

    private void f1(IVideoModel iVideoModel, Error error) throws Throwable {
        ChangeQuickRedirect changeQuickRedirect = wd;
        if (changeQuickRedirect != null && DRm.V0(iVideoModel, error, this, changeQuickRedirect, false, 708300).a) {
            return;
        }
        if (this.ca.c(false)) {
            this.ca.j(301, 0, 0, iVideoModel, error);
        } else {
            a0(iVideoModel, error);
        }
    }
