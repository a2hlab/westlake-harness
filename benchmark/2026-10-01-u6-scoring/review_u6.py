"""Materialize the manually reviewed U6 decisions and pinned scoring evidence."""

import argparse
from collections import Counter
import copy
from pathlib import Path

import score


SIGNOFF = "outer ACK(95) 2026-10-01T04:36:43+0800; user confirmed strict input identity"
WALLS = {
    "burgerking": ("realm-libz", 46101, 46002, "libz.so"),
    "fd-api": ("appcompat-theme", 31103, 31118, "Theme.AppCompat"),
    "fd-breezyweather": ("startup-getclass-null", 44625, 44640, "Object.getClass()"),
    "fd-client": ("accountmanager-null", 50580, 50595, "accountManager"),
    "fd-fluffychat": ("flutter-field-id", 22691, 22684, "fid == null"),
    "fd-gallery": ("mediastore-next-api", 57067, 57068, "canManageMedia"),
    "fd-im-vector-app": ("realm-libz", 50192, 50193, "libz.so"),
    "fd-immich": ("flutter-field-id", 33578, 33571, "fid == null"),
    "fd-kitchenowl": ("private-runtime-reload", 30193, 30223, "liboh_android_runtime.so"),
    "fd-libre": ("flutter-field-id", 26713, 26706, "fid == null"),
    "fd-libretube": ("tagsoup-xmlreader", 75297, 75298, "XMLReader"),
    "fd-meet": ("jitsi-native-relocation", 36157, 36157, "android_set_abort_message"),
    "fd-musicplayer": ("bitmap-color-space", 54265, 54266, "without a color space"),
    "fd-plus": ("osmand-map-layer-null", 75115, 75130, "MapInfoLayer.isMapControlsVisible()"),
    "fd-reader": ("tagsoup-xmlreader", 65239, 65240, "XMLReader"),
    "fd-saber": ("flutter-field-id", 38707, 38700, "fid == null"),
    "fd-tutanota": ("webview-provider", 38422, 38437, "UnsupportedOperationException"),
    "fd-wifianalyzer": ("country-preference-null", 38711, 38744, "Object.getClass()"),
    "localsend": ("private-runtime-reload", 26566, 26595, "liboh_android_runtime.so"),
    "mcdonalds": ("splash-datasource-null", 58669, 58684, "DataSourceModuleProvider.v()"),
    "mindustry": ("opensles-create-engine", 34586, 34609, "slCreateEngine"),
    "toutiao": ("mainactivity-boolean-null", 70561, 70598, "Boolean.booleanValue()"),
    "vlc": ("vlc-onboarding-inflate", 46871, 46945, "Failed to resolve attribute"),
    "wikipedia": ("tagsoup-xmlreader", 78340, 78299, "XMLReader"),
    "x": ("application-object-graph", 44937, 44952, "application object graph"),
}
CHECKPOINTS = {
    "fd-catima": [("J7-appwidget", 34483, "appwidget AppWidgetManager allocated"),
                  ("J7-search", 21385, "installed search, queryLocalInterface=OK")],
    "fd-uhabits": [("J7-appwidget", 24793, "appwidget AppWidgetManager allocated")],
    "fd-wifianalyzer": [("J7-wifi", 38230, "wifi WifiManager allocated (non-null)")],
    "opencamera": [("J7-battery", 32178, "synthetic ACTION_BATTERY_CHANGED sticky Intent")],
}
WHITE = {"fd-app", "fd-AppManager", "noice", "termux", "fd-shatteredpixeldungeon", "fd-organicmaps"}
DESKTOP = {"fd-gallery", "toutiao", "wikipedia"}


