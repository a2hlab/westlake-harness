from pathlib import Path
p=Path.home()/'a2hlab/ws/westlake-touchfix/framework/window/jni/oh_input_bridge.cpp'
s=p.read_text()
s=s.replace('// mRoots is ordered bottom to top. A newer hit wins even if an older Activity has\n// focus; focus only breaks a tie at the same stacking position.', '// mRoots is not a reliable Z-order: Toutiao has its dialog at root[0] and its\n// Activity at root[1]. Rank Android window type first, insertion order next,\n// and focus only when those are tied.')
old='''    jmethodID focusM = env->GetMethodID(viewCls, "hasWindowFocus", "()Z");
    const jboolean focused = focusM ? env->CallBooleanMethod(view, focusM) : JNI_FALSE;
    if (env->ExceptionCheck()) { env->ExceptionClear(); }
    return static_cast<int>(rootIndex) * 2 + 1 + (focused ? 1 : 0);'''
new='''    jint windowType = 1; // Base application if attributes are temporarily absent.
    jfieldID attrsF = env->GetFieldID(vriCls, "mWindowAttributes",
                                     "Landroid/view/WindowManager$LayoutParams;");
    if (attrsF && !env->ExceptionCheck()) {
        jobject attrs = env->GetObjectField(vri, attrsF);
        if (attrs && !env->ExceptionCheck()) {
            jclass attrsCls = env->GetObjectClass(attrs);
            jfieldID typeF = attrsCls ? env->GetFieldID(attrsCls, "type", "I") : nullptr;
            if (typeF && !env->ExceptionCheck()) windowType = env->GetIntField(attrs, typeF);
            if (attrsCls) env->DeleteLocalRef(attrsCls);
            env->DeleteLocalRef(attrs);
        }
    }
    if (env->ExceptionCheck()) env->ExceptionClear();
    // TYPE_APPLICATION(2) dialogs outrank TYPE_BASE_APPLICATION(1). Attached
    // panels/dialogs (1000/1002/1003...) outrank both; application media (1001)
    // is deliberately below the base window. This is the app-window subset of
    // Android's InputDispatcher layer ordering, not numerical type ordering.
    const int layer = windowType == 1001 ? 0 :
        windowType >= 1000 && windowType < 2000 ? 3 :
        windowType == 2 ? 2 : 1;
    jmethodID focusM = env->GetMethodID(viewCls, "hasWindowFocus", "()Z");
    const jboolean focused = focusM ? env->CallBooleanMethod(view, focusM) : JNI_FALSE;
    if (env->ExceptionCheck()) env->ExceptionClear();
    const int score = layer * 100000 + static_cast<int>(rootIndex) * 2 + 1 +
                      (focused ? 1 : 0);
    fprintf(stderr,
            "[WESTLAKE-TOUCH-8] candidate root[%d] type=%d frame=[%d,%d-%d,%d] focus=%d score=%d\\n",
            (int)rootIndex, (int)windowType, (int)left, (int)top,
            (int)right, (int)bottom, (int)focused, score);
    fflush(stderr);
    return score;'''
assert s.count(old)==1
s=s.replace(old,new)
old='''    LOGI("dispatchTouchViaViewRoot: root[%d] screen=(%.1f,%.1f) origin=(%.1f,%.1f)",
         chosenRoot, (double)x, (double)y,
         (double)chosenOriginX, (double)chosenOriginY);'''
new='''    fprintf(stderr, "[WESTLAKE-TOUCH-8] tap root[%d] screen=(%.1f,%.1f) origin=(%.1f,%.1f)\\n",
            chosenRoot, (double)x, (double)y,
            (double)chosenOriginX, (double)chosenOriginY);
    fflush(stderr);'''
assert s.count(old)==1
s=s.replace(old,new)
p.write_text(s)
