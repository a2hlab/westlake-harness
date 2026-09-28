#!/usr/bin/env python3
# Phase 2 diagnostic: log fIsAtEnd state + checkException + isAtEnd return
# to find why production stops reading at 165 bytes (no read(8) for pos=173)
# while SmokeTest6 reads all 229 bytes.

import sys

PATH = '/home/HanBingChen/aosp/frameworks/base/libs/hwui/jni/CreateJavaOutputStreamAdaptor.cpp'

with open(PATH) as f:
    s = f.read()

# Probe checkException to see when fIsAtEnd is being set
old_chk = '''    bool checkException(JNIEnv* env) {
        if (!env->ExceptionCheck()) {
            return false;
        }

        env->ExceptionDescribe();
        if (fSwallowExceptions) {
            env->ExceptionClear();
        }

        // There is no way to recover from the error, so consider the stream
        // to be at the end.
        fIsAtEnd = true;

        return true;
    }'''

new_chk = '''    bool checkException(JNIEnv* env) {
        if (!env->ExceptionCheck()) {
            return false;
        }

        fprintf(stderr, "[doRead-DIAG] checkException: setting fIsAtEnd=true (Java exception)\\n");
        env->ExceptionDescribe();
        if (fSwallowExceptions) {
            env->ExceptionClear();
        }

        // There is no way to recover from the error, so consider the stream
        // to be at the end.
        fIsAtEnd = true;

        return true;
    }'''

if old_chk in s:
    s = s.replace(old_chk, new_chk)
    print('checkException probe added')
else:
    print('FAIL: checkException pattern not found')
    sys.exit(1)

# Probe isAtEnd() to log when FrontBufferedStream queries it
old_isatend = '''    bool isAtEnd() const override { return fIsAtEnd; }'''
new_isatend = '''    bool isAtEnd() const override {
        fprintf(stderr, "[doRead-DIAG] isAtEnd() returns %d (fBytesRead=%zu)\\n", fIsAtEnd, fBytesRead);
        return fIsAtEnd;
    }'''

if old_isatend in s:
    s = s.replace(old_isatend, new_isatend)
    print('isAtEnd probe added')
else:
    print('FAIL: isAtEnd pattern not found')
    sys.exit(1)

# Also probe doRead exit to see why it returns
old_exit = '''            buffer = (void*)((char*)buffer + n);
            bytesRead += n;
            size -= n;
            fBytesRead += n;
        } while (size != 0);

        return bytesRead;
    }'''

new_exit = '''            buffer = (void*)((char*)buffer + n);
            bytesRead += n;
            size -= n;
            fBytesRead += n;
        } while (size != 0);

        fprintf(stderr, "[doRead-DIAG] doRead returning bytesRead=%zu fBytesRead=%zu fIsAtEnd=%d\\n",
                bytesRead, fBytesRead, fIsAtEnd);
        return bytesRead;
    }'''

if old_exit in s:
    s = s.replace(old_exit, new_exit)
    print('doRead exit probe added')

with open(PATH, 'w') as f:
    f.write(s)

print('PHASE 2 PATCH OK')
