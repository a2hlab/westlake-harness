package adapter.core.unitysvc;

/**
 * [UNITY-SVC-STUB] Safe-default stub extending android.content.IClipboard.Stub.
 * Signatures taken verbatim from AOSP javap (framework-minus-apex turbine, 2026-07-11).
 *
 * Unlike the other unitysvc stubs, clipboard keeps a tiny in-memory primary
 * ClipData so a Unity app that copies then pastes within its own process sees
 * consistent behaviour: setPrimaryClip stores it, getPrimaryClip returns it,
 * hasPrimaryClip / getPrimaryClipDescription reflect it, clearPrimaryClip drops
 * it. All other methods return safe defaults (null/0/false, no-op).
 */
public final class ClipboardStub extends android.content.IClipboard.Stub {
    private android.content.ClipData mClip;

    @Override public synchronized void setPrimaryClip(android.content.ClipData p0, java.lang.String p1, java.lang.String p2, int p3, int p4) throws android.os.RemoteException { mClip = p0; }
    @Override public synchronized void setPrimaryClipAsPackage(android.content.ClipData p0, java.lang.String p1, java.lang.String p2, int p3, int p4, java.lang.String p5) throws android.os.RemoteException { mClip = p0; }
    @Override public synchronized void clearPrimaryClip(java.lang.String p0, java.lang.String p1, int p2, int p3) throws android.os.RemoteException { mClip = null; }
    @Override public synchronized android.content.ClipData getPrimaryClip(java.lang.String p0, java.lang.String p1, int p2, int p3) throws android.os.RemoteException { return mClip; }
    @Override public synchronized android.content.ClipDescription getPrimaryClipDescription(java.lang.String p0, java.lang.String p1, int p2, int p3) throws android.os.RemoteException { return mClip != null ? mClip.getDescription() : null; }
    @Override public synchronized boolean hasPrimaryClip(java.lang.String p0, java.lang.String p1, int p2, int p3) throws android.os.RemoteException { return mClip != null; }
    @Override public void addPrimaryClipChangedListener(android.content.IOnPrimaryClipChangedListener p0, java.lang.String p1, java.lang.String p2, int p3, int p4) throws android.os.RemoteException {}
    @Override public void removePrimaryClipChangedListener(android.content.IOnPrimaryClipChangedListener p0, java.lang.String p1, java.lang.String p2, int p3, int p4) throws android.os.RemoteException {}
    @Override public synchronized boolean hasClipboardText(java.lang.String p0, java.lang.String p1, int p2, int p3) throws android.os.RemoteException { return mClip != null && mClip.getItemCount() > 0; }
    @Override public java.lang.String getPrimaryClipSource(java.lang.String p0, java.lang.String p1, int p2, int p3) throws android.os.RemoteException { return null; }
    @Override public boolean areClipboardAccessNotificationsEnabledForUser(int p0) throws android.os.RemoteException { return false; }
    @Override public void setClipboardAccessNotificationsEnabledForUser(boolean p0, int p1) throws android.os.RemoteException {}
}
