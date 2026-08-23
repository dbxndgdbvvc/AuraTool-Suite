import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging

from core.licensing import LicenseManager
from modules.localization import LocalizationManager
from modules.flashing_engine import FlashingEngine
from modules.biometrics_fix import BiometricsFix
from modules.smart_devices import SmartDeviceManager
from modules.data_recovery import DataRecoveryModule
from modules.account_repair import AccountRepairModule
from modules.aura_ai_assistant import AuraAIAssistant
from modules.ultimate_repair import UltimateRepairModule
from modules.chat_rooms import ChatRoomManager
from modules.media_stream import MediaStreamEngine
from modules.ecommerce import ECommerceManager
from auratool_factory import FactoryManager


class TextHandler(logging.Handler):
    """Streams application logging into GUI output window."""

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
    """Standalone Native Desktop Application GUI."""

    MANUFACTURERS = {
        "Samsung": ["Galaxy S23 Ultra", "Galaxy S22", "Galaxy A54", "Galaxy Tab S8", "Galaxy Watch 6"],
        "Apple": ["iPhone 15 Pro", "iPhone 14", "iPad Pro 12.9", "Apple Watch Series 9"],
        "Xiaomi": ["Redmi Note 12", "Xiaomi 13 Pro", "POCO X5 Pro"],
        "Huawei": ["P50 Pro", "Mate 40 Pro", "Nova 10"],
        "Smart Wearables & AR/VR": ["Apple Vision Pro", "Meta Quest 3", "Ray-Ban Meta Smart Glasses"],
        "Qualcomm Generic": ["Snapdragon 8 Gen 2", "Snapdragon 778G"],
        "MediaTek (MTK) Generic": ["Dimensity 9000", "Helio G99"],
    }

    def __init__(self, license_info: dict, driver_status: dict, factory_mgr: FactoryManager | None = None):
        self.root = tk.Tk()
        self.root.title("AuraTool-Suite — Universal Desktop Platform 2030")
        self.root.geometry("1180x820")

        self.license_info = license_info
        self.driver_status = driver_status
        self.license_mgr = LicenseManager()
        self.loc_mgr = LocalizationManager("ar")

        self.flashing_engine = FlashingEngine()
        self.biometrics_fix = BiometricsFix()
        self.smart_dev_mgr = SmartDeviceManager()
        self.data_recovery = DataRecoveryModule()
        self.account_repair = AccountRepairModule()
        self.ai_assistant = AuraAIAssistant()
        self.ultimate_repair = UltimateRepairModule()
        self.chat_mgr = ChatRoomManager()
        self.media_stream = MediaStreamEngine()
        self.ecommerce_mgr = ECommerceManager()
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
        # Top Header Bar
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill=tk.X)

        self.title_lbl = ttk.Label(header, text=self.loc_mgr.get_string("title"), font=("Helvetica", 13, "bold"))
        self.title_lbl.pack(side=tk.LEFT if not self.loc_mgr.is_rtl() else tk.RIGHT)

        hwid = self.license_info.get("hwid", "N/A")
        lic_txt = f"{self.loc_mgr.get_string('license_lbl')} {self.license_info['tier']} ({self.license_info['days_remaining']} days left) | HWID: {hwid}"
        self.lic_lbl = ttk.Label(header, text=lic_txt, font=("Helvetica", 9), foreground="green" if self.license_info["is_active"] else "red")
        self.lic_lbl.pack(side=tk.RIGHT if not self.loc_mgr.is_rtl() else tk.LEFT)

        # Activation / License Bar
        act_bar = ttk.LabelFrame(self.root, text="License Activation & HWID Binding / تفعيل الترخيص", padding=5)
        act_bar.pack(fill=tk.X, padx=10, pady=2)

        ttk.Label(act_bar, text="Enter License Key (6-Month AT-6M-... or 1-Year AT-1Y-...):").pack(side=tk.LEFT, padx=5)
        self.key_entry = ttk.Entry(act_bar, width=32)
        self.key_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(act_bar, text="Activate Key / تفعيل المفتاح", command=self._action_activate_key).pack(side=tk.LEFT, padx=5)

        # Tabbed Navigation Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)

        # Tab 1: Aura-AI Assistant
        ai_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(ai_tab, text=self.loc_mgr.get_string("ai_tab"))
        self._build_ai_tab(ai_tab)

        # Tab 2: Vendor & Device Operations
        vendor_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(vendor_tab, text=self.loc_mgr.get_string("vendor_tab"))
        self._build_vendor_tab(vendor_tab)

        # Tab 3: Ultimate System & Virus Repair
        repair_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(repair_tab, text=self.loc_mgr.get_string("repair_tab"))
        self._build_repair_tab(repair_tab)

        # Tab 4: Deep Data Recovery
        recovery_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(recovery_tab, text=self.loc_mgr.get_string("recovery_tab"))
        self._build_recovery_tab(recovery_tab)

        # Tab 5: Live Chat Rooms
        chat_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(chat_tab, text=self.loc_mgr.get_string("chat_tab"))
        self._build_chat_tab(chat_tab)

        # Tab 6: Media Stream Network
        stream_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(stream_tab, text=self.loc_mgr.get_string("stream_tab"))
        self._build_stream_tab(stream_tab)

        # Tab 7: E-Commerce Store
        store_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(store_tab, text=self.loc_mgr.get_string("store_tab"))
        self._build_store_tab(store_tab)

        # Tab 8: Settings & i18n
        settings_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(settings_tab, text=self.loc_mgr.get_string("settings_tab"))
        self._build_settings_tab(settings_tab)

        # Bottom System Output Console
        console_frame = ttk.LabelFrame(self.root, text="System Log Console / سجل النظام", padding=5)
        console_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)

        self.console = scrolledtext.ScrolledText(console_frame, height=7, state='disabled', bg="black", fg="light green", font=("Consolas", 9))
        self.console.pack(fill=tk.BOTH, expand=True)

    def _build_ai_tab(self, parent):
        ttk.Label(parent, text="Aura-AI Voice/Command Assistant & Diagnostic Log Engine", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        f = ttk.Frame(parent, padding=5)
        f.pack(fill=tk.X, pady=5)
        ttk.Label(f, text="Command:").pack(side=tk.LEFT, padx=5)
        self.ai_cmd_entry = ttk.Entry(f, width=50)
        self.ai_cmd_entry.pack(side=tk.LEFT, padx=5)
        self.ai_cmd_entry.insert(0, "Analyze log and bypass FRP lock")
        ttk.Button(f, text=self.loc_mgr.get_string("run_ai"), command=self._action_run_ai).pack(side=tk.LEFT, padx=5)

    def _build_vendor_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill=tk.X, pady=5)
        ttk.Label(top, text="Manufacturer:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.vendor_cb = ttk.Combobox(top, values=list(self.MANUFACTURERS.keys()), state="readonly")
        self.vendor_cb.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.vendor_cb.current(0)

        ttk.Label(top, text="Model:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.model_cb = ttk.Combobox(top, values=self.MANUFACTURERS["Samsung"], state="readonly")
        self.model_cb.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.model_cb.current(0)

        btn_f = ttk.LabelFrame(parent, text="Operations", padding=10)
        btn_f.pack(fill=tk.X, pady=10)
        ttk.Button(btn_f, text=self.loc_mgr.get_string("flash"), command=self._action_flash).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_f, text=self.loc_mgr.get_string("bypass_frp"), command=self._action_bypass_frp).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_f, text="Backup EFS / NVRAM", command=self._action_backup_efs).pack(side=tk.LEFT, padx=5)

    def _build_repair_tab(self, parent):
        ttk.Label(parent, text="System Bootloop, Black Screen & Virus Removal Engine", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        f = ttk.Frame(parent, padding=5)
        f.pack(fill=tk.X, pady=10)
        ttk.Button(f, text="Repair Bootloop & Crash", command=self._action_fix_bootloop).pack(side=tk.LEFT, padx=5)
        ttk.Button(f, text="Scan & Remove Viruses", command=self._action_clean_virus).pack(side=tk.LEFT, padx=5)
        ttk.Button(f, text="Recalibrate Biometrics", command=self._action_recalib_bio).pack(side=tk.LEFT, padx=5)

    def _build_recovery_tab(self, parent):
        ttk.Label(parent, text="Deep Scan Data Recovery (Photos, Videos, SMS, Contacts)", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        ttk.Button(parent, text=self.loc_mgr.get_string("start_scan"), command=self._action_deep_scan).pack(anchor=tk.W, pady=5)

    def _build_chat_tab(self, parent):
        ttk.Label(parent, text="Real-Time Technician Community & Support Rooms", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        self.chat_txt = scrolledtext.ScrolledText(parent, height=12, state="disabled")
        self.chat_txt.pack(fill=tk.BOTH, expand=True, pady=5)

        input_f = ttk.Frame(parent)
        input_f.pack(fill=tk.X, pady=5)
        self.chat_entry = ttk.Entry(input_f, width=60)
        self.chat_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(input_f, text="Send", command=self._action_send_chat).pack(side=tk.LEFT, padx=5)

    def _build_stream_tab(self, parent):
        ttk.Label(parent, text="Media Streaming & Hardware Testpoint Tutorials", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        for vid in self.media_stream.list_streams():
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=f"[{vid['category']}] {vid['title']} ({vid['duration']})").pack(side=tk.LEFT, padx=5)
            ttk.Button(row, text="Play Stream", command=lambda v=vid['id']: self._action_play_stream(v)).pack(side=tk.RIGHT, padx=5)

    def _build_store_tab(self, parent):
        ttk.Label(parent, text="In-App Store — Spare Parts, Tools & Subscriptions", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        cols = ("ID", "Name", "Category", "Price", "Stock")
        self.store_tree = ttk.Treeview(parent, columns=cols, show="headings", height=8)
        for c in cols:
            self.store_tree.heading(c, text=c)
            self.store_tree.column(c, width=120 if c != "Name" else 240)
        self.store_tree.pack(fill=tk.BOTH, expand=True, pady=5)

        for item in self.ecommerce_mgr.get_catalogue():
            self.store_tree.insert("", tk.END, values=(item["id"], item["name"], item["category"], f"${item['price']:.2f}", item["stock"]))

        ttk.Button(parent, text=self.loc_mgr.get_string("checkout"), command=self._action_checkout).pack(anchor=tk.W, pady=5)

    def _build_settings_tab(self, parent):
        ttk.Label(parent, text="Select Interface Language / اختر لغة الواجهة:", font=("Helvetica", 10)).pack(anchor=tk.W, pady=5)
        self.lang_cb = ttk.Combobox(parent, values=list(LocalizationManager.SUPPORTED_LANGUAGES.values()), state="readonly")
        self.lang_cb.pack(anchor=tk.W, pady=5)
        self.lang_cb.current(1)

        ttk.Button(parent, text="Apply Language / تطبيق اللغة", command=self._action_change_lang).pack(anchor=tk.W, pady=5)

    def _action_activate_key(self):
        key = self.key_entry.get().strip()
        if not key:
            messagebox.showwarning("Activation", "Please enter a license key.")
            return

        if self.license_mgr.activate_key(key):
            new_status = self.license_mgr.check_license_status()
            self.license_info = new_status
            lic_txt = f"{self.loc_mgr.get_string('license_lbl')} {new_status['tier']} ({new_status['days_remaining']} days left) | HWID: {new_status['hwid']}"
            self.lic_lbl.config(text=lic_txt, foreground="green")
            messagebox.showinfo("Activation Success", f"License activated successfully!\nTier: {new_status['tier']}\nValid for: {new_status['days_remaining']} days.")
        else:
            messagebox.showerror("Activation Failed", "Invalid key or key is locked to another HWID machine.")

    def _action_run_ai(self):
        res = self.ai_assistant.process_voice_or_text_command(self.ai_cmd_entry.get())
        logging.info(f"Aura-AI Response: {res['message']}")

    def _action_flash(self):
        m = self.model_cb.get()
        logging.info(self.loc_mgr.get_arabic_log("FLASHING_START"))
        self.flashing_engine.flash_firmware(m, f"/firmware/{m}.bin")

    def _action_bypass_frp(self):
        m = self.model_cb.get()
        self.account_repair.bypass_frp_and_cloud_locks(m)
        logging.info(self.loc_mgr.get_arabic_log("FRP_SUCCESS"))

    def _action_backup_efs(self):
        m = self.model_cb.get()
        self.account_repair.backup_efs_nvram(m, f"/backups/{m}/efs")

    def _action_fix_bootloop(self):
        m = self.model_cb.get()
        self.ultimate_repair.repair_major_system_issues(m)

    def _action_clean_virus(self):
        m = self.model_cb.get()
        res = self.ultimate_repair.scan_and_remove_viruses(m)
        logging.info(self.loc_mgr.get_arabic_log("VIRUS_REMOVED"))

    def _action_recalib_bio(self):
        m = self.model_cb.get()
        self.biometrics_fix.recalibrate_sensors(m)

    def _action_deep_scan(self):
        m = self.model_cb.get()
        logging.info(self.loc_mgr.get_arabic_log("RECOVERY_START"))
        res = self.data_recovery.perform_deep_scan(m)
        messagebox.showinfo("Deep Scan Finished", f"Photos: {res['photos_found']}\nSMS: {res['sms_messages_found']}\nContacts: {res['contacts_found']}")

    def _action_send_chat(self):
        txt = self.chat_entry.get().strip()
        if txt:
            msg = self.chat_mgr.send_message("Technician", "general", txt)
            self.chat_txt.configure(state="normal")
            self.chat_txt.insert(tk.END, f"[{msg.timestamp}] {msg.sender}: {msg.content}\n")
            self.chat_txt.configure(state="disabled")
            self.chat_entry.delete(0, tk.END)

    def _action_play_stream(self, stream_id):
        res = self.media_stream.start_stream(stream_id)
        logging.info(f"Stream URL: {res['stream_url']}")

    def _action_checkout(self):
        sel = self.store_tree.selection()
        if sel:
            item_id = self.store_tree.item(sel[0])["values"][0]
            self.ecommerce_mgr.add_to_cart(item_id)
            order = self.ecommerce_mgr.checkout()
            messagebox.showinfo("Order Placed", f"Order ID: {order['order_id']} Total: ${order['total_amount']:.2f}")

    def _action_change_lang(self):
        selected = self.lang_cb.get()
        for code, name in LocalizationManager.SUPPORTED_LANGUAGES.items():
            if name == selected:
                self.loc_mgr.set_language(code)
                self.title_lbl.config(text=self.loc_mgr.get_string("title"))
                logging.info(f"Language changed to {selected}.")
                break

    def run(self):
        self.root.mainloop()
