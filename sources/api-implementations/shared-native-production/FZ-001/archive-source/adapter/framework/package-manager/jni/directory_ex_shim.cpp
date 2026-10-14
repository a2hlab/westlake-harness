/*
 * directory_ex_shim.cpp — strong definition for the directory_ex.h shim.
 * See that header for the ABI-namespace rationale. Recursive mkdir -p,
 * POSIX only; same semantics as OH c_utils ForceCreateDirectory.
 */
#include "directory_ex.h"

#include <sys/stat.h>
#include <dirent.h>
#include <sys/types.h>
#include <cerrno>
#include <unistd.h>
#include <cstring>
#include <string>

namespace OHOS {

bool ForceCreateDirectory(const std::string& path)
{
    if (path.empty()) {
        return false;
    }
    struct stat st;
    if (stat(path.c_str(), &st) == 0) {
        return S_ISDIR(st.st_mode);
    }
    // mkdir -p: create each parent component, then the final component
    std::string cur;
    cur.reserve(path.size());
    for (size_t i = 0; i < path.size(); ++i) {
        cur.push_back(path[i]);
        if (path[i] == '/' && i > 0) {
            struct stat ps;
            if (stat(cur.c_str(), &ps) != 0 && mkdir(cur.c_str(), 0755) != 0 && errno != EEXIST) {
                return false;
            }
        }
    }
    if (mkdir(cur.c_str(), 0755) != 0 && errno != EEXIST) {
        return false;
    }
    return stat(path.c_str(), &st) == 0 && S_ISDIR(st.st_mode);
}

bool ForceRemoveDirectory(const std::string& path)
{
    if (path.empty()) {
        return false;
    }
    struct stat st;
    if (lstat(path.c_str(), &st) != 0) {
        return errno == ENOENT;  // already gone
    }
    if (!S_ISDIR(st.st_mode)) {
        return false;
    }
    // depth-first: children first, then the dir itself (like remove_all)
    DIR* d = opendir(path.c_str());
    if (d != nullptr) {
        struct dirent* e;
        while ((e = readdir(d)) != nullptr) {
            if (strcmp(e->d_name, ".") == 0 || strcmp(e->d_name, "..") == 0) {
                continue;
            }
            std::string child = path + "/" + e->d_name;
            struct stat cs;
            if (lstat(child.c_str(), &cs) == 0 && S_ISDIR(cs.st_mode)) {
                ForceRemoveDirectory(child);
            } else {
                unlink(child.c_str());
            }
        }
        closedir(d);
    }
    return rmdir(path.c_str()) == 0;
}

}  // namespace OHOS
