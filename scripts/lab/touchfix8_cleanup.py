from pathlib import Path
p=Path.home()/'a2hlab/ws/westlake-touchfix/framework/window/jni/oh_input_bridge.cpp'
s=p.read_text()
s=s.replace('''    fprintf(stderr,
            "[WESTLAKE-TOUCH-8] candidate root[%d] type=%d flags=0x%x frame=[%d,%d-%d,%d] focus=%d score=%d\\n",
            (int)rootIndex, (int)windowType, (unsigned)windowFlags,
            (int)left, (int)top, (int)right, (int)bottom, (int)focused, score);
    fflush(stderr);''','''    if (getenv("WL_TOUCH_TRACE") != nullptr) {
        fprintf(stderr,
                "[WESTLAKE-TOUCH-8] candidate root[%d] type=%d flags=0x%x frame=[%d,%d-%d,%d] focus=%d score=%d\\n",
                (int)rootIndex, (int)windowType, (unsigned)windowFlags,
                (int)left, (int)top, (int)right, (int)bottom, (int)focused, score);
        fflush(stderr);
    }''',1)
start=s.index('int32_t OHInputBridge::dispatchTouchViaViewRoot(')
end=s.index('// ============================================================\n// dispatchDragViaViewRoot',start)
b=s[start:end]
b=b.replace('    jmethodID hasFocusM = env->GetMethodID(viewCls, "hasWindowFocus", "()Z");\n','',1)
b=b.replace('    jobject decorView = nullptr, fallbackView = nullptr;','    jobject decorView = nullptr;',1)
b=b.replace('    jobject vriMatch = nullptr, vriFallback = nullptr;','    jobject vriMatch = nullptr;',1)
b=b.replace('    int chosenRoot = -1, fallbackIdx = -1;   // WESTLAKE §460','    int chosenRoot = -1;',1)
b=b.replace('''            // §408: an explicit index wins; otherwise prefer a window that is focused OR actually
            // shown, and only fall back to "the first root that exists".''','''            // Explicit rN wins; automatic input uses screen hit, layer, and touchability.''',1)
left=b.index('                // WESTLAKE §460: keep the LAST match, not the first.')
right=b.index('                if (decorView)',left)
b=b[:left]+b[right:]
old='''            } else if (!fallbackView) {
                fallbackView = env->NewGlobalRef(view);
                vriFallback = env->NewGlobalRef(vri);
                fallbackIdx = (int)i;
            }'''
assert b.count(old)==1
b=b.replace(old,'            }')
b=b.replace('''    if (!decorView && fallbackView) { env->DeleteGlobalRef(fallbackView); env->DeleteGlobalRef(vriFallback); }
    else if (fallbackView) { env->DeleteGlobalRef(fallbackView); fallbackView = nullptr; }
''','',1)
b=b.replace('        // (no early break — see §460: we want the LAST matching root)\n','',1)
s=s[:start]+b+s[end:]
start=s.index('int32_t OHInputBridge::dispatchDragViaViewRoot(')
end=s.index('// ============================================================\n// dispatchSingleTouchViaViewRoot',start)
b=s[start:end]
b=b.replace('    jmethodID hasFocusM = env->GetMethodID(viewCls, "hasWindowFocus", "()Z");\n','',1)
b=b.replace('    jobject decorView = nullptr, fallbackView = nullptr;','    jobject decorView = nullptr;',1)
b=b.replace('    jobject vriMatch = nullptr, vriFallback = nullptr;   // §405/§406b: global refs, guarded scan','    jobject vriMatch = nullptr;   // §405/§406b: global refs, guarded scan',1)
b=b.replace('    int dragRoot = -1, dragFallbackIdx = -1;   // WESTLAKE §460b','    int dragRoot = -1;',1)
b=b.replace('''            // §408: an explicit index wins; otherwise prefer a window that is focused OR actually
            // shown, and only fall back to "the first root that exists".''','''            // Keep the DOWN target for this synthetic drag; all points share its origin.''',1)
b=b.replace('''                // WESTLAKE §460b: keep the LAST match — same reason as the tap path. Without this a
                // drag inside a dialog (the volume Slider) went to the Activity underneath.
''','',1)
old='''            else if (!fallbackView) {
                fallbackView = env->NewGlobalRef(view);
                vriFallback = env->NewGlobalRef(vri);
                dragFallbackIdx = (int)i;
            }'''
assert b.count(old)==1
b=b.replace(old,'')
b=b.replace('''    if (!decorView && fallbackView) { env->DeleteGlobalRef(fallbackView); env->DeleteGlobalRef(vriFallback); }
    else if (fallbackView) { env->DeleteGlobalRef(fallbackView); fallbackView = nullptr; }
''','',1)
b=b.replace('        // (no early break — §460b: we want the LAST matching root)\n','',1)
s=s[:start]+b+s[end:]
start=s.index('int32_t OHInputBridge::dispatchSingleTouchViaViewRoot(')
end=s.index('// ============================================================',start)
b=s[start:end]
b=b.replace('    jmethodID hasFocusM = env->GetMethodID(viewCls, "hasWindowFocus", "()Z");\n','',1)
b=b.replace('    jobject decorView = nullptr, fallbackView = nullptr;','    jobject decorView = nullptr;',1)
b=b.replace('    jobject vriMatch = nullptr, vriFallback = nullptr;   // §405/§406b: global refs, guarded scan','    jobject vriMatch = nullptr;   // §405/§406b: global refs, guarded scan',1)
b=b.replace('''            // §408: an explicit index wins; otherwise prefer a window that is focused OR actually
            // shown, and only fall back to "the first root that exists".''','''            // Use the same screen hit and root-local translation as click and drag.''',1)
old='''            else if (!fallbackView) {
                fallbackView = env->NewGlobalRef(view);
                vriFallback = env->NewGlobalRef(vri);
            }'''
assert b.count(old)==1
b=b.replace(old,'')
b=b.replace('''    if (!decorView && fallbackView) { env->DeleteGlobalRef(fallbackView); env->DeleteGlobalRef(vriFallback); }
    else if (fallbackView) { env->DeleteGlobalRef(fallbackView); fallbackView = nullptr; }
''','',1)
s=s[:start]+b+s[end:]
assert 'fallbackView' not in s[s.index('int32_t OHInputBridge::dispatchTouchViaViewRoot('):s.index('// ============================================================\n// dispatchSingleTouchViaViewRoot')]
p.write_text(s)
