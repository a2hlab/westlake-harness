// evidence_id: ev_efcf8453f69584e8f9dcaf9304869730f5f44d303dc5f233f562233c8a86d2c6
// class: X.C4cC  method: C1  descriptor: (Ljava/lang/String;Ljava/util/Map;)V  overload_count: 1
// provider: JADX headless 0.7.1  APK sha256 a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395
// NOTE: static decompile; display/overload names are engine-local aliases; APK never executed.

    /* JADX WARN: Code duplicated, block: B:18:0x004b  */
    /* JADX WARN: Multi-variable type inference failed */
    /* JADX WARN: Type inference failed for: r3v2, types: [boolean, int] */
    /* JADX WARN: Type inference failed for: r3v5 */
    /* JADX WARN: Type inference failed for: r3v6 */
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
    private void C1(String str, java.util.Map<String, String> map) throws Throwable {
        ?? IsMpd;
        ChangeQuickRedirect changeQuickRedirect = wd;
        if (changeQuickRedirect != null && DRm.V0(str, map, this, changeQuickRedirect, false, 708519).a) {
            return;
        }
        C4d6 c4d6 = this.P7;
        c4d6.a = str;
        c4d6.c = false;
        ChangeQuickRedirect changeQuickRedirect2 = wd;
        if (changeQuickRedirect2 != null) {
            C31U c31uN0 = DRm.N0(str, this, changeQuickRedirect2, false, 708604);
            if (c31uN0.a) {
                IsMpd = c31uN0.e;
            } else {
                IsMpd = FormatProvider.FormatProviderHolder.isMpd(str);
            }
        } else {
            IsMpd = FormatProvider.FormatProviderHolder.isMpd(str);
        }
        this.c1 = IsMpd;
        this.Y0 = IsMpd;
        this.H0.setIntOption(17, IsMpd);
        if (O1(true) || this.A) {
            i1(str, map);
            return;
        }
        if (TTHelper.isIP(str)) {
            i1(str, map);
            return;
        }
        if (str.indexOf("http") == 0) {
            ((HashMap) this.h4).put(this.P7.a, new C4d2(this, "", "", d(18, this.g5 ? 1 : 0), d(403, this.u6 ? 1 : 0), "single"));
            N1();
            d1(str);
            return;
        }
        i1(str, map);
    }
