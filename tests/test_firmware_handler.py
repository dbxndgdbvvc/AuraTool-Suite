"""
Unit Tests — Firmware Handler Engine
=====================================
Tests for modules/firmware_handler.py covering file type detection,
payload.bin extraction, scatter file parsing, raw program XML parsing,
boot image header parsing, IPSW analysis, checksum verification,
and firmware info extraction.
"""

import hashlib
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.firmware_handler import FirmwareHandler, MAGIC_SIGNATURES


# ═══════════════════════════════════════════════════════════════════════════════
#  MAGIC SIGNATURES
# ═══════════════════════════════════════════════════════════════════════════════

class TestMagicSignatures(unittest.TestCase):
    """Test MAGIC_SIGNATURES data integrity."""

    def test_all_signatures_have_type_and_desc(self):
        for magic, info in MAGIC_SIGNATURES.items():
            with self.subTest(magic=magic):
                self.assertIn("type", info, f"Magic {magic!r} missing 'type'")
                self.assertIn("desc", info, f"Magic {magic!r} missing 'desc'")

    def test_android_boot_magic(self):
        self.assertIn(b"ANDROID!", MAGIC_SIGNATURES)
        self.assertEqual(MAGIC_SIGNATURES[b"ANDROID!"]["type"], "BOOT_IMAGE")

    def test_payload_bin_magic(self):
        self.assertIn(b"CrAU", MAGIC_SIGNATURES)
        self.assertEqual(MAGIC_SIGNATURES[b"CrAU"]["type"], "PAYLOAD_BIN")

    def test_samsung_tar_magic(self):
        self.assertIn(b"ALS\x00", MAGIC_SIGNATURES)
        self.assertEqual(MAGIC_SIGNATURES[b"ALS\x00"]["type"], "SAMSUNG_TAR")

    def test_zip_magic(self):
        self.assertIn(b"PK\x03\x04", MAGIC_SIGNATURES)
        self.assertEqual(MAGIC_SIGNATURES[b"PK\x03\x04"]["type"], "ZIP")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIRMWARE HANDLER INIT
# ═══════════════════════════════════════════════════════════════════════════════

class TestFirmwareHandlerInit(unittest.TestCase):
    """Test FirmwareHandler initialization."""

    def setUp(self):
        self.fh = FirmwareHandler()

    def test_instance_creation(self):
        self.assertIsInstance(self.fh, FirmwareHandler)

    def test_crypto_lazy_loaded(self):
        self.assertIsNone(self.fh._crypto)

    def test_get_crypto_returns_instance(self):
        c = self.fh._get_crypto()
        self.assertIsNotNone(c)
        self.assertEqual(self.fh._crypto, c)  # Cached


