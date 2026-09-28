#include "apk_manifest_parser.h"

#include <iostream>
#include <map>
#include <string>

int main(int argc, char** argv)
{
    if (argc != 2) {
        std::cerr << "usage: service_manifest_test APK\n";
        return 2;
    }

    oh_adapter::ApkManifestParser::ManifestData manifest;
    if (!oh_adapter::ApkManifestParser::Parse(argv[1], manifest)) {
        std::cerr << "manifest parse failed\n";
        return 3;
    }

    std::map<std::string, std::string> expected {
        {"com.a2hlab.bridge.fn07.serviceprobe.LocalEchoService", ""},
        {"com.a2hlab.bridge.fn07.serviceprobe.NullBindingService", ""},
        {"com.a2hlab.bridge.fn07.serviceprobe.RebindService", ""},
        {"com.a2hlab.bridge.fn07.serviceprobe.RemoteService", ":remote"},
    };
    if (manifest.packageName != "com.a2hlab.bridge.fn07.serviceprobe" ||
        manifest.services.size() != expected.size()) {
        std::cerr << "unexpected package/service count: " << manifest.packageName
                  << " count=" << manifest.services.size() << "\n";
        return 4;
    }

    for (const auto& service : manifest.services) {
        auto it = expected.find(service.name);
        if (it == expected.end() || it->second != service.processName ||
            service.exported || !service.permission.empty()) {
            std::cerr << "service mismatch: " << service.name
                      << " process=" << service.processName
                      << " exported=" << service.exported
                      << " permission=" << service.permission << "\n";
            return 5;
        }
        std::cout << service.name << '\t'
                  << (service.processName.empty() ? "<default>" : service.processName)
                  << "\texported=false\n";
    }
    std::cout << "FN07_SERVICE_MANIFEST_PARSE_PASS count="
              << manifest.services.size() << "\n";
    return 0;
}
