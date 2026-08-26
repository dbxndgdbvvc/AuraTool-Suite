"""
AuraTool-Suite — Aura-AI Assistant Module
==========================================
Advanced AI diagnostic assistant providing:
  - Voice & text command processing for device maintenance
  - System log analysis with instant error detection
  - Integrated licensing engine (15-day trial, 6-month, annual VIP)
  - Full device ecosystem support (phones, tablets, wearables, AR/VR)
"""

import logging
import re
import time
from datetime import datetime, date


class AuraAIAssistant:
    """
    Aura-AI Diagnostic & Smart Assistant Engine.
    Analyses system logs, processes voice/text commands,
    and interfaces with the licensing subsystem for activation checks.
    """

    # ------------------------------------------------------------------ #
    #  Signature patterns for common log anomalies
    # ------------------------------------------------------------------ #
    LOG_SIGNATURES = {
        "kernel_panic":    r"kernel\s+panic",
        "bootloop":        r"(boot\s*loop|repeated\s+reboot)",
        "frp_locked":      r"(frp\s+lock|factory\s+reset\s+protection)",
        "ufs_error":       r"(ufs\s+error|emmc\s+error|bad\s+block)",
        "memory_corrupt":  r"(memory\s+corrupt|ram\s+error|dm-verity)",
        "wifi_failure":    r"(wifi\s+(fail|error)|wlan\s+down)",
        "bluetooth_issue": r"(bluetooth\s+(fail|error|off))",
        "touchscreen":     r"(touch\s*(screen)?\s+(fail|error|unresponsive)|digitizer\s+error)",
        "battery_drain":   r"(battery\s+drain|thermal\s+throttl)",
        "camera_fail":     r"(camera\s+(fail|error)|sensor\s+not\s+detected)",
        "network_lost":    r"(no\s+service|sim\s+(not|missing)|baseband\s+error)",
        "storage_full":    r"(storage\s+full|no\s+space\s+left|quota\s+exceeded)",
        "app_crash":       r"(fatal\s+exception|anr\s+in|force\s+close)",
        "virus_detected":  r"(malware|virus|trojan|rootkit|suspicious\s+package)",
        "bootloader":      r"(bootloader\s+locked|dm-verity\s+corrupt)",
    }

    # ------------------------------------------------------------------ #
    #  Command vocabulary (maps natural-language triggers to actions)
    # ------------------------------------------------------------------ #
    COMMAND_MAP = {
        # --- More specific keywords first to avoid false matches ---
        "restore":        "restore_data",
        "activate":       "activate_license",
        "flash":          "flash_firmware",
        "update":         "flash_firmware",
        "frp":            "bypass_frp",
        "bypass":         "bypass_frp",
        "account":        "bypass_frp",
        "lock":           "bypass_frp",
        "diagnose":       "analyze_logs",
        "log":            "analyze_logs",
        "error":          "analyze_logs",
        "health":         "storage_health",
        "storage":        "storage_health",
        "backup":         "backup_data",
        "recover":        "recover_data",
        "biometric":      "fix_biometrics",
        "fingerprint":    "fix_biometrics",
        "face":           "fix_biometrics",
        "reboot":         "reboot_device",
        "restart":        "reboot_device",
        "repair":         "ultimate_repair",
        "fix":            "ultimate_repair",
        "license":        "check_license",
        "scan":           "scan_devices",
        "detect":         "scan_devices",
        "localize":       "localize_device",
        "language":       "localize_device",
        "arabic":         "localize_device",
        "عربي":           "localize_device",
    }

    # ------------------------------------------------------------------ #
    #  Supported device ecosystem (2000 – 2030)
    # ------------------------------------------------------------------ #
    DEVICE_ECOSYSTEM = {
        "smartphones": [
            "Samsung Galaxy S-series", "Samsung Galaxy A-series",
            "Apple iPhone", "Xiaomi Mi/Redmi/POCO",
            "Huawei P/Mate/Nova", "OnePlus", "Google Pixel",
            "Oppo Find/Reno", "Vivo X/S", "Nokia",
            "Motorola/Lenovo", "Sony Xperia",
            "Realme", "Infinix/Tecno", "ZTE/Nubia",
            "HTC", "LG (legacy)", "Blackberry (legacy)",
        ],
        "tablets": [
            "Samsung Galaxy Tab", "Apple iPad / iPad Pro / iPad Air",
            "Xiaomi Pad", "Huawei MatePad", "Lenovo Tab",
            "Microsoft Surface", "Amazon Fire Tablet",
            "Google Pixel Tablet",
        ],
        "smartwatches": [
            "Apple Watch Series / Ultra",
            "Samsung Galaxy Watch",
            "WearOS Generic", "Xiaomi Watch",
            "Huawei Watch GT", "Amazfit",
        ],
        "smart_glasses_ar_vr": [
            "Apple Vision Pro", "Meta Quest 3 / Quest Pro",
            "Ray-Ban Meta Smart Glasses",
            "XREAL Air", "Rokid AR",
            "Google Glass (legacy)", "Microsoft HoloLens",
            "Generic AR/VR Headset",
        ],
    }

    # ------------------------------------------------------------------ #
    #  Health-score deduction table
    # ------------------------------------------------------------------ #
    SEVERITY_SCORE = {
        "kernel_panic":   25,
        "bootloop":       20,
        "memory_corrupt": 20,
        "ufs_error":      15,
        "virus_detected": 15,
        "frp_locked":     10,
        "bootloader":     10,
        "network_lost":   10,
        "app_crash":       5,
        "wifi_failure":    5,
        "bluetooth_issue": 3,
        "touchscreen":     5,
        "battery_drain":   5,
        "camera_fail":     5,
        "storage_full":    5,
    }

    RECOMMENDED_ACTIONS = {
        "kernel_panic":   "Flash stock firmware via fastboot/EDL and verify bootloader integrity.",
        "bootloop":       "Enter recovery mode; wipe cache + factory reset, or re-flash system partition.",
        "frp_locked":     "Use FRP bypass module to clear cloud-account lock after factory reset.",
        "ufs_error":      "Run storage health scan; replace eMMC/UFS if bad blocks exceed threshold.",
        "memory_corrupt":  "Perform deep memory test; re-flash partition table and verify dm-verity.",
        "wifi_failure":    "Reset network stack; restore EFS/NVRAM partition backup.",
        "bluetooth_issue": "Toggle BT stack; clear Bluetooth cache and re-pair devices.",
        "touchscreen":     "Recalibrate digitizer via biometric calibration module.",
        "battery_drain":   "Run power audit; check for rogue background services.",
        "camera_fail":     "Check camera flex cable connection; recalibrate camera sensor.",
        "network_lost":    "Verify baseband version; restore EFS backup; check SIM tray.",
        "storage_full":    "Clear app cache; move media to external storage.",
        "app_crash":       "Clear app data; reinstall affected package via package manager.",
        "virus_detected":  "Boot into safe mode; run full system antivirus scan; factory reset if needed.",
        "bootloader":      "Unlock bootloader (warning: voids warranty); re-flash verified boot image.",
    }

    # ------------------------------------------------------------------ #

    def __init__(self):
        self.logger = logging.getLogger("AuraTool.AuraAI")
        self.last_analysis = None
        self.session_log = []

    # ================================================================== #
    #  PUBLIC API
    # ================================================================== #

    def process_voice_or_text_command(self, command_text: str) -> dict:
        """
        Parse a natural-language (voice-transcribed or typed) command and
        route it to the appropriate internal action.
        """
        self.logger.info(f"AI received command: {command_text}")
        normalised = command_text.lower().strip()

        matched_action = None
        for keyword, action in self.COMMAND_MAP.items():
            if keyword in normalised:
                matched_action = action
                break

        if matched_action is None:
            response = {
                "status": "UNKNOWN_COMMAND",
                "message": (
                    "I could not map that command to an action. "
                    "Try phrases like: 'flash firmware', 'bypass FRP', "
                    "'analyze logs', 'storage health', 'backup data', "
                    "'fix biometrics', 'check license', or 'scan devices'."
                ),
                "confidence": 0.0,
            }
        else:
            response = self._execute_action(matched_action, normalised)

        self.session_log.append({
            "timestamp": datetime.now().isoformat(),
            "command": command_text,
            "result": response,
        })
        return response

    def analyze_system_logs(self, log_text: str) -> dict:
        """
        Scan raw log text against known error signatures and return a
        health report with score, detected issues, and recommendations.
        """
        self.logger.info("Starting AI log analysis...")
        issues = []
        total_deduction = 0

        for issue_name, pattern in self.LOG_SIGNATURES.items():
            if re.search(pattern, log_text, re.IGNORECASE):
                issues.append(issue_name)
                total_deduction += self.SEVERITY_SCORE.get(issue_name, 3)

        health_score = max(0, 100 - total_deduction)

        recommendations = []
        for issue in issues:
            rec = self.RECOMMENDED_ACTIONS.get(issue)
            if rec:
                recommendations.append(rec)

        result = {
            "health_score": health_score,
            "issues_detected": issues,
            "issue_count": len(issues),
            "recommended_action": recommendations[0] if recommendations else "No critical issues found.",
            "all_recommendations": recommendations,
            "analyzed_at": datetime.now().isoformat(),
        }
        self.last_analysis = result
        self.logger.info(
            f"Log analysis complete — score: {health_score}%, "
            f"issues: {len(issues)}"
        )
        return result

    def verify_extended_license_2030(self) -> dict:
        """
        Verify licensing status using the HWID-based license manager.
        """
        from core.license_manager import LicenseManager

        mgr = LicenseManager()
        status = mgr.check_license()

        result = {
            "tier": status["tier_label"],
            "is_active": status["is_active"],
            "days_remaining": status["days_remaining"],
            "activation_date": status["activation_date"],
            "expiration_date": status["expiration_date"],
            "hwid": status["hwid"],
            "supported_until_year": 2030 if status["tier"] == "rental_1y" else None,
            "ecosystem_supported": True,
        }
        self.logger.info(f"License verified: {result['tier']} — active: {result['is_active']}")
        return result

    def activate_license_key(self, key: str) -> dict:
        """Activate a license key via the HWID-based license manager."""
        from core.license_manager import LicenseManager

        mgr = LicenseManager()
        result = mgr.activate(key)
        return {
            "activated": result["success"],
            "message": result["message"],
            "status": result["status"] if result["success"] else None,
        }

    def get_supported_devices(self) -> dict:
        """Return the full device ecosystem map."""
        return self.DEVICE_ECOSYSTEM

    def diagnose_device(self, device_id: str, log_text: str = "") -> dict:
        """
        Combined device diagnosis: log analysis + device-type awareness
        + actionable recommendation.
        """
        diag = self.analyze_system_logs(log_text) if log_text else {
            "health_score": 100,
            "issues_detected": [],
            "recommended_action": "No log data provided — connect device and capture logs first.",
        }
        diag["device_id"] = device_id
        diag["device_class"] = self._classify_device(device_id)
        return diag

    # ================================================================== #
    #  PRIVATE HELPERS
    # ================================================================== #

    def _execute_action(self, action: str, command_text: str) -> dict:
        """Dispatch the matched action and return a result dict."""
        dispatch = {
            "flash_firmware":    self._act_flash,
            "bypass_frp":        self._act_bypass_frp,
            "analyze_logs":      self._act_analyze_logs,
            "storage_health":    self._act_storage_health,
            "backup_data":       self._act_backup,
            "restore_data":      self._act_restore,
            "recover_data":      self._act_recover,
            "fix_biometrics":    self._act_biometrics,
            "reboot_device":     self._act_reboot,
            "ultimate_repair":   self._act_repair,
            "check_license":     self._act_check_license,
            "activate_license":  self._act_activate,
            "scan_devices":      self._act_scan,
            "localize_device":   self._act_localize,
        }
        handler = dispatch.get(action, self._act_unknown)
        return handler(command_text)

    # --- Individual action handlers ----------------------------------- #

    def _act_flash(self, cmd: str) -> dict:
        self.logger.info("AI action: flash_firmware triggered.")
        return {
            "status": "ACTION_QUEUED",
            "action": "flash_firmware",
            "message": "Firmware flash process queued. Select target device and firmware image in the Vendor tab.",
            "confidence": 0.95,
        }

    def _act_bypass_frp(self, cmd: str) -> dict:
        self.logger.info("AI action: bypass_frp triggered.")
        return {
            "status": "ACTION_QUEUED",
            "action": "bypass_frp",
            "message": "FRP / Cloud-lock bypass queued. Connect device via ADB/Fastboot/EDL and select the device model.",
            "confidence": 0.92,
        }

    def _act_analyze_logs(self, cmd: str) -> dict:
        """Analyze logs from the command context or request log input."""
        self.logger.info("AI action: analyze_logs triggered.")
        # Check if log text is embedded in the command
        log_patterns = [
            r"analyze\s+(?:this\s+)?log[s]?:?\s*(.+)",
            r"scan\s+(?:this\s+)?log[s]?:?\s*(.+)",
            r"check\s+(?:this\s+)?log[s]?:?\s*(.+)",
        ]
        for pattern in log_patterns:
            match = re.search(pattern, cmd, re.IGNORECASE)
            if match:
                log_text = match.group(1).strip()
                analysis = self.analyze_system_logs(log_text)
                return {
                    "status": "ANALYSIS_COMPLETE",
                    "action": "analyze_logs",
                    "message": (
                        f"Log analysis complete. Health score: {analysis['health_score']}%. "
                        f"Issues found: {analysis['issue_count']}. "
                        f"{analysis['recommended_action']}"
                    ),
                    "analysis": analysis,
                    "confidence": 0.95,
                }
        # No log text provided in command
        return {
            "status": "NEEDS_LOG",
            "action": "analyze_logs",
            "message": "Please provide a system log file or paste log text for analysis.",
            "confidence": 1.0,
        }

    def _act_storage_health(self, cmd: str) -> dict:
        self.logger.info("AI action: storage_health triggered.")
        return {
            "status": "ACTION_QUEUED",
            "action": "storage_health",
            "message": "Storage health scan queued. Will check UFS/eMMC bad blocks and read/write speeds.",
            "confidence": 0.90,
        }

    def _act_backup(self, cmd: str) -> dict:
        self.logger.info("AI action: backup_data triggered.")
        return {
            "status": "ACTION_QUEUED",
            "action": "backup_data",
            "message": "Data backup queued. EFS/NVRAM and user data will be secured.",
            "confidence": 0.93,
        }

    def _act_restore(self, cmd: str) -> dict:
        self.logger.info("AI action: restore_data triggered.")
        return {
            "status": "ACTION_QUEUED",
            "action": "restore_data",
            "message": "Data restore queued. Select backup source before proceeding.",
            "confidence": 0.91,
        }

    def _act_recover(self, cmd: str) -> dict:
        self.logger.info("AI action: recover_data triggered.")
        return {
            "status": "ACTION_QUEUED",
            "action": "recover_data",
            "message": "Deep data recovery scan queued. Photos, contacts, SMS, and call logs will be scanned.",
            "confidence": 0.88,
        }

    def _act_biometrics(self, cmd: str) -> dict:
        self.logger.info("AI action: fix_biometrics triggered.")
        return {
            "status": "ACTION_QUEUED",
            "action": "fix_biometrics",
            "message": "Biometric sensor diagnostics and recalibration queued.",
            "confidence": 0.87,
        }

    def _act_reboot(self, cmd: str) -> dict:
        self.logger.info("AI action: reboot_device triggered.")
        return {
            "status": "ACTION_QUEUED",
            "action": "reboot_device",
            "message": "Device reboot command queued. Choose target mode (Normal, Fastboot, EDL, Recovery).",
            "confidence": 0.94,
        }

    def _act_repair(self, cmd: str) -> dict:
        self.logger.info("AI action: ultimate_repair triggered.")
        return {
            "status": "ACTION_QUEUED",
            "action": "ultimate_repair",
            "message": "Ultimate repair suite queued. Will scan for major/minor issues and apply fixes.",
            "confidence": 0.85,
        }

    def _act_check_license(self, cmd: str) -> dict:
        lic = self.verify_extended_license_2030()
        return {
            "status": "INFO",
            "action": "check_license",
            "message": (
                f"License: {lic['tier']} | Active: {lic['is_active']} | "
                f"Days remaining: {lic['days_remaining']}"
            ),
            "confidence": 1.0,
        }

    def _act_activate(self, cmd: str) -> dict:
        """Activate a license key from the command context or request key input."""
        self.logger.info("AI action: activate_license triggered.")
        # Check if a license key is embedded in the command
        key_pattern = r"(AT\w{2,4}-[A-Z0-9]{4,12})"
        match = re.search(key_pattern, cmd, re.IGNORECASE)
        if match:
            key = match.group(1).upper()
            result = self.activate_license_key(key)
            if result["activated"]:
                return {
                    "status": "ACTIVATED",
                    "action": "activate_license",
                    "message": f"License activated successfully: {result['message']}",
                    "license_info": result["status"],
                    "confidence": 1.0,
                }
            else:
                return {
                    "status": "ACTIVATION_FAILED",
                    "action": "activate_license",
                    "message": f"Activation failed: {result['message']}",
                    "confidence": 1.0,
                }
        # No key provided in command
        return {
            "status": "NEEDS_KEY",
            "action": "activate_license",
            "message": "Please enter a valid license key to activate (e.g., AT6M-A1B2C3D4E5F6).",
            "confidence": 1.0,
        }

    def _act_scan(self, cmd: str) -> dict:
        self.logger.info("AI action: scan_devices triggered.")
        all_devices = []
        for category, models in self.DEVICE_ECOSYSTEM.items():
            for model in models:
                all_devices.append({"category": category, "model": model})
        return {
            "status": "SCAN_COMPLETE",
            "action": "scan_devices",
            "message": f"Ecosystem scan complete. {len(all_devices)} device families supported.",
            "device_families": len(all_devices),
            "confidence": 0.96,
        }

    def _act_localize(self, cmd: str) -> dict:
        self.logger.info("AI action: localize_device triggered.")
        detected_lang = "ar" if ("عربي" in cmd or "arabic" in cmd) else "en"
        return {
            "status": "ACTION_QUEUED",
            "action": "localize_device",
            "message": f"Localization queued. Target language detected: {detected_lang}.",
            "target_language": detected_lang,
            "confidence": 0.89,
        }

    def _act_unknown(self, cmd: str) -> dict:
        return {
            "status": "UNKNOWN",
            "message": "Command not recognised by the AI engine.",
            "confidence": 0.0,
        }

    # --- Classification helper ---------------------------------------- #

    def _classify_device(self, device_id: str) -> str:
        """Classify a device ID string into an ecosystem category."""
        lower = device_id.lower()
        if any(kw in lower for kw in ("watch", "band", "wear", "watchos")):
            return "smartwatch"
        if any(kw in lower for kw in ("tab", "ipad", "pad", "surface", "tablet")):
            return "tablet"
        if any(kw in lower for kw in ("glass", "quest", "hololens", "vision", "ar ", "vr ", "headset", "xreal", "rokid", "pico ", "vive ", "spectacles")):
            return "smart_glasses_ar_vr"
        return "smartphone"
