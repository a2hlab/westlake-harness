# Incremental actual61b full128 evidence archives

Archive only completed stable windows after their after-identity gate passes and the original driver advances. Require no source writer, stable metadata snapshots, before/after file hashes, full tar-member verification and independent remote SHA/size/gzip verification. If stability fails, pause archiving without affecting the runner.

- [Window01](window-01/README.md): durable and verified; no full-round verdict.
- [Window02](window-02/README.md): durable and verified; before_unlock/smoke0, no full-round verdict.

Running later windows are excluded. The final128 aggregate and outer signoff remain separate work. No device calls or running-pin changes occur in this archiving lane.

- [Window-03](window-03/README.md): durable and verified; single-window scope only.
