# Original baseline, before recovery changes

The first real desktop-icon launch created parent11444 and child13101. Its initial page reported a network error. The board clock was synchronized from1970 and the user connected networking; the same child then displayed the news feed in `original-feed.jpeg`. This proves the original first-launch path for this boot, not manual recovery after a crash. No new recovery payload was deployed.

The original cfg is saved with its exact SHA in `results.json`. The temporary display-timeout override was restored and the observation lock released. Private raw logs remain in the controller’s persistent evidence directory, not tmp.
