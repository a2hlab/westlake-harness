# T8 §276 identity gate + three surgical patches (#90, offline, no re-bake yet)

Per DIGEST §276 (baseline jar identity is the real gate), confirmed each class's **deployed** stage jar and the exact
signatures, from the deployed generation `westlake-generation-u9-j10g-238ffc14/native/payload/android/framework/*.jar`
(dexdump, build-tools 37.0.0). Re-bake waits for outer-ring go. ③b is cx-bms (native).

## §276 identity gate — results (deployed j10g-238ffc14)
| item | class | deployed stage jar | state in the deployed jar | signature pinned |
|---|---|---|---|---|
| ① | `com.android.org.conscrypt.SSLParametersImpl` | `adapter-mainline-stubs.jar` (BCP) | **ABSENT** (dexdump count 0) — the presence-only stub is in mainline-stubs *source* but was not in the baked j10g jar | n/a (new class) |
| ② | `adapter.packagemanager.PackageManagerAdapter` | **`oh-adapter-framework.jar` (BCP)** — 357 refs; **not** `adapter-runtime-bcp.jar` (this generation uses oh-adapter-framework.jar), and **0** in the non-BCP `oh-adapter-runtime.jar` | `getInstallSourceInfo(String,int)` **exists**, body = `logStub(...); const/4 v1,0; return-object v1` → **returns null** (the NameNotFound trigger) | `android.content.pm.InstallSourceInfo` in deployed `framework.jar` has **PUBLIC** ctor `(String initiatingPackageName, SigningInfo, String originatingPackageName, String installingPackageName)V` (0x10001) and a 6-arg public ctor; the 4-arg is the target |
| ③a | `com.android.i18n.phonenumbers.PhoneNumberUtil` | `adapter-mainline-stubs.jar` (BCP) | **empty shell present** (18-line stub: empty ctor + 3 empty nested classes); `getInstance` method count = **0** → `NoSuchMethodError` | n/a (replace class + metadata) |

All three are BCP → changing them needs a boot-image re-bake (T7d/FZ-005 pipeline, design.md). The patches below are
written; **re-bake is held** for the outer ring (next round).

## Patch ② — `PackageManagerAdapter.getInstallSourceInfo` → all-null `InstallSourceInfo` (CONCRETE, applyable)
Surgical smali on `oh-adapter-framework.jar` (baksmali → edit the one method → smali 2.5.2 `-a 29` → dex 039, the
CLAMP48 path; 0 deletions, pure method-body swap). Current → new:
```smali
# BEFORE (returns null -> app sees NameNotFound):
#   const-string v1, "getInstallSourceInfo"
#   const-string v2, ""
#   invoke-direct {p0, v1, v2}, ...->logStub(Ljava/lang/String;Ljava/lang/String;)V
#   const/4 v1, 0x0
#   return-object v1
.method public getInstallSourceInfo(Ljava/lang/String;I)Landroid/content/pm/InstallSourceInfo;
    .locals 5
    const-string v0, "getInstallSourceInfo"
    const-string v1, ""
    invoke-direct {p0, v0, v1}, Ladapter/packagemanager/PackageManagerAdapter;->logStub(Ljava/lang/String;Ljava/lang/String;)V
    # all-null = "installed by nobody", the truthful route-A answer (no initiating/originating/installing pkg, no signing info)
    new-instance v0, Landroid/content/pm/InstallSourceInfo;
    const/4 v1, 0x0
    const/4 v2, 0x0
    const/4 v3, 0x0
    const/4 v4, 0x0
    invoke-direct {v0, v1, v2, v3, v4}, Landroid/content/pm/InstallSourceInfo;-><init>(Ljava/lang/String;Landroid/content/pm/SigningInfo;Ljava/lang/String;Ljava/lang/String;)V
    return-object v0
.end method
```
(Also in `cluster2-getInstallSourceInfo.smali`.) The 4-arg ctor is PUBLIC (0x10001) and `PackageManagerAdapter` is in a
different package (`adapter.packagemanager` vs `android.content.pm`), so PUBLIC is required and confirmed — no reflection
or Parcel. `logStub` is kept (unchanged). `.locals` bumped 2→5 for the instance + four null args.

Source-tree equivalent (if `/home/dspfac/bridge-build` is reachable), `PackageManagerAdapter.java`:
```java
public InstallSourceInfo getInstallSourceInfo(String packageName, int flags) {
    logStub("getInstallSourceInfo", "");
    return new InstallSourceInfo(null, null, null, null);  // installed by nobody
}
```

## Patch ① — `SSLParametersImpl` presence stub: build-inclusion (no surgery)
The class is a **new addition**, not a method patch: the presence-only stub already exists at
`framework/mainline-stubs/java/com/android/org/conscrypt/SSLParametersImpl.java` (private throwing ctor; okhttp only
needs the class to *exist* + probe a field — TLS goes through JSSE/SSLSockets, §676/§441). The "patch" is: **include it
in the `adapter-mainline-stubs.jar` build** (d8 adds the class) so it is in the baked image — it is absent from the
deployed jar (gate above). No smali surgery. Verify after build: dexdump count ≥1 for
`Lcom/android/org/conscrypt/SSLParametersImpl;` and that the jar goes into `swap_jars` (G1).

## Patch ③a — `PhoneNumberUtil`: replace the empty shell with real AOSP libphonenumber (class replacement)
Not a tiny surgery — the 18-line shell must be replaced by the real `com.android.i18n.phonenumbers.PhoneNumberUtil`
(+ `PhoneNumberUtil.getInstance()` and the metadata it loads). Source = AOSP `external/libphonenumber`
(the i18n-repackaged `com.android.i18n.phonenumbers.*`), same move as T7d replacing the tagsoup stub with full AOSP r1
tagsoup. Build-inclusion into `adapter-mainline-stubs.jar`:
- bring the real `PhoneNumberUtil` + its direct deps (Phonemetadata, metadata loader) and the **metadata assets**
  (`/com/android/i18n/phonenumbers/data/PhoneNumberMetadataProto*`), which `createInstance`/`getInstance` loads via the
  classloader resource stream — confirm the resource path resolves from the baked jar (if assets can't ship in the jar,
  a metadata-less `getInstance()` that returns a util with empty metadata avoids the NoSuchMethodError but limits
  parsing; clipboardeditor only needs `getInstance()` to resolve, so a minimal real `getInstance()` + lazy/empty
  metadata is the floor).
- size: libphonenumber + metadata adds ~hundreds of KB to the BCP → check image budget + G1 checksum.

## Re-bake bundle + gates (held for outer-ring go)
①②③a ride **one** re-bake (all touch BCP jars: ①③a `adapter-mainline-stubs.jar`, ② `oh-adapter-framework.jar`): RB-off
host dex2oat (oat247, concurrent-copying=false), overlay 27 files (libart untouched), 4 offline gates (rb / t4b /
image_predeploy G1 both changed jars in `swap_jars` / G2 suspend-check shape). Regression controls + evidence apps per
design.md. Evidence: dexdump of the deployed j10g-238ffc14 framework jars (counts + ctor flags above).
