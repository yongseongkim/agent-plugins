"""Extract source-resolution frames for a specific question at original playback times."""
import argparse
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile


def extract(media, times, question, output):
    media = media.resolve(strict=True)
    if not times or any(not math.isfinite(t) or t < 0 for t in times):
        raise ValueError("Use finite, nonnegative seconds on the original media timeline")
    if not question.strip():
        raise ValueError("Specify the question the frames should answer")
    times = sorted(set(times))
    output.mkdir(parents=True, exist_ok=True)
    # 같은 구간을 동시에 추출해도 결과가 섞이지 않도록 요청마다 폴더를 만든다.
    with tempfile.TemporaryDirectory(dir=output) as temp:
        directory = Path(temp)
        # 요청한 시각에 프레임이 없으면 그다음 프레임을 쓴다.
        # 두 요청 시각이 연속된 두 프레임 사이에 있으면 두 요청에 같은 이미지를 쓴다.
        expressions = [f"gte(t,{t})*(isnan(prev_pts)+lt(prev_pts*TB,{t}))" for t in times]
        filters = "select='" + "+".join(expressions) + "',showinfo"
        command = [
            "ffmpeg", "-hide_banner", "-nostats", "-copyts", "-start_at_zero", "-i", str(media),
            "-map", "0:v:0", "-an", "-vf", filters, "-fps_mode", "vfr",
            "-frames:v", str(len(times)), "-q:v", "2", str(directory / "frame-%06d.jpg"),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise ValueError("ffmpeg: " + result.stderr[-1500:])
        # 긴 영상에서는 showinfo의 pts_time이 반올림되므로 정수 pts를 초로 환산한다.
        info = [line for line in result.stderr.splitlines() if "Parsed_showinfo_" in line]
        base = re.search(r"config in time_base:\s*(\d+)/(\d+)", "\n".join(info))
        pts = [int(m[1]) for line in info if (m := re.search(r"\bn:\s*\d+\s+pts:\s*(-?\d+)", line))]
        if not base or not pts:
            raise ValueError("No video frame at or after the requested times")
        timestamps = [p * int(base[1]) / int(base[2]) for p in pts]
        images = sorted(directory.glob("frame-*.jpg"))
        if len(images) != len(timestamps):
            raise ValueError("Image count and source timestamp count differ")
        frames = []
        for t in times:
            index = next((i for i, ts in enumerate(timestamps) if ts >= t - 1e-8), None)
            if index is None:
                frames.append({"requestedSeconds": t, "status": "outside-video-frames"})
            else:
                frames.append({"requestedSeconds": t, "timeSeconds": timestamps[index],
                               "image": images[index].name, "status": "extracted"})
        report = {"media": str(media), "question": question, "frames": frames}
        (directory / "frames.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        dest = directory.with_name("inspection-" + directory.name)
        directory.rename(dest)
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
