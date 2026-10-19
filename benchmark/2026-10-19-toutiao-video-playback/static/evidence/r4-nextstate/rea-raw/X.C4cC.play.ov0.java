// evidence_id: ev_737cfd1d6d1b8bf0623385e01143462acf2241527b8415d2256b72255cf232e6
// class: X.C4cC  method: play  descriptor: ()V  overload_count: 1
// provider: JADX headless 0.7.1  APK sha256 a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395
// NOTE: static decompile; display/overload names are engine-local aliases; APK never executed.

    @Override // X.MKt
    public void play() throws Throwable {
        ChangeQuickRedirect changeQuickRedirect = wd;
        if (changeQuickRedirect != null && DRm.z0(this, changeQuickRedirect, false, 708323).a) {
            return;
        }
        if (TTVideoEngineLog.isPredicateLoglevelTurnOn(2)) {
            TTVideoEngineLog.i(g(), StringBuilderOpt.releaseLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.appendLogger(StringBuilderOpt.getLogger(), "play:"), this)));
        }
        if (this.k == 5) {
            TTVideoEngineLog.e(g(), "already released, return");
            return;
        }
        Iterator<C4dQ> it = TTVideoEngine.sEngineStateListeners.iterator();
        while (it.hasNext()) {
            it.next().b();
        }
        if (this.ca.c(false)) {
            this.ca.g(1);
        } else {
            c0();
        }
    }
