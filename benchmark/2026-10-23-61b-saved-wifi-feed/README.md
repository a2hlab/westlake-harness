# T59: saved WiFi and Toutiao content continuation

The T58 network-error screen was not proof that the application launch chain was broken. During the 235-second T59 window (10:49:20–10:53:15 CST), ordinary Settings UI connected a saved compatibility network without entering or reading credentials. Toutiao's retry then showed a populated feed. One article still failed with a network-error page; another displayed its text body. In-app return and feed scrolling were observed. Original failures remain alongside successes.

This is a continuation of the same boot and live application process, not a new boot's first icon tap. Connectivity was not stable: the device obtained an IPv4 address and a route, then lost both within roughly three minutes. The WiFi service dump also disagreed with Settings/ifconfig during connection. A populated or cached feed does not establish continuous Internet access.

Evidence: `04-tt-r8.jpeg` (feed), `05-content-c16.jpeg` (first article failure), `05-content-x12.jpeg` (second article text, image placeholder), `05-content-b3b.jpeg` and `05-content-b4.jpeg` (return), `05-content-s3b.jpeg` (scroll). `results.json` preserves the inner record; `outer-review.json` binds the missing literal `%s` hash and distinguishes current observations from unverified claims. WiFi settings screenshots remain in the persistent private raw directory named in that review.

The actual `run.sh` comparison is supplied, including both inputs: only line 19 differs (`WL_PARENT_ID=30` to `32`). The standard `/usr/bin/diff` returned 1 for the difference. An earlier PATH-selected DevEco `diff` returned 0 despite printing a difference; its original receipt is retained privately. No script was changed on the board by this observation.

Power restoration was independently read as Timeout=30000ms and OverrideTimeout=10000ms before the window was released. No runtime deployment, process-close/reopen test or new seal occurred. Next action is a bounded connection-stability observation before attempting a final reboot-and-first-icon check.
