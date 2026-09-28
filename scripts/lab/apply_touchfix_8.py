from pathlib import Path

source = Path('/home/zhaoyue/a2hlab/ws/westlake-touchfix/framework/window/jni/oh_input_bridge.cpp')
s = source.read_text()
needle = '\n\nOHInputBridge& OHInputBridge::getInstance() {'
helper = '''

// The Android session gives ViewRootImpl a screen-space frame. OH WindowSessionAdapter
// places a dialog at that frame and moves its SurfaceControl there; the input channel
// still receives display-space touch coordinates. Hit-test in screen space, then
// translate only the selected root's automatic input into its local View coordinates.
// mRoots is ordered bottom to top. A newer hit wins even if an older Activity has
// focus; focus only breaks a tie at the same stacking position.
static int wl_touch_target_priority(JNIEnv* env, jobject vri, jobject view,
                                    jclass vriCls, jclass viewCls, int wantedRoot,
                                    jint rootIndex, float screenX, float screenY,
                                    float* originX, float* originY) {
    *originX = 0.0f;
    *originY = 0.0f;
    if (wantedRoot >= 0) {
        // rN is a diagnostic root-local override, preserving its old coordinates.
        return rootIndex == wantedRoot ? INT_MAX : 0;
    }
    jmethodID widthM = env->GetMethodID(viewCls, "getWidth", "()I");
    jmethodID heightM = env->GetMethodID(viewCls, "getHeight", "()I");
    jmethodID shownM = env->GetMethodID(viewCls, "isShown", "()Z");
    if (!widthM || !heightM || !shownM || env->ExceptionCheck()) {
        env->ExceptionClear();
        return 0;
    }
    const jint width = env->CallIntMethod(view, widthM);
    const jint height = env->CallIntMethod(view, heightM);
    const jboolean shown = env->CallBooleanMethod(view, shownM);
    if (env->ExceptionCheck()) { env->ExceptionClear(); return 0; }
    if (width <= 0 || height <= 0 || !shown) return 0;

    jfieldID frameF = env->GetFieldID(vriCls, "mWinFrame", "Landroid/graphics/Rect;");
    jclass rectCls = env->FindClass("android/graphics/Rect");
    if (!frameF || !rectCls || env->ExceptionCheck()) {
        env->ExceptionClear();
        return 0;
    }
    jfieldID leftF = env->GetFieldID(rectCls, "left", "I");
    jfieldID topF = env->GetFieldID(rectCls, "top", "I");
    jfieldID rightF = env->GetFieldID(rectCls, "right", "I");
    jfieldID bottomF = env->GetFieldID(rectCls, "bottom", "I");
    if (!leftF || !topF || !rightF || !bottomF || env->ExceptionCheck()) {
        env->ExceptionClear();
        env->DeleteLocalRef(rectCls);
        return 0;
    }
    jobject frame = env->GetObjectField(vri, frameF);
    if (!frame || env->ExceptionCheck()) {
        env->ExceptionClear();
        if (frame) env->DeleteLocalRef(frame);
        env->DeleteLocalRef(rectCls);
        return 0;
    }
    const jint left = env->GetIntField(frame, leftF);
    const jint top = env->GetIntField(frame, topF);
    const jint right = env->GetIntField(frame, rightF);
    const jint bottom = env->GetIntField(frame, bottomF);
    env->DeleteLocalRef(frame);
    env->DeleteLocalRef(rectCls);
    if (env->ExceptionCheck()) { env->ExceptionClear(); return 0; }
    if (right <= left || bottom <= top || screenX < left || screenX >= right ||
        screenY < top || screenY >= bottom) return 0;
    *originX = static_cast<float>(left);
    *originY = static_cast<float>(top);
    jmethodID focusM = env->GetMethodID(viewCls, "hasWindowFocus", "()Z");
    const jboolean focused = focusM ? env->CallBooleanMethod(view, focusM) : JNI_FALSE;
    if (env->ExceptionCheck()) { env->ExceptionClear(); }
    return static_cast<int>(rootIndex) * 2 + 1 + (focused ? 1 : 0);
}
'''
assert s.count(needle) == 1
s = s.replace(needle, helper + needle)
s = s.replace('#include <cstdarg>\n', '#include <cstdarg>\n#include <climits>\n', 1)

# Touch, drag, and one-event stream all use the same hit test. Key and character
# dispatch keep their focus routing because they have no screen coordinate.
start = s.index('int32_t OHInputBridge::dispatchTouchViaViewRoot(')
end = s.index('// ============================================================\n// dispatchDragViaViewRoot', start)
block = s[start:end]
block = block.replace('    int chosenPriority = 0;\n', '    int chosenPriority = 0;\n    float chosenOriginX = 0.f, chosenOriginY = 0.f;\n', 1)
old = '''            const int priority = wl_root_target_priority(
                env, view, viewCls, hasFocusM, want, i);
            if (priority > 0 && priority >= chosenPriority) {'''
new = '''            float originX = 0.f, originY = 0.f;
            const int priority = wl_touch_target_priority(
                env, vri, view, vriCls, viewCls, want, i, x, y,
                &originX, &originY);
            if (priority > 0 && priority >= chosenPriority) {
                chosenOriginX = originX;
                chosenOriginY = originY;'''
