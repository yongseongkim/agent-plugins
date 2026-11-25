"""Extract source-resolution frames for a specific question at original playback times."""
import argparse
from bisect import bisect_left, bisect_right
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def has_indexed_timestamps(media):
    # TS 입력은 탐색 시 다음 키프레임으로 건너뛸 수 있고, raw H.264에는 원본 PTS가 없을 수 있다.
    if not shutil.which("ffprobe"):
        return False
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=format_name",
        "-of", "default=nw=1:nk=1", str(media),
    ], capture_output=True, text=True)
    formats = set(result.stdout.strip().split(","))
    return result.returncode == 0 and bool(formats.intersection({"mov", "mp4", "matroska", "webm"}))


def extract_group(media, times, directory, prefix, seek):
    # 마지막 요청 시각 이후의 프레임도 통과시켜, 요청 여러 개가 한 장에 겹쳐도 곧바로 디코딩을 마친다.
    crossings = [f"gte(t,{t})*(isnan(prev_pts)+lt(prev_pts*TB,{t}))" for t in times[:-1]]
    crossings.append(f"gte(t,{times[-1]})")
    filters = "select='" + "+".join(crossings) + "',showinfo"
    command = ["ffmpeg", "-hide_banner", "-nostats", "-nostdin", "-xerror", "-copyts", "-start_at_zero"]
    if seek and times[0] >= 1:
        command.extend(["-ss", str(math.floor(times[0])), "-noaccurate_seek"])
    command.extend([
        "-i", str(media), "-map", "0:v:0", "-an", "-vf", filters, "-fps_mode", "vfr",
        "-frames:v", str(len(times)), "-pix_fmt", "yuvj444p", "-q:v", "2",
        str(directory / (prefix + "%06d.jpg")),
    ])
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise ValueError("ffmpeg: " + result.stderr[-1500:])

    # 긴 영상에서는 showinfo의 pts_time이 반올림되므로 정수 pts를 초로 환산한다.
    images = sorted(directory.glob(prefix + "*.jpg"))
    log = "\n".join(line for line in result.stderr.splitlines() if "Parsed_showinfo_" in line)
    base = re.search(r"config in time_base:\s*(\d+)/(\d+)", log)
    pts = re.findall(r"\bn:\s*\d+\s+pts:\s*(-?\d+)", log)
    if images and (not base or len(pts) < len(images)):
        raise ValueError("Missing presentation timestamp for extracted frame")
    seconds = [int(p) * int(base[1]) / int(base[2]) for p in pts[:len(images)]]
    frames = []
    used = set()
    for requested in times:
        index = bisect_left(seconds, requested)
        if index == len(images):
            frames.append({"requestedSeconds": requested, "status": "outside-video-frames"})
            continue
        image = images[index]
        used.add(image)
        frames.append({"requestedSeconds": requested, "timeSeconds": seconds[index],
                       "image": image.name, "status": "extracted"})
    for image in set(images) - used:
        image.unlink()
    return frames


def extract(media, times, question, output):
    media = media.resolve(strict=True)
    if not times or any(not math.isfinite(t) or t < 0 for t in times):
        raise ValueError("Use finite, nonnegative seconds on the original media timeline")
    if not question.strip():
        raise ValueError("Specify the question the frames should answer")
    times = sorted(set(times))
    seek = times[-1] >= 1 and has_indexed_timestamps(media)
    # 가까운 요청은 한 번에 읽고, 멀리 떨어진 장면은 그 구간으로 건너뛴다.
    groups = [[times[0]]]
    for requested in times[1:]:
        if seek and requested - groups[-1][-1] > 5:
            groups.append([])
        groups[-1].append(requested)

    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as temp:
        staging = Path(temp) / "frames"
        staging.mkdir()
        frames = []
        for i, group in enumerate(groups):
            if frames:
                previous = frames[-1]
                # A long VFR gap can map requests in separate groups to the same frame.
                covered = bisect_right(group, previous["timeSeconds"]) if "timeSeconds" in previous else len(group)
                frames.extend({**previous, "requestedSeconds": t} for t in group[:covered])
                group = group[covered:]
            if group:
                frames.extend(extract_group(media, group, staging, f"frame-{i + 1:04d}-", seek))
        if all(f["status"] == "outside-video-frames" for f in frames):
            raise ValueError("No video frame at or after the requested times")
        report = {"media": str(media), "question": question, "frames": frames}
        (staging / "frames.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        dest = output / ("inspection-" + Path(temp).name)
        staging.rename(dest)
    return dest / "frames.json"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media", type=Path)
    parser.add_argument("--at", required=True, nargs="+", type=float, help="Original media seconds")
    parser.add_argument("--question", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(extract(args.media, args.at, args.question, args.out))
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