def build(prepared, root):
    prior = score.read(score.ROOT / "benchmark/2026-09-30-u4-sweep/J6N4-SCORING.json")
    preserved = {row["key"] for row in prior["rows"] if row["t20"] == "own-ui"}
    own_ui = preserved | {"fd-catima", "opencamera", "fd-feeder", "antennapod", "fd-noice"}
    if len(preserved) != 24 or len(own_ui) != 29:
        raise ValueError("outer own-UI cohort changed")
    review = score.review_template(prepared)
    review.update(complete=True, outer_signoff=SIGNOFF)
    observations = []
    indexed = {row["key"]: row for row in prepared["rows"]}
    for reviewed in review["rows"]:
        row = indexed[reviewed["key"]]
        key = row["key"]
        log_path = root / row["log"]
        lines = log_path.read_text(errors="replace").splitlines() if log_path.exists() else []

        def witness(number, needle=None):
            event = score.classify.parse(lines[number - 1], number)
            if event is None or number not in row["allowed_evidence_lines"] or (needle and needle not in event["message"]):
                raise ValueError("reviewed source line changed: " + key + ":" + str(number))
            return event

        if row["t20_sha256"]:
            visual = "own-ui" if key in own_ui else "white" if key in WHITE else "black" if key == "fd-mobile" else "desktop" if key in DESKTOP else "not-own-ui"
            reviewed["t20"] = dict(sha256=row["t20_sha256"], visual=visual,
                                   description="Outer full t20 review ACK95 04:36:43; " + ("named own-UI key" if visual == "own-ui" else "named visual category" if visual != "not-own-ui" else "not in the complete own-UI set; finer category not claimed"))
        if key in own_ui:
            windows = [event for event in row["candidates"] if "createSession: published process window target" in event["message"]]
            positive = windows[-1]["line"] if windows else row["binding_lines"][-1]
            reviewed["first_wall"] = dict(id="none", lines=[positive],
                                          rationale="Outer-reviewed own first-page UI plus target execution; no pre-t20 terminal. This does not infer any checkpoint from UI.")
        elif key in WALLS:
            identifier, terminal_line, root_line, needle = WALLS[key]
            if row["termination"]["terminal"]["event"]["line"] != terminal_line:
                raise ValueError("selected termination changed: " + key)
            cause = witness(root_line, needle)
            terminal = witness(terminal_line)
            if (cause["pid"], cause["tid"]) != (terminal["pid"], terminal["tid"]):
                raise ValueError("reviewed cause crossed threads")
            reviewed["first_wall"] = dict(id=identifier, lines=sorted({terminal_line, root_line}),
                                          rationale="Manually reviewed termination-linked cause, not earliest warning: " + needle + ". Native signal rows additionally have a PID/TID/time-bound fault-thread stack in observations.")
        for fix, number, needle in CHECKPOINTS.get(key, []):
            witness(number, needle)
            reviewed["checkpoints"].append(dict(fix_id=fix, outcome="crossed", lines=[number],
                                                rationale="Positive execution of the named repair's initialization/return behavior: " + needle + "; not a claim of complete framework service functionality."))
        if key == "firefox":
            if not row["identity_verified"] or len(row["identity"]["sidecars"]) != 18:
                raise ValueError("Firefox merged input/native installation is unverified")
            reviewed["checkpoints"].append(dict(fix_id="INPUT-merged", outcome="crossed", lines=[row["binding_lines"][0]],
                                                rationale="Exact frozen merged APK plus all 18 sidecars match; native assembly verifies installation, and package launch executes. No mozglue runtime crossing is inferred."))
        references = set()
        for claim in ([reviewed["first_wall"]] if reviewed["first_wall"] else []) + reviewed["checkpoints"]:
            references.update(claim["lines"])
        compact = {field: copy.deepcopy(value) for field, value in row.items() if field not in {"candidates", "allowed_evidence_lines", "noise"}}
        compact["allowed_evidence_lines"] = sorted(references)
        compact["review_witnesses"] = [witness(number) for number in sorted(references)]
        compact["noise_counts"] = dict(Counter(item["signature_id"] for item in row["noise"]))
        compact["terminal_diagnostics"] = [event for event in row["termination"].get("context", [])
                                             if event["level"] == "F" or "JNI FatalError" in event["message"]][:12]
        compact["termination"].pop("context", None)
        compact["termination"].pop("noise_context", None)
        observations.append(compact)
    result = score.score(prepared, review)
    result["outer_lighting"] = dict(preserved=24, new_stable=3, stable_total=27, additional_flaky=2, observed_own_ui=29,
                                    frozen_flaky_keys=["antennapod", "fd-noice", "fd-notes", "fd-uhabits"],
                                    note="Outer aggregate retains two previously lit flaky keys; frozen scoring still marks all four single-attempt flaky t20 unknown.")
    return dict(review=review, observations=dict(prepared_sha256=score.seal(prepared), registry_sha256=prepared["registry_sha256"],
                                                indices=prepared["indices"], rows=observations), scoring=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    print(score.encoded(build(score.read(args.prepared), args.source.resolve())), end="")


if __name__ == "__main__":
    main()