# ═══════════════════════════════════════════════════════════════════════════════
#  FILE TYPE DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestFileTypeDetection(unittest.TestCase):
    """Test detect_file_type with real and simulated files."""

    def setUp(self):
        self.fh = FirmwareHandler()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_magic(self, magic: bytes, suffix: str = ".bin") -> str:
        fpath = os.path.join(self.tmpdir, f"test{suffix}")
        with open(fpath, "wb") as f:
            f.write(magic + os.urandom(256))
        return fpath

    def test_detect_android_boot_image(self):
        fpath = self._write_magic(b"ANDROID!")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "BOOT_IMAGE")
        self.assertEqual(r["description"], "Android Boot Image")

    def test_detect_payload_bin(self):
        fpath = self._write_magic(b"CrAU")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "PAYLOAD_BIN")

    def test_detect_samsung_tar(self):
        fpath = self._write_magic(b"ALS\x00")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "SAMSUNG_TAR")

    def test_detect_samsung_odin(self):
        fpath = self._write_magic(b"S00S")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "SAMSUNG_ODIN")

    def test_detect_apple_ipsw(self):
        fpath = self._write_magic(b"AEA\x00")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "APPLE_IPSW")

    def test_detect_apple_img4(self):
        fpath = self._write_magic(b"IM4P")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "APPLE_IMG4")

    def test_detect_qualcomm_edl(self):
        fpath = self._write_magic(b"QDL")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "EDL_FIREHOSE")

    def test_detect_mtk_da(self):
        fpath = self._write_magic(b"MTK\x00")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "MTK_DA")

    def test_detect_zip(self):
        fpath = self._write_magic(b"PK\x03\x04")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "ZIP")

    def test_detect_gzip(self):
        fpath = self._write_magic(b"\x1f\x8b")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "GZIP")

    def test_detect_bzip2(self):
        fpath = self._write_magic(b"BZh")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "BZIP2")

    def test_detect_xz(self):
        fpath = self._write_magic(b"\xfd7zXZ\x00")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "XZ")

    def test_detect_png(self):
        fpath = self._write_magic(b"\x89PNG")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "PNG")

    def test_detect_jpeg(self):
        fpath = self._write_magic(b"\xff\xd8\xff")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "JPEG")

    def test_detect_pdf(self):
        fpath = self._write_magic(b"%PDF")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "PDF")

    def test_detect_sqlite(self):
        fpath = self._write_magic(b"SQLite")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "SQLITE")

    def test_detect_elf_binary(self):
        fpath = self._write_magic(b"\x7fELF")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "ELF")

    def test_detect_pe_executable(self):
        fpath = self._write_magic(b"MZ")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "PE")

    def test_detect_unknown_file(self):
        fpath = self._write_magic(b"\x00\x00\x00\x00")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["type"], "UNKNOWN")

    def test_detect_nonexistent_file(self):
        r = self.fh.detect_file_type("/nonexistent/file.bin")
        self.assertEqual(r["type"], "UNKNOWN")
        self.assertIn("Cannot read", r["description"])

    def test_detection_includes_path(self):
        fpath = self._write_magic(b"CrAU")
        r = self.fh.detect_file_type(fpath)
        self.assertEqual(r["path"], fpath)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAYLOAD.BIN EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestPayloadBinExtraction(unittest.TestCase):
    """Test extract_payload_bin with real and simulated files."""

    def setUp(self):
        self.fh = FirmwareHandler()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_extract_simulated_when_nonexistent(self):
        out = os.path.join(self.tmpdir, "out_sim")
        r = self.fh.extract_payload_bin("/nonexistent/payload.bin", out)
        self.assertEqual(r["status"], "EXTRACTED")
        self.assertGreater(r["count"], 0)
        self.assertTrue(os.path.isdir(out))

    def test_extract_creates_output_files(self):
        out = os.path.join(self.tmpdir, "out_files")
        r = self.fh.extract_payload_bin("/nonexistent/payload.bin", out)
        for partition_path in r["partitions"]:
            self.assertTrue(os.path.isfile(partition_path), f"{partition_path} should exist")

    def test_extract_boot_image_has_magic(self):
        out = os.path.join(self.tmpdir, "out_boot")
        r = self.fh.extract_payload_bin("/nonexistent/payload.bin", out)
        # Find boot.img in extracted files
        boot_files = [p for p in r["partitions"] if "boot" in os.path.basename(p)]
        if boot_files:
            with open(boot_files[0], "rb") as f:
                magic = f.read(8)
            self.assertEqual(magic[:8], b"ANDROID!")

    def test_extract_crau_payload(self):
        """Test parsing of real CrAU format payload."""
        out = os.path.join(self.tmpdir, "out_crau")
        # Build a minimal CrAU payload
        payload_path = os.path.join(self.tmpdir, "payload.bin")
        version = struct.pack(">Q", 2)
        manifest = b"fake_manifest_data"
        manifest_size = struct.pack(">Q", len(manifest))
        sig_size = struct.pack(">I", 0)
        with open(payload_path, "wb") as f:
            f.write(b"CrAU" + version + manifest_size + sig_size + manifest)

        r = self.fh.extract_payload_bin(payload_path, out)
        self.assertEqual(r["status"], "EXTRACTED")
        # Without protobuf, falls back to simulation with partitions list
        self.assertIn("partitions", r)
        self.assertGreater(r.get("count", 0), 0)


# ═══════════════════════════════════════════════════════════════════════════════
#  SCATTER FILE PARSING
# ═══════════════════════════════════════════════════════════════════════════════

class TestScatterFileParsing(unittest.TestCase):
    """Test parse_scatter_file."""

    def setUp(self):
        self.fh = FirmwareHandler()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_simulated_scatter_when_nonexistent(self):
        r = self.fh.parse_scatter_file("/nonexistent/scatter.txt")
        self.assertEqual(r["status"], "SIMULATED")
        self.assertEqual(r["platform"], "MediaTek")
        self.assertGreater(r["count"], 0)

    def test_simulated_scatter_has_preloader(self):
        r = self.fh.parse_scatter_file("/nonexistent/scatter.txt")
        names = [p["name"] for p in r["partitions"]]
        self.assertIn("preloader", names)
        self.assertIn("boot", names)
        self.assertIn("system", names)

    def test_parse_real_scatter_file(self):
        scatter_path = os.path.join(self.tmpdir, "scatter.txt")
        content = (
            "partition_name=preloader\n"
            "file_name=preloader.bin\n"
            "partition_name=pgpt\n"
            "file_name=pgpt.bin\n"
            "partition_name=boot\n"
            "file_name=boot.img\n"
        )
        with open(scatter_path, "w") as f:
            f.write(content)
        r = self.fh.parse_scatter_file(scatter_path)
        self.assertEqual(r["status"], "PARSED")
        self.assertEqual(r["platform"], "MediaTek")
        self.assertEqual(r["count"], 3)
        self.assertEqual(r["partitions"][0]["name"], "preloader")
        self.assertEqual(r["partitions"][0]["file"], "preloader.bin")


