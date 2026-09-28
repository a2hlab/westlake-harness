package adapter.core.unitysvc;

/**
 * [UNITY-SVC-STUB] Auto-generated safe-default stub extending android.os.IThermalService.Stub.
 * Generated 2026-07-11 from AOSP javap signatures (framework-minus-apex turbine).
 * Non-void methods return null/0/false per adapter DisplayManagerAdapter template.
 */
public final class ThermalServiceStub extends android.os.IThermalService.Stub {
    @Override public boolean registerThermalEventListener(android.os.IThermalEventListener p0) throws android.os.RemoteException { return false; }
    @Override public boolean registerThermalEventListenerWithType(android.os.IThermalEventListener p0, int p1) throws android.os.RemoteException { return false; }
    @Override public boolean unregisterThermalEventListener(android.os.IThermalEventListener p0) throws android.os.RemoteException { return false; }
    @Override public android.os.Temperature[] getCurrentTemperatures() throws android.os.RemoteException { return null; }
    @Override public android.os.Temperature[] getCurrentTemperaturesWithType(int p0) throws android.os.RemoteException { return null; }
    @Override public boolean registerThermalStatusListener(android.os.IThermalStatusListener p0) throws android.os.RemoteException { return false; }
    @Override public boolean unregisterThermalStatusListener(android.os.IThermalStatusListener p0) throws android.os.RemoteException { return false; }
    @Override public int getCurrentThermalStatus() throws android.os.RemoteException { return 0; }
    @Override public android.os.CoolingDevice[] getCurrentCoolingDevices() throws android.os.RemoteException { return null; }
    @Override public android.os.CoolingDevice[] getCurrentCoolingDevicesWithType(int p0) throws android.os.RemoteException { return null; }
    @Override public float getThermalHeadroom(int p0) throws android.os.RemoteException { return 0f; }
}
