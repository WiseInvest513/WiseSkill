"""Count repeated on-screen treatments and foreground elements by runtime."""

import argparse
from collections import Counter
import json
import math
from pathlib import Path


def audit(data, limit):
    spans = data["visual_spans"]
    duration_ms = round(data["duration"] * 1000)
    if not spans or duration_ms <= 0:
        raise ValueError("A positive duration and visible spans are required")
    totals = {name: Counter() for name in ("families", "patterns", "assets")}
    box_ms = 0
    last = 0
    for span in spans:
        start, end = span["start_ms"], span["end_ms"]
        if not all(type(time) is int for time in (start, end)) or start != last or end <= start:
            raise ValueError(f"Visual spans must cover contiguous integer milliseconds after {last}")
        elapsed = end - start
        last = end
        if type(span["box_dominant"]) is not bool:
            raise ValueError("box_dominant must be a boolean")
        if span["box_dominant"]:
            box_ms += elapsed
        for group, entries in (
            ("families", [span["family"]]),
            ("patterns", span.get("patterns", [])),
            ("assets", span.get("assets", [])),
        ):
            if not isinstance(entries, list) or not all(isinstance(name, str) and name.strip() for name in entries):
                raise ValueError(f"{group} must contain nonempty names")
            for name in set(entries):
                totals[group][name] += elapsed
    if last != duration_ms:
        raise ValueError(f"Timeline ends at {last} ms, expected {duration_ms} ms")

    def record(name, millis):
        return {"name": name, "duration_ms": millis, "share": millis / duration_ms}

    groups = {group: [record(name, time) for name, time in counts.most_common()]
              for group, counts in totals.items()}
    body_box = data.get("max_body_box_share")
    if body_box is not None and (
        isinstance(body_box, bool) or not isinstance(body_box, (float, int))
        or not math.isfinite(body_box) or not 0 <= body_box <= 1
    ):
        raise ValueError("max_body_box_share must be between 0 and 1")

    boxes = record("box-dominant", box_ms)
    area = {"name": "body-box-area", "share": body_box}
    checks = [boxes, area] + [entry for history in groups.values() for entry in history]
    violations = [entry for entry in checks if entry["share"] is not None and entry["share"] > limit]
    unmeasured = [key for key in ("patterns", "assets") if not all(key in span for span in spans)]
    if body_box is None:
        unmeasured.append("body-box-area")

    return {"status": "fail" if violations else "partial" if unmeasured else "pass",
            "duration_ms": duration_ms, "spans": len(spans), "limit": limit,
            "boxes": boxes, "body_box_area": area, **groups,
            "violations": violations, "unmeasured": unmeasured}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timeline", type=Path)
    parser.add_argument("--limit", type=float, default=.20)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if not 0 < args.limit <= 1:
        parser.error("--limit must be greater than 0 and at most 1")
    try:
        report = audit(json.loads(args.timeline.read_text()), args.limit)
    except (OSError, TypeError, ValueError, KeyError) as error:
        parser.exit(2, f"{error}\n")
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(output)
    else:
        print(output, end="")
    return int(report["status"] != "pass")


if __name__ == "__main__":
    raise SystemExit(main())
