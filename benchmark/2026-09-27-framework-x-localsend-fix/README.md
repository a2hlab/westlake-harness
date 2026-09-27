# 2026-09-27 framework merged fix — X telephony NPE + LocalSend Impeller (#48 horizontal)
Two framework walls fixed with 3 small source edits, all in adapter-runtime-bcp.jar (BCP):
(1) X/Twitter PhoneStateListener NPE — route getService("telephony.registry") to a no-op
ITelephonyRegistry (OHServiceManager + LocalServiceBinders); (2) LocalSend Flutter Impeller first-frame
pc=0 — inject io.flutter.embedding.android.EnableImpeller=false in ApplicationMetaDataReader (→ Skia GL).
Patch: framework-fix.patch. Build env (dspfac bridge-build) inaccessible from my session → source patch
delivered; claude-2 rebuilds (source or smali) + deploys on 5ea34a45 ONLY (not 61b06572 Toutiao). NOTES.md.
