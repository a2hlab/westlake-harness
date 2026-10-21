# T37 handoff to cc-video (outer relays)

User confirms final T36 commit a06156a958 contains watchdog 9072bbfb032afc217ed01e369f3ce859b2c63e310e42815158780973f71391bc and outer requested changes. No replay of that old SHA is needed.

Exact counterexamples: candidate-replay-03/{birth_read_failure_after_term,malformed_proc_stat,missing_proc_root,missing_fd_directory,failed_fd_readlink,nonlistener_socket_row,newhost_owned_enum_failure}.receipt.json under this directory. Original five blocker classes are in README.md. Guardrails: parent_owned remains read-only; recorded exact epoch and complete enumerations before signal; strict old-parent exit before sed/inode change; proven socket creation/listener/path ownership before unlink; no second epoch/start/spawn on repeated clicks or partial failures.

New review runner: candidate_review.py --candidate <candidate-dir> --payload <actual-package/payload> --expect-watchdog-sha <64hex> --out <new-T37-run-dir>. --payload may be omitted only for source-only review; assembly then remains failed/unknown. New source SHA is required; known rejected SHAs exit3 without re-executing. Source and payload are read-only. Please provide the complete immutable entry/members/startup/manifest package and exact new SHA, not merely the two src files. A source-only delivery cannot establish entry reaches the candidate.

Delivery status: Herdr socket denied; connected cowork bus requires approval while policy is never. No retry. User explicitly delegated relay to outer. This file is not a successful direct-delivery receipt.
