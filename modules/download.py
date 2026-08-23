"""
AuraTool-Suite — Download Manager
===================================
Manages download of firmware packages, flash tools, drivers,
and auxiliary resources with progress tracking and integrity verification.
"""

import hashlib
import logging
import os
import time


class DownloadManager:
    """
    Handles downloading firmware images, flash tools, driver packages,
    and other resources with checksum verification.
    """

    BASE_URL = "https://downloads.auratool-suite.com"

    FIRMWARE_CATALOGUE = {
        "Samsung": {
            "Galaxy S23": {
                "url": f"{BASE_URL}/firmware/samsung/galaxy-s23/latest.tar",
                "size_mb": 4200,
                "sha256": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
                "android_version": "14",
            },
            "Galaxy S22": {
                "url": f"{BASE_URL}/firmware/samsung/galaxy-s22/latest.tar",
                "size_mb": 3800,
                "sha256": "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
                "android_version": "14",
            },
            "Galaxy A54": {
                "url": f"{BASE_URL}/firmware/samsung/galaxy-a54/latest.tar",
                "size_mb": 3200,
                "sha256": "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
                "android_version": "14",
            },
        },
        "Xiaomi": {
            "Redmi Note 12": {
                "url": f"{BASE_URL}/firmware/xiaomi/redmi-note-12/latest.zip",
                "size_mb": 3500,
                "sha256": "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
                "android_version": "13",
            },
        },
    }

    def __init__(self, download_dir: str = "./downloads"):
        self.logger = logging.getLogger("AuraTool.Download")
        self.download_dir = download_dir
        self.active_downloads = []
        self.completed_downloads = []

    def list_available_firmware(self, manufacturer: str = None) -> list:
        """List available firmware downloads, optionally filtered by manufacturer."""
        results = []
        catalogue = self.FIRMWARE_CATALOGUE
        if manufacturer:
            catalogue = {manufacturer: catalogue.get(manufacturer, {})}

        for mfr, models in catalogue.items():
            for model, info in models.items():
                results.append({
                    "manufacturer": mfr,
                    "model": model,
                    "url": info["url"],
                    "size_mb": info["size_mb"],
                    "android_version": info["android_version"],
                })
        return results

    def download_firmware(self, manufacturer: str, model: str, callback=None) -> dict:
        """Download a firmware package with progress callback."""
        mfr_data = self.FIRMWARE_CATALOGUE.get(manufacturer, {})
        fw_info = mfr_data.get(model)

        if not fw_info:
            return {"error": f"No firmware found for {manufacturer} {model}"}

        self.logger.info(f"Downloading firmware: {manufacturer} {model} ({fw_info['size_mb']} MB)")
        os.makedirs(self.download_dir, exist_ok=True)
        dest = os.path.join(self.download_dir, f"{manufacturer}_{model}_firmware.bin")

        # Simulate download with progress
        total_chunks = 20
        for i in range(1, total_chunks + 1):
            time.sleep(0.1)
            if callback:
                callback(i, total_chunks, f"Downloading {manufacturer} {model} ({i}/{total_chunks})")

        # Simulate writing the file
        with open(dest, "wb") as f:
            f.write(f"Firmware placeholder: {manufacturer} {model}".encode())

        result = {
            "manufacturer": manufacturer,
            "model": model,
            "destination": dest,
            "size_mb": fw_info["size_mb"],
            "sha256_expected": fw_info["sha256"],
            "status": "DOWNLOADED",
        }
        self.completed_downloads.append(result)
        self.logger.info(f"Download complete: {dest}")
        return result

    def verify_download(self, filepath: str, expected_sha256: str) -> bool:
        """Verify downloaded file integrity against expected SHA-256."""
        self.logger.info(f"Verifying integrity of {filepath}...")
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        actual = h.hexdigest()
        match = actual == expected_sha256
        if match:
            self.logger.info("  Integrity check PASSED.")
        else:
            self.logger.warning(f"  Integrity check FAILED. Expected: {expected_sha256[:16]}...")
        return match

    def get_download_history(self) -> list:
        """Return all completed downloads."""
        return self.completed_downloads
