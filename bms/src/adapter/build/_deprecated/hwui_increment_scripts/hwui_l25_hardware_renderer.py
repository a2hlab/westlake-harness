#!/usr/bin/env python3
"""L2.5: Real implementation of HardwareRenderer ContextFactory + RenderProxy.

Replaces the round 6+ stubs in jni/android_graphics_HardwareRenderer.cpp with
a real ContextFactoryImpl class that provides AnimationContext and a real
RenderProxy construction.

This is what the AOSP 14 source originally does — we just restored it after
the round 6 #if 0 / nullptr stubs.
"""
import os, re, shutil

HWUI = '/home/HanBingChen/aosp/frameworks/base/libs/hwui'
TARGET = f'{HWUI}/jni/android_graphics_HardwareRenderer.cpp'

# Backup once
bak = TARGET + '.bak.l25'
if not os.path.exists(bak):
    shutil.copy(TARGET, bak)
shutil.copy(bak, TARGET)

with open(TARGET) as f:
    c = f.read()

# 1. Insert ContextFactoryImpl class before createProxy
contextfactory_impl = '''
// L2.5: Real ContextFactoryImpl (restores AOSP 14 behavior)
class ContextFactoryImpl : public android::uirenderer::IContextFactory {
public:
    explicit ContextFactoryImpl(android::uirenderer::RootRenderNode* rootNode)
        : mRootNode(rootNode) {}
    android::uirenderer::AnimationContext* createAnimationContext(
            android::uirenderer::renderthread::TimeLord& clock) override {
        return new android::uirenderer::AnimationContext(clock);
    }
private:
    android::uirenderer::RootRenderNode* mRootNode;
};

'''

# Insert before createRootRenderNode (a stable anchor)
anchor = 'static jlong android_view_ThreadedRenderer_createRootRenderNode'
if 'class ContextFactoryImpl' not in c:
    c = c.replace(anchor, contextfactory_impl + anchor)

# 2. Replace createProxy stub with real implementation
old_create_proxy = '''static jlong android_view_ThreadedRenderer_createProxy(JNIEnv* env, jobject clazz,
        jboolean translucent, jlong rootRenderNodePtr) {
    RootRenderNode* rootRenderNode = reinterpret_cast<RootRenderNode*>(rootRenderNodePtr);
    /* M133 */ void* factory = nullptr; (void)factory;
    RenderProxy* proxy = /* M133 */ nullptr;
    return (jlong) proxy;
}'''

new_create_proxy = '''static jlong android_view_ThreadedRenderer_createProxy(JNIEnv* env, jobject clazz,
        jboolean translucent, jlong rootRenderNodePtr) {
    RootRenderNode* rootRenderNode = reinterpret_cast<RootRenderNode*>(rootRenderNodePtr);
    // L2.5: real ContextFactoryImpl + RenderProxy (restores AOSP 14 behavior)
    ContextFactoryImpl factory(rootRenderNode);
    return (jlong) new RenderProxy(translucent, rootRenderNode, &factory);
}'''

if old_create_proxy in c:
    c = c.replace(old_create_proxy, new_create_proxy)
    print('Replaced createProxy stub with real impl')
else:
    print('WARN: createProxy stub not found - may already be patched')

# 3. Need #include for AnimationContext
if '#include <AnimationContext.h>' not in c and '#include "AnimationContext.h"' not in c:
    c = c.replace('#include <renderthread/RenderProxy.h>',
                  '#include <renderthread/RenderProxy.h>\n#include <AnimationContext.h>')

with open(TARGET, 'w') as f:
    f.write(c)

print(f'Patched: {os.path.basename(TARGET)}')
