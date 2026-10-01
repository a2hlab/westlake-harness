#pragma once
constexpr int LOG_CORE = 0;
namespace OHOS { namespace HiviewDFX {
struct HiLogLabel { int type; unsigned domain; const char* tag; };
struct HiLog {
    static void Info(const HiLogLabel&, const char*, ...) {}
    static void Warn(const HiLogLabel&, const char*, ...) {}
    static void Error(const HiLogLabel&, const char*, ...) {}
};
}}
