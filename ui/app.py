import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging

from modules.localization import LocalizationManager
from modules.flashing_engine import FlashingEngine
from modules.biometrics_fix import BiometricsFix
from modules.smart_devices import SmartDeviceManager
from modules.data_recovery import DataRecoveryModule
from modules.account_repair import AccountRepairModule
from modules.aura_ai_assistant import AuraAIAssistant
from modules.ultimate_repair import UltimateRepairModule
from auratool_factory import (
    FactoryManager, DeviceCategory, RepairStatus,
    PartType, COMMON_PARTS,
)

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
    """Cross-platform GUI implementation using Tkinter for Windows and Linux Ubuntu compatibility."""

    MANUFACTURERS = {
        "Samsung": ["Galaxy S23", "Galaxy S22", "Galaxy A54", "Galaxy Tab S8", "Galaxy Watch 6"],
        "Apple": ["iPhone 15 Pro", "iPhone 14", "iPad Pro 12.9", "Apple Watch Series 9"],
        "Xiaomi": ["Redmi Note 12", "Xiaomi 13 Pro", "Mi 11 Ultra", "POCO X5"],
        "Huawei": ["P50 Pro", "Mate 40 Pro", "Nova 10", "Y9 Prime"],
        "Smart Wearables & AR/VR": ["Apple Vision Pro", "Meta Quest 3", "Ray-Ban Meta Smart Glasses", "WearOS Generic"],
        "Qualcomm Generic": ["Snapdragon 8 Gen 2 Generic", "Snapdragon 778G Generic"],
        "MediaTek (MTK) Generic": ["Dimensity 9000 Generic", "Helio G99 Generic"]
    }

    def __init__(self, license_info: dict, driver_status: dict, factory_mgr: FactoryManager | None = None):
        self.root = tk.Tk()
        self.root.title("AuraTool-Suite - Advanced Ecosystem Maintenance Framework (2000-2030)")
        self.root.geometry("1100x750")

        self.license_info = license_info
        self.driver_status = driver_status
        self.loc_mgr = LocalizationManager("en")
        self.flashing_engine = FlashingEngine()
        self.biometrics_fix = BiometricsFix()
        self.smart_dev_mgr = SmartDeviceManager()
        self.data_recovery = DataRecoveryModule()
        self.account_repair = AccountRepairModule()
        self.ai_assistant = AuraAIAssistant()
        self.ultimate_repair = UltimateRepairModule()
        self.factory_mgr = factory_mgr or FactoryManager()

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

        self.title_lbl = ttk.Label(header, text="AuraTool-Suite 2030", font=("Helvetica", 16, "bold"))
        self.title_lbl.pack(side=tk.LEFT)

        lic_text = f"License: {self.license_info['tier']} ({self.license_info['days_remaining']} days left)"
        self.lic_lbl = ttk.Label(header, text=lic_text, font=("Helvetica", 10), foreground="green" if self.license_info['is_active'] else "red")
        self.lic_lbl.pack(side=tk.RIGHT)

        # Main Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)

        # Tab 1: AI Assistant
        ai_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(ai_tab, text="Aura-AI Diagnostic")
        self._build_ai_tab(ai_tab)

        # Tab 2: Vendor Operations
        vendor_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(vendor_tab, text="Vendor Operations")
        self._build_vendor_tab(vendor_tab)

        # Tab 3: Ultimate System Repair
        ult_repair_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(ult_repair_tab, text="Ultimate Repair")
        self._build_ultimate_repair_tab(ult_repair_tab)

        # Tab 4: Biometrics & Diagnostics
        bio_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(bio_tab, text="Biometrics & Diagnostics")
        self._build_biometrics_tab(bio_tab)

        # Tab 5: Data Recovery
        recovery_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(recovery_tab, text="Data Recovery")
        self._build_recovery_tab(recovery_tab)

        # Tab 6: Network & Security Maintenance
        repair_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(repair_tab, text="Network & Repair")
        self._build_repair_tab(repair_tab)

        # Tab 7: Smart Devices & Peripherals
        smart_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(smart_tab, text="Smart Devices & Ecosystem")
        self._build_smart_tab(smart_tab)

        # Tab 8: Workshop & Factory
        workshop_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(workshop_tab, text="Workshop Factory")
        self._build_workshop_tab(workshop_tab)

        # Tab 9: Settings & Language
        settings_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(settings_tab, text="Settings")
        self._build_settings_tab(settings_tab)

        # Console Frame
        console_frame = ttk.LabelFrame(self.root, text="System Output Console", padding=5)
        console_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)

        self.console = scrolledtext.ScrolledText(console_frame, height=8, state='disabled', bg="black", fg="light green", font=("Consolas", 9))
        self.console.pack(fill=tk.BOTH, expand=True)

    def _build_ai_tab(self, parent):
        ttk.Label(parent, text="Aura-AI Assistant & Log Diagnostic Engine", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        
        cmd_frame = ttk.Frame(parent, padding=5)
        cmd_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(cmd_frame, text="Enter Voice/Text Command:").pack(side=tk.LEFT, padx=5)
        self.ai_cmd_entry = ttk.Entry(cmd_frame, width=45)
        self.ai_cmd_entry.pack(side=tk.LEFT, padx=5)
        self.ai_cmd_entry.insert(0, "Analyze device log and bypass FRP")
        
        ttk.Button(cmd_frame, text="Run AI Command", command=self._action_run_ai_command).pack(side=tk.LEFT, padx=5)

        ttk.Button(parent, text="Analyze System Logs (Instant AI Diagnosis)", command=self._action_analyze_logs).pack(anchor=tk.W, pady=5)
        ttk.Button(parent, text="Check Ecosystem & License 2030 Status", command=self._action_check_ai_license).pack(anchor=tk.W, pady=5)

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
        ttk.Button(btn_frame, text="Read Partition Table", command=self._action_read_ptable).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(btn_frame, text="Check Storage Health (UFS/eMMC)", command=self._action_storage_health).grid(row=1, column=0, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(btn_frame, text="Reboot Fastboot / BROM / EDL", command=self._action_reboot_fastboot).grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)

    def _build_ultimate_repair_tab(self, parent):
        ttk.Label(parent, text="Ultimate System & Account Repair Suite", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        
        btn_frame = ttk.Frame(parent, padding=5)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Fix Bootloop & Memory Errors", command=self._action_fix_major).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Button(btn_frame, text="Fix App Crashes & Network Stack", command=self._action_fix_minor).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Button(btn_frame, text="Repair Cloud & Account Sync Loops", command=self._action_fix_cloud_sync).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

    def _build_biometrics_tab(self, parent):
        ttk.Label(parent, text="Biometric Hardware Sensor Diagnostics & Calibration", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        ttk.Button(parent, text="Run Hardware Diagnostics", command=self._action_bio_diag).pack(anchor=tk.W, pady=5)
        ttk.Button(parent, text="Recalibrate Optical Fingerprint & Face Sensors", command=self._action_bio_calib).pack(anchor=tk.W, pady=5)

    def _build_recovery_tab(self, parent):
        ttk.Label(parent, text="Deep Scan & Data Recovery System", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        ttk.Label(parent, text="Scan lost media, contacts, SMS messages, and system logs across mobile, tablet & wearable storage.").pack(anchor=tk.W, pady=2)
        
        btn_frame = ttk.Frame(parent, padding=5)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="Start Deep Scan", command=self._action_deep_scan).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Export Contacts & Messages", command=self._action_export_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Extract Recovered Media", command=self._action_extract_media).pack(side=tk.LEFT, padx=5)

    def _build_repair_tab(self, parent):
        ttk.Label(parent, text="Network Partition (EFS/NVRAM) & Security Maintenance", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        
        btn_frame = ttk.Frame(parent, padding=5)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Run Account & FRP Diagnostics", command=self._action_run_acc_diag).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Button(btn_frame, text="Bypass FRP & Cloud Lock", command=self._action_bypass_frp).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Button(btn_frame, text="Backup EFS / NVRAM Partitions", command=self._action_backup_efs).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Button(btn_frame, text="Restore EFS / NVRAM Partitions", command=self._action_restore_efs).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

    def _build_smart_tab(self, parent):
        ttk.Label(parent, text="Connected Ecosystem Smart Devices (Tablets, iPads, Wearables, AR/VR)", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        ttk.Button(parent, text="Scan Ecosystem Devices (2000-2030)", command=self._action_scan_smart).pack(anchor=tk.W, pady=5)

    def _build_workshop_tab(self, parent):
        """Build the Workshop & Factory Management tab."""
        # ---- Sub-notebook for sub-sections ----
        sub = ttk.Notebook(parent)
        sub.pack(expand=True, fill=tk.BOTH)

        # --- Sub-tab: Clients ---
        clients_frame = ttk.Frame(sub, padding=8)
        sub.add(clients_frame, text="Clients")
        self._build_workshop_clients(clients_frame)

        # --- Sub-tab: Tickets ---
        tickets_frame = ttk.Frame(sub, padding=8)
        sub.add(tickets_frame, text="Repair Tickets")
        self._build_workshop_tickets(tickets_frame)

        # --- Sub-tab: Inventory ---
        inv_frame = ttk.Frame(sub, padding=8)
        sub.add(inv_frame, text="Spare Parts Inventory")
        self._build_workshop_inventory(inv_frame)

        # --- Sub-tab: Diagnostics ---
        diag_frame = ttk.Frame(sub, padding=8)
        sub.add(diag_frame, text="Diagnostics")
        self._build_workshop_diagnostics(diag_frame)

        # --- Sub-tab: Dashboard ---
        dash_frame = ttk.Frame(sub, padding=8)
        sub.add(dash_frame, text="Dashboard")
        self._build_workshop_dashboard(dash_frame)

    # -- Workshop: Clients Sub-tab ---------------------------------------
    def _build_workshop_clients(self, parent):
        ttk.Label(parent, text="Client Management", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))

        form = ttk.Frame(parent)
        form.pack(fill=tk.X, pady=5)
        ttk.Label(form, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=4)
        self.fw_client_name = ttk.Entry(form, width=25)
        self.fw_client_name.grid(row=0, column=1, padx=4)
        ttk.Label(form, text="Phone:").grid(row=0, column=2, sticky=tk.W, padx=4)
        self.fw_client_phone = ttk.Entry(form, width=18)
        self.fw_client_phone.grid(row=0, column=3, padx=4)
        ttk.Label(form, text="Email:").grid(row=1, column=0, sticky=tk.W, padx=4)
        self.fw_client_email = ttk.Entry(form, width=25)
        self.fw_client_email.grid(row=1, column=1, padx=4)
        ttk.Label(form, text="Address:").grid(row=1, column=2, sticky=tk.W, padx=4)
        self.fw_client_addr = ttk.Entry(form, width=18)
        self.fw_client_addr.grid(row=1, column=3, padx=4)

        btn_row = ttk.Frame(parent)
        btn_row.pack(fill=tk.X, pady=5)
        ttk.Button(btn_row, text="Register Client", command=self._fw_add_client).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Refresh List", command=self._fw_refresh_clients).pack(side=tk.LEFT, padx=4)

        ttk.Label(parent, text="Search:").pack(anchor=tk.W, pady=(5, 0))
        search_row = ttk.Frame(parent)
        search_row.pack(fill=tk.X, pady=2)
        self.fw_client_search = ttk.Entry(search_row, width=30)
        self.fw_client_search.pack(side=tk.LEFT, padx=4)
        ttk.Button(search_row, text="Search", command=self._fw_search_clients).pack(side=tk.LEFT, padx=4)

        cols = ("ID", "Name", "Phone", "Email", "Repairs")
        self.fw_clients_tree = ttk.Treeview(parent, columns=cols, show="headings", height=8)
        for c in cols:
            self.fw_clients_tree.heading(c, text=c)
            self.fw_clients_tree.column(c, width=120 if c != "Name" else 160)
        self.fw_clients_tree.pack(fill=tk.BOTH, expand=True, pady=5)
        self._fw_refresh_clients()

    # -- Workshop: Tickets Sub-tab ---------------------------------------
    def _build_workshop_tickets(self, parent):
        ttk.Label(parent, text="Repair Ticket Management", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))

        form = ttk.Frame(parent)
        form.pack(fill=tk.X, pady=5)
        ttk.Label(form, text="Client ID:").grid(row=0, column=0, sticky=tk.W, padx=4)
        self.fw_tk_client = ttk.Entry(form, width=12)
        self.fw_tk_client.grid(row=0, column=1, padx=4)
        ttk.Label(form, text="Category:").grid(row=0, column=2, sticky=tk.W, padx=4)
        self.fw_tk_cat = ttk.Combobox(form, values=[c.value for c in DeviceCategory], state="readonly", width=14)
        self.fw_tk_cat.grid(row=0, column=3, padx=4)
        self.fw_tk_cat.current(0)
        ttk.Label(form, text="Brand:").grid(row=0, column=4, sticky=tk.W, padx=4)
        self.fw_tk_brand = ttk.Entry(form, width=14)
        self.fw_tk_brand.grid(row=0, column=5, padx=4)
        ttk.Label(form, text="Model:").grid(row=1, column=0, sticky=tk.W, padx=4)
        self.fw_tk_model = ttk.Entry(form, width=14)
        self.fw_tk_model.grid(row=1, column=1, padx=4)
        ttk.Label(form, text="Issue:").grid(row=1, column=2, sticky=tk.W, padx=4)
        self.fw_tk_issue = ttk.Entry(form, width=35)
        self.fw_tk_issue.grid(row=1, column=3, columnspan=3, padx=4, sticky=tk.EW)
        ttk.Label(form, text="Technician:").grid(row=2, column=0, sticky=tk.W, padx=4)
        self.fw_tk_tech = ttk.Entry(form, width=14)
        self.fw_tk_tech.grid(row=2, column=1, padx=4)
        ttk.Label(form, text="Priority (1-3):").grid(row=2, column=2, sticky=tk.W, padx=4)
        self.fw_tk_prio = ttk.Combobox(form, values=["1", "2", "3"], state="readonly", width=5)
        self.fw_tk_prio.grid(row=2, column=3, padx=4)
        self.fw_tk_prio.current(1)

        btn_row = ttk.Frame(parent)
        btn_row.pack(fill=tk.X, pady=5)
        ttk.Button(btn_row, text="Create Ticket", command=self._fw_create_ticket).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Start Diagnostic", command=self._fw_start_diag).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Advance Step (Pass)", command=lambda: self._fw_advance_diag(True)).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Advance Step (Fail)", command=lambda: self._fw_advance_diag(False)).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Mark Delivered", command=self._fw_deliver_ticket).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Cancel", command=self._fw_cancel_ticket).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Refresh", command=self._fw_refresh_tickets).pack(side=tk.LEFT, padx=4)

        cols = ("ID", "Client", "Category", "Brand", "Model", "Status", "Priority", "Days")
        self.fw_tk_tree = ttk.Treeview(parent, columns=cols, show="headings", height=8)
        for c in cols:
            self.fw_tk_tree.heading(c, text=c)
            self.fw_tk_tree.column(c, width=110)
        self.fw_tk_tree.column("ID", width=90)
        self.fw_tk_tree.column("Model", width=120)
        self.fw_tk_tree.pack(fill=tk.BOTH, expand=True, pady=5)
        self._fw_refresh_tickets()

    # -- Workshop: Inventory Sub-tab -------------------------------------
    def _build_workshop_inventory(self, parent):
        ttk.Label(parent, text="Spare Parts Inventory", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))

        form = ttk.Frame(parent)
        form.pack(fill=tk.X, pady=5)
        ttk.Label(form, text="Part Type:").grid(row=0, column=0, sticky=tk.W, padx=4)
        self.fw_inv_type = ttk.Combobox(form, values=[p.value for p in PartType], state="readonly", width=22)
        self.fw_inv_type.grid(row=0, column=1, padx=4)
        self.fw_inv_type.current(0)
        ttk.Label(form, text="Name:").grid(row=0, column=2, sticky=tk.W, padx=4)
        self.fw_inv_name = ttk.Entry(form, width=22)
        self.fw_inv_name.grid(row=0, column=3, padx=4)
        ttk.Label(form, text="Compatible (comma-sep):").grid(row=1, column=0, sticky=tk.W, padx=4)
        self.fw_inv_compat = ttk.Entry(form, width=30)
        self.fw_inv_compat.grid(row=1, column=1, columnspan=2, padx=4, sticky=tk.EW)
        ttk.Label(form, text="Qty:").grid(row=1, column=3, sticky=tk.W, padx=4)
        self.fw_inv_qty = ttk.Entry(form, width=6)
        self.fw_inv_qty.grid(row=1, column=4, padx=4)
        self.fw_inv_qty.insert(0, "10")
        ttk.Label(form, text="Unit Cost:").grid(row=2, column=0, sticky=tk.W, padx=4)
        self.fw_inv_cost = ttk.Entry(form, width=8)
        self.fw_inv_cost.grid(row=2, column=1, padx=4, sticky=tk.W)
        self.fw_inv_cost.insert(0, "0.0")
        ttk.Label(form, text="Supplier:").grid(row=2, column=2, sticky=tk.W, padx=4)
        self.fw_inv_supplier = ttk.Entry(form, width=18)
        self.fw_inv_supplier.grid(row=2, column=3, padx=4)

        btn_row = ttk.Frame(parent)
        btn_row.pack(fill=tk.X, pady=5)
        ttk.Button(btn_row, text="Add Part", command=self._fw_add_part).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Remove Selected", command=self._fw_remove_part).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Seed Common Parts", command=self._fw_seed_parts).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Refresh", command=self._fw_refresh_inventory).pack(side=tk.LEFT, padx=4)

        cols = ("ID", "Type", "Name", "Compatible", "Qty", "Min", "Cost", "Stock Value")
        self.fw_inv_tree = ttk.Treeview(parent, columns=cols, show="headings", height=8)
        for c in cols:
            self.fw_inv_tree.heading(c, text=c)
            w = 90 if c not in ("Name", "Compatible") else 140
            self.fw_inv_tree.column(c, width=w)
        self.fw_inv_tree.pack(fill=tk.BOTH, expand=True, pady=5)
        self._fw_refresh_inventory()

    # -- Workshop: Diagnostics Sub-tab -----------------------------------
    def _build_workshop_diagnostics(self, parent):
        ttk.Label(parent, text="Diagnostic Workflow Tracker", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))

        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=5)
        ttk.Label(row, text="Ticket ID:").pack(side=tk.LEFT, padx=4)
        self.fw_diag_tid = ttk.Entry(row, width=14)
        self.fw_diag_tid.pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Load Workflow", command=self._fw_load_diag).pack(side=tk.LEFT, padx=4)

        cols = ("Step", "Status", "Notes", "Findings")
        self.fw_diag_tree = ttk.Treeview(parent, columns=cols, show="headings", height=10)
        for c in cols:
            self.fw_diag_tree.heading(c, text=c)
            self.fw_diag_tree.column(c, width=200 if c in ("Notes", "Findings") else 180)
        self.fw_diag_tree.pack(fill=tk.BOTH, expand=True, pady=5)

        self.fw_diag_status = ttk.Label(parent, text="", font=("Helvetica", 10))
        self.fw_diag_status.pack(anchor=tk.W, pady=2)

    # -- Workshop: Dashboard Sub-tab -------------------------------------
    def _build_workshop_dashboard(self, parent):
        ttk.Label(parent, text="Workshop Dashboard & Reports", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))

        ttk.Button(parent, text="Refresh Dashboard", command=self._fw_refresh_dashboard).pack(anchor=tk.W, pady=4)

        self.fw_dash_text = scrolledtext.ScrolledText(parent, height=18, state="disabled",
                                                      font=("Consolas", 10), bg="#1e1e1e", fg="#d4d4d4")
        self.fw_dash_text.pack(fill=tk.BOTH, expand=True, pady=5)
        self._fw_refresh_dashboard()

    # ------------------------------------------------------------------
    #  Workshop — Action Methods
    # ------------------------------------------------------------------
    def _fw_add_client(self):
        name = self.fw_client_name.get().strip()
        if not name:
            messagebox.showwarning("Workshop", "Client name is required.")
            return
        c = self.factory_mgr.clients.add_client(
            name, self.fw_client_phone.get().strip(),
            self.fw_client_email.get().strip(), self.fw_client_addr.get().strip(),
        )
        logging.info(f"Client registered: {c.name} (ID: {c.client_id})")
        self.fw_client_name.delete(0, tk.END)
        self.fw_client_phone.delete(0, tk.END)
        self.fw_client_email.delete(0, tk.END)
        self.fw_client_addr.delete(0, tk.END)
        self._fw_refresh_clients()

    def _fw_refresh_clients(self):
        self.fw_clients_tree.delete(*self.fw_clients_tree.get_children())
        for c in self.factory_mgr.clients.clients.values():
            self.fw_clients_tree.insert("", tk.END, values=(
                c.client_id, c.name, c.phone, c.email, c.total_repairs,
            ))

    def _fw_search_clients(self):
        q = self.fw_client_search.get().strip()
        results = self.factory_mgr.clients.search(q) if q else list(self.factory_mgr.clients.clients.values())
        self.fw_clients_tree.delete(*self.fw_clients_tree.get_children())
        for c in results:
            self.fw_clients_tree.insert("", tk.END, values=(
                c.client_id, c.name, c.phone, c.email, c.total_repairs,
            ))

    def _fw_create_ticket(self):
        client_id = self.fw_tk_client.get().strip()
        if not client_id:
            messagebox.showwarning("Workshop", "Client ID is required.")
            return
        cat = DeviceCategory(self.fw_tk_cat.get())
        brand = self.fw_tk_brand.get().strip()
        model = self.fw_tk_model.get().strip()
        issue = self.fw_tk_issue.get().strip()
        tech = self.fw_tk_tech.get().strip()
        prio = int(self.fw_tk_prio.get())
        t = self.factory_mgr.create_ticket(client_id, cat, brand, model, issue, technician=tech, priority=prio)
        logging.info(f"Ticket created: {t.ticket_id} — {brand} {model} [{cat.value}]")
        self._fw_refresh_tickets()

    def _fw_start_diag(self):
        sel = self.fw_tk_tree.selection()
        if not sel:
            messagebox.showwarning("Workshop", "Select a ticket first.")
            return
        tid = self.fw_tk_tree.item(sel[0])['values'][0]
        wf = self.factory_mgr.start_diagnostic(tid)
        if wf:
            logging.info(f"Diagnostic started for {tid} ({len(wf.steps)} steps)")
        self._fw_refresh_tickets()

    def _fw_advance_diag(self, passed: bool):
        sel = self.fw_tk_tree.selection()
        if not sel:
            messagebox.showwarning("Workshop", "Select a ticket first.")
            return
        tid = self.fw_tk_tree.item(sel[0])['values'][0]
        wf = self.factory_mgr.workflows.get(tid)
        if wf is None or wf.is_complete:
            messagebox.showinfo("Workshop", "No active diagnostic workflow for this ticket.")
            return
        step_name = wf.current_step.step.value if wf.current_step else "?"
        result = self.factory_mgr.advance_diagnostic(tid, passed, f"{'Passed' if passed else 'Failed'} from GUI")
        if result:
            status = "✅ PASSED" if passed else "❌ FAILED"
            logging.info(f"Diagnostic {tid}: {step_name} → {status}")
        self._fw_refresh_tickets()

    def _fw_deliver_ticket(self):
        sel = self.fw_tk_tree.selection()
        if not sel:
            messagebox.showwarning("Workshop", "Select a ticket first.")
            return
        tid = self.fw_tk_tree.item(sel[0])['values'][0]
        self.factory_mgr.update_status(tid, RepairStatus.DELIVERED)
        logging.info(f"Ticket {tid} marked as DELIVERED.")
        self._fw_refresh_tickets()

    def _fw_cancel_ticket(self):
        sel = self.fw_tk_tree.selection()
        if not sel:
            messagebox.showwarning("Workshop", "Select a ticket first.")
            return
        tid = self.fw_tk_tree.item(sel[0])['values'][0]
        self.factory_mgr.cancel_ticket(tid)
        logging.info(f"Ticket {tid} CANCELLED.")
        self._fw_refresh_tickets()

    def _fw_refresh_tickets(self):
        self.fw_tk_tree.delete(*self.fw_tk_tree.get_children())
        for t in self.factory_mgr.tickets.values():
            self.fw_tk_tree.insert("", tk.END, values=(
                t.ticket_id, t.client_id, t.device_category.value,
                t.device_brand, t.device_model, t.status.value,
                t.priority, t.days_open,
            ))

    def _fw_add_part(self):
        ptype = PartType(self.fw_inv_type.get())
        name = self.fw_inv_name.get().strip()
        if not name:
            messagebox.showwarning("Workshop", "Part name is required.")
            return
        compat = [s.strip() for s in self.fw_inv_compat.get().split(",") if s.strip()]
        qty = int(self.fw_inv_qty.get() or "0")
        cost = float(self.fw_inv_cost.get() or "0")
        supplier = self.fw_inv_supplier.get().strip()
        part = self.factory_mgr.inventory.add_part(ptype, name, compat, qty=qty, cost=cost, supplier=supplier)
        logging.info(f"Part added: {part.name} ({part.part_type.value}) qty={qty}")
        self.fw_inv_name.delete(0, tk.END)
        self.fw_inv_compat.delete(0, tk.END)
        self.fw_inv_qty.delete(0, tk.END)
        self.fw_inv_qty.insert(0, "10")
        self._fw_refresh_inventory()

    def _fw_remove_part(self):
        sel = self.fw_inv_tree.selection()
        if not sel:
            messagebox.showwarning("Workshop", "Select a part to remove.")
            return
        pid = self.fw_inv_tree.item(sel[0])['values'][0]
        self.factory_mgr.inventory.remove_part(pid)
        logging.info(f"Part {pid} removed from inventory.")
        self._fw_refresh_inventory()

    def _fw_seed_parts(self):
        count = 0
        for p in COMMON_PARTS:
            self.factory_mgr.inventory.add_part(
                p["part_type"], p["name"], p["compatible"],
                qty=20, cost=p["cost"], supplier="AuraParts Inc.",
            )
            count += 1
        logging.info(f"Seeded {count} common spare parts into inventory.")
        self._fw_refresh_inventory()

    def _fw_refresh_inventory(self):
        self.fw_inv_tree.delete(*self.fw_inv_tree.get_children())
        for p in self.factory_mgr.inventory.parts.values():
            val = p.quantity * p.unit_cost
            self.fw_inv_tree.insert("", tk.END, values=(
                p.part_id, p.part_type.value, p.name,
                ",".join(p.compatible_devices[:3]) + ("..." if len(p.compatible_devices) > 3 else ""),
                p.quantity, p.min_stock, f"${p.unit_cost:.2f}", f"${val:.2f}",
            ))

    def _fw_load_diag(self):
        tid = self.fw_diag_tid.get().strip()
        wf = self.factory_mgr.workflows.get(tid)
        self.fw_diag_tree.delete(*self.fw_diag_tree.get_children())
        if wf is None:
            self.fw_diag_status.config(text=f"No workflow found for ticket {tid}")
            return
        for i, rec in enumerate(wf.steps):
            marker = "→" if i == wf.current_index and not wf.is_complete else "✓" if rec.status == "passed" else "✗" if rec.status == "failed" else "·"
            findings_str = str(rec.findings) if rec.findings else ""
            self.fw_diag_tree.insert("", tk.END, values=(
                f"{marker} {rec.step.value}", rec.status, rec.notes, findings_str,
            ))
        s = wf.summary()
        self.fw_diag_status.config(
            text=f"Progress: {s['completed']}/{s['total_steps']} ({s['progress']}) | "
                 f"Failures: {s['failures']} | Complete: {s['complete']}"
        )

    def _fw_refresh_dashboard(self):
        dash = self.factory_mgr.dashboard()
        lines = [
            "=" * 55,
            "  AuraTool-Suite — Workshop Dashboard",
            "=" * 55,
            "",
            f"  Open Tickets:      {dash['open_tickets']}",
            f"  Overdue (>7 days): {dash['overdue']}",
            f"  Total Clients:     {dash['total_clients']}",
            f"  Low-Stock Parts:   {dash['low_stock_parts']}",
            f"  Inventory Value:   ${dash['inventory_value']:,.2f}",
            "",
            "  Status Breakdown:",
        ]
        for status, count in dash["by_status"].items():
            if count:
                lines.append(f"    {status:20s} {count}")
        lines.append("")
        lines.append("  By Device Category:")
        for cat, count in dash["by_category"].items():
            if count:
                lines.append(f"    {cat:20s} {count}")
        lines.append("")
        rev = dash["revenue"]
        lines.append("  Revenue Report:")
        lines.append(f"    Repairs Completed: {rev['total_repairs']}")
        lines.append(f"    Total Revenue:     ${rev['total_revenue']:,.2f}")
        lines.append(f"    Average Cost:      ${rev['average_cost']:,.2f}")
        if rev["by_brand"]:
            lines.append("")
            lines.append("    By Brand:")
            for brand, amt in rev["by_brand"].items():
                lines.append(f"      {brand:18s} ${amt:,.2f}")
        lines.append("")
        low = self.factory_mgr.inventory.low_stock_items()
        if low:
            lines.append(f"  🚨 Low Stock Alerts ({len(low)} items):")
            for p in low:
                lines.append(f"    • {p.name} ({p.part_type.value}): {p.quantity}/{p.min_stock}")
        lines.append("=" * 55)
        self.fw_dash_text.configure(state="normal")
        self.fw_dash_text.delete("1.0", tk.END)
        self.fw_dash_text.insert(tk.END, "\n".join(lines))
        self.fw_dash_text.configure(state="disabled")

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

    def _action_run_ai_command(self):
        cmd = self.ai_cmd_entry.get()
        res = self.ai_assistant.process_voice_or_text_command(cmd)
        logging.info(f"AI Assistant Response: {res['message']}")

    def _action_analyze_logs(self):
        sample_log = "Error: kernel panic bad block ufs error frp_locked"
        diag = self.ai_assistant.analyze_system_logs(sample_log)
        messagebox.showinfo("Aura-AI Diagnostic", f"Health Score: {diag['health_score']}%\nIssues: {', '.join(diag['issues_detected'])}\nRecommendation: {diag['recommended_action']}")

    def _action_check_ai_license(self):
        status = self.ai_assistant.verify_extended_license_2030()
        logging.info(f"License Verified: {status['tier']} | Ecosystem Support until Year {status['supported_until_year']}")

    def _action_flash(self):
        model = self.model_cb.get()
        logging.info(f"Starting firmware flash process for model: {model}")
        self.flashing_engine.flash_firmware(model, f"/firmware/{model}/update.tar", mode="FASTBOOT")

    def _action_read_ptable(self):
        logging.info(f"Reading partition table for device model: {self.model_cb.get()}")

    def _action_storage_health(self):
        model = self.model_cb.get()
        health = self.flashing_engine.scan_storage_health(model)
        logging.info(f"Storage Health ({model}): {health['storage_health']} | Read: {health['read_speed_mbps']} MB/s")

    def _action_reboot_fastboot(self):
        logging.info(f"Sending reboot-bootloader signal to connected device ({self.model_cb.get()}).")

    def _action_fix_major(self):
        model = self.model_cb.get()
        res = self.ultimate_repair.repair_major_system_issues(model)
        logging.info(f"Major Repair Complete for {model}: {res['status']}")

    def _action_fix_minor(self):
        model = self.model_cb.get()
        res = self.ultimate_repair.repair_minor_system_issues(model)
        logging.info(f"Minor Repair Complete for {model}: {res['status']}")

    def _action_fix_cloud_sync(self):
        model = self.model_cb.get()
        self.ultimate_repair.repair_cloud_and_account_sync(model)

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

    def _action_run_acc_diag(self):
        model = self.model_cb.get()
        res = self.account_repair.run_account_diagnostics(model)
        logging.info(f"Account & Security Diagnostics Result: {res}")

    def _action_bypass_frp(self):
        model = self.model_cb.get()
        self.account_repair.bypass_frp_and_cloud_locks(model)

    def _action_backup_efs(self):
        model = self.model_cb.get()
        self.account_repair.backup_efs_nvram(model, f"/backups/{model}/efs_backup/")

    def _action_restore_efs(self):
        model = self.model_cb.get()
        self.account_repair.restore_efs_nvram(model, f"/backups/{model}/efs_backup/")

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
