import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins/video-analysis/skills/video-analysis/scripts"
sys.path.insert(0, str(SCRIPTS))

from inspect_frames import extract
from video_evidence import build_timeline, write_json


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
                (12, "점심 먹으러 가요", subtitle), (12, "서점", sign),
                (15, "길을 건너면", subtitle), (15, "출구", None),
            ])
            (run / "onscreen_text.json").write_text(json.dumps({"segments": [
                {"start": 1, "text": "상단 제목", "boundingBox": {**sign, "y": -7e-7}},
                {"start": 2, "text": "위치 미상", "boundingBox": {**sign, "width": 400}},
                {"start": 3, "text": "오른쪽 끝", "boundingBox": {**sign, "x": 0.8000007}},
                {"start": 4, "text": "프레임 밖", "boundingBox": {**sign, "x": 0.82}},
            ]}))
            events = build_timeline(run, "demo")["events"]
            self.assertEqual(events[0]["boundingBox"], {**sign, "y": 0, "height": 0.079999})
            self.assertEqual(events[1]["text"], "위치 미상")
            self.assertNotIn("boundingBox", events[1])
            self.assertEqual(events[2]["boundingBox"], {**sign, "x": 0.800001, "width": 0.199999})
            self.assertNotIn("boundingBox", events[3])

    def test_vtt_preserves_technical_text_and_removes_only_cue_markup(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            (run / "captions.vtt").write_text(
                "WEBVTT\n\n00:00.000 --> 00:02.000 align:start\n"
                "<v Speaker><c.blue><i>List<String></i></c></v> <00:00:01.000>"
                "a < b && c > d; a <b && c > d; &lt;b&gt; <lang en>ok</lang>\n"
            )
            event, = build_timeline(run, "demo")["events"]
            self.assertEqual(event["text"], "List<String> a < b && c > d; a <b && c > d; <b> ok")

    def test_bad_ocr_input_leaves_other_tracks_and_valid_text_writable(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            (run / "captions.vtt").write_text("WEBVTT\n\n00:00.000 --> 00:01.000\nHello\n")
            track = run / "onscreen_text.json"
            for confidence in ("NaN", "Infinity", "unknown", {}):
                with self.subTest(confidence=confidence):
                    track.write_text(json.dumps({"segments": [{"start": 2, "text": "OK", "confidence": confidence}]}))
                    result = build_timeline(run, "demo")
                    write_json(run / "evidence_timeline.json", result)
                    self.assertEqual([e["text"] for e in result["events"]], ["Hello", "OK"])
                    self.assertNotIn("confidence", result["events"][1])
            for contents in (b'{"segments":[null]}', b'{"segments":{}}', b'\xff'):
                with self.subTest(contents=contents):
                    track.write_bytes(contents)
                    result = build_timeline(run, "demo")
                    self.assertEqual(result["sources"]["ocr"]["status"], "error")
                    self.assertEqual([e["text"] for e in result["events"]], ["Hello"])

    def test_multivideo_fingerprint_identifies_the_selected_video(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            videos = [{"videoId": key, "segments": [{"start": 0, "text": key}]} for key in ("a", "b")]
            (run / "captions.json").write_text(json.dumps({"videos": videos}))
            a, b = (build_timeline(run, key) for key in ("a", "b"))
            self.assertNotEqual(a["events"], b["events"])
            self.assertNotEqual(a["inputFingerprint"], b["inputFingerprint"])
            self.assertEqual(a["inputFingerprint"], build_timeline(run, "a")["inputFingerprint"])

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

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "needs FFmpeg")
    def test_seek_matches_original_vfr_timestamps_and_skips_redundant_decodes(self):
        import inspect_frames

        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            media = run / "offset-vfr.mkv"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=48x32:r=10:d=12",
                            "-vf", "select='not(mod(n,3))+not(mod(n,7))'", "-fps_mode", "vfr",
                            "-output_ts_offset", "7", "-c:v", "ffv1", str(media)], check=True)
            raw = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_frames",
                                           "-show_entries", "frame=best_effort_timestamp_time", "-of", "json",
                                           str(media)], text=True)
            source_times = [float(f["best_effort_timestamp_time"]) for f in json.loads(raw)["frames"]]
            self.assertEqual(source_times[0], 7)
            playback = [round(t - source_times[0], 6) for t in source_times]
            requests = [0, 9.01, 9.02, 10.5, 12, 13]
            with patch.object(inspect_frames, "extract_group", wraps=inspect_frames.extract_group) as groups:
                manifest = extract(media, requests, "Check scene", run / "visual")
            frames = json.loads(manifest.read_text())["frames"]
            expected = [next((t for t in playback if t >= r), None) for r in requests]
            self.assertEqual([f.get("timeSeconds") for f in frames], expected)
            self.assertEqual(frames[1]["image"], frames[2]["image"])
            self.assertEqual([call.args[1] for call in groups.call_args_list], [[0], requests[1:]])
            with self.assertRaisesRegex(ValueError, "No video frame"):
                extract(media, [20], "Outside", run / "visual")
            self.assertEqual(list((run / "visual").iterdir()), [manifest.parent])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "needs FFmpeg")
    def test_sparse_vfr_reuses_a_frame_across_distant_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            media = run / "sparse.mkv"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=32x32:r=1:d=12",
                            "-vf", "select='eq(n,0)+eq(n,10)+eq(n,11)'", "-fps_mode", "vfr",
                            "-c:v", "ffv1", str(media)], check=True)
            manifest = extract(media, [0.1, 7.5, 10.5], "Read the slide", run / "out")
            frames = json.loads(manifest.read_text())["frames"]
            self.assertEqual([f["timeSeconds"] for f in frames], [10, 10, 11])
            self.assertEqual(frames[0]["image"], frames[1]["image"])
            self.assertEqual(len(list(manifest.parent.glob("*.jpg"))), 2)

    @unittest.skipUnless(shutil.which("ffmpeg"), "needs FFmpeg")
    def test_transport_stream_keeps_frames_between_keyframes(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            media = run / "recording.ts"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=48x32:r=10:d=8",
                            "-c:v", "mpeg2video", "-g", "15", "-f", "mpegts", str(media)], check=True)
            manifest = extract(media, [0, 6.05, 6.06], "Check transport stream", run / "out")
            frames = json.loads(manifest.read_text())["frames"]
            self.assertEqual([f["timeSeconds"] for f in frames], [0, 6.1, 6.1])
            self.assertEqual(frames[1]["image"], frames[2]["image"])
