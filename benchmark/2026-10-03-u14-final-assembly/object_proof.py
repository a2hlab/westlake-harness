from collections import deque
import hashlib
import json
import re
import struct

from common import HERE, RELEASE, portable, save, sha

TOOL = "cd3babf9b1db4066c3e38414aeb74a0c251305a9d167a3a547a615ec4519d8f5"


def streamed_sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract(path):
    previous = deque(maxlen=50)
    excerpt = []
    end = 0
    sentinel = 0
    with path.open(errors="replace") as stream:
        for number, line in enumerate(stream, 1):
            text = line.rstrip()
            if "0x7003e360: java.util.concurrent.CancellationException" in text:
                end = number + 18
            if number <= end:
                excerpt.append(dict(line=number, text=text))
            if "CANCELLED: 0x7003e360" in text:
                sentinel += 1
                excerpt.extend(previous)
                excerpt.append(dict(line=number, text=text))
            previous.append(dict(line=number, text=text))
    joined = "\n".join(row["text"] for row in excerpt)
    required = ["backtrace: 0x7003e380", "0: 0x7003e3a8", "1: 0x700d51c8", "Class: sun.nio.ch.PendingFuture", "0x7003e3a8: long[] length:2", '"sun.nio.ch.PendingFuture"', "CANCELLED: 0x7003e360"]
    if sentinel != 1 or any(value not in joined for value in required):
        raise ValueError("New image object chain not established")
    return excerpt


def main():
    root = RELEASE / "oatdump"
    session = root / "oatdump-headeronly-session.log"
    text = session.read_text()
    if TOOL not in text:
        raise ValueError("Frozen oatdump identity not recorded")
    rows = []
    for number in [1, 2]:
        label = "headeronly-run" + str(number)
        path = root / ("oatdump-" + label + ".log")
        status = json.loads((root / ("oatdump-" + label + ".status.json")).read_text())
        actual = streamed_sha(path)
        record = re.search(r"\[rc " + label + r"\] 0\s+\d+\s+\d+\s+([0-9a-f]{64})", text)
        if status != {"oatdump_exit_code": 0} or not record or actual != record[1]:
            raise ValueError("Actual complete oatdump hash/exit mismatch")
        excerpt = extract(path)
        image = RELEASE / ("run" + str(number)) / "boot.art"
        with image.open("rb") as stream:
            stream.seek(0x3e3a8)
            array = stream.read(32)
        length = struct.unpack_from("<I", array, 8)[0]
        method, dex_pc = struct.unpack_from("<QQ", array, 16)
        if length != 2 or dex_pc != 2:
            raise ValueError("New long-array layout differs")
        argv_line = next(line for line in text.splitlines() if line.startswith("[cmd " + label + "] "))
        proof = HERE / "evidence" / ("object-" + label + ".txt")
        proof.write_text("\n".join(str(row["line"]) + ": " + row["text"] for row in excerpt) + "\n")
        rows.append(dict(run=number, boot_art_sha256=sha(image), tool_sha256=TOOL, actual_command=argv_line,
            oatdump_log=path, oatdump_log_sha256=actual, oatdump_exit_code=0, excerpt=proof.relative_to(HERE), excerpt_sha256=sha(proof),
            object="sun.nio.ch.PendingFuture.CANCELLED.backtrace[0] long[2] element 0", field_start="0x3e3b8", field_end_exclusive="0x3e3c0", method_word=hex(method), dex_pc=dex_pc))
    if rows[0]["method_word"] == rows[1]["method_word"]:
        raise ValueError("Independent new bake words unexpectedly agree")
    save("object-proof.json", dict(status="verified-object-chain", rows=rows, session=session, session_sha256=sha(session),
        source_inventory_check="Remote oatdump_u14.sh copies each run group then sha256sum -c before loading; script/session kept in evidence",
        paired_byte_exception_approved=False, runtime_harmlessness="Not established by this read-only object identity proof"))
    for source in [session, root / "oatdump_u14.sh", root / "oatdump_ho.sh"]:
        destination = HERE / "evidence" / source.name
        destination.write_text(portable(source.read_text()))
    review_path = HERE / "reproduction-review.json"
    review = json.loads(review_path.read_text())
    review["object_owner"] = rows[0]["object"]
    review["object_proof"] = "object-proof.json"
    review["object_proof_sha256"] = sha(HERE / "object-proof.json")
    save(review_path, review)
    draft_path = HERE / "image-exception-draft.json"
    draft = json.loads(draft_path.read_text())
    draft["status"] = "proposed"
    draft["object"]["identity"] = rows[0]["object"]
    draft["object"]["object"] = rows[0]["object"]
    draft["evidence"].append("benchmark/2026-10-03-u14-final-assembly/object-proof.json")
    draft["reason"] = "Actual new frozen-tool bakes differ only in this freshly identified sentinel backtrace element; exact new pair requires outer approval; no runtime-harmlessness assertion"
    save(draft_path, draft)
    print("OBJECT run1/run2 oatdump_rc=0 full_hashes=verified PendingFuture.CANCELLED->backtrace->long[2]; exact_U14_exception=unapproved")


if __name__ == "__main__":
    main()
