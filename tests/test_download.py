"""
Unit Tests — Download Manager
================================
Tests for DownloadManager: listing, downloading, verification, error handling.
"""

import hashlib
import os
import tempfile
import unittest
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.download import DownloadManager


class TestListFirmware(unittest.TestCase):
    """Test firmware listing functionality."""

    def setUp(self):
        self.dl = DownloadManager()

    def test_list_all_firmware(self):
        result = self.dl.list_available_firmware()
        self.assertGreater(len(result), 0)

    def test_list_samsung_firmware(self):
        result = self.dl.list_available_firmware("Samsung")
        self.assertGreater(len(result), 0)
        for fw in result:
            self.assertEqual(fw["manufacturer"], "Samsung")

    def test_list_xiaomi_firmware(self):
        result = self.dl.list_available_firmware("Xiaomi")
        self.assertGreater(len(result), 0)
        for fw in result:
            self.assertEqual(fw["manufacturer"], "Xiaomi")

    def test_list_unknown_manufacturer(self):
        result = self.dl.list_available_firmware("UnknownBrand")
        self.assertEqual(len(result), 0)

    def test_firmware_info_structure(self):
        result = self.dl.list_available_firmware()
        for fw in result:
            self.assertIn("manufacturer", fw)
            self.assertIn("model", fw)
            self.assertIn("url", fw)
            self.assertIn("size_mb", fw)
            self.assertIn("android_version", fw)


class TestDownloadFirmware(unittest.TestCase):
    """Test firmware download functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dl = DownloadManager(download_dir=self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_download_unknown_firmware_returns_error(self):
        result = self.dl.download_firmware("UnknownBrand", "UnknownModel")
        self.assertIn("error", result)

    def test_download_history_tracking(self):
        # Download will fail (URL doesn't exist), but error is tracked
        result = self.dl.download_firmware("Samsung", "Galaxy S23")
        # Result should have status or error
        self.assertTrue(
            result.get("status") == "DOWNLOADED" or result.get("error") is not None
        )


class TestVerifyDownload(unittest.TestCase):
    """Test download verification functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dl = DownloadManager(download_dir=self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_verify_valid_file(self):
        # Create a test file with known content
        test_content = b"Hello, World!"
        test_file = os.path.join(self.temp_dir, "test.bin")
        with open(test_file, "wb") as f:
            f.write(test_content)

        expected_hash = hashlib.sha256(test_content).hexdigest()
        result = self.dl.verify_download(test_file, expected_hash)

        self.assertTrue(result["valid"])
        self.assertEqual(result["actual_sha256"], expected_hash)

    def test_verify_invalid_file(self):
        # Create a test file
        test_file = os.path.join(self.temp_dir, "test.bin")
        with open(test_file, "wb") as f:
            f.write(b"Hello, World!")

        # Wrong hash
        wrong_hash = "0" * 64
        result = self.dl.verify_download(test_file, wrong_hash)

        self.assertFalse(result["valid"])

    def test_verify_nonexistent_file(self):
        result = self.dl.verify_download("/nonexistent/file.bin", "abc123")
        self.assertFalse(result["valid"])
        self.assertIn("error", result)

    def test_verify_empty_file(self):
        test_file = os.path.join(self.temp_dir, "empty.bin")
        with open(test_file, "wb") as f:
            pass  # Empty file

        expected_hash = hashlib.sha256(b"").hexdigest()
        result = self.dl.verify_download(test_file, expected_hash)

        self.assertTrue(result["valid"])
        self.assertEqual(result["file_size"], 0)


class TestDownloadHistory(unittest.TestCase):
    """Test download history management."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dl = DownloadManager(download_dir=self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_history_starts_empty(self):
        self.assertEqual(len(self.dl.get_download_history()), 0)

    def test_clear_history(self):
        self.dl.clear_download_history()
        self.assertEqual(len(self.dl.get_download_history()), 0)


class TestDiskUsage(unittest.TestCase):
    """Test disk usage statistics."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dl = DownloadManager(download_dir=self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_disk_usage_empty_dir(self):
        usage = self.dl.get_disk_usage()
        self.assertEqual(usage["file_count"], 0)
        self.assertEqual(usage["total_size_bytes"], 0)

    def test_disk_usage_with_files(self):
        # Create test files
        for i in range(3):
            test_file = os.path.join(self.temp_dir, f"test{i}.bin")
            with open(test_file, "wb") as f:
                f.write(b"x" * 1024)  # 1KB each

        usage = self.dl.get_disk_usage()
        self.assertEqual(usage["file_count"], 3)
        self.assertEqual(usage["total_size_bytes"], 3 * 1024)

    def test_disk_usage_nonexistent_dir(self):
        dl = DownloadManager(download_dir="/nonexistent/dir")
        usage = dl.get_disk_usage()
        self.assertEqual(usage["file_count"], 0)


class TestDownloadManagerInit(unittest.TestCase):
    """Test DownloadManager initialization."""

    def test_default_download_dir(self):
        dl = DownloadManager()
        self.assertEqual(dl.download_dir, "./downloads")

    def test_custom_download_dir(self):
        dl = DownloadManager(download_dir="/tmp/firmware")
        self.assertEqual(dl.download_dir, "/tmp/firmware")

    def test_logger_initialized(self):
        dl = DownloadManager()
        self.assertIsNotNone(dl.logger)


if __name__ == "__main__":
    unittest.main()
