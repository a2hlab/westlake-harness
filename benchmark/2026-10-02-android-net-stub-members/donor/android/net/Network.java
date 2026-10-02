// Donor for adapter-mainline-stubs android.net.Network (merge rule: see NetworkInfo.java).
// Source: AOSP android-14.0.0_r1 packages/modules/Connectivity/framework/src/android/net/Network.java.
// The deployed stub has no netId (only a no-arg constructor), i.e. every Network is NETID_UNSET; the added
// members follow AOSP for that case and use the process default network for I/O.
package android.net;

import java.io.IOException;
import java.net.InetAddress;
import java.net.Socket;
import java.net.URL;
import java.net.URLConnection;
import java.net.UnknownHostException;
import javax.net.SocketFactory;

public class Network {
    public Network() {}                                                  // [existing]

    /** AOSP :469: `if (netId == 0) return 0L;` -- the stub's Network carries no netId. */
    public long getNetworkHandle() { return 0L; }

    /** AOSP :452: rejects 0 and a handle without HANDLE_MAGIC (0xcafed00d, :93-94) exactly as AOSP does. */
    public static Network fromNetworkHandle(long networkHandle) {
        if (networkHandle == 0) {
            throw new IllegalArgumentException(
                    "Network.fromNetworkHandle refusing to instantiate NETID_UNSET Network.");
        }
        if ((networkHandle & ((1L << 32) - 1)) != 0xcafed00dL) {
            throw new IllegalArgumentException("Value passed to fromNetworkHandle() is not a network handle.");
        }
        return new Network();
    }

    /** AOSP :319 opens through this network's proxy/socket factory; here every network is the default one. */
    public URLConnection openConnection(URL url) throws IOException { return url.openConnection(); }

    /** AOSP binds the socket's fd to this network; on the single default network that is already true. */
    public void bindSocket(Socket socket) throws IOException {}

    /** AOSP :287 returns a factory whose sockets are bound to this network; here that is the default factory. */
    public SocketFactory getSocketFactory() { return SocketFactory.getDefault(); }

    /** AOSP :144 resolves on this network's netId; the default network's resolver is InetAddress's. */
    public InetAddress[] getAllByName(String host) throws UnknownHostException { return InetAddress.getAllByName(host); }
}
