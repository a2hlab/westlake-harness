# EGL state-machine adversarial review

The original 13 host cases passed, but two displays sharing the same numeric image exposed an early wrong-display rejection: the second valid image could not be destroyed. The real production function failed the independent counterexample (rc -6). The author changed only the search to prefer the full display/image pair; the identical probe then passed all 14 cases against SHA 5bd6686c.

Host seams do not validate the platform resolver, AHardwareBuffer provenance or a deployed display instance. Original failing and corrected sources, fixtures, compiler commands and raw results remain indexed in persistent storage.
