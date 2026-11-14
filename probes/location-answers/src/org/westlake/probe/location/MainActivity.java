package org.westlake.probe.location;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;
import android.os.CancellationSignal;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import java.util.List;

/**
 * Location answers on Westlake (ADR-0009), one line each: [WL-LOC-PROBE] <name> = <value>.
 *
 * The device's location switch and providers; what a runtime permission request is answered; the last known
 * location; a one-shot getCurrentLocation; and a listener on the fused provider for 60 seconds, counting fixes.
 * Coordinates are never logged: only whether a fix came, its provider and its accuracy.
 */
public class MainActivity extends Activity {
    private static final String TAG = "WL-LOC-PROBE";
    private static final long LISTEN_MS = 60_000;
    private final Handler main = new Handler(Looper.getMainLooper());
    private LocationManager lm;
    int fixes;

    static void line(String name, Object value) {
        String text = "[" + TAG + "] " + name + " = " + value;
        System.err.println(text);
        Log.i(TAG, text);
    }

    static String describe(Location location) {
        if (location == null) return "null";
        return "fix from " + location.getProvider() + ", accuracy " + Math.round(location.getAccuracy()) + " m, age "
                + (System.currentTimeMillis() - location.getTime()) / 1000 + " s";
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        lm = getSystemService(LocationManager.class);
        line("service", lm != null ? "present" : "null");
        if (lm == null) {
            line("verdict", "FAIL_NO_SERVICE");
            return;
        }
        line("location-enabled", lm.isLocationEnabled());
        List<String> all = lm.getAllProviders();
        line("providers", all);
        for (String provider : all) line("provider-enabled " + provider, lm.isProviderEnabled(provider));
        line("check-self fine", checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED);
        requestPermissions(new String[] {Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION}, 1);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        StringBuilder answer = new StringBuilder();
        for (int i = 0; i < permissions.length; i++) {
            answer.append(permissions[i].substring(permissions[i].lastIndexOf('.') + 1)).append(':')
                    .append(grantResults[i] == PackageManager.PERMISSION_GRANTED ? "granted" : "denied").append(' ');
        }
        line("permission-request", answer.toString().trim());
        startRequests();
    }

    private void startRequests() {
        try {
            line("last-known fused", describe(lm.getLastKnownLocation(LocationManager.FUSED_PROVIDER)));
        } catch (RuntimeException e) {
            line("last-known fused", "threw " + e);
        }
        final long started = System.currentTimeMillis();
        try {
            lm.getCurrentLocation(LocationManager.FUSED_PROVIDER, new CancellationSignal(), getMainExecutor(),
                    new Current(started));
        } catch (RuntimeException e) {
            line("current-location", "threw " + e);
        }
        final LocationListener listener = new Fixes();
        try {
            lm.requestLocationUpdates(LocationManager.FUSED_PROVIDER, 1000L, 0f, listener, Looper.getMainLooper());
            line("listener", "registered on fused, every 1 s");
        } catch (RuntimeException e) {
            line("listener", "threw " + e);
        }
        main.postDelayed(() -> {
            lm.removeUpdates(listener);
            line("listener fixes in " + LISTEN_MS / 1000 + " s", fixes);
            line("verdict", fixes > 0 ? "PASS_FIXES" : "NO_FIXES");
        }, LISTEN_MS);
    }

    /** getCurrentLocation's answer. */
    static final class Current implements java.util.function.Consumer<Location> {
        private final long started;

        Current(long started) {
            this.started = started;
        }

        @Override
        public void accept(Location location) {
            line("current-location", describe(location) + " after " + (System.currentTimeMillis() - started) / 1000 + " s");
        }
    }

    /** The listener's fixes, counted; the first three logged. */
    final class Fixes implements LocationListener {
        @Override
        public void onLocationChanged(Location location) {
            fixes++;
            if (fixes <= 3) line("listener fix " + fixes, describe(location));
        }

        @Override
        public void onProviderEnabled(String provider) {
            line("listener provider-enabled", provider);
        }

        @Override
        public void onProviderDisabled(String provider) {
            line("listener provider-disabled", provider);
        }
    }
}
