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
