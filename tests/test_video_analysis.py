import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins/video-analysis/skills/video-analysis/scripts"
sys.path.insert(0, str(SCRIPTS))

from inspect_frames import extract
from video_evidence import build_timeline


class GeneralVideoAnalysisTests(unittest.TestCase):
    def test_ocr_keeps_per_line_positions_across_frames_and_text_without_positions(self):
        subtitle = {"x": 0.2, "y": 0.88, "width": 0.6, "height": 0.04}
        sign = {"x": 0.1, "y": 0.25, "width": 0.2, "height": 0.08}
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            frames = [
                {"time": 12, "lines": [{"text": "점심 먹으러 가요", **subtitle}, {"text": "서점", **sign}]},
                {"time": 15, "lines": [{"text": "길을 건너면", **subtitle}, {"text": "출구"}]},
            ]
            (run / "ocr.jsonl").write_text("\n".join(json.dumps(frame) for frame in frames))
            events = build_timeline(run, "demo")["events"]
            self.assertEqual([(e["startSeconds"], e["text"], e.get("boundingBox")) for e in events], [
                (12, "서점", sign), (12, "점심 먹으러 가요", subtitle),
                (15, "길을 건너면", subtitle), (15, "출구", None),
            ])
            (run / "onscreen_text.json").write_text(json.dumps({"segments": [
                {"start": 1, "text": "상단 제목", "boundingBox": {**sign, "y": -4e-11}},
                {"start": 2, "text": "위치 미상", "boundingBox": {**sign, "width": 400}},
            ]}))
            events = build_timeline(run, "demo")["events"]
            self.assertEqual(events[0]["boundingBox"], {**sign, "y": 0})
            self.assertEqual(events[1]["text"], "위치 미상")
            self.assertNotIn("boundingBox", events[1])

    def test_vtt_word_timed_asr_and_frame_ocr_preserve_sources_and_unknown_time(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            (run / "captions.vtt").write_text("WEBVTT\n\n00:00.000 --> 00:01.000\nStart\n")
            (run / "asr.json").write_text(json.dumps({"segments": [
                {"start": 0, "end": 1, "text": "Start", "words": []},
                {"text": "undated"},
            ]}))
            (run / "ocr.jsonl").write_text('{"time":0.5,"lines":[{"text":"−1.5%","confidence":0.98}]}\n')
            result = build_timeline(run, "demo")
            self.assertEqual([(e["source"], e["startSeconds"], e["text"]) for e in result["events"]],
                             [("transcript", 0, "Start"), ("ocr", 0.5, "−1.5%")])
            self.assertEqual(result["sources"]["whisper"]["duplicateOf"], "transcript")
            self.assertEqual(result["sources"]["whisper"]["untimedSegmentCount"], 1)
            (run / "ocr.jsonl").write_text('broken\n')
            partial = build_timeline(run, "demo")
            self.assertEqual(partial["sources"]["ocr"]["status"], "error")
            self.assertEqual(len(partial["events"]), 1)

    @unittest.skipUnless(shutil.which("ffmpeg"), "frame inspection requires ffmpeg")
    def test_selected_frames_use_playback_timestamps(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            media = run / "example.mkv"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=32x32:r=10:d=1",
                            "-c:v", "ffv1", str(media)], check=True)
            manifest = extract(media, [0, 0.31, 0.32, 1], "What changes?", run / "visual")
            frames = json.loads(manifest.read_text())["frames"]
            self.assertEqual([f.get("timeSeconds") for f in frames], [0, 0.4, 0.4, None])
            self.assertEqual(frames[1]["image"], frames[2]["image"])
            self.assertTrue((manifest.parent / frames[1]["image"]).is_file())
            self.assertEqual(frames[-1]["status"], "outside-video-frames")
