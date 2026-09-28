#!/usr/bin/env python3
"""Host contract for the WindowManagerGlobal -> IWindowSession ingress."""

from pathlib import Path
import re


WINDOW_DIR = Path(__file__).resolve().parents[1] / "java"
ADAPTER_ROOT = Path(__file__).resolve().parents[3]
OH61_WINDOW_JNI = (
    ADAPTER_ROOT
    / "sources"
    / "oh61-v7-b2133b5b"
    / "framework"
    / "window"
    / "jni"
    / "window_session_adapter.cpp"
)
ACTIVITY = (
    ADAPTER_ROOT
    / "framework"
    / "activity"
    / "java"
    / "ActivityClientControllerAdapter.java"
).read_text(encoding="utf-8")
OH61_ACTIVITY_NATIVE = (
    ADAPTER_ROOT
    / "sources"
    / "oh61-v7-b2133b5b"
    / "framework"
    / "activity"
    / "jni"
    / "oh_ability_manager_client.cpp"
).read_text(encoding="utf-8")
OH61_ANW = (
    ADAPTER_ROOT
    / "sources"
    / "oh61-v7-b2133b5b"
    / "framework"
    / "window"
    / "jni"
    / "oh_anativewindow_shim.cpp"
).read_text(encoding="utf-8")
HWUI_PATCH = (
    ADAPTER_ROOT
    / "aosp_patches"
    / "libs"
    / "hwui"
    / "hwui_oh_abi_patch.cpp"
).read_text(encoding="utf-8")
MANAGER = (WINDOW_DIR / "WindowManagerAdapter.java").read_text(encoding="utf-8")
SESSION = (WINDOW_DIR / "WindowSessionAdapter.java").read_text(encoding="utf-8")
OH61_JNI = OH61_WINDOW_JNI.read_text(encoding="utf-8")
WINDOW_NATIVE = (
    ADAPTER_ROOT
    / "framework"
    / "window"
    / "jni"
    / "oh_window_manager_client.cpp"
).read_text(encoding="utf-8")


def test_window_session_ingress_contract():
    """验证 window session 入口与 APP_CONTENT receipt 的静态接线合同。"""
    open_session = re.search(
        r"public IWindowSession openSession\(IWindowSessionCallback callback\)"
        r".*?\{(?P<body>.*?)\n    \}",
        MANAGER,
        flags=re.DOTALL,
    )
    assert open_session, "WindowManagerAdapter.openSession implementation missing"
    body = open_session.group("body")
    assert "return WindowSessionAdapter.getInstance();" in body
    assert "return null;" not in body

    assert "private static volatile WindowSessionAdapter sInstance;" in SESSION
    assert "public static WindowSessionAdapter getInstance()" in SESSION
    assert "sInstance = new WindowSessionAdapter();" in SESSION

    assert (
        '"Ljava/lang/String;Ljava/lang/String;IIIIIJ)[I"' in OH61_JNI
    ), "OH6.1 bridge is missing the current nativeCreateSession ABI"
    assert (
        "RegisterNatives(clazz, &kMethods[i], 1)" in OH61_JNI
    ), "OH6.1 bridge must register methods independently for mixed-generation tolerance"

    assert "nativeOpenForegroundTransition" in ACTIVITY
    assert re.search(
        r"waiting for typed\s*\"\s*\+\s*\"Fn04\.A02 APP_CONTENT receipt",
        ACTIVITY,
    )
    assert "OnDrawListener" not in ACTIVITY
    assert "postDelayed(reporter, 800)" not in ACTIVITY
    assert "g_fn03FirstFrameGate.Present(receipt)" in OH61_ACTIVITY_NATIVE
    assert 'receipt.producerActionId = "Fn04.A02"' in OH61_ACTIVITY_NATIVE
    assert '"FN03_A10_TYPED_RECEIPT_V1"' in OH61_ACTIVITY_NATIVE
    assert '"FN03_A07_ACK_RESULT_V1"' in OH61_ACTIVITY_NATIVE
    assert '"OH_Fn03Receipt", "%{public}s"' in OH61_ACTIVITY_NATIVE
    assert "g_fn03AckReducer.Receipt(" in OH61_ACTIVITY_NATIVE
    assert "fn03_on_app_content_present" in OH61_ANW
    assert "oh_anw_notify_presented" in OH61_ANW
    assert OH61_ANW.count("FN04_A02_PRESENT_V1") == 2
    flush_call = "OH_NativeWindow_NativeWindowFlushBuffer(a->oh, ohBuf, fenceFd, region)"
    assert flush_call in OH61_ANW
    assert (
        OH61_ANW.index(flush_call)
        < OH61_ANW.index("fn03_on_app_content_present(a->ohTokenAddr, frameId)")
    ), "Fn04.A02 receipt must follow the real OH buffer flush"
    assert 'dlsym(h, "oh_anw_notify_presented")' in HWUI_PATCH
    assert "g_egl_surface_owner[surface] = window;" in HWUI_PATCH
    assert "if (result) notify_presented_after_success(surface);" in HWUI_PATCH
    assert (
        HWUI_PATCH.index("g_real_eglSwapBuffers_fn(dpy, surface)")
        < HWUI_PATCH.rindex("if (result) notify_presented_after_success(surface);")
    ), "EGL path must emit only after the real swap succeeds"
    assert "g_egl_surface_owner.erase(surface);" in HWUI_PATCH


def test_power_and_lock_flags_are_translated_not_silently_accepted():
    """验证首窗 power/lock flags 同时进入 Java allowlist 与 OH 属性。"""
    for flag in (
        "FLAG_KEEP_SCREEN_ON",
        "FLAG_SHOW_WHEN_LOCKED",
        "FLAG_TURN_SCREEN_ON",
        "FLAG_DISMISS_KEYGUARD",
    ):
        assert f"WindowManager.LayoutParams.{flag}" in SESSION

    assert "ANDROID_FLAG_KEEP_SCREEN_ON        = 0x00000080" in WINDOW_NATIVE
    assert "ANDROID_FLAG_SHOW_WHEN_LOCKED      = 0x00080000" in WINDOW_NATIVE
    assert "ANDROID_FLAG_TURN_SCREEN_ON        = 0x00200000" in WINDOW_NATIVE
    assert "ANDROID_FLAG_DISMISS_KEYGUARD      = 0x00400000" in WINDOW_NATIVE
    assert "property->SetKeepScreenOn(" in WINDOW_NATIVE
    assert "property->SetTurnScreenOn(" in WINDOW_NATIVE
    assert "WindowFlag::WINDOW_FLAG_SHOW_WHEN_LOCKED" in WINDOW_NATIVE

    # The create-time NEED_AVOID pulse must not erase the translated lock flag.
    assert "mappedOhWindowFlags = property->GetWindowFlags()" in WINDOW_NATIVE
    assert "mappedOhWindowFlags | static_cast<uint32_t>(" in WINDOW_NATIVE
    assert "property->SetWindowFlags(mappedOhWindowFlags);" in WINDOW_NATIVE


if __name__ == "__main__":
    test_window_session_ingress_contract()
    test_power_and_lock_flags_are_translated_not_silently_accepted()
    print("Window session ingress contract: PASS")
