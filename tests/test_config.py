import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
from pathlib import Path
import yaml

from dask_iclx.config import (
    _ensure_user_config_file,
    _set_base_config,
    _user_config_file_path,
)


class TestConfig(unittest.TestCase):
    """Test configuration functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(
            lambda: os.rmdir(self.temp_dir) if os.path.exists(self.temp_dir) else None
        )

    @patch("dask.config.ensure_file")
    def test_ensure_user_config_file(self, mock_ensure_file):
        """Test that user config file is properly ensured."""
        _ensure_user_config_file()
        mock_ensure_file.assert_called_once()

    @patch("dask.config.update")
    @patch("builtins.open")
    @patch("yaml.safe_load")
    def test_set_base_config_default_priority(
        self, mock_yaml_load, mock_open, mock_update
    ):
        """Test setting base config with default priority."""
        mock_yaml_load.return_value = {"test_key": "test_value"}
        mock_open.return_value.__enter__.return_value = MagicMock()

        _set_base_config()

        mock_update.assert_called_once()
        args, kwargs = mock_update.call_args
        self.assertEqual(kwargs.get("priority"), "old")

    @patch("dask.config.update")
    @patch("builtins.open")
    @patch("yaml.safe_load")
    def test_set_base_config_custom_priority(
        self, mock_yaml_load, mock_open, mock_update
    ):
        """Test setting base config with custom priority."""
        mock_yaml_load.return_value = {"test_key": "test_value"}
        mock_open.return_value.__enter__.return_value = MagicMock()

        _set_base_config(priority="new")

        mock_update.assert_called_once()
        args, kwargs = mock_update.call_args
        self.assertEqual(kwargs.get("priority"), "new")

    @patch("dask.config.PATH", "/mock/path")
    def test_user_config_file_path(self):
        """Test user config file path generation."""
        result = _user_config_file_path()
        expected = Path("/mock/path") / "jobqueue-ic.yaml"
        self.assertEqual(result, expected)

    def test_yaml_config_format(self):
        """Test that the YAML config file is properly formatted."""
        from dask_iclx.config import PKG_CONFIG_FILE

        with open(PKG_CONFIG_FILE) as f:
            config = yaml.safe_load(f)

        # Check basic structure
        self.assertIn("jobqueue", config)
        self.assertIn("ic", config["jobqueue"])

        # Check required fields
        ic_config = config["jobqueue"]["ic"]
        required_fields = [
            "name",
            "cores",
            "memory",
            "worker-image",
            "container-runtime",
            "death-timeout",
        ]
        for field in required_fields:
            self.assertIn(field, ic_config)


if __name__ == "__main__":
    unittest.main()
