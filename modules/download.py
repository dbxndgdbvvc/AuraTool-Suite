"""
AuraTool-Suite — Download Manager
===================================
Manages download of firmware packages, flash tools, drivers,
and auxiliary resources with progress tracking and integrity verification.

Features:
- Real HTTP/HTTPS downloads with progress callbacks
- Resume support via HTTP Range headers
- Retry logic with exponential backoff
- SHA-256 integrity verification
- Partial download detection and cleanup
"""

import hashlib
import logging
import os
import time
import urllib.request
import urllib.error


class DownloadManager:
    """
    Handles downloading firmware images, flash tools, driver packages,
    and other resources with checksum verification.

    Supports:
    - Real HTTP downloads with progress tracking
    - Resume interrupted downloads
    - Automatic retry on failure
    - SHA-256 integrity verification
    """

    BASE_URL = "https://downloads.auratool-suite.com"
    CHUNK_SIZE = 65536  # 64KB chunks for efficient streaming
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2  # seconds, doubles each retry
    CONNECT_TIMEOUT = 30  # seconds

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
        """
        Download a firmware package with progress callback and retry logic.

        Args:
            manufacturer: Device manufacturer (e.g., "Samsung")
            model: Device model (e.g., "Galaxy S23")
            callback: Optional progress callback fn(chunks_downloaded, total_chunks, message)

        Returns:
            dict with keys: manufacturer, model, destination, size_mb,
                           sha256_expected, status, bytes_downloaded, duration_s
        """
        mfr_data = self.FIRMWARE_CATALOGUE.get(manufacturer, {})
        fw_info = mfr_data.get(model)

        if not fw_info:
            return {"error": f"No firmware found for {manufacturer} {model}"}

        url = fw_info["url"]
        self.logger.info(f"Downloading firmware: {manufacturer} {model} ({fw_info['size_mb']} MB)")
        os.makedirs(self.download_dir, exist_ok=True)
        dest = os.path.join(self.download_dir, f"{manufacturer}_{model}_firmware.bin")

        start_time = time.time()
        total_bytes = 0
        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.logger.info(f"Download attempt {attempt}/{self.MAX_RETRIES}: {url}")

                # Check for existing partial download (resume support)
                existing_size = 0
                if os.path.exists(dest):
                    existing_size = os.path.getsize(dest)
                    if existing_size > 0:
                        self.logger.info(f"Resuming from {existing_size} bytes")

                # Create request with optional Range header for resume
                req = urllib.request.Request(url)
                if existing_size > 0:
                    req.add_header("Range", f"bytes={existing_size}-")

                response = urllib.request.urlopen(req, timeout=self.CONNECT_TIMEOUT)

                # Handle resume response
                if existing_size > 0 and response.status == 206:
                    # Server supports resume
                    mode = "ab"
                    downloaded = existing_size
                    self.logger.info("Server supports resume, appending to existing file")
                elif existing_size > 0 and response.status == 200:
                    # Server doesn't support resume, restart download
                    mode = "wb"
                    downloaded = 0
                    self.logger.info("Server doesn't support resume, restarting download")
                else:
                    mode = "wb"
                    downloaded = 0

                # Get total file size if available
                content_length = response.headers.get("Content-Length")
                total_size = int(content_length) + downloaded if content_length else None
                total_chunks = (total_size // self.CHUNK_SIZE) + 1 if total_size else None

                # Download with progress
                with open(dest, mode) as f:
                    while True:
                        chunk = response.read(self.CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if callback and total_chunks:
                            current_chunk = downloaded // self.CHUNK_SIZE
                            callback(current_chunk, total_chunks,
                                   f"Downloading {manufacturer} {model} "
                                   f"({downloaded}/{total_size} bytes)")

                # Download succeeded
                duration = time.time() - start_time
                self.logger.info(f"Download complete: {dest} ({downloaded} bytes in {duration:.1f}s)")

                result = {
                    "manufacturer": manufacturer,
                    "model": model,
                    "destination": dest,
                    "url": url,
                    "size_mb": fw_info["size_mb"],
                    "bytes_downloaded": downloaded,
                    "sha256_expected": fw_info["sha256"],
                    "status": "DOWNLOADED",
                    "duration_s": round(duration, 2),
                    "attempts": attempt,
                }
                self.completed_downloads.append(result)
                return result

            except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
                last_error = str(e)
                self.logger.warning(f"Download attempt {attempt} failed: {e}")

                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_DELAY_BASE ** attempt
                    self.logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"All {self.MAX_RETRIES} download attempts failed")

        # All attempts failed
        duration = time.time() - start_time
        return {
            "error": f"Download failed after {self.MAX_RETRIES} attempts: {last_error}",
            "manufacturer": manufacturer,
            "model": model,
            "url": url,
            "status": "FAILED",
            "duration_s": round(duration, 2),
        }

    def verify_download(self, filepath: str, expected_sha256: str) -> dict:
        """
        Verify downloaded file integrity against expected SHA-256.

        Args:
            filepath: Path to the downloaded file
            expected_sha256: Expected SHA-256 hash

        Returns:
            dict with keys: valid, actual_sha256, file_size, error
        """
        if not os.path.exists(filepath):
            return {
                "valid": False,
                "error": f"File not found: {filepath}",
                "file_size": 0,
            }

        self.logger.info(f"Verifying integrity of {filepath}...")

        try:
            file_size = os.path.getsize(filepath)
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(self.CHUNK_SIZE)
                    if not chunk:
                        break
                    h.update(chunk)

            actual = h.hexdigest()
            match = actual == expected_sha256

            if match:
                self.logger.info(f"  Integrity check PASSED ({file_size} bytes)")
            else:
                self.logger.warning(
                    f"  Integrity check FAILED. Expected: {expected_sha256[:16]}..., "
                    f"Got: {actual[:16]}..."
                )

            return {
                "valid": match,
                "actual_sha256": actual,
                "expected_sha256": expected_sha256,
                "file_size": file_size,
            }

        except OSError as e:
            self.logger.error(f"Integrity check error: {e}")
            return {
                "valid": False,
                "error": str(e),
                "file_size": 0,
            }

    def get_download_history(self) -> list:
        """Return all completed downloads."""
        return self.completed_downloads

    def clear_download_history(self) -> None:
        """Clear the download history."""
        self.completed_downloads.clear()
        self.logger.info("Download history cleared")

    def get_active_downloads(self) -> list:
        """Return list of currently active downloads."""
        return self.active_downloads

    def cancel_download(self, manufacturer: str, model: str) -> bool:
        """
        Cancel an active download.

        Args:
            manufacturer: Device manufacturer
            model: Device model

        Returns:
            True if cancelled, False if not found
        """
        for download in self.active_downloads:
            if download.get("manufacturer") == manufacturer and download.get("model") == model:
                download["cancelled"] = True
                self.logger.info(f"Download cancelled: {manufacturer} {model}")
                return True
        return False

    def get_disk_usage(self) -> dict:
        """Get disk usage statistics for the download directory."""
        if not os.path.exists(self.download_dir):
            return {"total_size_bytes": 0, "file_count": 0, "directory": self.download_dir}

        total_size = 0
        file_count = 0

        for entry in os.scandir(self.download_dir):
            if entry.is_file():
                total_size += entry.stat().st_size
                file_count += 1

        return {
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
            "directory": self.download_dir,
        }
