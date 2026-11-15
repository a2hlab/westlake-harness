package org.westlake.probe.notification;

import android.Manifest;
import android.app.Activity;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Person;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

/**
 * Notification answers on Westlake (ADR-0009), one line each: [WL-NOTIFY-PROBE] <name> = <value>.
 *
 * Creates four channels (high, default, low, min) and posts eight notifications: plain, big text, inbox,
 * progress, min importance, a messaging style under a tag, one cancelled after 8 s, and one on a channel that was
 * never created. The progress one is updated at 5 s and finished at 10 s. At 90 s everything is cancelled with
 * cancelAll. What OH shows is read on the device side (hidumper -s 3203 -a --active); this app logs what Android
 * answers it.
 */
public class MainActivity extends Activity {
    private static final String TAG = "WL-NOTIFY-PROBE";
    private final Handler main = new Handler(Looper.getMainLooper());
    private NotificationManager nm;

    static void line(String name, Object value) {
        String text = "[" + TAG + "] " + name + " = " + value;
        System.err.println(text);
        Log.i(TAG, text);
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        nm = getSystemService(NotificationManager.class);
        line("service", nm != null ? "present" : "null");
        if (nm == null) {
            line("verdict", "FAIL_NO_SERVICE");
            return;
        }
        line("enabled", nm.areNotificationsEnabled());
        channel("high", "High", NotificationManager.IMPORTANCE_HIGH);
        channel("default", "Default", NotificationManager.IMPORTANCE_DEFAULT);
        channel("low", "Low", NotificationManager.IMPORTANCE_LOW);
        channel("min", "Min", NotificationManager.IMPORTANCE_MIN);
        line("channels", nm.getNotificationChannels().size());
        requestPermissions(new String[] {Manifest.permission.POST_NOTIFICATIONS}, 1);
    }

    private void channel(String id, String name, int importance) {
        NotificationChannel channel = new NotificationChannel(id, name, importance);
        channel.setSound(null, null);   // the probe makes no noise; LocalNotifications' sound path is tested elsewhere
        nm.createNotificationChannel(channel);
    }

    private Notification.Builder builder(String channel, String title, String text) {
        return new Notification.Builder(this, channel)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle(title)
                .setContentText(text);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        line("permission-request", grantResults.length > 0 && grantResults[0] == 0 ? "granted" : "denied");
        post();
    }

    private void post() {
        nm.notify(1, builder("default", "Probe 1: default", "Plain text, auto-cancel").setAutoCancel(true).build());
        nm.notify(2, builder("high", "Probe 2: high ✓ 🙂", "Big text style")
                .setStyle(new Notification.BigTextStyle().bigText(
                        "Big text: Westlake shows an Android app's notification in OH's notification centre. "
                                + "This one is on a high-importance channel, so OH shows a banner."))
                .build());
        nm.notify(3, builder("low", "Probe 3: low", "Inbox style")
                .setStyle(new Notification.InboxStyle().addLine("Line one").addLine("Line two").addLine("Line three")
                        .setSummaryText("3 lines"))
                .build());
        nm.notify(4, builder("default", "Probe 4: progress", "30%").setProgress(100, 30, false).setOngoing(true)
                .setOnlyAlertOnce(true).build());
        nm.notify(5, builder("min", "Probe 5: min", "Minimum importance").build());
        Person ada = new Person.Builder().setName("Ada").build();
        nm.notify("chat", 6, builder("high", "Probe 6: messages", "2 messages")
                .setCategory(Notification.CATEGORY_MESSAGE)
                .setStyle(new Notification.MessagingStyle(new Person.Builder().setName("Me").build())
                        .addMessage("Hello from the probe", System.currentTimeMillis() - 60_000, ada)
                        .addMessage("Second message", System.currentTimeMillis(), ada))
                .build());
        nm.notify(7, builder("default", "Probe 7: cancelled at 8 s", "Should disappear").build());
        nm.notify(8, builder("never-created", "Probe 8: unknown channel", "Channel never created").build());
        line("posted", 8);
        line("active after posting", nm.getActiveNotifications().length);
        main.postDelayed(() -> {
            nm.notify(4, builder("default", "Probe 4: progress", "60%").setProgress(100, 60, false).setOngoing(true)
                    .setOnlyAlertOnce(true).build());
            line("updated", "4 to 60%");
        }, 5_000);
        main.postDelayed(() -> {
            nm.cancel(7);
            line("cancelled", 7);
        }, 8_000);
        main.postDelayed(() -> {
            nm.notify(4, builder("default", "Probe 4: progress", "Done").setOnlyAlertOnce(true).build());
            line("updated", "4 done");
            line("active at 10 s", nm.getActiveNotifications().length);
        }, 10_000);
        main.postDelayed(() -> {
            nm.cancelAll();
            line("cancelled", "all");
            line("active after cancelAll", nm.getActiveNotifications().length);
            line("verdict", "DONE");
        }, 90_000);
    }
}
