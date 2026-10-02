// Donor for adapter-mainline-stubs android.net.TrafficStats (merge rule: see NetworkInfo.java).
// Source: AOSP android-14.0.0_r1 packages/modules/Connectivity/framework-t/src/android/net/TrafficStats.java.
// route-A has no NetworkStatsService: byte counters return UNSUPPORTED (-1, :64), the documented AOSP answer when
// a counter is unavailable; the deployed setThreadStatsTag() is a no-op, so the thread tag/uid stay at the AOSP
// SocketTags initial values (-1, :287-288) and tagSocket has no tagger to call.
package android.net;

import java.net.DatagramSocket;
import java.net.Socket;
import java.net.SocketException;

public class TrafficStats {
    public TrafficStats() {}                                          // [existing]

    public static long getTotalRxBytes() { return -1; }                // AOSP :907
    public static long getTotalTxBytes() { return -1; }                // AOSP getTotalTxBytes
    public static long getMobileRxBytes() { return -1; }               // AOSP :675 (no mobile ifaces)
    public static long getMobileTxBytes() { return -1; }               // AOSP getMobileTxBytes
    public static long getUidRxBytes(int uid) { return -1; }           // AOSP :959
    public static long getUidTxBytes(int uid) { return -1; }           // AOSP getUidTxBytes
    public static int getThreadStatsTag() { return -1; }               // AOSP :391 sThreadUidTag.get().tag
    public static int getThreadStatsUid() { return -1; }               // AOSP :432 sThreadUidTag.get().uid
    public static void tagSocket(Socket socket) throws SocketException {}   // AOSP :471 SocketTagger.get().tag(socket)
    public static void untagSocket(Socket socket) throws SocketException {}       // AOSP untagSocket: SocketTagger
    public static void tagDatagramSocket(DatagramSocket socket) throws SocketException {}    // AOSP: SocketTagger
    public static void untagDatagramSocket(DatagramSocket socket) throws SocketException {}  // AOSP: SocketTagger
    public static void clearThreadStatsTag() {}                         // AOSP: tag back to -1; already -1 here
    public static void incrementOperationCount(int operationCount) {}   // AOSP: counts into netstats; none here
    public static void incrementOperationCount(int tag, int operationCount) {}
}
