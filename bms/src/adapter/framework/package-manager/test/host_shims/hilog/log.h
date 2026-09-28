/*
 * hilog/log.h — HOST-TEST SHIM (not for device/target builds).
 *
 * Maps the OH HiLog surface used by package-manager/jni sources onto
 * stderr so host tests can grep typed tokens (e.g.
 * ICONLESS_APK_TEMPLATE_PLACEHOLDER). Format strings use OH's %{public}s
 * style; this shim strips the visibility wrapper before printing.
 */
#ifndef HOST_SHIM_HILOG_LOG_H
#define HOST_SHIM_HILOG_LOG_H

#include <cstdarg>
#include <cstdio>
#include <string>

enum LogType { LOG_CORE = 0, LOG_APP = 3 };

struct LogLabel {
    LogType type;
    unsigned int domain;
    const char* tag;
};

namespace OHOS {
namespace HiviewDFX {

class HiLog {
public:
    static int Info(const LogLabel& label, const char* fmt, ...)
    {
        va_list ap;
        va_start(ap, fmt);
        int rc = Print("I", label, fmt, ap);
        va_end(ap);
        return rc;
    }
    static int Warn(const LogLabel& label, const char* fmt, ...)
    {
        va_list ap;
        va_start(ap, fmt);
        int rc = Print("W", label, fmt, ap);
        va_end(ap);
        return rc;
    }
    static int Error(const LogLabel& label, const char* fmt, ...)
    {
        va_list ap;
        va_start(ap, fmt);
        int rc = Print("E", label, fmt, ap);
        va_end(ap);
        return rc;
    }

private:
    static int Print(const char* level, const LogLabel& label, const char* fmt, va_list ap)
    {
        // Strip "%{public}" / "%{private}" wrappers -> plain printf verbs.
        std::string plain;
        for (const char* p = fmt; *p != '\0';) {
            if (p[0] == '%' && p[1] == '{') {
                const char* close = p;
                while (*close != '\0' && *close != '}') ++close;
                if (*close == '}') {
                    plain += '%';
                    p = close + 1;
                    continue;
                }
            }
            plain += *p++;
        }
        fprintf(stderr, "%s %s: ", level, label.tag != nullptr ? label.tag : "?");
        int rc = vfprintf(stderr, plain.c_str(), ap);
        fputc('\n', stderr);
        return rc;
    }
};

}  // namespace HiviewDFX
}  // namespace OHOS

// Macro surface used by axml_parser.cpp (which selects it via
// #if defined(HILOG_ERROR)). Real OH HILOG_* take a LogType and build the
// LogLabel internally; mirror that here.
#define HILOG_ERROR(logType, ...) \
    OHOS::HiviewDFX::HiLog::Error(LogLabel{logType, 0, "HILOG"}, __VA_ARGS__)
#define HILOG_INFO(logType, ...) \
    OHOS::HiviewDFX::HiLog::Info(LogLabel{logType, 0, "HILOG"}, __VA_ARGS__)
#define HILOG_WARN(logType, ...) \
    OHOS::HiviewDFX::HiLog::Warn(LogLabel{logType, 0, "HILOG"}, __VA_ARGS__)

#endif  // HOST_SHIM_HILOG_LOG_H