# ═══════════════════════════════════════════════════════════════════════════════
#  QUALCOMM RAW PROGRAM XML
# ═══════════════════════════════════════════════════════════════════════════════

class TestRawProgramXML(unittest.TestCase):
    """Test parse_raw_program_xml."""

    def setUp(self):
        self.fh = FirmwareHandler()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_simulated_when_nonexistent(self):
        r = self.fh.parse_raw_program_xml("/nonexistent/rawprogram.xml")
        self.assertEqual(r["status"], "SIMULATED")
        self.assertEqual(r["platform"], "Qualcomm")
        self.assertGreater(r["count"], 0)

    def test_parse_real_xml(self):
        xml_path = os.path.join(self.tmpdir, "rawprogram0.xml")
        content = '''<?xml version="1.0"?>
<data>
  <program SECTOR_SIZE_IN_BYTES="512" filename="gpt.bin" num_partition_sectors="65536" start_sector="0"/>
  <program SECTOR_SIZE_IN_BYTES="512" filename="userdata.img" num_partition_sectors="2097152" start_sector="131072"/>
</data>'''
        with open(xml_path, "w") as f:
            f.write(content)
        r = self.fh.parse_raw_program_xml(xml_path)
        self.assertEqual(r["status"], "PARSED")
        self.assertEqual(r["platform"], "Qualcomm")
        self.assertEqual(r["count"], 2)
        self.assertEqual(r["partitions"][0]["filename"], "gpt.bin")


# ═══════════════════════════════════════════════════════════════════════════════
#  BOOT IMAGE HEADER
# ═══════════════════════════════════════════════════════════════════════════════

class TestBootImageParsing(unittest.TestCase):
    """Test parse_boot_image."""

    def setUp(self):
        self.fh = FirmwareHandler()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_simulated_boot_header(self):
        r = self.fh.parse_boot_image("/nonexistent/boot.img")
        self.assertTrue(r["valid"])
        self.assertEqual(r["magic"], "ANDROID!")
        self.assertIn("kernel_size", r)
        self.assertIn("ramdisk_size", r)
        self.assertIn("page_size", r)

    def test_parse_real_boot_image(self):
        boot_path = os.path.join(self.tmpdir, "boot.img")
        # Build a minimal Android boot image header
        magic = b"ANDROID!"
        kernel_size = struct.pack("<I", 24154112)
        kernel_addr = struct.pack("<I", 0x00008000)
        ramdisk_size = struct.pack("<I", 4567890)
        ramdisk_addr = struct.pack("<I", 0x01000000)
        second_size = struct.pack("<I", 0)
        second_addr = struct.pack("<I", 0)
        tags_addr = struct.pack("<I", 0x00000100)
        page_size = struct.pack("<I", 4096)
        with open(boot_path, "wb") as f:
            f.write(magic + kernel_size + kernel_addr + ramdisk_size +
                    ramdisk_addr + second_size + second_addr + tags_addr + page_size)
        r = self.fh.parse_boot_image(boot_path)
        self.assertTrue(r["valid"])
        self.assertEqual(r["magic"], "ANDROID!")
        self.assertEqual(r["kernel_size"], 24154112)
        self.assertEqual(r["ramdisk_size"], 4567890)
        self.assertEqual(r["page_size"], 4096)

    def test_parse_invalid_boot_image(self):
        boot_path = os.path.join(self.tmpdir, "bad_boot.img")
        with open(boot_path, "wb") as f:
            f.write(b"NOT_MAGIC" + os.urandom(256))
        r = self.fh.parse_boot_image(boot_path)
        self.assertFalse(r["valid"])
        self.assertIn("error", r)


# ═══════════════════════════════════════════════════════════════════════════════
#  IPSW ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIPSWAnalysis(unittest.TestCase):
    """Test analyze_ipsw."""

    def setUp(self):
        self.fh = FirmwareHandler()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_simulated_ipsw(self):
        r = self.fh.analyze_ipsw("/nonexistent/iphone.ipsw")
        self.assertTrue(r["valid"])
        self.assertIn("device", r)
        self.assertIn("version", r)
        self.assertGreater(r["count"], 0)
        self.assertEqual(r["status"], "SIMULATED")

    def test_analyze_real_zip_ipsw(self):
        import zipfile
        ipsw_path = os.path.join(self.tmpdir, "test.ipsw")
        with zipfile.ZipFile(ipsw_path, "w") as zf:
            zf.writestr("Firmware/DFU/iBSS.img4", "fake_ibss")
            zf.writestr("Restore/kernelcache.img4", "fake_kernel")
            zf.writestr("098-21416-056.dmg", "fake_dmg")
            zf.writestr("manifest.plist", "fake_plist")
        r = self.fh.analyze_ipsw(ipsw_path)
        self.assertTrue(r["valid"])
        self.assertEqual(r["status"], "ANALYZED")
        # analyze_ipsw filters for .dmg and .plist extensions
        self.assertEqual(r["count"], 2)


