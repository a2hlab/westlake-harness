from pathlib import Path
p=Path.home()/'a2hlab/ws/westlake-touchfix/framework/window/jni/oh_input_bridge.cpp'
s=p.read_text()
start=s.index('// dispatchTouchViaViewRoot — direct in-process touch dispatch')
end=s.index('// ============================================================\n// dispatchSingleTouchViaViewRoot',start)
b=s[start:end]
old='''// Touch DOES reach the bridge (OnInputEvent(PointerEvent) fires), but the
// InputChannel MOTION path (injectTouchEvent → consumer worker) doesn't land
// on the deployed runtime — same as keys. So we build the MotionEvent here and
// dispatch it straight into the focused ViewRootImpl (bypassing the channel),
// the proven path from dispatchKeyViaViewRoot. Enables tap/click: nav-tab
// switching, sound play/info/volume buttons, etc.'''
new='''// Route a display-space tap to the eligible Android window and pass its
// window-local coordinates to the in-process dispatch path. The deployed
// runtime cannot rely on InputChannel delivery for this control channel.'''
assert b.count(old)==1
b=b.replace(old,new)
old='''    // Act on ACTION_UP: synthesize a DOWN -> (delay) -> UP tap dispatched to the
    // focused decor view ON THE UI THREAD via noice's OHTouchInjector helper
    // (loaded through the app classloader — no boot-image change needed). The
    // bridge builds the events + paces DOWN/UP (so RecyclerView CheckForTap sets
    // PREPRESSED and the UP performClick()s); the helper does the main-Looper post.'''
new='''    // On ACTION_UP, synthesize a paced DOWN/UP on the selected root. The
    // explicit click action uses the main MessageQueue's hit-tested callback.'''
assert b.count(old)==1
b=b.replace(old,new)
assert b.count('    // --- find focused decor view (mView) ---')==2
b=b.replace('    // --- find focused decor view (mView) ---','    // --- choose a touchable root covering the display-space point ---')
s=s[:start]+b+s[end:]
start=s.index('int32_t OHInputBridge::dispatchSingleTouchViaViewRoot(')
end=s.index('// ============================================================',start)
b=s[start:end]
assert b.count('    // --- focused decor view (same resolution as dispatchTouchViaViewRoot) ---')==1
b=b.replace('    // --- focused decor view (same resolution as dispatchTouchViaViewRoot) ---','    // --- same screen-frame hit test as click and synthetic drag ---')
s=s[:start]+b+s[end:]
p.write_text(s)
