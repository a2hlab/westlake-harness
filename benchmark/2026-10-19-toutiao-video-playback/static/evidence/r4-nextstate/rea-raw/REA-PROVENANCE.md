# REA raw materials — r4-nextstate (full evidence_ids)
Objects: libttmplayer b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02 ;
APK a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395.
Ghidra image base 0x100000. First R-E PT_LOAD has p_offset==p_vaddr==0, so .text/.rodata file_offset==vaddr==ghidra-0x100000. The RW PT_LOAD has p_offset 0x43d748 / p_vaddr 0x441748 (skew 0x4000); .bss (vaddr 0x4759e0) is SHT_NOBITS => NO file offset.

## libttmplayer (REA Ghidra 12.1.4)
- search_strings "debug.ttplayer.log.enable" -> string @ghidra 0x4c6e03 (vaddr=file 0x3c6e03). evidence_id ev_dbafe43d47cc563ec81a169a27ef2843433710a257af95f97b107d82f13f9376
- xref 0x4c6e03 -> 0x394b00 (adrp/add x0,string; the string-reference site). evidence_id ev_9efe64739d568f0c45ea9d2ec2abacd922d86cbb9d1d4bd73bdafbac252625b9
- resolve_containing_procedure 0x394b00 -> JNI_OnLoad @0x394ac0..0x394e13. evidence_id ev_f6ee059fa8daf4bbc585623411ef27657b06e30c331be8d58edafca4ec24afe0
- procedure_pseudo_code JNI_OnLoad (full body). evidence_id ev_ac375204ad3421e7170189682e725f3a208a772ed31d872aff9d251ef8826c1a ; saved jni_onload.gate-excerpt.txt
  - CORRECTION (outer LLVM, video-r5-provider-readonly/player-onload.txt): the actual bl __system_property_get is at ghidra 0x394b18 (file 0x294b18); 0x394b00 is the add x0,string. True-compare + "log enabled" branch confirmed.
- search_strings "avmdl" -> 0 matches (NOT proof of no indirect/dlsym use). evidence_id ev_fe244c4d21dfca8095561b4970f548cbb4081edde7cba5783ce6af2162396642

## APK DEX (JADX 0.7.1, class_count 139838)
- search_android_classes VideoPlayerImpl. evidence_id ev_e9b8009c36d0d53475786bacbaf6b47835bbd2d9321ca0caffef393925f305f3
- search_android_classes AVMDLDataLoader. evidence_id ev_62f25e0887ff747a14b184e93ae6b8a44665cd038838b4ada6588d7bb647679b
- search_android_classes DataLoaderHelper. evidence_id ev_ece809228a7ef6376259651c16b0aa85b70bc73860cc95a7e740ab8ef8bd59d1
- inspect_android_class DataLoaderHelper (methods -> DataLoaderHelper.methods.txt). evidence_id ev_b74c7e05a19ae565a42025b59b6077853a7e697c55f03e86078134fc2d2e6fd1
- inspect_android_method _supportProxy ov0 (delegates to ov1 after hotfix hook). evidence_id ev_8e1953c0f86507cc1886c97f7da9ecebadada08d74e70eee142c0a341fe3700c
- inspect_android_method _supportProxy ov1 (proxy-eligibility by URL scheme/HLS; NOT the loader-ready gate). evidence_id ev_bf3f098ba1a99cfa372131626edeec07c4adfe4da0d59ae3118917b5e98ff58d
