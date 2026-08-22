import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging

from modules.localization import LocalizationManager
from modules.flashing_engine import FlashingEngine
from modules.biometrics_fix import BiometricsFix
from modules.smart_devices import SmartDeviceManager
from modules.data_recovery import DataRecoveryModule

class TextHandler(logging.Handler):
    """Custom logging handler to stream logs directly into UI Console."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
        self.text_widget.after(0, append)

class AuraToolUI:
    """Cross-platform GUI implementation using Tkinter for Windows and Linux compatibility."""

    MANUFACTURERS = {
        "Samsung": ["Galaxy S23", "Galaxy S22", "Galaxy A54", "Galaxy Tab S8"],
        "Xiaomi": ["Redmi Note 12", "Xiaomi 13 Pro", "Mi 11 Ultra", "POCO X5"],
        "Huawei": ["P50 Pro", "Mate 40 Pro", "Nova 10", "Y9 Prime"],
        "Qualcomm Generic": ["Snapdragon 8 Gen 2 Generic", "Snapdragon 778G Generic"],
        "MediaTek (MTK) Generic": ["Dimensity 9000 Generic", "Helio G99 Generic"]
    }

    def __init__(self, license_info: dict, driver_status: dict):
        self.root = tk.Tk()
        self.root.title("AuraTool-Suite - Advanced Maintenance Framework")
        self.root.geometry("900x650")

        self.license_info = license_info
        self.driver_status = driver_status
        self.loc_mgr = LocalizationManager("en")
        self.flashing_engine = FlashingEngine()
        self.biometrics_fix = BiometricsFix()
        self.smart_dev_mgr = SmartDeviceManager()
        self.data_recovery = DataRecoveryModule()

        self._build_ui()
        self._setup_logging()

    def _setup_logging(self):
        handler = TextHandler(self.console)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S")
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)

    def _build_ui(self):
        # Header / Status Bar
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill=tk.X)

        self.title_lbl = ttk.Label(header, text="AuraTool-Suite", font=("Helvetica", 16, "bold"))
        self.title_lbl.pack(side=tk.LEFT)

        lic_text = f"License: {self.license_info['tier']} ({self.license_info['days_remaining']} days left)"
        self.lic_lbl = ttk.Label(header, text=lic_text, font=("Helvetica", 10), foreground="green" if self.license_info['is_active'] else "red")
        self.lic_lbl.pack(side=tk.RIGHT)

        # Main Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)

        # Tab 1: Manufacturer & Model Operations
        vendor_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(vendor_tab, text="Vendor Operations")
        self._build_vendor_tab(vendor_tab)

        # Tab 2: Biometrics & Diagnostics
        bio_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(bio_tab, text="Biometrics & Diagnostics")
        self._build_biometrics_tab(bio_tab)

        # Tab 3: Data Recovery
        recovery_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(recovery_tab, text="Data Recovery")
        self._build_recovery_tab(recovery_tab)

        # Tab 4: Smart Devices & Peripherals
        smart_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(smart_tab, text="Smart Devices")
        self._build_smart_tab(smart_tab)

        # Tab 5: Settings & Language
        settings_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(settings_tab, text="Settings")
        self._build_settings_tab(settings_tab)

        # Console Frame
        console_frame = ttk.LabelFrame(self.root, text="System Output Console", padding=5)
        console_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)

        self.console = scrolledtext.ScrolledText(console_frame, height=8, state='disabled', bg="black", fg="light green", font=("Consolas", 9))
        self.console.pack(fill=tk.BOTH, expand=True)

    def _build_vendor_tab(self, parent):
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X, pady=5)

        ttk.Label(top_frame, text="Manufacturer:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.vendor_cb = ttk.Combobox(top_frame, values=list(self.MANUFACTURERS.keys()), state="readonly")
        self.vendor_cb.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.vendor_cb.current(0)
        self.vendor_cb.bind("<<ComboboxSelected>>", self._on_vendor_change)

        ttk.Label(top_frame, text="Device Model:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.model_cb = ttk.Combobox(top_frame, values=self.MANUFACTURERS["Samsung"], state="readonly")
        self.model_cb.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.model_cb.current(0)

        # Action Buttons
        btn_frame = ttk.LabelFrame(parent, text="Available Maintenance Actions", padding=10)
        btn_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        ttk.Button(btn_frame, text="Flash Firmware Image", command=self._action_flash).grid(row=0, column=0, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(btn_frame, text="Read Device Partition Table", command=self._action_read_ptable).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(btn_frame, text="Verify System Integrity", command=self._action_verify).grid(row=1, column=0, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(btn_frame, text="Reboot to Fastboot/Bootloader", command=self._action_reboot_fastboot).grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)

    def _build_biometrics_tab(self, parent):
        ttk.Label(parent, text="Biometric Hardware Sensor Diagnostics & Calibration", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        ttk.Button(parent, text="Run Hardware Diagnostics", command=self._action_bio_diag).pack(anchor=tk.W, pady=5)
        ttk.Button(parent, text="Recalibrate Optical Fingerprint Sensor", command=self._action_bio_calib).pack(anchor=tk.W, pady=5)

    def _build_recovery_tab(self, parent):
        ttk.Label(parent, text="Deep Scan & File Recovery System", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        ttk.Label(parent, text="Scan for lost media files, documents, contacts, SMS messages, and call logs.").pack(anchor=tk.W, pady=2)
        
        btn_frame = ttk.Frame(parent, padding=5)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="Start Deep Scan", command=self._action_deep_scan).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Export Contacts & Messages", command=self._action_export_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Extract Recovered Media", command=self._action_extract_media).pack(side=tk.LEFT, padx=5)

    def _build_smart_tab(self, parent):
        ttk.Label(parent, text="Connected Non-Phone Smart Devices (Tablets, Wearables)", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        ttk.Button(parent, text="Scan for Smart Devices", command=self._action_scan_smart).pack(anchor=tk.W, pady=5)

    def _build_settings_tab(self, parent):
        ttk.Label(parent, text="Select Language / اختر اللغة:", font=("Helvetica", 10)).pack(anchor=tk.W, pady=5)
        self.lang_cb = ttk.Combobox(parent, values=list(LocalizationManager.SUPPORTED_LANGUAGES.values()), state="readonly")
        self.lang_cb.pack(anchor=tk.W, pady=5)
        self.lang_cb.current(0)

        ttk.Button(parent, text="Apply Language", command=self._action_change_lang).pack(anchor=tk.W, pady=5)

        driver_str = "\n".join([f"• {k.upper()}: {'Available' if v else 'Not Configured'}" for k, v in self.driver_status.items()])
        ttk.Label(parent, text=f"\nDriver Subsystem Status:\n{driver_str}", font=("Helvetica", 10)).pack(anchor=tk.W, pady=10)

    def _on_vendor_change(self, event):
        vendor = self.vendor_cb.get()
        models = self.MANUFACTURERS.get(vendor, [])
        self.model_cb.config(values=models)
        if models:
            self.model_cb.current(0)

    def _action_flash(self):
        model = self.model_cb.get()
        logging.info(f"Starting firmware flash process for model: {model}")
        self.flashing_engine.flash_firmware(model, f"/firmware/{model}/update.tar", mode="FASTBOOT")

    def _action_read_ptable(self):
        logging.info(f"Reading partition table for device model: {self.model_cb.get()}")

    def _action_verify(self):
        logging.info(f"Verifying system software integrity for: {self.model_cb.get()}")

    def _action_reboot_fastboot(self):
        logging.info(f"Sending reboot-bootloader signal to connected device ({self.model_cb.get()}).")

    def _action_bio_diag(self):
        results = self.biometrics_fix.run_diagnostics(self.model_cb.get())
        logging.info(f"Biometric Diagnostics Result: {results}")

    def _action_bio_calib(self):
        self.biometrics_fix.recalibrate_sensors(self.model_cb.get())

    def _action_deep_scan(self):
        model = self.model_cb.get()
        res = self.data_recovery.perform_deep_scan(model)
        messagebox.showinfo("Recovery Scan Complete", f"Scan finished for {model}.\nPhotos: {res['photos_found']}\nContacts: {res['contacts_found']}\nSMS: {res['sms_messages_found']}")

    def _action_export_data(self):
        model = self.model_cb.get()
        records = self.data_recovery.extract_contacts_and_logs(model)
        logging.info(f"Extracted {len(records)} structure records for device {model}.")

    def _action_extract_media(self):
        model = self.model_cb.get()
        self.data_recovery.extract_media(model, f"/backups/{model}/recovery_output/")
        logging.info(f"Media extraction completed for device {model}.")

    def _action_scan_smart(self):
        devices = self.smart_dev_mgr.detect_connected_devices()
        for dev in devices:
            logging.info(f"Detected Peripheral: {dev['vendor']} {dev['model']} [{dev['type']}] -> Status: {dev['status']}")

    def _action_change_lang(self):
        selected_name = self.lang_cb.get()
        for code, name in LocalizationManager.SUPPORTED_LANGUAGES.items():
            if name == selected_name:
                self.loc_mgr.set_language(code)
                self.title_lbl.config(text=self.loc_mgr.get_string("title"))
                logging.info(f"Language updated to: {selected_name}")
                break

    def run(self):
        self.root.mainloop()
