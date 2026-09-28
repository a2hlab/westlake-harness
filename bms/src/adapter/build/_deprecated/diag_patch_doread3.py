#!/usr/bin/env python3
# Phase 3 diag: log read() entry with buffer pointer (to detect NULL skip path)
# and any other virtual method calls that might EOF the stream.

PATH = '/home/HanBingChen/aosp/frameworks/base/libs/hwui/jni/CreateJavaOutputStreamAdaptor.cpp'

with open(PATH) as f:
    s = f.read()

# Probe outer read() entry
old_read = '''    size_t read(void* buffer, size_t size) override {
        auto* env = android::requireEnv(fJvm);
        if (!fSwallowExceptions && checkException(env)) {'''

new_read = '''    size_t read(void* buffer, size_t size) override {
        fprintf(stderr, "[doRead-DIAG] read(%p, %zu) entry fBytesRead=%zu fIsAtEnd=%d\\n",
                buffer, size, fBytesRead, fIsAtEnd);
        auto* env = android::requireEnv(fJvm);
        if (!fSwallowExceptions && checkException(env)) {'''

if old_read in s:
    s = s.replace(old_read, new_read)
    print('outer read probe added')
else:
    print('FAIL outer read pattern not found')

# Probe skip path NULL buffer
old_skip = '''                size_t amount = this->doSkip(size - amountSkipped, env);
                if (0 == amount) {
                    char tmp;
                    amount = this->doRead(&tmp, 1, env);
                    if (0 == amount) {
                        // if read returned 0, we're at EOF
                        fIsAtEnd = true;
                        break;
                    }
                }'''

new_skip = '''                size_t amount = this->doSkip(size - amountSkipped, env);
                fprintf(stderr, "[doRead-DIAG] skip path: doSkip(%zu) returned %zu\\n",
                        size - amountSkipped, amount);
                if (0 == amount) {
                    char tmp;
                    amount = this->doRead(&tmp, 1, env);
                    fprintf(stderr, "[doRead-DIAG] skip fallback doRead(1) returned %zu\\n", amount);
                    if (0 == amount) {
                        // if read returned 0, we're at EOF
                        fprintf(stderr, "[doRead-DIAG] skip path setting fIsAtEnd=true\\n");
                        fIsAtEnd = true;
                        break;
                    }
                }'''

if old_skip in s:
    s = s.replace(old_skip, new_skip)
    print('skip path probe added')

with open(PATH, 'w') as f:
    f.write(s)

print('PHASE 3 PATCH OK')
