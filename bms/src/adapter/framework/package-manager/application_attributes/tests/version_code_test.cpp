#include "version_code.h"
#include "version_oracle_values.h"

#include <gtest/gtest.h>

namespace oh_adapter::application_attributes {
namespace {

TEST(SPC_02_Contract, AllBitPatterns)
{
    for (const auto& value : VERSION_ORACLE) {
        SCOPED_TRACE(::testing::Message() << "major=" << value.major
            << " minor=" << value.minor);
        EXPECT_EQ(ComposeVersionCodeBits({value.major, value.minor}), value.bits)
            << "SPC02_BIT_PATTERN_MUST_MATCH_ANDROID";
    }
}

TEST(SPC_02_Contract, SignedAndRoundtrip)
{
    for (const auto& value : VERSION_ORACLE) {
        SCOPED_TRACE(::testing::Message() << "bits=" << value.bits);
        const auto split = SplitVersionCodeBits(value.bits);
        EXPECT_EQ(split.major, value.splitMajor) << "SPC02_MAJOR_ROUNDTRIP";
        EXPECT_EQ(split.minor, value.splitMinor) << "SPC02_MINOR_ROUNDTRIP";
        EXPECT_EQ(ComposeVersionCodeBits(split), value.bits) << "SPC02_FULL_ROUNDTRIP";
        EXPECT_EQ(JavaLongFromVersionBits(value.bits), value.javaLong)
            << "SPC02_SIGNED_JAVA_LONG";
    }
}

}  // namespace
}  // namespace oh_adapter::application_attributes
