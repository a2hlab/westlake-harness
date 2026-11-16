# notification-answers probe

Records what Westlake answers an app that posts notifications (ADR-0009), one line each
(`[WL-NOTIFY-PROBE] <name> = <value>`), and gives OH's notification centre something to show:

- whether NotificationManager exists and `areNotificationsEnabled`, four channels created (high, default, low,
  min) and the answer of a POST_NOTIFICATIONS request;
- eight notifications: plain with auto-cancel (default), big text (high), inbox (low), progress at 30% (default,
  ongoing, alert once), min importance, a messaging style under the tag `chat` (high, category message), one that
  is cancelled at 8 s, and one on a channel that was never created;
- the progress one updated to 60% at 5 s and finished at 10 s;
- `getActiveNotifications` after posting, at 10 s and after `cancelAll` at 90 s; `verdict = DONE` at 90 s.

The channels have no sound, so the probe makes no noise. What OH shows is read on the device:
`hidumper -s 3203 -a --active` lists OH's active notifications with their owner, label, slot and reminder flags.

    ./build.sh      # out/notification-answers-probe.apk (pure Java; D8 from the cmdline-tools R8 jar)

## First runs (2026-11-14)

The host application's notification switch on: `enabled = true`, four channels, POST_NOTIFICATIONS granted.
OH showed all eight, owned by the host application and labelled `<package>|<tag>`: slot 1 (SERVICE_REMINDER) for
the default, low, high and unknown-channel ones, slot 0 (SOCIAL_COMMUNICATION) for the messaging style, slot 2
(CONTENT_INFORMATION: no status bar icon, under "more notifications") for min. OH's sound and vibration were off for
all of them, and no banner showed: OH leaves an ordinary application's banners off until the user allows them.

The first build passed the label only as PublishNotification's argument. OH stored the notifications without it,
so every cancel failed with ERR_ANS_NOTIFICATION_NOT_EXISTS. With the label set on the request, the cancel at 8 s
and the `cancelAll` at 90 s removed them from OH's list.
