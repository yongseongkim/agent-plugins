import json
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class CatalogTests(unittest.TestCase):
    def test_both_catalogs_expose_every_plugin_and_its_bundled_skills(self):
        codex = read_json(ROOT / ".agents/plugins/marketplace.json")
        claude = read_json(ROOT / ".claude-plugin/marketplace.json")
        self.assertEqual(codex["name"], claude["name"])

        packages = {path.name: path for path in (ROOT / "plugins").iterdir() if path.is_dir()}
        for catalog in (codex, claude):
            self.assertCountEqual([entry["name"] for entry in catalog["plugins"]], packages.keys())
        for entry in codex["plugins"]:
            self.assertEqual(ROOT / entry["source"]["path"], packages[entry["name"]])
        for entry in claude["plugins"]:
            self.assertEqual(ROOT / entry["source"], packages[entry["name"]])

        for name, package in packages.items():
            with self.subTest(plugin=name):
                portable = read_json(package / "plugin.json")
                native = read_json(package / ".claude-plugin/plugin.json")
                self.assertEqual(portable["name"], name)
                for key in ("name", "version", "description", "author"):
                    self.assertEqual(portable[key], native[key])
                self.assertTrue(list((package / "skills").glob("*/SKILL.md")))

    @unittest.skipUnless(yaml, "install PyYAML for skill metadata validation")
    def test_skill_frontmatter_identifies_each_bundled_skill(self):
        for path in (ROOT / "plugins").glob("*/skills/*/SKILL.md"):
            with self.subTest(path=path):
                lines = path.read_text(encoding="utf-8").splitlines()
                self.assertEqual(lines[0], "---")
                metadata = yaml.safe_load("\n".join(lines[1:lines.index("---", 1)]))
                self.assertEqual(metadata["name"], path.parent.name)
                self.assertIsInstance(metadata["description"], str)
                self.assertTrue(metadata["description"].strip())

    def test_legacy_video_analysis_path_resolves_to_packaged_skill(self):
        legacy = ROOT / "skills/video-analysis"
        self.assertTrue(legacy.is_symlink())
        self.assertEqual(legacy.resolve(strict=True), ROOT / "plugins/video-analysis/skills/video-analysis")
