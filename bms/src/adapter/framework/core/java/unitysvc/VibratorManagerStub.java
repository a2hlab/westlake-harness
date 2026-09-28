package adapter.core.unitysvc;

/**
 * [UNITY-SVC-STUB] Auto-generated safe-default stub extending android.os.IVibratorManagerService.Stub.
 * Generated 2026-07-11 from AOSP javap signatures (framework-minus-apex turbine).
 * Non-void methods return null/0/false per adapter DisplayManagerAdapter template.
 */
public final class VibratorManagerStub extends android.os.IVibratorManagerService.Stub {
    @Override public int[] getVibratorIds() throws android.os.RemoteException { return null; }
    @Override public android.os.VibratorInfo getVibratorInfo(int p0) throws android.os.RemoteException { return null; }
    @Override public boolean isVibrating(int p0) throws android.os.RemoteException { return false; }
    @Override public boolean registerVibratorStateListener(int p0, android.os.IVibratorStateListener p1) throws android.os.RemoteException { return false; }
    @Override public boolean unregisterVibratorStateListener(int p0, android.os.IVibratorStateListener p1) throws android.os.RemoteException { return false; }
    @Override public boolean setAlwaysOnEffect(int p0, java.lang.String p1, int p2, android.os.CombinedVibration p3, android.os.VibrationAttributes p4) throws android.os.RemoteException { return false; }
    @Override public void vibrate(int p0, int p1, java.lang.String p2, android.os.CombinedVibration p3, android.os.VibrationAttributes p4, java.lang.String p5, android.os.IBinder p6) throws android.os.RemoteException {}
    @Override public void cancelVibrate(int p0, android.os.IBinder p1) throws android.os.RemoteException {}
}
