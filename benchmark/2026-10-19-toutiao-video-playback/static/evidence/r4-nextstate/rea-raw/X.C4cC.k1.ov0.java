// evidence_id: ev_d7753a6a2b63459e300b375ad9f9d41254d465f77b87485325ac410d99ce3e01
// class: X.C4cC  method: k1  descriptor: ()V  overload_count: 1
// provider: JADX headless 0.7.1  APK sha256 a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395
// NOTE: static decompile; display/overload names are engine-local aliases; APK never executed.

    private void k1() throws Throwable {
        String str;
        String str2;
        ChangeQuickRedirect changeQuickRedirect = wd;
        boolean z = false;
        if (changeQuickRedirect != null && DRm.z0(this, changeQuickRedirect, false, 708363).a) {
            return;
        }
        C4cg c4cg = this.j0;
        if (c4cg != null) {
            c4cg.d();
        }
        this.O3.z2(this.a);
        this.O3.t2(this.b);
        if (this.F8 == 0) {
            this.F8 = System.currentTimeMillis();
        }
        if (this.A || this.u || this.c5 != null || this.f5 != null) {
            V0(this.v3);
            if (this.A) {
                str = this.B;
            } else {
                str = this.v;
            }
            a1(str);
            if (this.A) {
                str2 = this.B;
            } else {
                str2 = this.v;
            }
            C1(str2, this.w3);
        } else if (this.F4) {
            long jCurrentTimeMillis = System.currentTimeMillis() / 1000;
            long j = this.G4.mUrlTime;
            if (j > 0 && jCurrentTimeMillis - j > 2400) {
                z = true;
            }
            if (z) {
                M0();
            }
            a1(this.G4.mUrl);
            V0(this.G4.mVideoID);
            C1(this.G4.mUrl, this.w3);
        } else if (this.O4) {
            V0(this.v3);
            a1(this.P4.playURL);
            C1(this.P4.playURL, this.w3);
        } else if (this.N4) {
            V0(this.v3);
            e1(this.J3);
        } else {
            V0(this.v3);
            M0();
        }
        if (this.d == null || !V3()) {
            return;
        }
        setPlayInfo(5, 0L);
    }
