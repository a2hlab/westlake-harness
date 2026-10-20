# W04 later after-close image

This is a separate observation after the reviewed restoration and unlock, not a replacement for the original gray t30 image. Independent viewing of the unchanged [later snapshot](after-close-gray.jpeg), whose status bar reads 04:21, still shows an empty gray content area without feed or video.

Both boot reads equal `80b23c89-01e7-4865-88c7-b8b75e0b4a83`. The actual four argv/rc receipts cover boot read, snapshot, receive and boot read; each process rc is 0, with empty stderr. Snapshot success is explicit in stdout. The image is 39,973 bytes, SHA-256 `a3691399dd3ac2ca5b52a55176cbc1f4231934a08659ce3348bac8cd047dde0d`. No click, wake or launch appears in this receipt set.

`results.json` pins all 17 original receipt/image inputs under a private alias. No previous W04 record or API proposal was changed. This does not attribute the gray screen to the candidate or baseline, and does not establish a successful UI recovery. The peer only read local files.
