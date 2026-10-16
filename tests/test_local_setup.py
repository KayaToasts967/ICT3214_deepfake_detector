import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from backend.run import load_local_environment, main as run_local
from scripts.package_release import build_release


class LocalSetupTests(unittest.TestCase):
    def test_environment_settings_are_literal_and_do_not_override_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            env = Path(directory) / ".env"
            env.write_text('# comment\nVOICE_SCOPE_PORT=8001\nDETECTOR_PLUGIN="plugins.test:create_detector"\nMODEL_DIR=$(echo secret)\n', encoding="utf-8")
            with patch.dict(os.environ, {"VOICE_SCOPE_PORT": "8123"}, clear=True):
                load_local_environment(env)
                self.assertEqual(os.environ["VOICE_SCOPE_PORT"], "8123")
                self.assertEqual(os.environ["DETECTOR_PLUGIN"], "plugins.test:create_detector")
                self.assertEqual(os.environ["MODEL_DIR"], "$(echo secret)")

    def test_invalid_environment_entry_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            env = Path(directory) / ".env"
            env.write_text("not a setting", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_local_environment(env)

    def test_native_launcher_uses_loopback_and_single_worker(self):
        with patch("backend.run.load_local_environment"), patch.dict(os.environ, {}, clear=True), patch("sys.argv", ["run.py", "--port", "8123"]), patch("uvicorn.run") as start:
            run_local()
            start.assert_called_once_with("backend.main:app", host="127.0.0.1", port=8123, workers=1)

    def test_container_launcher_has_fixed_internal_port(self):
        with patch("backend.run.load_local_environment"), patch("sys.argv", ["run.py", "--container", "--port", "8000"]), patch("uvicorn.run") as start:
            run_local()
            start.assert_called_once_with("backend.main:app", host="0.0.0.0", port=8000, workers=1)

    def test_invalid_port_is_rejected(self):
        with patch("backend.run.load_local_environment"), patch("sys.argv", ["run.py", "--port", "65536"]), self.assertRaises(SystemExit):
            run_local()

    def test_source_zip_excludes_local_environment_and_cloud_data(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "handoff.zip"
            build_release(root, output)
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
                self.assertIn("voice-scope/compose.yaml", names)
                self.assertIn("voice-scope/.env.example", names)
                self.assertIn("voice-scope/models/README.md", names)
                for name in names:
                    parts = Path(name).parts
                    self.assertFalse(set(parts) & {".git", ".openai", ".venv", ".runtime", "artifacts", "__pycache__"})
                    self.assertNotEqual(Path(name).name, ".env")


if __name__ == "__main__":
    unittest.main()
