"""Local example safeguards without importing or contacting a real tracker."""
import importlib.util
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

path = Path(__file__).resolve().parents[1] / "examples" / "trackio_local.py"
spec = importlib.util.spec_from_file_location("trackio_local_example", path)
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)


class LocalExampleTests(unittest.TestCase):
    def check_rejected(self, settings):
        sdk = Mock()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "must-not-exist"
            with patch.dict(os.environ, settings, clear=True), patch.dict("sys.modules", {"trackio": sdk}):
                with self.assertRaises(SystemExit) as raised:
                    example.main(["audit.json", str(output)])
                message = str(raised.exception)
                for key, value in settings.items():
                    self.assertIn(key, message)
                    if value:
                        self.assertNotIn(value, message)
                    self.assertEqual(os.environ[key], value)
                self.assertIn("unset", message)
                self.assertIn("trackio_existing_run.py", message)
                self.assertFalse(output.exists())
                sdk.init.assert_not_called()

    def test_space_setting_rejected(self):
        self.check_rejected({"TRACKIO_SPACE_ID": "private-org/private-space"})

    def test_server_setting_rejected(self):
        self.check_rejected({"TRACKIO_SERVER_URL": "https://user:secret@example.invalid"})

    def test_bucket_setting_rejected(self):
        self.check_rejected({"TRACKIO_BUCKET_ID": "org/private-bucket"})

    def test_both_settings_rejected(self):
        self.check_rejected({"TRACKIO_SPACE_ID": "secret-space", "TRACKIO_SERVER_URL": "secret-url"})

    def test_empty_setting_requires_unset(self):
        self.check_rejected({"TRACKIO_SPACE_ID": ""})

    def test_local_path_and_caller_steps(self):
        sdk = Mock()
        assessment = object()
        adapter = Mock(return_value=SimpleNamespace(status="logged"))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "local"
            with patch.dict(os.environ, {}, clear=True), patch.dict("sys.modules", {"trackio": sdk}), \
                    patch("kalanos_tracking.load_assessment", return_value=assessment), \
                    patch("kalanos_tracking.log_to_trackio", adapter):
                example.main(["audit.json", str(output)])
                self.assertEqual(os.environ["TRACKIO_DIR"], str(output.resolve()))
                sdk.init.assert_called_once_with(project="kalanos-local-smoke", name="run")
                adapter.assert_called_once_with(assessment, run=sdk.init.return_value, step=0,
                                                slot="train_data", artifact="summary", strict=True)
                sdk.log.assert_called_once_with({"loss": 1.0}, step=1)
                sdk.finish.assert_called_once_with()

    def test_usage_before_initialization(self):
        with self.assertRaises(SystemExit):
            example.main([])
