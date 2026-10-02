package android.annotation;
/** Compile-only: the hidden AOSP annotation (not merged into the stubs jar). */
public @interface SdkConstant {
    SdkConstantType value();
    enum SdkConstantType { ACTIVITY_INTENT_ACTION, BROADCAST_INTENT_ACTION, SERVICE_ACTION, INTENT_CATEGORY, FEATURE }
}
