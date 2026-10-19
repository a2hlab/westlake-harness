// evidence_id: ev_7753ef974104fd7a7d1a90f3d8382e8864fafda4b61cc88ae6aedde963e662cc
// class: X.C4cC  method: c0  descriptor: ()V  overload_count: 1
// provider: JADX headless 0.7.1  APK sha256 a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395
// NOTE: static decompile; display/overload names are engine-local aliases; APK never executed.

    public void c0() throws Throwable {
        ChangeQuickRedirect changeQuickRedirect = wd;
        if (changeQuickRedirect != null && DRm.z0(this, changeQuickRedirect, false, 708326).a) {
            return;
        }
        S0();
        boolean z = true;
        this.H = true;
        this.I = false;
        this.f1133J = false;
        this.U = 0;
        IVideoModel iVideoModel = this.J3;
        if (iVideoModel != null) {
            iVideoModel.setUpResolution(this.o5);
        }
        if (this.O) {
            this.O3.setIntOption(14, 1);
            this.O = false;
        }
        C3ew.b().a(this.Uc);
        if (!this.n0 && this.R <= 0 && !this.M) {
            z = false;
        }
        h1(z);
        this.V = false;
    }
