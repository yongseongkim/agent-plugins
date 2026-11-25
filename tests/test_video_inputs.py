import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins/video-analysis/skills/video-analysis/scripts"
sys.path.insert(0, str(SCRIPTS))

from video_evidence import build_timeline


class VideoInputTests(unittest.TestCase):
    def test_successful_transcription_without_speech_is_an_empty_track(self):
        import importlib.util

        whisper = types.SimpleNamespace(transcribe=lambda *a, **kw: {"segments": [], "text": ""})
        spec = importlib.util.spec_from_file_location("transcribe", SCRIPTS / "transcribe.py")
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"mlx_whisper": whisper}):
            spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            asr = run / "asr.json"
            with patch.object(module, "version", return_value="test"), patch.object(
                sys, "argv", ["transcribe.py", "ambient.wav", str(asr)]
            ):
                module.main()
            self.assertEqual(json.loads(asr.read_text())["segments"], [])
            self.assertEqual(build_timeline(run, "ambient")["sources"]["whisper"]["status"], "empty")

    @unittest.skipUnless(sys.platform == "darwin" and shutil.which("swiftc"), "requires macOS Vision and Swift")
    def test_ocr_reports_input_errors_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "ocr"
            cache = root / "module-cache"
            subprocess.run(["swiftc", "-module-cache-path", str(cache), str(SCRIPTS / "ocr.swift"),
                            "-o", str(binary)], check=True, capture_output=True)
            invalid = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 1)
            self.assertIn("Usage:", invalid.stderr)

            frames = root / "frames"
            frames.mkdir()
            (frames / "unnumbered.jpg").touch()
            target = root / "nested" / "ocr.jsonl"
            command = [str(binary), str(frames), "1", str(target), "en-US"]
            invalid = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 1)
            self.assertIn("Expected numbered frames", invalid.stderr)
            self.assertEqual(list(target.parent.iterdir()), [])

            target.write_text("previous result\n")
            (frames / "unnumbered.jpg").rename(frames / "0000001.jpg")
            invalid = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 1)
            self.assertIn("Vision OCR failed", invalid.stderr)
            self.assertEqual(list(target.parent.iterdir()), [target])
            self.assertEqual(target.read_text(), "previous result\n")
