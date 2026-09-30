#!/bin/bash
# Wait for the operator to attach herdr (their own `herdr` starts the server), then open the inner-loop pane in
# westlake-harness with the octoscode start command typed but not submitted: pressing Enter stays the operator's call.
. "$(dirname "${BASH_SOURCE[0]}")/lab_paths.sh" || exit 1
for i in $(seq 1 720); do
  if herdr status 2>/dev/null | grep -q "status: running" && tail -n 3 ~/.config/herdr/herdr-client.log | grep -q "handshake succeeded"; then
    sleep 2
    herdr pane list 2>/dev/null | grep -q '"label":"inner-loop"' && { echo "inner-loop pane already exists"; exit 0; }
    W=$(herdr pane list 2>/dev/null | python3 -c "import json,sys;p=json.load(sys.stdin)['result']['panes'];print(p[0]['pane_id'] if p else '')")
    [ -z "$W" ] && { sleep 5; continue; }
    P=$(herdr pane split "$W" --direction right --cwd "$WORKSPACES/westlake-harness" --no-focus | grep -o -E '"pane_id":"[^"]+"' | head -1 | cut -d'"' -f4)
    herdr pane rename "$P" inner-loop >/dev/null; sleep 1
    herdr pane send-text "$P" 'octoscode --stdio-command "octos serve --stdio --solo --danger-full-access"' >/dev/null
    echo "attached; inner-loop pane $P created beside $W, start command typed (not submitted)"; exit 0
  fi
  sleep 10
done
echo "no herdr client attached within 2 hours"
