import json
from pathlib import Path
import re
import shutil

from collect import HERE, WS, portable, save, sha


def main():
    source = WS / "westlake-inputs/aosp-14.0.0_r1-src/frameworks/av"
    sums = source / "SHA256SUMS"
    files = []
    for line in sums.read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        name = name.strip().removeprefix("./")
        path = source / name
        if sha(path) != digest:
            raise ValueError("14r1 source mismatch: " + name)
        target = HERE / "inputs/aosp14" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        files.append(dict(path=portable(path), sha256=digest, snapshot=str(target.relative_to(HERE))))
    save("sources.json", dict(tag="android-14.0.0_r1", commit="402dbe885fd58af75e4c1d7e790fbf4bb22f29f9",
        source=portable(source), source_receipt_sha256=sha(source / "SOURCE.txt"), checksums_sha256=sha(sums), files=files))
    headers = source / "media/ndk/include/media"
    symbols = json.loads((HERE / "observations.json").read_text())["unity"]["imports"]
    apis = []
    bodies = []
    for symbol in symbols:
        matches = []
        for header in headers.glob("*.h"):
            original = header.read_text()
            clean = re.sub(r"/\*.*?\*/|//[^\n]*", "", original, flags=re.S)
            pattern = r"^([\w \t*]+)\b" + symbol + r"\s*\((.*?)\)\s*__INTRODUCED_IN\(\d+\)\s*;"
            match = re.search(pattern, clean, re.M | re.S)
            if match:
                matches.append((header, original, match))
        if len(matches) != 1:
            raise ValueError("declaration mismatch: " + symbol)
        header, original, match = matches[0]
        returns = " ".join(match[1].split())
        arguments = []
        identifiers = []
        for index, argument in enumerate(match[2].split(",")):
            argument = " ".join(argument.split())
            argument = argument.replace("_off_t_compat", "off_t")
            if not argument or argument == "void":
                continue
            identifier = "argument" + str(index)
            named = re.search(r"\b([A-Za-z_]\w*)$", argument)
            if named and " " in argument and named[1] not in {"AMediaCodec", "AMediaFormat", "AMediaExtractor", "AMediaDataSource", "AImage", "AImageReader", "void"}:
                argument = argument[:named.start()] + identifier
            else:
                argument += " " + identifier
            arguments.append(argument)
            identifiers.append(identifier)
        signature = returns + " " + symbol + "(" + ", ".join(arguments) + ")"
        body, behavior = implementation(symbol, returns, identifiers)
        bodies.append(signature + " {\n" + "\n".join("    " + statement for statement in body) + "\n}\n")
        line = next(number for number, text in enumerate(original.splitlines(), 1) if symbol + "(" in text or symbol + " (" in text)
        apis.append(dict(symbol=symbol, declaration=signature + ";", returns=returns, behavior=behavior,
                         header=str(header.relative_to(source)), line=line, header_sha256=sha(header)))
    includes = """#include "platform.h"
#include <media/NdkMediaCodec.h>
#include <media/NdkMediaExtractor.h>
#include <media/NdkImageReader.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "objects.c.inc"

const char westlake_mediandk_presence_provenance[] = "westlake-mediandk-v2-typed-unsupported-no-codec";

"""
    (HERE / "candidate.c").write_text(includes + "\n".join(bodies))
    save("api.json", dict(imported_count=50, apis=apis, status_unsupported=-10002,
                          extra_exports=["AMediaFormat_new"], functional_decoding=False))
    (HERE / "exports.map").write_text("{\n  global:\n    " + ";\n    ".join(symbols + ["AMediaFormat_new", "westlake_mediandk_presence_provenance"]) + ";\n  local: *;\n};\n")


def implementation(symbol, returns, args):
    if symbol == "AMediaDataSource_new":
        return ["return calloc(1, sizeof(AMediaDataSource));"], "real-callback-holder-allocation"
    if symbol == "AMediaDataSource_delete":
        return ["free(argument0);"], "real-object-delete"
    if symbol.startswith("AMediaDataSource_set"):
        field = {"setUserdata": "userdata", "setClose": "close", "setGetSize": "get_size", "setReadAt": "read_at"}[symbol.removeprefix("AMediaDataSource_")]
        return ["if (argument0 != NULL) argument0->" + field + " = argument1;"], "real-callback-holder-write"
    if symbol == "AMediaExtractor_new":
        return ["return calloc(1, sizeof(AMediaExtractor));"], "unconfigured-object-allocation"
    if symbol == "AMediaExtractor_delete":
        return ["free(argument0);", "return AMEDIA_OK;"], "real-object-delete"
    if symbol == "AMediaFormat_delete":
        return ["delete_format(argument0);", "return AMEDIA_OK;"], "real-object-delete"
    if symbol == "AMediaFormat_setInt32":
        return ["set_int32(argument0, argument1, argument2);"], "real-int32-property-write"
    if symbol == "AMediaFormat_getInt32":
        return ["return get_int32(argument0, argument1, argument2);"], "real-int32-property-read"
    if symbol == "AImage_deleteAsync":
        return ["(void)argument0;", "if (argument1 >= 0) close(argument1);"], "no-image-produced-release-transferred-fence"
    if returns == "media_status_t":
        body = ["(void)" + name + ";" for name in args]
        if symbol in {"AImageReader_newWithUsage", "AImageReader_acquireLatestImage", "AImageReader_getWindow", "AImage_getHardwareBuffer"}:
            body.append("if (" + args[-1] + " != NULL) *" + args[-1] + " = NULL;")
        body.append("return unsupported_media(__func__);")
        return body, "AMEDIA_ERROR_UNSUPPORTED"
    body = ["(void)" + name + ";" for name in args]
    if "*" in returns:
        if symbol in {"AMediaCodec_getInputBuffer", "AMediaCodec_getOutputBuffer"}:
            body.append("if (" + args[-1] + " != NULL) *" + args[-1] + " = 0;")
        body += ["unsupported_media(__func__);", "return NULL;"]
        return body, "unsupported-pointer-NULL"
    if returns == "bool":
        body.append("return false;")
        return body, "no-item-false-output-unchanged"
    if returns == "void":
        body.append("unsupported_media(__func__);")
        return body, "void-no-object-produced-diagnostic"
    if returns == "size_t":
        body.append("return 0;")
        return body, "unconfigured-no-tracks"
    body.append("return " + ("unsupported_media(__func__);" if symbol.startswith("AMediaCodec_dequeue") else "-1;"))
    return body, "unsupported-code-or-no-sample"


if __name__ == "__main__":
    main()
