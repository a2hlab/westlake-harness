# SDK rules source binding

Pinned version: `android-16.0.0_r4`. SDK tests execute the real immutable APK descriptor, ZIP, binary XML parser and production C++ rules. Only the existing HiLog external edge is shimmed.

The first eleven cases in `SPC_11_Contract.DefaultsAndRepeats` retain the expected values of the eleven original `UsesSdkTest` methods in source order. Additional cases cover signed values, namespace identity, null attributes, preview/fingerprinted codenames, min/target/APEX-max error ordering, repeated extension declarations and profile availability.

These fixtures are project tests, not copied CTS execution. The original CTS bytes, APKs, helpers and assertions remain mandatory in SPC-13/SPC-29 tier3. No original CTS source is modified.

| Fixed source | SHA256 of decoded source | Binding |
|---|---|---|
| [core/java/com/android/internal/pm/pkg/parsing/ParsingPackageUtils.java](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r4/core/java/com/android/internal/pm/pkg/parsing/ParsingPackageUtils.java) | `50428e406310bd062e8520ceff92e5baf152ed0894c4f19401a003bcc74ffab5` | 1718–1887: defaults, overwrite and target/min/max/extensions order |
| [core/java/android/content/pm/parsing/FrameworkParsingPackageUtils.java](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r4/core/java/android/content/pm/parsing/FrameworkParsingPackageUtils.java) | `b4db00cfc47f4a34ae991095622f57ce946f067235861dcb4dee22af2a88f339` | 298–445: numeric and codename compatibility |
| [hostsidetests/packagemanager/parsing/host/src/android/content/pm/parsing/cts/host/UsesSdkTest.kt](https://android.googlesource.com/platform/cts/+/android-16.0.0_r4/hostsidetests/packagemanager/parsing/host/src/android/content/pm/parsing/cts/host/UsesSdkTest.kt) | `235ac561ed5ceff0ff70fbff14050977c5e05944e994e6481d6364bfd9c57aea` | All eleven original methods |
| [java/android/os/ext/SdkExtensions.java](https://android.googlesource.com/platform/packages/modules/SdkExtensions/+/android-16.0.0_r4/java/android/os/ext/SdkExtensions.java) | `c9f1bdc6a2ab5d85586e7e100121a1138bab7c171293d9cdd3ca885afd147af4` | getExtensionVersion: recognized IDs and unknown-ID zero |
| [java/com/android/modules/utils/build/UnboundedSdkLevel.java](https://android.googlesource.com/platform/frameworks/libs/modules-utils/+/android-16.0.0_r4/java/com/android/modules/utils/build/UnboundedSdkLevel.java) | `f3adfc147d0c20632df32978113abb8533ea1b9e6098f8a72abbd069a9569f44` | isAtMostInternal/removeFingerprint: APEX target codenames |
| [core/res/res/values/public-final.xml](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r4/core/res/res/values/public-final.xml) | `409d80607492834e1773499f9f00b6b0ead474a1b63e6d35eb549c6b458f82c9` | Android SDK attribute resource IDs |

`SdkProfileV2` comes from the runtime profile owner. Test profiles are explicit fixture inputs. Numeric declaration-only legacy parsing returns no compatibility verdict; preview/extension/APEX resolution requires the profile. Typed compatibility errors are retained alongside the existing parser verdict until the later error-domain/wire tasks consume them.

## Android character and integer boundaries

APEX `UnboundedSdkLevel` calls `Character.isUpperCase(charAt(0))`. Android native calls ICU `u_isupper` (category Lu), not the broader Other_Uppercase property described in Java documentation. Integer parsing uses one optional sign and ICU `u_digit` for each UTF-16 unit. Supplementary letters/digits begin with a surrogate. The table contains only the needed BMP data: 609 Lu ranges and 37 Nd digit sets, generated from the pinned UnicodeData hash; accompanying Unicode-3.0 license is retained.

- [ojluni/src/main/native/Character.cpp](https://android.googlesource.com/platform/libcore/+/android-16.0.0_r4/ojluni/src/main/native/Character.cpp), SHA256 `419ab41a3fc8dcc80d85712a1bb6c8a8b922b9df11fd701a2e1348c9212b2963`.
- [icu4c/source/common/uchar.cpp](https://android.googlesource.com/platform/external/icu/+/android-16.0.0_r4/icu4c/source/common/uchar.cpp), SHA256 `616306226fba773db23db5c917062514c966bd5b360da17d62948333867a46af`.
- [icu4c/source/data/unidata/UnicodeData.txt](https://android.googlesource.com/platform/external/icu/+/android-16.0.0_r4/icu4c/source/data/unidata/UnicodeData.txt), SHA256 `ff58e5823bd095166564a006e47d111130813dcf8bf234ef79fa51a870edb48f`.
- [core/java/com/android/internal/util/XmlUtils.java](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r4/core/java/com/android/internal/util/XmlUtils.java), SHA256 `451b81de0cc2f9835fe179b69e8458c4eee8e02365fb7babea6c763524455530`.

Reproduce the committed table with the decoded fixed source (the generator rejects a different hash):

```sh
python3 tests/oracle/generate_android_character_tables.py --unicode-data UnicodeData.txt --output src/android_character_data.h
```

`+-0` and `0x+-0` throw during TypedArray/XmlUtils integer coercion; the outer full parser maps such exceptions to `INSTALL_PARSE_FAILED_UNEXPECTED_EXCEPTION` (ParsingPackageUtils:673–675). This remains distinct from a parsed negative or invalid extension SDK declaration. Tests also cover fullwidth/Arabic Nd digits, BMP Greek Lu, lowercase, non-Lu Roman numeral and supplementary uppercase codepoints.