# ═══════════════════════════════════════════════════════════════════════════════
#  CHECKSUM VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestChecksumVerification(unittest.TestCase):
    """Test verify_checksum and compute_hash."""

    def setUp(self):
        self.fh = FirmwareHandler()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_verify_valid_checksum(self):
        fpath = os.path.join(self.tmpdir, "test.bin")
        data = b"hello firmware world"
        with open(fpath, "wb") as f:
            f.write(data)
        expected = hashlib.sha256(data).hexdigest()
        r = self.fh.verify_checksum(fpath, expected)
        self.assertTrue(r["valid"])
        self.assertEqual(r["algorithm"], "sha256")

    def test_verify_invalid_checksum(self):
        fpath = os.path.join(self.tmpdir, "test.bin")
        with open(fpath, "wb") as f:
            f.write(b"some data")
        r = self.fh.verify_checksum(fpath, "0" * 64)
        self.assertFalse(r["valid"])

    def test_compute_hash(self):
        fpath = os.path.join(self.tmpdir, "hash.bin")
        data = b"test data for hashing"
        with open(fpath, "wb") as f:
            f.write(data)
        h = self.fh.compute_hash(fpath, "sha256")
        self.assertEqual(h, hashlib.sha256(data).hexdigest())

    def test_compute_hash_sha512(self):
        fpath = os.path.join(self.tmpdir, "hash512.bin")
        data = b"another test"
        with open(fpath, "wb") as f:
            f.write(data)
        h = self.fh.compute_hash(fpath, "sha512")
        self.assertEqual(h, hashlib.sha512(data).hexdigest())


# ═══════════════════════════════════════════════════════════════════════════════
#  FIRMWARE INFO
# ═══════════════════════════════════════════════════════════════════════════════

class TestFirmwareInfo(unittest.TestCase):
    """Test get_firmware_info."""

    def setUp(self):
        self.fh = FirmwareHandler()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_firmware_info_includes_size(self):
        fpath = os.path.join(self.tmpdir, "fw.bin")
        data = b"\x00" * 1024 * 1024  # 1 MB
        with open(fpath, "wb") as f:
            f.write(data)
        r = self.fh.get_firmware_info(fpath)
        self.assertEqual(r["size_bytes"], 1024 * 1024)
        self.assertAlmostEqual(r["size_mb"], 1.0, places=1)

    def test_firmware_info_payload_bin(self):
        fpath = os.path.join(self.tmpdir, "payload.bin")
        with open(fpath, "wb") as f:
            f.write(b"CrAU" + os.urandom(100))
        r = self.fh.get_firmware_info(fpath)
        self.assertEqual(r["type"], "PAYLOAD_BIN")
        self.assertIn("details", r)
        self.assertIn("payload", r["details"].lower())

    def test_firmware_info_samsung_tar(self):
        fpath = os.path.join(self.tmpdir, "fw.tar")
        with open(fpath, "wb") as f:
            f.write(b"ALS\x00" + os.urandom(100))
        r = self.fh.get_firmware_info(fpath)
        self.assertEqual(r["type"], "SAMSUNG_TAR")
        self.assertIn("details", r)

    def test_firmware_info_boot_image(self):
        fpath = os.path.join(self.tmpdir, "boot.img")
        with open(fpath, "wb") as f:
            f.write(b"ANDROID!" + b"\x00" * 256)
        r = self.fh.get_firmware_info(fpath)
        self.assertEqual(r["type"], "BOOT_IMAGE")
        self.assertIn("details", r)


# ═══════════════════════════════════════════════════════════════════════════════
#  CHECKSUM WITH NONEXISTENT FILE
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        self.fh = FirmwareHandler()

    def test_checksum_nonexistent_file(self):
        r = self.fh.verify_checksum("/nonexistent/file", "abc")
        self.assertFalse(r["valid"])
        self.assertIn("error", r)

    def test_firmware_info_nonexistent_file(self):
        r = self.fh.get_firmware_info("/nonexistent/file")
        self.assertEqual(r["type"], "UNKNOWN")
        self.assertEqual(r["size_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
