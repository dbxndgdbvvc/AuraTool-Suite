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
from modules.chat_rooms import ChatRoomManager
from modules.media_stream import MediaStreamEngine
from modules.ecommerce import ECommerceManager
from auratool_factory import FactoryManager

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
    """Cross-platform Standalone Desktop GUI implementation using Tkinter."""

    MANUFACTURERS = {
        "Samsung": ["Galaxy S23", "Galaxy S22", "Galaxy A54", "Galaxy Tab S8", "Galaxy Watch 6"],
        "Apple": ["iPhone 15 Pro", "iPhone 14", "iPad Pro 12.9", "Apple Watch Series 9"],
        "Xiaomi": ["Redmi Note 12", "Xiaomi 13 Pro", "Mi 11 Ultra", "POCO X5"],
        "Huawei": ["P50 Pro", "Mate 40 Pro", "Nova 10", "Y9 Prime"],
        "Smart Wearables & AR/VR": ["Apple Vision Pro", "Meta Quest 3", "Ray-Ban Meta Smart Glasses"],
        "Qualcomm Generic": ["Snapdragon 8 Gen 2 Generic", "Snapdragon 778G Generic"],
        "MediaTek (MTK) Generic": ["Dimensity 9000 Generic", "Helio G99 Generic"]
    }

    def __init__(self, license_info: dict, driver_status: dict, factory_mgr: FactoryManager | None = None):
        self.root = tk.Tk()
        self.root.title("AuraTool-Suite - Standalone Native Desktop Framework 2030")
        self.root.geometry("1150x780")

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
        # Header / Status Bar
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill=tk.X)

        self.title_lbl = ttk.Label(header, text="AuraTool-Suite 2030", font=("Helvetica", 16, "bold"))
        self.title_lbl.pack(side=tk.LEFT)

        hwid_text = f"HWID: {self.license_info.get('hwid', 'UNKNOWN')}"
        lic_text = f"License: {self.license_info['tier']} ({self.license_info['days_remaining']} days left) | {hwid_text}"
        self.lic_lbl = ttk.Label(header, text=lic_text, font=("Helvetica", 10), foreground="green" if self.license_info['is_active'] else "red")
        self.lic_lbl.pack(side=tk.RIGHT)

        # Main Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)

        # Tab 1: AI Assistant
        ai_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(ai_tab, text=self.loc_mgr.get_string("ai_tab"))
        self._build_ai_tab(ai_tab)

        # Tab 2: Vendor Operations
        vendor_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(vendor_tab, text=self.loc_mgr.get_string("vendor_tab"))
        self._build_vendor_tab(vendor_tab)

        # Tab 3: Ultimate System Repair
        ult_repair_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(ult_repair_tab, text=self.loc_mgr.get_string("repair_tab"))
        self._build_ultimate_repair_tab(ult_repair_tab)

        # Tab 4: Live Chat Rooms
        chat_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(chat_tab, text=self.loc_mgr.get_string("chat_tab"))
        self._build_chat_tab(chat_tab)

        # Tab 5: Media Streaming Network
        stream_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(stream_tab, text=self.loc_mgr.get_string("stream_tab"))
        self._build_stream_tab(stream_tab)

        # Tab 6: E-Commerce Store
        store_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(store_tab, text=self.loc_mgr.get_string("store_tab"))
        self._build_store_tab(store_tab)

        # Tab 7: Settings & Multi-Language
        settings_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(settings_tab, text=self.loc_mgr.get_string("settings_tab"))
        self._build_settings_tab(settings_tab)

        # Console Frame
        console_frame = ttk.LabelFrame(self.root, text="System Output Console", padding=5)
        console_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)

        self.console = scrolledtext.ScrolledText(console_frame, height=7, state='disabled', bg="black", fg="light green", font=("Consolas", 9))
        self.console.pack(fill=tk.BOTH, expand=True)

    def _build_ai_tab(self, parent):
        ttk.Label(parent, text="Aura-AI Assistant & Log Diagnostic Engine", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        cmd_frame = ttk.Frame(parent, padding=5)
        cmd_frame.pack(fill=tk.X, pady=5)
        ttk.Label(cmd_frame, text="Command:").pack(side=tk.LEFT, padx=5)
        self.ai_cmd_entry = ttk.Entry(cmd_frame, width=45)
        self.ai_cmd_entry.pack(side=tk.LEFT, padx=5)
        self.ai_cmd_entry.insert(0, "Analyze device log and bypass FRP")
        ttk.Button(cmd_frame, text="Run AI Command", command=self._action_run_ai_command).pack(side=tk.LEFT, padx=5)

    def _build_vendor_tab(self, parent):
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X, pady=5)
        ttk.Label(top_frame, text="Manufacturer:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.vendor_cb = ttk.Combobox(top_frame, values=list(self.MANUFACTURERS.keys()), state="readonly")
        self.vendor_cb.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.vendor_cb.current(0)

        ttk.Label(top_frame, text="Device Model:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.model_cb = ttk.Combobox(top_frame, values=self.MANUFACTURERS["Samsung"], state="readonly")
        self.model_cb.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.model_cb.current(0)

        ttk.Button(parent, text="Flash Firmware Image", command=self._action_flash).pack(anchor=tk.W, pady=10)

    def _build_ultimate_repair_tab(self, parent):
        ttk.Label(parent, text="Ultimate System & Account Repair Suite", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        ttk.Button(parent, text="Fix Bootloop & Memory Errors", command=self._action_fix_major).pack(anchor=tk.W, pady=5)

    def _build_chat_tab(self, parent):
        ttk.Label(parent, text="Technician & Support Chat Rooms", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        self.chat_display = scrolledtext.ScrolledText(parent, height=12, state="disabled")
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=5)

        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.X, pady=5)
        self.chat_entry = ttk.Entry(input_frame, width=60)
        self.chat_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(input_frame, text="Send Message", command=self._action_send_chat).pack(side=tk.LEFT, padx=5)

    def _build_stream_tab(self, parent):
        ttk.Label(parent, text="Media Streaming & Technical Video Tutorials", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        for vid in self.media_stream.list_streams():
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=f"[{vid['category']}] {vid['title']} ({vid['duration']})").pack(side=tk.LEFT, padx=5)
            ttk.Button(row, text="Play Stream", command=lambda v=vid['id']: self._action_play_stream(v)).pack(side=tk.RIGHT, padx=5)

    def _build_store_tab(self, parent):
        ttk.Label(parent, text="E-Commerce Store & Spare Parts Catalogue", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=5)
        cols = ("ID", "Name", "Category", "Price", "Stock")
        self.store_tree = ttk.Treeview(parent, columns=cols, show="headings", height=8)
        for c in cols:
            self.store_tree.heading(c, text=c)
            self.store_tree.column(c, width=120 if c != "Name" else 220)
        self.store_tree.pack(fill=tk.BOTH, expand=True, pady=5)

        for item in self.ecommerce_mgr.get_catalogue():
            self.store_tree.insert("", tk.END, values=(item["id"], item["name"], item["category"], f"${item['price']:.2f}", item["stock"]))

        ttk.Button(parent, text="Add Selected to Cart & Checkout", command=self._action_checkout).pack(anchor=tk.W, pady=5)

    def _build_settings_tab(self, parent):
        ttk.Label(parent, text="Select Display Language / اختر اللغة:", font=("Helvetica", 10)).pack(anchor=tk.W, pady=5)
        self.lang_cb = ttk.Combobox(parent, values=list(LocalizationManager.SUPPORTED_LANGUAGES.values()), state="readonly")
        self.lang_cb.pack(anchor=tk.W, pady=5)
        self.lang_cb.current(0)
        ttk.Button(parent, text="Apply Language", command=self._action_change_lang).pack(anchor=tk.W, pady=5)

    def _action_run_ai_command(self):
        res = self.ai_assistant.process_voice_or_text_command(self.ai_cmd_entry.get())
        logging.info(f"AI Assistant: {res['message']}")

    def _action_flash(self):
        logging.info(f"Flashing model: {self.model_cb.get()}")

    def _action_fix_major(self):
        logging.info("Executing ultimate repair...")

    def _action_send_chat(self):
        msg = self.chat_entry.get().strip()
        if msg:
            m = self.chat_mgr.send_message("Technician", "general", msg)
            self.chat_display.configure(state="normal")
            self.chat_display.insert(tk.END, f"[{m.timestamp}] {m.sender}: {m.content}\n")
            self.chat_display.configure(state="disabled")
            self.chat_entry.delete(0, tk.END)

    def _action_play_stream(self, stream_id):
        res = self.media_stream.start_stream(stream_id)
        logging.info(f"Media Stream: {res['stream_url']}")

    def _action_checkout(self):
        sel = self.store_tree.selection()
        if not sel:
            messagebox.showwarning("Store", "Select an item to purchase.")
            return
        item_id = self.store_tree.item(sel[0])['values'][0]
        self.ecommerce_mgr.add_to_cart(item_id, 1)
        order = self.ecommerce_mgr.checkout()
        messagebox.showinfo("Order Complete", f"Order #{order['order_id']} total: ${order['total_amount']:.2f}")

    def _action_change_lang(self):
        selected = self.lang_cb.get()
        for code, name in LocalizationManager.SUPPORTED_LANGUAGES.items():
            if name == selected:
                self.loc_mgr.set_language(code)
                logging.info(f"Language updated to {selected}.")
                break

    def run(self):
        self.root.mainloop()
