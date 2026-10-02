# Gecko compat relocation scope: the resident handle is not the scope

## Incorrect premise and new rule

Window5 already logs three successful resident GNU queries in each failing
Gecko process. Adding the same inherited compat SONAME again is not a proven
repair; it can overwrite an OH namespace edge. No competing namespace patch,
fresh compat copy, global promotion or device experiment is delivered here.
**0 movements are proven; 2 are conditional scope targets, not new lights.**

## Exact consumer and owner evidence

| Key / PID | Successful resident queries | GNU relocation / exception | Terminal |
|---|---|---|---|
| fd-fennec_fdroid / 25084 | 18746,18891,18962 | 19016 / 19024 | SIGKILL9 at19154 |
| firefox / 25608 | 30769,30931,31018 | 31058 / 31068 | SIGKILL9 at31211 |

Paths, raw hilog SHA, original numbered lines and per-PID pointer equality are
in `results.json` and `evidence/*-hilog.txt`. Each process resolves the same GNU
address through the sealed/default resident handles before its load failure.
This proves neither successful app relocation nor a unique whole-process
compat mapping. The two libmozglue consumers NEEDED libdl/liblog/libm/libc,
**not compat**. Their GNU request is LIBC from libc.so, hash0x50d63.

The exact baseline is host65cc3535, ANLeebd62f2, loader0718f01e and
compat015aa3a6; complete hashes are in `results.json`. WHOIS generation-scoped
outputs and explicit baseline paths are retained; no glob-selected copy is used.
GNU and android_dlopen_ext are already exported by actual015aa.

## App versus B8 runtime ClassLoader namespace

Registry::GetOrCreate calls ANL_CreateDomain; Registry::Open calls ANL_Dlopen.
The actual ANL ELF non-libflutter dispatch loads its host callback at4068,
passes the domain base/app namespace at406c and BLRs at40bc. The separate
libflutter path passes domain+0x100 at40b0. Gecko's libmozglue takes the former.
See `evidence/anl-open.txt`; exact failing numeric domain IDs are unlogged and
are not invented. B8 runtime-CL and app-CL instances share the constructor,
but are not proven to be the same namespace instance.

R3's host constructs bridge with CREATE_INHERIT_DEFAULT and app with
LOCAL_NS_PREFERED. Ordinary app domains inherit the bridge allowlist atcfc8
and the already-resident compat-owner whitelist atcffc. The exact source calls
are `inputs/stock-host.c:317` and `:325`. The private-branch default/sealed
inherits are d0a4/d0bc. `open-host` retains all17 edges, 8 open sites, zero
INHERIT-REPEAT and four unchanged INHERIT-AFTER-OPEN syntactic may-paths;
DEFAULT-NS/MULTI-NS are not suppressed. ANL/loader have indirect host dispatch,
so their zero direct open sites/edges does not mean no namespace operations.

### Source-provenance limit

Local frozen b67 app_native_loader.c matches U9 ROUTE_A_INPUTS cc0b48b8;
registry matches db4201cb. **The ANL receipt alone does not reproduce deployed
eebd62f2:** its full source predates the flutter override (actual ELF has
flutter_prepare/third namespace). This source is admitted as a receipt-matched
reference only. App dispatch above is independently established by the actual
ELF, not a claim that current bms-deploy ce216b5a or this old input is the full
deployed source. No rebuild of ANL is attempted.

## Factory linker behavior and coordinated minimal repair

Copied exact fd3c4701 disassembly shows saved symbol scope accepts global
providers or providers relocating in the same/immediate-parent namespace
(80f50–81004); dlopen retention is mode-dependent (867e4–8680c). Its normal
LIBC-hash relocation accepts unversioned providers under the observed empty
requested version-name path (8b220/8b224→8b294). A new LIBC version node is not
established as the fix. There is no traceable factory source/build receipt;
reference dynlink-linux.c is not silently treated as same-source.

Coordinate with cc-wiki's N11h-r2 common host constructor work, preserving
the original single compat edge rather than adding a second same-parent
inherit. **Making bridge/runtime single-copy alone does not demonstrate
compat relocation membership.** Before admitting any scope change, require
the real app consumer GNU relocation to bind to the existing resident compat
address and preserve other imports/owners. Global promotion exposes every
compat export and remains an unapproved alternative, not included in U12.

After GNU resolution, both actual libmozglue files still request absent
strtoll_l; Firefox additionally requests cleanup push/pop. They are static
next missing-symbol candidates, not guaranteed next termination ordering.
Next exact fatal and t20 remain unknown. The VLC export work can supply this
API family later but does not itself establish the app relocation scope.

## Delivery and rollback

This item changes **zero runtime files**; rollback is a no-op. No new build,
ABI delta or new N1/N2 package authorization exists; two-build receipts do not
apply to a read-only audit. The deployed_strings_diff self-comparisons are all
0/0 and explicitly baseline controls, not candidate repair proof. The source,
machine table, portable regressions and preflight form a coordination handoff,
not authorization to stack a second owner patch into cx-t0's draft.
