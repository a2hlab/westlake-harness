// Faithful reduction of ScopedIcuLocale.h:39-43 (AOSP external/icu .../ScopedIcuLocale.h).
// UErrorCode is an enum backed by int; U_ZERO_ERROR==0; U_FAILURE(x)==(x>0).
typedef int UErrorCode;                 // mirrors icu's enum (U_ZERO_ERROR=0, failures >0)
extern int forLanguageTag(const char* tag, UErrorCode& status);  // ICU: early-returns if status already failing
extern void use_valid_locale();
// Returns 1 if the locale was accepted (valid), 0 if treated as bogus — mirrors ScopedIcuLocale::valid().
int build_locale(const char* tag) {
    UErrorCode err;                     // ScopedIcuLocale.h:39  — NOT initialized
    forLanguageTag(tag, err);           // ScopedIcuLocale.h:40
    if (err > 0 /*U_FAILURE*/) {        // ScopedIcuLocale.h:41
        return 0;                       //   -> bogus -> getDisplayXxxNative returns NULL -> Java NPE
    }
    use_valid_locale();
    return 1;
}
