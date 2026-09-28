from pathlib import Path
p=Path.home()/'a2hlab/ws/westlake-touchfix/framework/window/jni/oh_input_bridge.cpp'
s=p.read_text()
s=s.replace('''    jint windowType = 1; // Base application if attributes are temporarily absent.
''','''    jint windowType = 1; // Base application if attributes are temporarily absent.
    jint windowFlags = 0;
''',1)
s=s.replace('''            if (typeF && !env->ExceptionCheck()) windowType = env->GetIntField(attrs, typeF);
''','''            if (typeF && !env->ExceptionCheck()) windowType = env->GetIntField(attrs, typeF);
            jfieldID flagsF = attrsCls ? env->GetFieldID(attrsCls, "flags", "I") : nullptr;
            if (flagsF && !env->ExceptionCheck()) windowFlags = env->GetIntField(attrs, flagsF);
''',1)
s=s.replace('''    const int score = layer * 100000 + static_cast<int>(rootIndex) * 2 + 1 +
                      (focused ? 1 : 0);
    fprintf(stderr,
            "[WESTLAKE-TOUCH-8] candidate root[%d] type=%d frame=[%d,%d-%d,%d] focus=%d score=%d\\n",
            (int)rootIndex, (int)windowType, (int)left, (int)top,
            (int)right, (int)bottom, (int)focused, score);
    fflush(stderr);
    return score;''','''    const int score = layer * 100000 + static_cast<int>(rootIndex) * 2 + 1 +
                      (focused ? 1 : 0);
    fprintf(stderr,
            "[WESTLAKE-TOUCH-8] candidate root[%d] type=%d flags=0x%x frame=[%d,%d-%d,%d] focus=%d score=%d\\n",
            (int)rootIndex, (int)windowType, (unsigned)windowFlags,
            (int)left, (int)top, (int)right, (int)bottom, (int)focused, score);
    fflush(stderr);
    // InputDispatcher excludes FLAG_NOT_TOUCHABLE windows even if their
    // transparent decor is laid out and isShown() reports true.
    if (windowFlags & 0x10) return 0;
    return score;''',1)
assert 'flags=0x%x' in s and 'if (windowFlags & 0x10)' in s
p.write_text(s)
