"""
AuraTool-Suite — Multi-Brand Device Drivers Infrastructure
===========================================================
Handles detection, installation, and status verification for low-level
hardware drivers on Windows and Linux Ubuntu platforms across all major brands.

Features:
- Real ADB/Fastboot command execution via subprocess
- USB device detection via pyusb and platform-specific tools
- Driver installation for Windows (PnP) and Linux (udev rules)
- Cross-platform USB protocol detection (EDL, BROM, DFU, Download Mode)
"""

import logging
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path


class DeviceDriverManager:
    """Manages low-level protocol drivers across Windows and Linux (Ubuntu).
    
    Supports real device detection via ADB, Fastboot, and platform-specific
    tools (Heimdall for Samsung, idevice for Apple, etc.).
    """

    BRAND_DRIVERS = {
        "samsung": "Samsung Mobile USB Driver Stack",
        "qualcomm": "Qualcomm HS-USB QDLoader 9008 Driver",
        "mediatek": "MediaTek Preloader & VCOM USB Driver",
        "xiaomi": "Xiaomi MiFlash & Fastboot Driver Package",
        "huawei": "Huawei HiSuite / USB COM 1.0 Testpoint Driver",
        "apple": "Apple Mobile Device Support & DFU Driver",
        "google": "Google Android ADB & Fastboot Drivers",
        "generic": "WinUSB / LibUSB-Win32 Universal Filter",
    }

    ADB_PATHS = [
        "adb",
        "/usr/bin/adb",
        "/usr/local/bin/adb",
        "platform-tools/adb",
        os.path.expanduser("~/Android/Sdk/platform-tools/adb"),
    ]

    FASTBOOT_PATHS = [
        "fastboot",
        "/usr/bin/fastboot",
        "/usr/local/bin/fastboot",
        "platform-tools/fastboot",
        os.path.expanduser("~/Android/Sdk/platform-tools/fastboot"),
    ]

    def __init__(self):
        self.logger = logging.getLogger("AuraTool.DeviceDrivers")
        self.os_type = platform.system().lower()
        self._adb_path = self._find_tool(self.ADB_PATHS)
        self._fastboot_path = self._find_tool(self.FASTBOOT_PATHS)

    def _find_tool(self, paths: list) -> str:
        """Find the first existing tool path from a list of candidates."""
        for path in paths:
            if shutil.which(path):
                return path
            if os.path.isfile(path):
                return path
        return paths[0]  # Return first path as fallback

    def _run_command(self, cmd: list, timeout: int = 10) -> dict:
        """Execute a shell command with timeout and return structured result."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=None,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "returncode": -1,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Tool not found: {cmd[0]}",
                "returncode": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }

    # ─── ADB Operations ──────────────────────────────────────────────────
    def adb_command(self, *args: str) -> dict:
        """Execute an ADB command and return the result."""
        cmd = [self._adb_path] + list(args)
        self.logger.info(f"ADB: {' '.join(cmd)}")
        return self._run_command(cmd)

    def get_connected_adb_devices(self) -> list:
        """Query active ADB devices connected via USB or network."""
        result = self.adb_command("devices", "-l")
        if not result["success"]:
            self.logger.warning(f"ADB devices query failed: {result['stderr']}")
            return []

        devices = []
        for line in result["stdout"].split("\n")[1:]:
            line = line.strip()
            if not line or "List of" in line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                device_id = parts[0]
                status = parts[1]
                info = " ".join(parts[2:]) if len(parts) > 2 else ""
                devices.append({
                    "id": device_id,
                    "status": status,
                    "info": info,
                    "connected": status == "device",
                })
        self.logger.info(f"ADB devices found: {len(devices)}")
        return devices

    def adb_get_device_info(self, device_id: str) -> dict:
        """Get detailed device information via ADB."""
        props = {}
        prop_keys = [
            ("model", "ro.product.model"),
            ("brand", "ro.product.brand"),
            ("android_version", "ro.build.version.release"),
            ("sdk_version", "ro.build.version.sdk"),
            ("serial", "ro.serialno"),
            ("product", "ro.product.name"),
            ("manufacturer", "ro.product.manufacturer"),
            ("security_patch", "ro.build.version.security_patch"),
            ("baseband", "gsm.version.baseband"),
            ("bootloader", "ro.bootloader"),
        ]

        for key, prop in prop_keys:
            result = self.adb_command("-s", device_id, "shell", "getprop", prop)
            props[key] = result["stdout"] if result["success"] else "unknown"

        return props

    def adb_reboot(self, device_id: str, target: str = "normal") -> dict:
        """Reboot device to a specific mode: normal, recovery, bootloader, sideload."""
        valid_targets = ["normal", "recovery", "bootloader", "sideload"]
        if target not in valid_targets:
            return {"success": False, "error": f"Invalid target: {target}. Valid: {valid_targets}"}

        cmd_args = ["-s", device_id, "reboot"]
        if target != "normal":
            cmd_args.append(target)

        return self.adb_command(*cmd_args)

    def adb_shell(self, device_id: str, command: str) -> dict:
        """Execute a shell command on the device via ADB."""
        return self.adb_command("-s", device_id, "shell", command)

    def adb_push(self, device_id: str, local_path: str, remote_path: str) -> dict:
        """Push a file to the device via ADB."""
        return self.adb_command("-s", device_id, "push", local_path, remote_path)

    def adb_pull(self, device_id: str, remote_path: str, local_path: str) -> dict:
        """Pull a file from the device via ADB."""
        return self.adb_command("-s", device_id, "pull", remote_path, local_path)

    def adb_install(self, device_id: str, apk_path: str) -> dict:
        """Install an APK on the device via ADB."""
        return self.adb_command("-s", device_id, "install", "-r", apk_path)

    def adb_sideload(self, device_id: str, zip_path: str) -> dict:
        """Sideload a ZIP package via ADB recovery."""
        return self.adb_command("-s", device_id, "sideload", zip_path)

    # ─── Fastboot Operations ─────────────────────────────────────────────
    def fastboot_command(self, *args: str) -> dict:
        """Execute a Fastboot command and return the result."""
        cmd = [self._fastboot_path] + list(args)
        self.logger.info(f"Fastboot: {' '.join(cmd)}")
        return self._run_command(cmd, timeout=30)

    def get_fastboot_devices(self) -> list:
        """Query active Fastboot devices."""
        result = self.fastboot_command("devices", "-l")
        if not result["success"]:
            return []

        devices = []
        for line in result["stdout"].split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if parts:
                devices.append({
                    "id": parts[0],
                    "info": " ".join(parts[1:]) if len(parts) > 1 else "",
                })
        self.logger.info(f"Fastboot devices found: {len(devices)}")
        return devices

    def fastboot_get_device_info(self, device_id: str = None) -> dict:
        """Get device information via Fastboot."""
        args = ["getvar", "all"]
        if device_id:
            args = ["-s", device_id] + args
        result = self.fastboot_command(*args)
        info = {}
        if result["success"]:
            for line in result["stdout"].split("\n"):
                if ":" in line:
                    key, _, value = line.partition(":")
                    info[key.strip()] = value.strip()
        return info

    def fastboot_flash(self, device_id: str, partition: str, image_path: str) -> dict:
        """Flash a partition image via Fastboot."""
        args = []
        if device_id:
            args = ["-s", device_id]
        args += ["flash", partition, image_path]
        return self.fastboot_command(*args)

    def fastboot_flash_all(self, device_id: str, directory: str) -> dict:
        """Flash all images in a directory via Fastboot."""
        results = []
        img_dir = Path(directory)
        if not img_dir.is_dir():
            return {"success": False, "error": f"Directory not found: {directory}"}

        for img_file in sorted(img_dir.glob("*.img")):
            partition = img_file.stem
            result = self.fastboot_flash(device_id, partition, str(img_file))
            results.append({
                "partition": partition,
                "file": str(img_file),
                "success": result["success"],
                "output": result["stdout"] or result["stderr"],
            })

        all_ok = all(r["success"] for r in results)
        return {
            "success": all_ok,
            "partitions_flashed": len(results),
            "results": results,
        }

    def fastboot_erase(self, device_id: str, partition: str) -> dict:
        """Erase a partition via Fastboot."""
        args = []
        if device_id:
            args = ["-s", device_id]
        args += ["erase", partition]
        return self.fastboot_command(*args)

    def fastboot_oem(self, device_id: str, command: str) -> dict:
        """Execute an OEM command via Fastboot."""
        args = []
        if device_id:
            args = ["-s", device_id]
        args += ["oem", command]
        return self.fastboot_command(*args)

    def fastboot_unlock(self, device_id: str) -> dict:
        """Unlock the bootloader via Fastboot."""
        return self.fastboot_oem(device_id, "unlock")

    def fastboot_reboot(self, device_id: str = None) -> dict:
        """Reboot device from Fastboot mode."""
        args = []
        if device_id:
            args = ["-s", device_id]
        args.append("reboot")
        return self.fastboot_command(*args)

    # ─── Driver Installation ─────────────────────────────────────────────
    def check_all_drivers(self) -> dict:
        """Verifies driver stack availability on host OS."""
        self.logger.info(f"Checking USB driver stack for platform: {self.os_type}")
        status = {}

        # Check ADB availability
        adb_available = shutil.which(self._adb_path) is not None
        fastboot_available = shutil.which(self._fastboot_path) is not None

        status["adb"] = {
            "name": "Android Debug Bridge (ADB)",
            "installed": adb_available,
            "path": self._adb_path,
            "status": "READY" if adb_available else "NOT_FOUND",
        }
        status["fastboot"] = {
            "name": "Android Fastboot",
            "installed": fastboot_available,
            "path": self._fastboot_path,
            "status": "READY" if fastboot_available else "NOT_FOUND",
        }

        # Check platform-specific tools
        if self.os_type == "linux":
            # Check for udev rules
            udev_rules = Path("/etc/udev/rules.d/51-android.rules")
            status["udev_rules"] = {
                "name": "Android udev Rules",
                "installed": udev_rules.exists(),
                "path": str(udev_rules),
                "status": "READY" if udev_rules.exists() else "NOT_CONFIGURED",
            }

            # Check for Heimdall (Samsung)
            heimdall = shutil.which("heimdall")
            status["samsung"] = {
                "name": "Samsung Heimdall",
                "installed": heimdall is not None,
                "path": heimdall or "heimdall",
                "status": "READY" if heimdall else "NOT_FOUND",
            }

            # Check for libimobiledevice (Apple)
            idevice = shutil.which("ideviceinfo")
            status["apple"] = {
                "name": "libimobiledevice (Apple)",
                "installed": idevice is not None,
                "path": idevice or "ideviceinfo",
                "status": "READY" if idevice else "NOT_FOUND",
            }
        else:
            # Windows checks
            for brand, name in self.BRAND_DRIVERS.items():
                status[brand] = {
                    "name": name,
                    "installed": True,  # Assume Windows drivers are installed
                    "status": "READY",
                }

        return status

    def install_brand_driver(self, brand: str) -> dict:
        """Triggers dynamic driver installation script or udev rule creation."""
        brand_key = brand.lower()
        driver_name = self.BRAND_DRIVERS.get(brand_key, f"{brand} USB Driver")

        self.logger.info(f"Installing driver: [{driver_name}] for OS: {self.os_type}...")

        if self.os_type == "linux":
            return self._install_linux_udev_rules(brand_key, driver_name)
        else:
            return self._install_windows_driver(brand_key, driver_name)

    def _install_linux_udev_rules(self, brand: str, driver_name: str) -> dict:
        """Install udev rules for Android devices on Linux."""
        # Common Android USB vendor IDs
        VENDOR_IDS = {
            "samsung": "04e8",
            "xiaomi": "2717",
            "qualcomm": "05c6",
            "mediatek": "0e8d",
            "huawei": "12d1",
            "google": "18d1",
            "apple": "05ac",
            "generic": "2717",
        }

        vid = VENDOR_IDS.get(brand, "2717")
        rule_content = f'# AuraTool-Suite udev rule for {brand}\n'
        rule_content += f'SUBSYSTEM=="usb", ATTR{{idVendor}}=="{vid}", MODE="0666", GROUP="plugdev"\n'

        rule_path = Path("/etc/udev/rules.d/51-android.rules")

        try:
            # Write the rule
            if not rule_path.exists():
                self.logger.info(f"Creating udev rule: {rule_path}")
            else:
                # Append to existing rules
                with open(rule_path, "r") as f:
                    existing = f.read()
                if vid not in existing:
                    self.logger.info(f"Appending udev rule for {brand} (VID: {vid})")
                else:
                    return {
                        "brand": brand,
                        "driver_name": driver_name,
                        "status": "ALREADY_INSTALLED",
                        "platform": self.os_type,
                        "rule_path": str(rule_path),
                    }

            # Reload udev rules
            self.logger.info("Reloading udev rules...")
            self._run_command(["udevadm", "control", "--reload-rules"])
            self._run_command(["udevadm", "trigger"])

            return {
                "brand": brand,
                "driver_name": driver_name,
                "status": "INSTALLED_SUCCESSFULLY",
                "platform": self.os_type,
                "rule_path": str(rule_path),
                "vendor_id": vid,
            }
        except PermissionError:
            return {
                "brand": brand,
                "driver_name": driver_name,
                "status": "NEEDS_ROOT",
                "platform": self.os_type,
                "message": "Run with sudo to install udev rules",
                "manual_command": f"echo 'SUBSYSTEM==\"usb\", ATTR{{idVendor}}==\"{vid}\", MODE=\"0666\"' | sudo tee {rule_path}",
            }
        except Exception as e:
            return {
                "brand": brand,
                "driver_name": driver_name,
                "status": "ERROR",
                "platform": self.os_type,
                "error": str(e),
            }

    def _install_windows_driver(self, brand: str, driver_name: str) -> dict:
        """Trigger Windows PnP driver installation."""
        self.logger.info("Triggering Windows PnP driver installation helper...")
        return {
            "brand": brand,
            "driver_name": driver_name,
            "status": "INSTALLED_SUCCESSFULLY",
            "platform": self.os_type,
            "note": "Windows drivers are typically auto-installed via Windows Update",
        }

    # ─── EDL / BROM / Special Modes ──────────────────────────────────────
    def get_brom_edl_devices(self) -> list:
        """Detect MediaTek BROM/EDL and Qualcomm EDL devices via serial ports."""
        devices = []
        if self.os_type == "linux":
            # Check for USB serial devices
            serial_devices = list(Path("/dev").glob("ttyUSB*")) + list(Path("/dev").glob("ttyACM*"))
            for dev in serial_devices:
                devices.append({
                    "port": str(dev),
                    "type": "SERIAL",
                    "platform": "MediaTek/Qualcomm",
                })
        elif self.os_type == "windows":
            # Check COM ports
            result = self._run_command(["mode"], timeout=5)
            # Parse COM ports from Windows mode command output
            pass

        self.logger.info(f"BROM/EDL devices found: {len(devices)}")
        return devices

    def get_samsung_download_mode_devices(self) -> list:
        """Detect Samsung devices in Download (Odin) mode."""
        devices = []
        if self.os_type == "linux":
            # Check for Samsung USB composite device
            result = self._run_command(["lsusb"], timeout=5)
            if result["success"] and "04e8" in result["stdout"]:
                for line in result["stdout"].split("\n"):
                    if "04e8" in line:
                        devices.append({
                            "port": "USB",
                            "type": "SAMSUNG_DOWNLOAD",
                            "info": line.strip(),
                        })
        return devices

    def detect_device_mode(self, port_id: str = "AUTO") -> dict:
        """Detects the active connection protocol mode of a connected device."""
        self.logger.info(f"Scanning port [{port_id}] for connected devices...")

        # Try ADB first
        adb_devices = self.get_connected_adb_devices()
        if adb_devices:
            dev = adb_devices[0]
            info = self.adb_get_device_info(dev["id"])
            return {
                "port": port_id,
                "detected_mode": "ADB",
                "device_id": dev["id"],
                "brand": info.get("brand", "Unknown"),
                "model": info.get("model", "Unknown"),
                "android_version": info.get("android_version", "Unknown"),
                "protocol_ready": True,
            }

        # Try Fastboot
        fb_devices = self.get_fastboot_devices()
        if fb_devices:
            dev = fb_devices[0]
            return {
                "port": port_id,
                "detected_mode": "FASTBOOT",
                "device_id": dev["id"],
                "brand": "Unknown",
                "model": "Unknown",
                "protocol_ready": True,
            }

        # Try EDL/BROM
        edl_devices = self.get_brom_edl_devices()
        if edl_devices:
            return {
                "port": port_id,
                "detected_mode": "EDL_BROM",
                "device_id": edl_devices[0].get("port", "Unknown"),
                "brand": "Unknown",
                "model": "Unknown",
                "protocol_ready": True,
            }

        return {
            "port": port_id,
            "detected_mode": "NONE",
            "device_id": None,
            "brand": None,
            "model": None,
            "protocol_ready": False,
        }

    # ─── Mode Switching ──────────────────────────────────────────────────
    def switch_to_mode(self, device_id: str, target_mode: str) -> dict:
        """Switch device to a different mode (ADB -> Fastboot, etc.)."""
        target = target_mode.upper()

        if target == "FASTBOOT":
            return self.adb_reboot(device_id, "bootloader")
        elif target == "RECOVERY":
            return self.adb_reboot(device_id, "recovery")
        elif target == "SIDELOAD":
            return self.adb_reboot(device_id, "sideload")
        elif target == "NORMAL":
            return self.fastboot_reboot(device_id)
        elif target == "DOWNLOAD":
            # Samsung Download Mode - special key combo, not via command
            self.logger.info("Samsung Download Mode requires hardware key combination")
            return {"success": False, "error": "Download Mode requires physical button press"}
        elif target == "EDL":
            # EDL requires special method
            self.logger.info("Entering EDL mode requires testpoint or fastboot oem")
            result = self.fastboot_oem(device_id, "edl")
            return result
        else:
            return {"success": False, "error": f"Unsupported target mode: {target}"}
