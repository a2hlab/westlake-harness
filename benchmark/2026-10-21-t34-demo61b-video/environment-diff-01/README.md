# T34 environment comparison: a missing equivalence proof, not a cause

T32 really rebooted on5cd and then displayed changing video. Its original preflight boot was13e5b7eb, the recorded `target boot` returned0, and the new boot was e562ad3e. The original video capture receipts match the public image bytes; this reviewer viewed both images (woman presenter, then man/vehicle). The explanation “5cd only worked with a retained old parent” is not supported.

T31 replay02 also had a new candidate boot, c5448a1d→7faf3549; its two cycles were warm reentries within that generation. Later activation independently rebooted8313cbf3→13e5b7eb, but explicitly reused replay02 visual cycles. Its final feed is not a freshly repeated video test.

| Area | Verified comparison / smallest gap |
|---|---|
| Startup script | Full actual5cd run bytes equal W03-b candidate run after only UID20011300→20011206 and WID29→30 substitutions. Equal script/exe is not equal inherited environment or loaded generation. |
| T34 preflight | More than fiveSOs: boot/birth/UID/tracer/private mount/exe/cfg/18controls/HAP/networkcompat, transaction content/private inode relations, OpenSLES/liblog providers. No full BCP/JAR/ART/shared-runtime cross-board check in this executor. |
| BCP and ART | W03-b parent log records private-asx/fw nine-entry BCP and private boot-framework.art. T31 maps show private ART/runtime/HWUI/image paths. Cross-board same-generation SHA/inode binding for these actual loaded objects remains missing; no mismatch is proven. |
| Maps / provider | A physical artifact or matching name does not establish the module that won in a namespace. Keep T31 actual slot evidence scoped to its own generation;61b winner remains unproven where not sampled. |

Minimum follow-up is to consume existing same-generation maps/environment and bind private BCP, ART images and actually loaded shared modules to content hashes. Avoid a broad new experiment merely to check stage files. Do not use system/android snapshot hashes as a substitute for private-asx objects. This review performs no device access and does not diagnose intermittent exits.

## Exact sources

