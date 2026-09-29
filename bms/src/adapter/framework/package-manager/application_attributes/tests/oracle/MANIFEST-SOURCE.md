# Version parser source binding

Behavior baseline: Android `android-16.0.0_r4`. Source locators are reference links, never runtime prerequisites.

| Source | File SHA256 | Rule used |
|---|---|---|
| [PackageImpl.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r4/core/java/com/android/internal/pm/parsing/pkg/PackageImpl.java) | `a07d839ec6a66a98128ea0331722b6b40d63fe5cb9e5d55779c76c42253dde4a` | Constructor reads versionCode and versionCodeMajor through getInteger with default 0. |
| [ApkLiteParseUtils.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r4/core/java/android/content/pm/parsing/ApkLiteParseUtils.java) | `08f79c177d44a4cf16709bd829db6556e120f824bd72529689d312ebbd8e1974` | parseApkLite preserves separate 32-bit high/low fields. |
| [TypedArray.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r4/core/java/android/content/res/TypedArray.java) | `5968e6f7f749f670d4c0dbc871bff3c71c818387968fae408b5388d1e2fdcdcc` | getInteger returns the default for TYPE_NULL, preserves TYPE_FIRST_INT..TYPE_LAST_INT bits, and rejects unresolved other types. |

The two production APK parsers share the root-version reader, selecting the Android styleable resource IDs through the existing AXML resource map. Non-Android same-name attributes are ignored, including mixed declarations in either order. Fixtures encode namespace start/end chunks, attribute namespace URI references and distinct string-pool/resource-map entries. The tests feed actual binary XML in ZIP files through both existing parser entry points; they do not implement a second parser. Decimal strings (including values above UINT32_MAX), floats, unresolved references, duplicate version attributes and damaged XML are negative fixtures. The unresolved reference fixture intentionally has no resources.arsc; this is not a claim to have implemented Android resource-table resolution.

V2 is a parser fact alongside the existing receipt: both integer words are decimal strings, with separate presence/source fields. The existing authority's persisted representation is upgraded by its own task. A default-constructed/legacy UNKNOWN value produces no V2 canonical object.

Host tests use the repository's existing HiLog shim and genuine minizip unzip/ioapi sources from zlib 1.3.1 (official archive SHA256 `9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23`). No filesystem, ZIP, AXML, SHA or descriptor-digest decision is mocked. Regular read-only temporary files exercise parsing; sealed-FD enforcement and real install/CTS runs remain separate criteria.

Android resource identity binding: [public-final.xml](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r4/core/res/res/values/public-final.xml), SHA256 `409d80607492834e1773499f9f00b6b0ead474a1b63e6d35eb549c6b458f82c9`. versionCode is `0x0101021b`; versionCodeMajor is `0x01010576`.

Root-source boundary: fixed r4 ParsingPackageUtils reads AndroidManifest TypedArray once when constructing the package; its parseBaseApkTags loop stops at the first root end. Nested unknown tags use ParsingUtils.unknownTag to skip the entire subtree (RIGID_PARSER=false). The JNI full parser follows this boundary; the existing canonical facts parser continues rejecting duplicate/nested manifest structures. The two parser entry points are not assumed to have identical acceptance domains.
