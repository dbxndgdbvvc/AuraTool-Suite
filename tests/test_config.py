"""
Unit Tests — Configuration Manager
====================================
Tests for Config: defaults, file loading, env overrides, validation.
"""

import json
import os
import tempfile
import unittest
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config, get_config, reset_config


class TestConfigDefaults(unittest.TestCase):
    """Test that default configuration values are correct."""

    def setUp(self):
        self.config = Config()

    def test_server_port_default(self):
        self.assertEqual(self.config.get("server.port"), 8500)

    def test_server_host_default(self):
        self.assertEqual(self.config.get("server.host"), "0.0.0.0")

    def test_download_directory_default(self):
        self.assertEqual(self.config.get("download.directory"), "./downloads")

    def test_download_max_retries_default(self):
        self.assertEqual(self.config.get("download.max_retries"), 3)

    def test_api_rate_limit_default(self):
        self.assertEqual(self.config.get("api.rate_limit"), 100)

    def test_logging_level_default(self):
        self.assertEqual(self.config.get("logging.level"), "INFO")

    def test_localization_default_lang(self):
        self.assertEqual(self.config.get("localization.default_lang"), "en")

    def test_rtl_languages_default(self):
        rtl = self.config.get("localization.rtl_languages")
        self.assertIn("ar", rtl)
        self.assertIn("fa", rtl)
        self.assertIn("ur", rtl)


class TestConfigDotNotation(unittest.TestCase):
    """Test dot notation access."""

    def setUp(self):
        self.config = Config()

    def test_nested_get(self):
        self.assertEqual(self.config.get("server.port"), 8500)

    def test_deep_nested_get(self):
        # Access non-existent deep path returns default
        result = self.config.get("nonexistent.deep.path", "fallback")
        self.assertEqual(result, "fallback")

    def test_set_value(self):
        self.config.set("server.port", 9999)
        self.assertEqual(self.config.get("server.port"), 9999)

    def test_set_creates_path(self):
        self.config.set("new.nested.key", "value")
        self.assertEqual(self.config.get("new.nested.key"), "value")

    def test_get_with_default(self):
        result = self.config.get("nonexistent.key", "default_val")
        self.assertEqual(result, "default_val")


class TestConfigFileLoading(unittest.TestCase):
    """Test loading configuration from files."""

    def test_load_json_file(self):
        config_data = {
            "server": {"port": 9999, "host": "127.0.0.1"},
            "api": {"rate_limit": 50},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            config = Config(f.name)
            os.unlink(f.name)

        self.assertEqual(config.get("server.port"), 9999)
        self.assertEqual(config.get("server.host"), "127.0.0.1")
        self.assertEqual(config.get("api.rate_limit"), 50)

    def test_load_yaml_file(self):
        """Test loading YAML config if PyYAML is installed."""
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not installed")

        config_data = {
            "server": {"port": 7777},
            "download": {"directory": "/tmp/fw"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            f.flush()
            config = Config(f.name)
            os.unlink(f.name)

        self.assertEqual(config.get("server.port"), 7777)
        self.assertEqual(config.get("download.directory"), "/tmp/fw")

    def test_nonexistent_file_uses_defaults(self):
        config = Config("/nonexistent/path/config.json")
        self.assertEqual(config.get("server.port"), 8500)

    def test_invalid_json_uses_defaults(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json content")
            f.flush()
            config = Config(f.name)
            os.unlink(f.name)

        # Should fall back to defaults
        self.assertEqual(config.get("server.port"), 8500)

    def test_partial_config_merges_with_defaults(self):
        """Config file should merge with, not replace, defaults."""
        config_data = {"server": {"port": 9999}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            config = Config(f.name)
            os.unlink(f.name)

        # Custom port
        self.assertEqual(config.get("server.port"), 9999)
        # Default host preserved
        self.assertEqual(config.get("server.host"), "0.0.0.0")


class TestConfigEnvOverrides(unittest.TestCase):
    """Test environment variable overrides."""

    def setUp(self):
        reset_config()

    def tearDown(self):
        # Clean up env vars
        for key in list(os.environ.keys()):
            if key.startswith("AURATOOL_"):
                del os.environ[key]
        reset_config()

    def test_env_override_server_port(self):
        os.environ["AURATOOL_SERVER_PORT"] = "9999"
        config = Config()
        self.assertEqual(config.get("server.port"), 9999)

    def test_env_override_boolean(self):
        os.environ["AURATOOL_API_REQUIRE_AUTH"] = "false"
        config = Config()
        self.assertEqual(config.get("api.require_auth"), False)

    def test_env_override_integer(self):
        os.environ["AURATOOL_DOWNLOAD_MAX_RETRIES"] = "5"
        config = Config()
        self.assertEqual(config.get("download.max_retries"), 5)


class TestConfigValidation(unittest.TestCase):
    """Test configuration validation."""

    def setUp(self):
        self.config = Config()

    def test_valid_config_has_no_errors(self):
        errors = self.config.validate()
        self.assertEqual(len(errors), 0)

    def test_invalid_port_detected(self):
        self.config.set("server.port", 99999)
        errors = self.config.validate()
        self.assertTrue(any("port" in e.lower() for e in errors))

    def test_negative_retries_detected(self):
        self.config.set("download.max_retries", -1)
        errors = self.config.validate()
        self.assertTrue(any("retries" in e.lower() for e in errors))


class TestConfigGetAll(unittest.TestCase):
    """Test get_all and get_section."""

    def setUp(self):
        self.config = Config()

    def test_get_all_returns_dict(self):
        all_config = self.config.get_all()
        self.assertIsInstance(all_config, dict)
        self.assertIn("server", all_config)

    def test_get_section(self):
        server = self.config.get_section("server")
        self.assertIn("port", server)
        self.assertIn("host", server)

    def test_get_section_missing(self):
        result = self.config.get_section("nonexistent")
        self.assertEqual(result, {})


class TestConfigSingleton(unittest.TestCase):
    """Test singleton behavior."""

    def setUp(self):
        reset_config()

    def tearDown(self):
        reset_config()

    def test_get_config_returns_same_instance(self):
        c1 = get_config()
        c2 = get_config()
        self.assertIs(c1, c2)

    def test_reset_config_creates_new_instance(self):
        c1 = get_config()
        reset_config()
        c2 = get_config()
        self.assertIsNot(c1, c2)


if __name__ == "__main__":
    unittest.main()
