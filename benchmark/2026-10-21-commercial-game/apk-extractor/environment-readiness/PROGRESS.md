# G10 first slice

Current local CLI: `orbctl status` returned `Stopped`, rc=1 in 0.0073 s. This is OrbStack-wide status, not per-machine proof. No whole-VM-dead claim; a2hlab machine state and cause remain unknown. No run command was repeated while stopped.

Outer-only action: `orbctl start a2hlab`. Help confirms this targets the named machine; bare `orbctl start` restores all previously running machines. Not executed by G10. After outer start, bound `orbctl run -m a2hlab -w / true` to 15 seconds and retain both streams/rc/time.

Local archive 61ff2def and compiler b107ce03 plus five source/command/object pins freshly rehashed: 7/7 match. No native compile, VM start/restart, device action or permissions change. Existing SSH/ps refusal retained, no retry. hw248 is a possible entry only: current access and exact remote hashes unverified. Python 3.10 incompatibility is with old build.py extraction; G09 build_native.py uses native tar.

Raw current evidence: `.private/`; public input hashes: `local-inputs.json`. Canonical board and git delivery pending; use landing if denied.
