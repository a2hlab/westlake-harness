import json
from unittest.mock import patch

import audit
import stats
from test_audit import StatsTests


def old_portable(value):
    return str(value).replace(str(audit.REPO), "$REPO").replace(str(audit.WS), "$WORKSPACES")


def main():
    test = StatsTests("test_selected_and_diagnostic_counts")
    with patch.object(audit, "REPO", audit.WS / "westlake-harness"):
        with patch.object(stats, "portable", old_portable):
            try:
                test.test_selected_and_diagnostic_counts()
            except FileNotFoundError as error:
                if "$REPO-u7-executor/" not in str(error):
                    raise
                print("BEFORE: reproduced FileNotFoundError: " + str(error))
                negative = dict(expected_failure="FileNotFoundError", message=str(error))
            else:
                raise AssertionError("old replacement did not reproduce the known master failure")
        test.test_selected_and_diagnostic_counts()
        print("AFTER: master REPO prefix + actual 166 selected/3 diagnostic records PASS")
    audit.save("evidence/path-prefix-replay.json", dict(device_access=False, master_prefix_simulated=True,
         negative=negative, corrected_stats_pass=True, selected=166, diagnostic_attempts=3,
         full_master_land_executed=False, reason="real master/index outside sandbox writable roots; full land replay uses a disposable master clone"))


if __name__ == "__main__":
    main()
