# T119 addendum — JIT and REQUEST dependency identity (5cd, read-only, 0.8 s of 90 s)

**Paths.** The two paths come from the t4 path-locator. CC checked that both cited source files (`appendix-5cd/appendix.json`, `selfcheck-5cd-r5.json`) match their recorded SHA-256, and that each cited line contains both the path and the SHA.

**Identity.** Boot ecb84d86 and host 5074 (birth 9930, Uid/Gid 20011300) were identical before and after the read.

| Field | Path | Actual SHA = declared | Size | Owner | Mode |
|---|---|---|---|---|---|
| JIT | `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bf…/prepare_jit50.sh` | **yes** (b42a28e7…), stable | 700 | 20011300:20011300 | 644 |
| REQUEST | `/data/local/tmp/a2hlab-app-c91d26bf…/request.bin` | **yes** (011a1625…), stable | 672 | 0:0 | 644 |

The files were stat-ed and hashed only; their content was not read and nothing was executed. The first-draft `unknown` rows in `../results.json` are kept unchanged as history.
