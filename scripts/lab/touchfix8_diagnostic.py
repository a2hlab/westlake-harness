from pathlib import Path
p=Path.home()/'a2hlab/ws/westlake-touchfix/framework/window/jni/oh_input_bridge.cpp'
s=p.read_text()
old='''    wl_view_log(ANDROID_LOG_INFO,
                "[WESTLAKE-TOUCH-8] candidate root[%d] type=%d frame=[%d,%d-%d,%d] focus=%d score=%d",
                (int)rootIndex, (int)windowType, (int)left, (int)top,
                (int)right, (int)bottom, (int)focused, score);'''
new='''    fprintf(stderr,
            "[WESTLAKE-TOUCH-8] candidate root[%d] type=%d frame=[%d,%d-%d,%d] focus=%d score=%d\\n",
            (int)rootIndex, (int)windowType, (int)left, (int)top,
            (int)right, (int)bottom, (int)focused, score);
    fflush(stderr);'''
assert s.count(old)==1
s=s.replace(old,new)
old='''    wl_view_log(ANDROID_LOG_INFO, "[WESTLAKE-TOUCH-8] tap root[%d] screen=(%.1f,%.1f) origin=(%.1f,%.1f)",
         chosenRoot, (double)x, (double)y,
         (double)chosenOriginX, (double)chosenOriginY);'''
new='''    fprintf(stderr, "[WESTLAKE-TOUCH-8] tap root[%d] screen=(%.1f,%.1f) origin=(%.1f,%.1f)\\n",
            chosenRoot, (double)x, (double)y,
            (double)chosenOriginX, (double)chosenOriginY);
    fflush(stderr);'''
assert s.count(old)==1
s=s.replace(old,new)
p.write_text(s)
