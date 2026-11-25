"""Build a source-attributed video evidence timeline using only the Python standard library."""
import argparse
import hashlib
import html
import json
import math
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


OUTPUT_FILE = "evidence_timeline.json"
RAW_INPUT_FILES = (
    "metadata.json",
    "captions.json",
    "audio_transcript.json",
    "onscreen_text.json",
)
SOURCE_FILES = {
    "transcript": (
        "transcripts.reviewed.json",
        "transcripts.json",
        "captions.json",
        "captions.vtt",
    ),
    "whisper": ("audio_transcript.json", "asr.json"),
    "ocr": ("onscreen_text.json", "ocr.jsonl"),
}
SOURCE_ORDER = {"transcript": 0, "whisper": 1, "ocr": 2}
BOX_FIELDS = ("x", "y", "width", "height")


def read_json(path):
    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def read_track(path):
    if path.suffix == ".json":
        return read_json(path)
    segments = []
    if path.suffix == ".vtt":
        # Keep the raw VTT intact. Timed cues may include positioning settings.
        def seconds(stamp):
            parts = stamp.replace(",", ".").split(":")
            return sum(float(part) * 60 ** i for i, part in enumerate(reversed(parts)))

        for block in re.split(r"\n[ \t]*\n", path.read_text(encoding="utf-8-sig")):
            lines = block.splitlines()
            if not lines or lines[0].startswith(("NOTE", "STYLE", "REGION")):
                continue
            for index, line in enumerate(lines):
                if " --> " in line:
                    start, end = line.split(" --> ", 1)
                    cue = html.unescape(re.sub(r"<[^>]*>", "", " ".join(lines[index + 1:])))
                    segments.append({"start": seconds(start.strip()), "end": seconds(end.split()[0]), "text": cue})
                    break
    else:
        with path.open(encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                frame = json.loads(line)
                for row in frame["lines"]:
                    segments.append({
                        "start": frame["time"],
                        "text": row["text"],
                        "confidence": row.get("confidence"),
                        "boundingBox": {key: row[key] for key in BOX_FIELDS if key in row},
                    })
    return {"segments": segments}


def write_json(path, value):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        try:
            json.dump(value, file, ensure_ascii=False, indent=2, allow_nan=False)
            file.write("\n")
            file.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unwrap_video(value, video_id=None):
    if not isinstance(value, dict):
        return {}
    if value.get("videoId") and video_id and value["videoId"] != video_id:
        return {"error": "video ID mismatch"}
    if "segments" in value or value.get("videoId"):
        return value
    for video in value.get("videos", []):
        if video_id is None or video.get("videoId") == video_id:
            return video
    return {}


def segment_end(segment):
    start = float(segment.get("start") or 0)
    if segment.get("end") is not None:
        return float(segment["end"])
    return start + float(segment.get("duration") or 0)


def input_records(run_dir):
    records = []
    input_names = list(RAW_INPUT_FILES)
    for candidates in SOURCE_FILES.values():
        for file_name in candidates:
            if file_name not in input_names:
                input_names.append(file_name)
    for file_name in input_names:
        path = run_dir / file_name
        if not path.is_file():
            continue
        try:
            value = read_json(path) if path.suffix == ".json" else {}
            error = value.get("error") if isinstance(value, dict) else None
        except (ValueError, UnicodeError) as exc:
            error = str(exc)
        records.append(
            {
                "file": file_name,
                "sha256": sha256_file(path),
                "status": "error" if error else "ready",
                **({"error": str(error)} if error else {}),
            }
        )
    return records


def input_fingerprint(records):
    digest = hashlib.sha256()
    digest.update(Path(__file__).read_bytes())
    for record in sorted(records, key=lambda value: value["file"]):
        digest.update(record["file"].encode())
        digest.update(record["sha256"].encode())
    return digest.hexdigest()


def selected_source(run_dir, candidates):
    for file_name in candidates:
        path = run_dir / file_name
        if path.is_file():
            return path
    return None


def normalized_ocr_box(box):
    if not isinstance(box, dict):
        return None
    values = [box.get(key) for key in BOX_FIELDS]
    # Vision can return a coordinate a fraction of a pixel outside the frame.
    if not all(type(v) in (int, float) and -1e-6 <= v <= 1 + 1e-6 for v in values):
        return None
    x, y, width, height = values
    left, top, right, bottom = (round(v, 6) for v in (x, y, x + width, y + height))
    if 0 <= left < right <= 1 and 0 <= top < bottom <= 1:
        return {"x": left, "y": top, "width": round(right - left, 6), "height": round(bottom - top, 6)}
    return None


def normalized_segments(video, source=None):
    segments = []
    for segment in video.get("segments", []):
        text = str(segment.get("text") or "").strip()
        if not text or segment.get("start") is None:
            continue
        start = float(segment["start"])
        if not math.isfinite(start) or start < 0 or not math.isfinite(segment_end(segment)):
            raise ValueError("Invalid segment time")
        event = {
            "startSeconds": round(start, 3),
            "endSeconds": round(max(start, segment_end(segment)), 3),
            "text": text,
        }
        if segment.get("confidence") is not None:
            event["confidence"] = float(segment["confidence"])
        if source == "ocr":
            box = normalized_ocr_box(segment.get("boundingBox"))
            if box is not None:
                event["boundingBox"] = box
        segments.append(event)
    return segments


def segments_fingerprint(segments):
    normalized = json.dumps(segments, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode()).hexdigest()


def build_timeline(run_dir, video_id):
    run_dir = Path(run_dir)
    records = input_records(run_dir)
    sources = {}
    events = []
    seen_segments = {}

    for source, candidates in SOURCE_FILES.items():
        path = selected_source(run_dir, candidates)
        if path is None:
            sources[source] = {"status": "missing"}
            continue
        try:
            value = read_track(path)
            video = unwrap_video(value, video_id)
            error = video.get("error") or (value.get("error") if isinstance(value, dict) else None)
            segments = normalized_segments(video, source) if not error else []
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            error = f"Invalid track: {exc}"
        if error:
            sources[source] = {
                "status": "error",
                "file": path.name,
                "sha256": sha256_file(path),
                "error": str(error),
            }
            continue
        untimed = sum(1 for item in video.get("segments", []) if item.get("text") and item.get("start") is None)
        time_note = {"untimedSegmentCount": untimed} if untimed else {}
        if not segments:
            sources[source] = {
                "status": "empty",
                "file": path.name,
                "sha256": sha256_file(path),
                "segmentCount": 0,
                **time_note,
            }
            continue
        fingerprint = segments_fingerprint(segments)
        summary = {
            "status": "ready",
            "file": path.name,
            "sha256": sha256_file(path),
            "language": video.get("language", "unknown"),
            "segmentCount": len(segments),
            **time_note,
        }
        if video.get("source"):
            summary["origin"] = video["source"]
        if fingerprint in seen_segments:
            summary["status"] = "duplicate"
            summary["duplicateOf"] = seen_segments[fingerprint]
            sources[source] = summary
            continue
        seen_segments[fingerprint] = source
        sources[source] = summary
        for segment in segments:
            events.append({"source": source, **segment})

    events.sort(
        key=lambda event: (
            event["startSeconds"],
            SOURCE_ORDER[event["source"]],
            event["endSeconds"],
            event["text"],
        )
    )
    return {
        "schemaVersion": 1,
        "videoId": video_id,
        "generatedAt": utc_now(),
        "inputFingerprint": input_fingerprint(records),
        "inputs": records,
        "sources": sources,
        "durationSeconds": max(
            (event["endSeconds"] for event in events),
            default=0,
        ),
        "events": events,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--video-id", help="YouTube ID or a stable local media identifier")
    args = parser.parse_args()
    metadata_path = args.run_dir / "metadata.json"
    metadata = read_json(metadata_path) if metadata_path.exists() else {}
    metadata_id = metadata.get("videoId") or metadata.get("id")
    if args.video_id and metadata_id and args.video_id != metadata_id:
        parser.error("Requested video ID differs from metadata")
    video_id = args.video_id or metadata_id
    if not video_id:
        parser.error("Provide --video-id or an id in metadata.json")
    data = build_timeline(args.run_dir, video_id)
    output = args.run_dir / OUTPUT_FILE
    write_json(output, data)
    print(f"{len(data['events'])} events -> {output}")
