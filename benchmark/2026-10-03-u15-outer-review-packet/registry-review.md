# Strict finding rebinding

204 mapped rows: **198 strictly equal / 6 different / 0 new / 0 unmapped**.
N1: 93 equal, 6 source-line shifts. N2: 105 equal, 0 differences.
Only issue_id/disposition/exception envelopes are removed. Manifest/input identities are compared separately. All actual finding fields, trace entries, line numbers and sequence remain in the comparison; issue IDs are independently recomputed.

The previous auto-identical helper drops numeric `line` and `sequence` recursively. That result does not satisfy this task's strict field equality. Six rows require explicit outer review; no exception row is applied here.

| Old ID | New ID | Actual changed fields |
|---|---|---|
| `02609461c1cec14eb98c7a763ab969b8db681683c6f68b7cc706be8923198a9c` | `d4b0f9dfaf26d2590d47be8b358aaf6bb213816afab362d3d84fdca71a1b43e3` | /detail/evidence/line: 660→665 |
| `2406badd0085d125fb7da20b3870711b0e20c2958f5d74d88d6c60716b958e65` | `36b907e0f15acf49fd2312ec95ee192ce22810aafa6cd35aa60a37bb13a1fd3f` | /detail/evidence/line: 103→111; /detail/trace/1/line: 549→557; /detail/trace/2/line: 133→141; /detail/trace/3/line: 103→111 |
| `92a07939e55ec5be01a438621b2b910973a113466d019abeb67b31f72361a720` | `220c7833b8d2fd76e35cd90b591aaa30c1cef6a8f23c74c6608bf90a1fc71628` | /detail/evidence/line: 105→113; /detail/trace/1/line: 549→557; /detail/trace/2/line: 133→141; /detail/trace/3/line: 105→113 |
| `294a52bcfee895a7a0c3fceed9f75bdb852cbf832fb2e60b0bda0517bc293c50` | `368d2818f26b9d1ab4c09415fb0562a97ef2b3a155aa6037f3afce97f32b6258` | /detail/evidence/line: 109→117; /detail/trace/1/line: 549→557; /detail/trace/2/line: 133→141; /detail/trace/3/line: 109→117 |
| `ff71f96fb7b31cc771196c23ab67bec89468bc97b3efcd6da81d31164699ae3d` | `919a67047b5aae5f0b2aaf82aa9c44fc7fea9811bee61c496f30d0bdbc658d88` | /detail/evidence/line: 113→121; /detail/trace/1/line: 549→557; /detail/trace/2/line: 133→141; /detail/trace/3/line: 113→121 |
| `f83a5797597324fea8c8a19ff6487727bd8dec0e2d449eb3a03958313f942df3` | `95212639ed26d437c985e0edd2e118944f1ecd3ea19be46ef9015c460cbc217a` | /detail/evidence/line: 117→125; /detail/trace/1/line: 549→557; /detail/trace/2/line: 133→141; /detail/trace/3/line: 117→125 |

Host main/plugin_handle: frozen n4-host.c line660→665. Five EGL cache findings: frozen egl.cpp evidence lines103/105/109/113/117→111/113/117/121/125; their registration trace549→557 and nativeClassInit133→141. Every old/new cited line was read from its SHA-checked scan-manifest source and matched exact text (`evidence_source_proofs`). Text, namespace, library, reason, source identity and sequence are unchanged; line differences remain differences.

`registry-comparison.json` retains all 204 complete old/new findings and named-field proofs. Missing N2 function/evidence fields are explicitly absent, not invented as source proof. `registry-mapping.csv` is the complete ID mapping. `changed-findings.json` isolates all six rows and every changed trace line.