assert block.count(old) == 1
block = block.replace(old, new)
block = block.replace('    if (!decorView) { decorView = fallbackView; vriMatch = vriFallback; chosenRoot = fallbackIdx; }\n',
                      '    if (!decorView && fallbackView) { env->DeleteGlobalRef(fallbackView); env->DeleteGlobalRef(vriFallback); }\n', 1)
block = block.replace('    if (!decorView) return fail("no decorView");\n',
                      '    if (!decorView) return fail("no root contains touch point");\n', 1)
anchor = '''    LOGI("dispatchTouchViaViewRoot: chose root[%d] of %d (g_rootIndex=%d)",
         chosenRoot, (int)nn, g_rootIndex.load());'''
assert block.count(anchor) == 1
block = block.replace(anchor, '''    LOGI("dispatchTouchViaViewRoot: root[%d] screen=(%.1f,%.1f) origin=(%.1f,%.1f)",
         chosenRoot, (double)x, (double)y,
         (double)chosenOriginX, (double)chosenOriginY);
    x -= chosenOriginX;
    y -= chosenOriginY;''')
s = s[:start] + block + s[end:]

start = s.index('int32_t OHInputBridge::dispatchDragViaViewRoot(')
end = s.index('// ============================================================\n// dispatchSingleTouchViaViewRoot', start)
block = s[start:end]
block = block.replace('    int dragPriority = 0;\n', '    int dragPriority = 0;\n    float chosenOriginX = 0.f, chosenOriginY = 0.f;\n', 1)
assert block.count(old) == 0
old_drag = '''            const int priority = wl_root_target_priority(
                env, view, viewCls, hasFocusM, want, i);
            if (priority > 0 && priority >= dragPriority) {'''
new_drag = '''            float originX = 0.f, originY = 0.f;
            const int priority = wl_touch_target_priority(
                env, vri, view, vriCls, viewCls, want, i, x1, y1,
                &originX, &originY);
            if (priority > 0 && priority >= dragPriority) {
                chosenOriginX = originX;
                chosenOriginY = originY;'''
assert block.count(old_drag) == 1
block = block.replace(old_drag,new_drag)
block = block.replace('    if (!decorView) { decorView = fallbackView; vriMatch = vriFallback; dragRoot = dragFallbackIdx; }\n',
                      '    if (!decorView && fallbackView) { env->DeleteGlobalRef(fallbackView); env->DeleteGlobalRef(vriFallback); }\n', 1)
block = block.replace('    if (!decorView) return fail("no decorView");\n',
                      '    if (!decorView) return fail("no root contains drag start");\n', 1)
anchor = '''    LOGI("dispatchDragViaViewRoot: chose root[%d] of %d (g_rootIndex=%d)",
         dragRoot, (int)nn, g_rootIndex.load());'''
assert block.count(anchor) == 1
block = block.replace(anchor, '''    LOGI("dispatchDragViaViewRoot: root[%d] start=(%.1f,%.1f) origin=(%.1f,%.1f)",
         dragRoot, (double)x1, (double)y1,
         (double)chosenOriginX, (double)chosenOriginY);
    x1 -= chosenOriginX;
    y1 -= chosenOriginY;
    x2 -= chosenOriginX;
    y2 -= chosenOriginY;''')
s = s[:start] + block + s[end:]

start = s.index('int32_t OHInputBridge::dispatchSingleTouchViaViewRoot(')
end = s.index('// ============================================================', start)
block = s[start:end]
block = block.replace('    int singlePriority = 0;\n', '    int singlePriority = 0;\n    float chosenOriginX = 0.f, chosenOriginY = 0.f;\n', 1)
old_single = '''            const int priority = wl_root_target_priority(
                env, view, viewCls, hasFocusM, want, i);
            if (priority > 0 && priority >= singlePriority) {'''
new_single = '''            float originX = 0.f, originY = 0.f;
            const int priority = wl_touch_target_priority(
                env, vri, view, vriCls, viewCls, want, i, x, y,
                &originX, &originY);
            if (priority > 0 && priority >= singlePriority) {
                chosenOriginX = originX;
                chosenOriginY = originY;'''
assert block.count(old_single) == 1
block = block.replace(old_single,new_single)
block = block.replace('    if (!decorView) { decorView = fallbackView; vriMatch = vriFallback; }\n',
                      '    if (!decorView && fallbackView) { env->DeleteGlobalRef(fallbackView); env->DeleteGlobalRef(vriFallback); }\n', 1)
block = block.replace('    if (!decorView) return fail("no decorView");\n',
                      '    if (!decorView) return fail("no root contains streamed touch");\n', 1)
anchor = '''    if (!decorView) return fail("no root contains streamed touch");'''
assert block.count(anchor) == 1
block = block.replace(anchor, anchor + '''
    LOGI("dispatchSingleTouchViaViewRoot: screen=(%.1f,%.1f) origin=(%.1f,%.1f)",
         (double)x, (double)y, (double)chosenOriginX, (double)chosenOriginY);
    x -= chosenOriginX;
    y -= chosenOriginY;''')
s = s[:start] + block + s[end:]
source.write_text(s)
print('patched',source)
