import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import install


class InstallationTests(unittest.TestCase):
    def test_user_and_project_layouts_and_installed_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layouts = {
                "user": [".agents/skills", ".claude/skills", ".gemini/config/skills"],
                "project": [".agents/skills", ".claude/skills"],
            }
            for mode, expected in layouts.items():
                with self.subTest(mode=mode), tempfile.TemporaryDirectory(dir=root) as target:
                    scope = Path(target)
                    argv = ["--user"] if mode == "user" else ["--project", target]
                    with patch("pathlib.Path.home", return_value=scope), patch.object(sys, "argv", ["install.py", *argv]):
                        install.main()
                        install.main()
                    self.assertEqual(set(scope.rglob("SKILL.md")), {scope / path / "video-analysis/SKILL.md" for path in expected})
                    for path in expected:
                        package = scope / path / "video-analysis"
                        self.assertEqual(install.contents(package), install.contents(install.PACKAGE))
                        run = scope / "video with spaces"
                        run.mkdir(exist_ok=True)
                        (run / "captions.vtt").write_text("WEBVTT\n\n00:01.000 --> 00:02.000\nHello\n")
                        subprocess.run([sys.executable, str(package / "scripts/video_evidence.py"), str(run),
                                        "--video-id", "fixture"], cwd=run, check=True, capture_output=True)
                        timeline = json.loads((run / "evidence_timeline.json").read_text())
                        self.assertEqual(timeline["events"][0]["text"], "Hello")

    def test_conflict_is_checked_before_writing_other_clients(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / ".claude/skills/video-analysis"
            existing.mkdir(parents=True)
            local = existing / "SKILL.md"
            local.write_text("Local edits")
            with self.assertRaises(ValueError):
                install.install(root, install.USER_DIRS, ["codex", "claude"])
            self.assertEqual(local.read_text(), "Local edits")
            self.assertFalse((root / ".agents").exists())
