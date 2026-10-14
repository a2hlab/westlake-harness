#!/usr/bin/env python3
"""Restore the two exact FZ002 archives into a new, private build directory."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tarfile

from acquire import sha256, verify


def layout():
    return json.loads(Path(__file__).with_name("archive-layout.lock.json").read_text())


def mapped_name(name, component):
    path = PurePosixPath(name)
    if ".." in path.parts:
        raise ValueError("ARCHIVE_TRAVERSAL")
    try:
        offset = path.parts.index(component)
    except ValueError as error:
        if component == "b68-generation":
            for member in layout()["auxiliary_members"]:
                if member["marker"] in path.parts:
                    position = path.parts.index(member["marker"])
                    suffix = PurePosixPath(*path.parts[position + 1:]).as_posix()
                    if suffix == member["suffix"]:
                        return "_external/" + member["marker"] + "/" + suffix
        raise ValueError("UNEXPECTED_ARCHIVE_ROOT " + name) from error
    suffix = path.parts[offset + 1:]
    if component == "platform-link":
        suffix = ("platform-link",) + suffix
    return PurePosixPath(*suffix).as_posix()


def restore(archive, destination, component):
    links = []
    count = 0
    with tarfile.open(archive, "r:gz") as stream:
        for member in stream:
            if any(part.startswith("._") for part in PurePosixPath(member.name).parts):
                continue
            name = mapped_name(member.name, component)
            if name == ".":
                continue
            target = destination / name
            for parent in [target] + list(target.parents):
                if parent == destination.parent:
                    break
                if parent.is_symlink():
                    raise ValueError("ARCHIVE_SYMLINK_PARENT " + name)
            if target.exists() and not (target.is_dir() and member.isdir()):
                raise ValueError("ARCHIVE_DUPLICATE " + name)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as output, stream.extractfile(member) as source:
                    while block := source.read(1024 * 1024):
                        output.write(block)
                target.chmod(member.mode & 0o777)
                if name.startswith("_external/"):
                    entry = next(item for item in layout()["auxiliary_members"] if name == "_external/" + item["marker"] + "/" + item["suffix"])
                    verify(target, entry["sha256"])
            elif member.issym() or member.islnk():
                links.append((member, name))
            else:
                raise ValueError("UNSUPPORTED_ARCHIVE_MEMBER " + name)
            count += 1
    for member, name in links:
        target = destination / name
        link = PurePosixPath(member.linkname)
        if member.islnk() or link.is_absolute():
            if "b68-generation" in link.parts:
                translated = destination / mapped_name(member.linkname, "b68-generation")
            elif "platform-link" in link.parts:
                translated = destination / mapped_name(member.linkname, "platform-link")
            else:
                suffix = member.linkname.split("/.work/", 1)[-1]
                declared = next((item for item in layout()["absolute_links"] if item["name"] == name and item["target_marker_suffix"] == suffix), None)
                if declared is None:
                    raise ValueError("EXTERNAL_ARCHIVE_LINK " + name)
                if suffix.startswith("product-tls-generation/frozen/"):
                    translated = destination / ".work" / suffix
                else:
                    translated = destination / "_unprovided_test_dependencies" / suffix
            value = os.path.relpath(translated, target.parent)
        else:
            value = member.linkname
        resolved = (target.parent / value).resolve()
        if not resolved.is_relative_to(destination.resolve()):
            raise ValueError("ARCHIVE_LINK_ESCAPE " + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if member.issym():
            target.symlink_to(value)
        else:
            os.link(resolved, target)
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--external", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads(Path(__file__).with_name("dependencies.lock.json").read_text())
    entries = {entry["id"]: entry for entry in lock["archives"]}
    verify(args.inputs, entries["FZ002_GENERATION"]["sha256"])
    verify(args.external, entries["FZ002_PLATFORM_LINK"]["sha256"])
    args.out.mkdir(parents=True, exist_ok=False)
    receipt = {"inputs_sha256": sha256(args.inputs), "external_sha256": sha256(args.external), "generation_path": str(args.out.resolve()), "build_executed": False}
    try:
        receipt["generation_members"] = restore(args.inputs, args.out, "b68-generation")
        receipt["external_members"] = restore(args.external, args.out, "platform-link")
        receipt["layout_lock_sha256"] = sha256(Path(__file__).with_name("archive-layout.lock.json"))
        receipt["unprovided_not_consumed_by_provider"] = ["v1-tests/include -> b67-generation stock_child_plugin/include", "v1-tests/src -> b67-generation stock_child_plugin/src"]
        receipt["whole_generation_complete"] = False
        receipt["status"] = "RESTORED_NOT_BUILT"
        exit_code = 0
    except (OSError, ValueError, tarfile.TarError) as error:
        receipt["status"] = "REJECT_PARTIAL_RETAINED"
        receipt["error"] = str(error)
        exit_code = 2
    receipt["exit_code"] = exit_code
    (args.out / "restore-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
