// BuildBoatAttackAndroid.cs — BoatAttack A 线（原生 Android APK）batchmode 构建入口。
// build-a.sh 在构建前把本文件复制到 project/Assets/Editor/，构建后删除，上游工作副本只留相机优先级一处改动。
// 参数按 docs/boat-attack-apk-lightup.md 2026-08-12 的 A 线记录重建：只打 demo_Island，IL2CPP、arm64、APK，
// 原生分辨率全屏；Player 前清理并重建本地 Addressables；签名只用 build-a.sh 注入的专用 JKS。
using System;
using UnityEditor;
using UnityEditor.AddressableAssets.Settings;
using UnityEditor.Build.Reporting;
using UnityEngine;

public static class BuildBoatAttackAndroid
{
    const string Scene = "Assets/scenes/demo_Island.unity";

    public static void Build()
    {
        string output = RequireEnv("BOAT_APK_OUT");

        if (!EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.Android, BuildTarget.Android))
            Fail("cannot switch active build target to Android");

        EditorUserBuildSettings.buildAppBundle = false;
        EditorUserBuildSettings.androidBuildSystem = AndroidBuildSystem.Gradle;
        PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android, ScriptingImplementation.IL2CPP);
        PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
        PlayerSettings.fullScreenMode = FullScreenMode.FullScreenWindow;
        // 原生分辨率：2020.3 无 PlayerSettings.Android.resolutionScalingMode（2021.2+ 才有），
        // 其缺省即不缩放，此处显式留空（见 notes/build-a.log CS0117/CS0103）。
        ConfigureSigning();

        AddressableAssetSettings.CleanPlayerContent();
        AddressableAssetSettings.BuildPlayerContent();

        BuildReport report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
        {
            scenes = new[] { Scene },
            locationPathName = output,
            target = BuildTarget.Android,
            targetGroup = BuildTargetGroup.Android,
            options = BuildOptions.None,
        });
        if (report.summary.result != BuildResult.Succeeded)
            Fail("BuildPlayer result=" + report.summary.result + " errors=" + report.summary.totalErrors);
        Debug.Log("BOAT_ATTACK_A_BUILD=PASS output=" + output);
    }

    static void ConfigureSigning()
    {
        PlayerSettings.Android.useCustomKeystore = true;
        PlayerSettings.Android.keystoreName = RequireEnv("BOAT_KEYSTORE");
        PlayerSettings.Android.keystorePass = RequireEnv("BOAT_KEYSTORE_PASS");
        PlayerSettings.Android.keyaliasName = RequireEnv("BOAT_KEY_ALIAS");
        PlayerSettings.Android.keyaliasPass = RequireEnv("BOAT_KEYSTORE_PASS");
    }

    static string RequireEnv(string name)
    {
        string value = Environment.GetEnvironmentVariable(name);
        if (string.IsNullOrEmpty(value))
            Fail("missing environment variable " + name);
        return value;
    }

    static void Fail(string message)
    {
        Debug.LogError("BOAT_ATTACK_A_BUILD=FAIL " + message);
        EditorApplication.Exit(1);
    }
}