- `$HOME/.local/share/westlake/toutiao-launcher-20261020/preflight-read-01/stdout`: lines 1,10,20,62; SHA256 `333c542e3d06aa97212fdcec20a20ef2283729cc4d959868d1db807182425069`.
- `$HOME/.local/share/westlake/toutiao-launcher-20261020/window-01/reboot-1792495763787840000/argv.json`: lines 5,6; SHA256 `ea05d85f4b391c570f63aee6e06db485104da1f25b63ee900a76e2fca916d8e0`.
- `$HOME/.local/share/westlake/toutiao-launcher-20261020/window-01/reboot-1792495763787840000/rc`; SHA256 `5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9`.
- `$HOME/.local/share/westlake/toutiao-launcher-20261020/window-01/new-boot.json`: lines 2; SHA256 `de214b4e872ce32c4ac8b7dc4fadbbae52ed43f1a2015fb70ac94e2542bf8088`.
- `$HOME/.local/share/westlake/toutiao-launcher-20261020/window-01/final-identity-1792496103834699000/stdout`: lines 13,20,33,26; SHA256 `b11b0048d3253ee47a4139a94ed8b4750b9b63f660de28103b6f30588ff2600a`.
- `benchmark/2026-10-20-t32-host-page-accepted/video-a.jpeg`; SHA256 `0910937370ccafe4ea42f61e423ef037827054336aef5fb41352ead0fa63d4c9`.
- `$HOME/.local/share/westlake/toutiao-launcher-20261020/window-01/capture-1792496005157660000/record.json`: lines 5,9; SHA256 `c12b4d53a8c60d0dc0cebac4e54654b958c9bb2b093a37d0967d5aefb26ab82d`.
- `benchmark/2026-10-20-t32-host-page-accepted/video-b.jpeg`; SHA256 `89364e7b2a6c26f32440c3a62e206dcd4b6a7a53d19206c18da8be1114467ebd`.
- `$HOME/.local/share/westlake/toutiao-launcher-20261020/window-01/capture-1792496043655730000/record.json`: lines 5,9; SHA256 `e11470eb868176aae6fb30a214e4ced811797afee9ecc53b7894601225e6b6e8`.
- `$HOME/.local/share/westlake/toutiao-resume-20261020/t31-replay-02/t31-5cd-window-01/fresh-read/read.stdout`: lines 2; SHA256 `af100711621c4fb44857aa415db80df21588bf7c3b10d7ac63614e8a1beafe08`.
- `$HOME/.local/share/westlake/toutiao-resume-20261020/t31-replay-02/t31-5cd-window-01/candidate-state-read/read.stdout`: lines 2,3; SHA256 `3f4be055a331d299c6803ed7b6a66960e6f685a44476e95e257121833e68dafc`.
- `$HOME/.local/share/westlake/toutiao-resume-20261020/t31-replay-02/t31-5cd-window-01/reboot-1792491368899928000.rc`; SHA256 `5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9`.
- `benchmark/2026-10-20-t31-runtime-peer/replay-02/README.md`: lines 3,3,9,5; SHA256 `8382cc3aeb2f1a4e49b8e839d29f1d46ceaf45e9a85f5dd8242cfc7c7973bf82`.
- `$HOME/.local/share/westlake/toutiao-resume-20261020/t31-activation-01/t31-5cd-window-01/apply/plan.json`: lines 10; SHA256 `b3e6f62697ed571a4707d7f8eacac6ccca2f28318763beec2611f1879064b766`.
- `$HOME/.local/share/westlake/toutiao-resume-20261020/t31-activation-01/t31-5cd-window-01/wait-candidate.stdout`: lines 1; SHA256 `75c56e578e3e737f943ea7da42a3e38e4138c6a2fb1f0d48592449502a7ac66d`.
- `benchmark/2026-10-20-t31-demo-retain/activation-verified/acceptance-addendum.json`: lines 12,3; SHA256 `493f6d3e17fcc6afa9b2c8388ebaafe12931c1444bd5469c0cad468b6000bbbe`.
- `benchmark/2026-10-20-t31-video-seal-final/final-signoff.json`: lines 5,9,240; SHA256 `5052bf3f60dd5a10d1de86b357ddd00369e034d15e80d848677ff1a4b1b08aef`.
- `benchmark/2026-10-21-t34-demo61b-video/deployment/executor61b.py`: lines 245,256,259,299,303,305; SHA256 `d75ecd42714f03b52db167c0978ec14c3ed7bcb5ad7e96c98be0d5b594c7060e`.
- `$HOME/.local/share/westlake/t34-demo61b-video-20261021/W-03-b/supplement/supplement.sh`: lines 37,40,43,46,49,52,34; SHA256 `29789b579d10892392c6992f854626577e822995fddf6eaef1bea940cf62987e`.
- `$HOME/.local/share/westlake/t34-demo61b-video-20261021/W-03-b/pre-rollback/parent.log`: lines 30,121; SHA256 `e79016eff8b6f93d956c447ad9eaedc5628e5d08c5092435a7248c7504984821`.
- `$HOME/.local/share/westlake/t34-demo61b-video-20261021/W-03-b/reboot/02-new-boot.stdout`: lines 1; SHA256 `0a2b131e7c2b25a0769ae8b6ee517f85f69b46e663b7fdef9e0385c16327032b`.
- `$HOME/.local/share/westlake/t34-demo61b-video-20261021/W-03-b/apply/after.run.sh`: lines 9,19,42; SHA256 `8d996f946e36de839280c7524dbb53d0538f922e3d8886a9895f522cac5f4954`.
- `$HOME/.local/share/westlake/toutiao-resume-20261020/t31-activation-01/t31-5cd-window-01/five-slots/maps-before.txt`: lines 4085,4086,4087,4088,5257,5258,5259,5260,38,6486,4884,4885,4886,4887; SHA256 `128c965a0d0bf98b9c564630287c3e1ebdb6c97dd2e2af52d5bf921002a5ac5b`.

The source table and classified differences are machine-readable in `results.json`. No API level, historical acceptance or runtime verdict is upgraded.
