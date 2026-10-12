# Capture/feed reboot: independent 20-key image review

Process survival and runner success were previously easy to mistake for a displayed app. This review uses the actual final t10/t20 images, including desktop-only Anki/NewPipe/VLC, blank dddmodel2, the blank HTML area inside the CaniWebView shell, and the black preview inside BinaryEye's visibly rendered scanner UI. It does not authorize sealing or infer working app functions from a welcome screen.

All recorded rows bind boot `9f5af7c8-d359-4c25-99c6-63206b50cf0a`. The first window stopped at its 35-minute new-key cutoff after 19 keys; the remaining OrganicMaps key uses a separate same-boot window. The prior red pre-lock round is preserved; no completed key was re-run by this reviewer. Device/VM/remote commands: **0**. Candidate mutations: **0**.

`image-review.json` records each original final-image SHA, concrete visible UI, historical **reported** t3 verdict, and terminal-log attribution. `facts-verbatim.txt` quotes each available round facts file unchanged; liveness and `foreground_unconfirmed` do not establish on-screen content. Caught `[B8-NATIVE]` optional HTML-library load errors also occur in visibly rendered apps, so they are retained as warnings rather than promoted to a fatal cause. NewPipe's WMS `already existed in array` rejection is an observation, not proof of SIGSEGV.

Missing or unreviewed keys: **none**.

| Key | Reported reference | This run: original final image | Visible evidence |
|---|---|---|---|
| anki | lit | desktop_only_not_lit | Launcher icon grid with AnkiDroid icon, no Anki app UI |
| fd-reader | lit | own_app_ui_visible | Read You welcome artwork, terms/privacy text and agree/continue button; no consent interaction or functional-read claim |
| fd-client | lit | own_app_ui_visible | Nextcloud onboarding: logo, data-control text, carousel indicators, login/provider/self-host buttons; no account/login operation |
| fd-noice | lit | own_app_ui_visible | Noice welcome screen with logo, explanatory text, skip/next controls; not a playback claim |
| fd-feeder | lit | own_app_ui_empty_state | Feeder all-feeds toolbar with menu/search/filter, explicit no-readable-content message and open/add-feed controls; rendered empty state, not pure-white frame or retrieved feeds |
| fd-com-amaze-filemanager | lit | own_app_ui_visible | Amaze file-manager toolbar, current external path, 1 folder/0 files count and Android folder row rendered; no file-operation claim |
| cv2-com-kaajjo-libresudoku | lit | own_app_ui_visible | LibreSudoku rendered 9x9 grid with digits, instructions, start button and language/backup/settings rows; gameplay interaction not exercised |
| fd-uhabits | lit | own_app_ui_empty_state | Loop habits screen: title, plus/filter/menu, weekday/date header and star with no-habits message; no created habit or interaction claim |
| cv2-org-secuso-privacyfriendly2048 | lit | own_app_ui_visible | Privacy Friendly 2048 Welcome tutorial with logo/grid illustration, explanatory text and SKIP/NEXT controls; not gameplay verification |
| cv2-org-andresoviedo-dddmodel2 | not_lit | blank_app_frame_not_lit | Uniform dark-gray content area with only status/navigation bars; no model, controls or text, cannot call lit |
| cv2-org-secuso-privacyfriendlyminesweeper | lit | own_app_ui_visible | Minesweeper welcome/tutorial page with mine illustration, game instructions and SKIP/NEXT controls; no gameplay input claim |
| cv2-com-ath0-rpn | lit | own_app_ui_visible | RPN calculator with 0.00 display, number keys, SWAP/DROP/ENTER and operations; arithmetic interaction not exercised |
| cv2-com-darkempire78-opencalculator | lit | own_app_ui_visible | OpenCalc colored number/operation keypad and display panel rendered; display initially blank/underscore, no arithmetic interaction |
| cv2-biz-binarysolutions-vatcalculator | lit | own_app_ui_visible | VAT calculator Albania/6 percent selectors and Base/Tax/Total fields plus Show support; no calculation performed, activity-qualified title visible |
| cv2-com-caniwebview-android | lit | own_app_shell_web_content_blank | CaniWebView toolbar, local-assets URL, LOAD button and WebView/Config tabs visible; large web-content area blank, cannot claim HTML rendered |
| newpipe | not_lit | desktop_only_not_lit | Launcher icon grid with NewPipe icon only, no NewPipe own UI; icon presence cannot establish lit |
| wikipedia | lit | own_app_ui_visible | Wikipedia welcome/knowledge page with Chinese explanatory text, more-info link, globe illustration and next arrow; no article/network interaction claim |
| fd-binaryeye | lit | own_app_ui_camera_preview_black | BinaryEye scanner UI: title, history/add/file/menu icons, crop/flash controls and bottom slider visibly rendered; black camera-preview area, no actual barcode/camera-image verification |
| vlc | not_lit | desktop_only_not_lit | Launcher grid with VLC cone icon, no VLC activity UI; no playback claim |
| fd-organicmaps | lit_splash | own_app_splash_only | Organic Maps green logo/splash with OpenStreetMap attribution; no map canvas or usable controls visible at t20 |

Source paths are relative to the canonical master tree. Images/large logs remain there and are individually pinned in `sources.json`; no private large stderr or user-data archive is included. Formal overall judgement remains with the outer reviewer.
