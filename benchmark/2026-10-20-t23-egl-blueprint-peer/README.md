# Minimal EGL reuse blueprint

R77 already solved Android-to-OH client-buffer import and display-owned EGL dispatch. Reuse that path with explicit slot claims and failure ownership, rather than copying its full-table leak, concurrent create race and early destroy release. `blueprint.json` pins source lines and testable invariants.

Exact a11c HWUI has a conditional GL/native-fence path that creates sync, duplicates its fd and destroys sync on one display. The same-implementation duplication shim is therefore a bounded companion to image import; runtime extension state remains unknown. Damage, termination and Vulkan behavior are excluded without evidence of a current path. No build or device operation ran.
