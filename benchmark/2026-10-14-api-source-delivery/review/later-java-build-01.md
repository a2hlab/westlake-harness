# New later-adapter Java build

The delivered later source now has a real **exit-code 0** compilation: **83 production Java inputs → 160 owned classes**, using the retained source compiler and hash-verified core/framework/extension prerequisites. The class JAR is 394,578 bytes, SHA-256 `f89e80256cbb174ef9ea81b10defc868892b7ad8cf7a230c0af0a17128511c6f`. JDK tree verification matches the supplied lock.

This is a new isolated build. It does not claim a historical r84–r89 build receipt, a byte-identical historical runtime, or a deployable DEX/boot image. The other delivered Java units are mainline stubs outside this seven-component compiler's input set. No device was accessed. The original source-delivery manifest and report remain unchanged; this later evidence supplements them.

All 168 raw output/log/receipt/class files are durably retained in the archive pinned by `later-java-build-01-archive.json`; before/after source SHA and metadata, tar contents, remote SHA/size and gzip validation all match. `later-java-build-01.json` maps original source inputs, prerequisite report hashes, output and raw-log pins.
