// Donor for adapter-mainline-stubs android.net.InetAddresses (merge rule: see NetworkInfo.java).
// Source: AOSP android-14.0.0_r1 packages/modules/Connectivity/framework/src/android/net/InetAddresses.java:
// parseNumericAddress = libcore InetAddress.parseNumericAddress (hidden API): a literal only, never DNS, and
// IllegalArgumentException for anything else. Same contract here with public java.net API: getByName() does not
// resolve when given a literal, and non-literals are rejected before it is called.
package android.net;

import java.net.InetAddress;
import java.net.UnknownHostException;

public class InetAddresses {
    public InetAddresses() {}                                         // [existing]

    /** AOSP :45 isNumericAddress = libcore InetAddress.isNumeric (hidden); same literal test as below. */
    public static boolean isNumericAddress(String address) {
        try {
            parseNumericAddress(address);
            return true;
        } catch (IllegalArgumentException e) {
            return false;
        }
    }

    public static InetAddress parseNumericAddress(String address) {
        if (address == null || address.isEmpty() || !address.matches("[0-9.]+|\\[?[0-9a-fA-F:.%A-Za-z]*:[0-9a-fA-F:.%A-Za-z]*\\]?")) {
            throw new IllegalArgumentException("Not a numeric address: " + address);
        }
        try {
            return InetAddress.getByName(address);
        } catch (UnknownHostException e) {
            throw new IllegalArgumentException("Not a numeric address: " + address, e);
        }
    }
}
