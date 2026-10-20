# T34 61b intake — public alias / SHA list (token T34-INTAKE-READY)

Board 61b `61b0657200000000000000000324012c` · boot `3394710e-965c-47cc-a9f5-2b06f3d6c3f1` ·
uid/gid 20011206 · token 537243994 · vc2 · power 30000/86400000 · debug false.

## Installed host HAP (ACTUAL on-board)
| alias | sha256 | bytes | note |
|---|---|---|---|
| entry.hap (current) | b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0 | 54215 | b189 = T33 successful same-sign retained baseline (not a contradiction of T33's earlier df385638 before-image) |

## Runtime before-image (6 objects — all match T33 reference.json except run.sh which is WID-rewritten)
| alias | sha256 | bytes | matches reference |
|---|---|---|---|
| run.sh | 6afd6fba3d0b34165a49f176a4dacecfbdc344bde54daa455ea9718b7206484f | 2863 | NO — ≠ d3518cef (ref) ≠ 5a3aef63 (T30-before); current WID30 single-field rewrite |
| bridge liboh_adapter_bridge.so | d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b | 2015744 | yes |
| mffmpeg libmffmpeg.so | fecf91e1fcda600661f501ce76a97456ad7e330b584013f2b742afb680b337c9 | 4870376 | yes |
| ttmplayer libttmplayer.so | b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02 | 4662040 | yes |
| shim libwebview_bionic_shim.so | 85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a | 51816 | yes |
| cfg 01_westlake_u13_toutiao.cfg | 91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e | 977 | yes |
| libopensles_android_compat.so | (absent) | — | compat absent (confirmed both paths) |

## Runtime identity (processes)
| role | pid | ppid | uid | exe | exe sha256 | mnt ns | WID |
|---|---|---|---|---|---|---|---|
| parent appspawn-x | 5066 | 1 | 0 | /data/local/tmp/asx/appspawn-x | a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c | 4026532996 | — |
| host imehost | 4859 | 395 | 20011206 | /system/bin/appspawn | bf8ddab28302302242b9c2014aea11717c0d55c62fc526339dce6959f007b32c | 4026532969 | 30 (imehost0) |
| child article.news | 7039 | 5066 | 20011206 | /data/local/tmp/asx/appspawn-x | a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c | 4026532996 | 32 |

## Guardian 18 controls
All 18 SHA match T33 reference.json (receipt `17-guardian18-sha`).

## Candidate video targets (recorded only; T30 final-01; 5cd params NOT applied)
bridge→b0e5602a · shim→7f8d75bb · mffmpeg→d2882303 · ttmplayer→0b4d95c5 · compat add→6e83e924 · run.sh 11d3d671 = **5cd REFERENCE, NOT 61b after** (61b new run.sh is cx-derived per board (WID30) then pinned)

## 5cd cross-board reference (read-only, identity only)
uid 20011300 · token 537137511 · vc2 — distinct board identity, not applied to 61b.

Receipts (raw argv/stdout/stderr/rc + recv before-image): `$HOME/.local/share/westlake/t34-demo61b-video-20261021/intake-01/`.
Transport errors: 0. Read-only: no lock, no device write, no install/reboot/perm, no REA, no 5ea, no user data.

## Supplement-01 (via cx render_supplement.py; one read-only exec, guards passed)
generated shell sha256 `04b176d3f2ae5158bdfd647ac22beb70a2b8aa285997688c6aae29cab04aa391` · exec rc 0 · receipts `$HOME/.local/share/westlake/t34-demo61b-video-20261021/supplement-01/`

| provider lib | sha256 |
|---|---|
| /system/lib64/libOpenSLES.so (compat absent → system stack) | 05d8ac90dbced47c8b47275a5d978bc922d4d8f6f84cd3df1b456633ae6d1100 |
| <rt>/liblog.so | d8ad176b41b820a4868b74394188429ad2dc69025661d320d0986dd713048ca4 |
| <rt>/libandroid_native_network_compat.so | f6c354d1513071533fddcc91749f44e57a626177a584fb1bb9f48bf6446ef01e |

physical == parent-private: every object's dev:inode AND sha256 equal between physical RT and the /data/local/tmp/asx bind view (/proc/5066/root/...) → no overlay/bind content divergence → migration must use **atomic rename, not in-place**. WL_PARENT_ID(parent environ)=30; parent mnt ns 4026532996; debug.ttplayer.log.enable unset.

## Sharing (exact RT mount ownership; coverage bounded)
Grepping the EXACT `org.westlake.imehost/files/a2hlab-source-c91d26bf` across captured mountinfo:
imehost RT mounted ONLY in parent 5066 + child 7039 (app mnt ns 4026532996, 4 identical rows each); init/appspawn/sceneboard/nwebspawn/host = 0. **No cross-process / other-app RT sharing** within coverage {init,appspawn,sceneboard,nwebspawn,host,parent,child}. (A generic `a2hlab` match hits a *different* app `com.a2hlab.bridge.zigzag`; that is not the imehost RT. distinct-inode only proved intra-list distinctness — this exact-RT ownership check is the sharing proof.) In-ns binds: RT/private-tmp→/data/local/tmp, RT→/data/local/tmp/asx, RT/app-data→/data/data, RT/i18n/etc/icu→/system/usr/icu.
