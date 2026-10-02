# First-fatal clusters on the candidate base (U10.1+T8+U11i, bundle 190afedd)

Source: stage-A window 5 runs of all 51 U9 non-lit keys (`sources.json`), `scripts/lab/first_fatal.py` per key, `scripts/lab/cluster_first_cause.py`. Reproduce: `python3 scripts/lab/candidate_first_fatal.py <out>`.

An earlier table from the same day (oc-t4) read run_index rows of another runtime fingerprint and the window/boards layout only; it does not describe the candidate base and is not used.

| group | keys | members |
|---|---|---|
| no-observed-termination | 20 | cv2-ca-vaults-randomlydie, cv2-com-bytehamster-flowitgame, cv2-com-degeder-yam, cv2-com-emmanuelmess-itsdicey, cv2-com-frequent-habits, cv2-com-paultirk-yatoo, cv2-dev-obfusk-jiten-webview, cv2-org-andresoviedo-dddmodel2, cv2-org-secuso-privacyfriendlyyahtzeedicer, cv2-timur-webrtc-check, fd-AppManager, fd-app, fd-mobile, fd-noice, fd-shatteredpixeldungeon, fd-tutanota, fd-uhabits, noice, termux, toutiao |
| signal:signo(6) | 8 | cv2-org-linaro-glmark2, fd-fluffychat, fd-immich, fd-kitchenowl, fd-libre, fd-saber, localsend, subwaysurfers |
| process-disappeared | 6 | burgerking, cv2-com-kaajjo-libresudoku, fd-fennec_fdroid, firefox, ppsspp, vlc |
| java:java.lang.NullPointerException | 6 | cv2-com-nononsenseapps-notepad, cv2-com-trianguloy-clipboardeditor, fd-breezyweather, fd-client, fd-wifianalyzer, mcdonalds |
| java:java.lang.IllegalStateException | 3 | fd-api, fd-plus, x |
| java:java.lang.UnsatisfiedLinkError | 3 | cv2-com-chessclock-android, fd-im-vector-app, mindustry |
| java:[CHILD_CK] J_invokeStaticMain_main_threw | 1 | fd-meet |
| java:java.lang.ClassNotFoundException | 1 | cv2-com-nbossard-packlist |
| java:java.lang.IllegalArgumentException | 1 | fd-musicplayer |
| java:java.lang.UnsupportedOperationException | 1 | cv2-com-stoutner-privacybrowser-standard |
| java:javax.crypto.AEADBadTagException | 1 | cv2-com-lcdcode-moodcairns |
