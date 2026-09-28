package adapter.core.unitysvc;

/**
 * [UNITY-SVC-STUB] Auto-generated safe-default stub extending android.os.IPowerManager.Stub.
 * Generated 2026-07-11 from AOSP javap signatures (framework-minus-apex turbine).
 * Non-void methods return null/0/false per adapter DisplayManagerAdapter template.
 */
public final class PowerManagerStub extends android.os.IPowerManager.Stub {
    @Override public void acquireWakeLock(android.os.IBinder p0, int p1, java.lang.String p2, java.lang.String p3, android.os.WorkSource p4, java.lang.String p5, int p6, android.os.IWakeLockCallback p7) throws android.os.RemoteException {}
    @Override public void acquireWakeLockWithUid(android.os.IBinder p0, int p1, java.lang.String p2, java.lang.String p3, int p4, int p5, android.os.IWakeLockCallback p6) throws android.os.RemoteException {}
    @Override public void releaseWakeLock(android.os.IBinder p0, int p1) throws android.os.RemoteException {}
    @Override public void updateWakeLockUids(android.os.IBinder p0, int[] p1) throws android.os.RemoteException {}
    @Override public void setPowerBoost(int p0, int p1) throws android.os.RemoteException {}
    @Override public void setPowerMode(int p0, boolean p1) throws android.os.RemoteException {}
    @Override public boolean setPowerModeChecked(int p0, boolean p1) throws android.os.RemoteException { return false; }
    @Override public void updateWakeLockWorkSource(android.os.IBinder p0, android.os.WorkSource p1, java.lang.String p2) throws android.os.RemoteException {}
    @Override public void updateWakeLockCallback(android.os.IBinder p0, android.os.IWakeLockCallback p1) throws android.os.RemoteException {}
    @Override public boolean isWakeLockLevelSupported(int p0) throws android.os.RemoteException { return false; }
    @Override public void userActivity(int p0, long p1, int p2, int p3) throws android.os.RemoteException {}
    @Override public void wakeUp(long p0, int p1, java.lang.String p2, java.lang.String p3) throws android.os.RemoteException {}
    @Override public void goToSleep(long p0, int p1, int p2) throws android.os.RemoteException {}
    @Override public void goToSleepWithDisplayId(int p0, long p1, int p2, int p3) throws android.os.RemoteException {}
    @Override public void nap(long p0) throws android.os.RemoteException {}
    @Override public float getBrightnessConstraint(int p0) throws android.os.RemoteException { return 0f; }
    @Override public boolean isInteractive() throws android.os.RemoteException { return false; }
    @Override public boolean isDisplayInteractive(int p0) throws android.os.RemoteException { return false; }
    @Override public boolean areAutoPowerSaveModesEnabled() throws android.os.RemoteException { return false; }
    @Override public boolean isPowerSaveMode() throws android.os.RemoteException { return false; }
    @Override public android.os.PowerSaveState getPowerSaveState(int p0) throws android.os.RemoteException { return null; }
    @Override public boolean setPowerSaveModeEnabled(boolean p0) throws android.os.RemoteException { return false; }
    @Override public android.os.BatterySaverPolicyConfig getFullPowerSavePolicy() throws android.os.RemoteException { return null; }
    @Override public boolean setFullPowerSavePolicy(android.os.BatterySaverPolicyConfig p0) throws android.os.RemoteException { return false; }
    @Override public boolean setDynamicPowerSaveHint(boolean p0, int p1) throws android.os.RemoteException { return false; }
    @Override public boolean setAdaptivePowerSavePolicy(android.os.BatterySaverPolicyConfig p0) throws android.os.RemoteException { return false; }
    @Override public boolean setAdaptivePowerSaveEnabled(boolean p0) throws android.os.RemoteException { return false; }
    @Override public int getPowerSaveModeTrigger() throws android.os.RemoteException { return 0; }
    @Override public void setBatteryDischargePrediction(android.os.ParcelDuration p0, boolean p1) throws android.os.RemoteException {}
    @Override public android.os.ParcelDuration getBatteryDischargePrediction() throws android.os.RemoteException { return null; }
    @Override public boolean isBatteryDischargePredictionPersonalized() throws android.os.RemoteException { return false; }
    @Override public boolean isDeviceIdleMode() throws android.os.RemoteException { return false; }
    @Override public boolean isLightDeviceIdleMode() throws android.os.RemoteException { return false; }
    @Override public boolean isLowPowerStandbySupported() throws android.os.RemoteException { return false; }
    @Override public boolean isLowPowerStandbyEnabled() throws android.os.RemoteException { return false; }
    @Override public void setLowPowerStandbyEnabled(boolean p0) throws android.os.RemoteException {}
    @Override public void setLowPowerStandbyActiveDuringMaintenance(boolean p0) throws android.os.RemoteException {}
    @Override public void forceLowPowerStandbyActive(boolean p0) throws android.os.RemoteException {}
    @Override public void setLowPowerStandbyPolicy(android.os.IPowerManager.LowPowerStandbyPolicy p0) throws android.os.RemoteException {}
    @Override public android.os.IPowerManager.LowPowerStandbyPolicy getLowPowerStandbyPolicy() throws android.os.RemoteException { return null; }
    @Override public boolean isExemptFromLowPowerStandby() throws android.os.RemoteException { return false; }
    @Override public boolean isReasonAllowedInLowPowerStandby(int p0) throws android.os.RemoteException { return false; }
    @Override public boolean isFeatureAllowedInLowPowerStandby(java.lang.String p0) throws android.os.RemoteException { return false; }
    @Override public void acquireLowPowerStandbyPorts(android.os.IBinder p0, java.util.List<android.os.IPowerManager.LowPowerStandbyPortDescription> p1) throws android.os.RemoteException {}
    @Override public void releaseLowPowerStandbyPorts(android.os.IBinder p0) throws android.os.RemoteException {}
    @Override public java.util.List<android.os.IPowerManager.LowPowerStandbyPortDescription> getActiveLowPowerStandbyPorts() throws android.os.RemoteException { return null; }
    @Override public void reboot(boolean p0, java.lang.String p1, boolean p2) throws android.os.RemoteException {}
    @Override public void rebootSafeMode(boolean p0, boolean p1) throws android.os.RemoteException {}
    @Override public void shutdown(boolean p0, java.lang.String p1, boolean p2) throws android.os.RemoteException {}
    @Override public void crash(java.lang.String p0) throws android.os.RemoteException {}
    @Override public int getLastShutdownReason() throws android.os.RemoteException { return 0; }
    @Override public int getLastSleepReason() throws android.os.RemoteException { return 0; }
    @Override public void setStayOnSetting(int p0) throws android.os.RemoteException {}
    @Override public void boostScreenBrightness(long p0) throws android.os.RemoteException {}
    @Override public void acquireWakeLockAsync(android.os.IBinder p0, int p1, java.lang.String p2, java.lang.String p3, android.os.WorkSource p4, java.lang.String p5) throws android.os.RemoteException {}
    @Override public void releaseWakeLockAsync(android.os.IBinder p0, int p1) throws android.os.RemoteException {}
    @Override public void updateWakeLockUidsAsync(android.os.IBinder p0, int[] p1) throws android.os.RemoteException {}
    @Override public boolean isScreenBrightnessBoosted() throws android.os.RemoteException { return false; }
    @Override public void setAttentionLight(boolean p0, int p1) throws android.os.RemoteException {}
    @Override public void setDozeAfterScreenOff(boolean p0) throws android.os.RemoteException {}
    @Override public boolean isAmbientDisplayAvailable() throws android.os.RemoteException { return false; }
    @Override public void suppressAmbientDisplay(java.lang.String p0, boolean p1) throws android.os.RemoteException {}
    @Override public boolean isAmbientDisplaySuppressedForToken(java.lang.String p0) throws android.os.RemoteException { return false; }
    @Override public boolean isAmbientDisplaySuppressed() throws android.os.RemoteException { return false; }
    @Override public boolean isAmbientDisplaySuppressedForTokenByApp(java.lang.String p0, int p1) throws android.os.RemoteException { return false; }
    @Override public boolean forceSuspend() throws android.os.RemoteException { return false; }
}
