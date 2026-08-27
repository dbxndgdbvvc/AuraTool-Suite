"""
AuraTool-Suite — Professional HD Desktop GUI
=============================================
High-resolution interface with SVG brand logos, organized sidebar navigation,
full RTL/Arabic support, and comprehensive phone maintenance tools.

Features:
- SVG brand logos for 21+ phone manufacturers
- Sidebar navigation with icon labels
- Professional dark theme with gradient accents
- RTL support for Arabic, Persian, Urdu
- Dynamic brand selection with icon preview
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
import os
import sys
import platform
from pathlib import Path

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
from modules.device_drivers import DeviceDriverManager
from core.security import SecurityManager
from auratool_factory import FactoryManager

# ─── Brand Icons Import ─────────────────────────────────────────────────────
try:
    from ui.brand_icons import get_brand_icons, BRAND_DEFINITIONS as BRAND_ICON_DEFS
    HAS_BRAND_ICONS = True
except ImportError:
    HAS_BRAND_ICONS = False

try:
    from ui.brand_svg import get_brand_svg_manager, BRAND_SVG_DATA
    HAS_SVG = True
except ImportError:
    HAS_SVG = False


# ═══════════════════════════════════════════════════════════════════════════
#  Color Palette (Professional Dark Theme)
# ═══════════════════════════════════════════════════════════════════════════

class Theme:
    BG_DARK = "#1a1a2e"
    BG_MEDIUM = "#16213e"
    BG_LIGHT = "#0f3460"
    ACCENT = "#e94560"
    ACCENT2 = "#533483"
    TEXT_WHITE = "#ffffff"
    TEXT_LIGHT = "#b0b0b0"
    TEXT_GREEN = "#00e676"
    TEXT_YELLOW = "#ffd600"
    TEXT_RED = "#ff1744"
    BTN_PRIMARY = "#e94560"
    BTN_SECONDARY = "#533483"
    BTN_SUCCESS = "#00c853"
    BORDER = "#2a2a4a"
    SIDEBAR_BG = "#0f0f23"
    SIDEBAR_ACTIVE = "#1a1a3e"
    TAB_BG = "#1a1a2e"
    CONSOLE_BG = "#0a0a1a"
    HEADER_BG = "#0a0a1a"


# ═══════════════════════════════════════════════════════════════════════════
#  Brand Data
# ═══════════════════════════════════════════════════════════════════════════

BRAND_LOGOS = {
    "Samsung":    {"emoji": "📱", "color": "#1428a0", "accent": "#ffffff"},
    "Apple":      {"emoji": "🍎", "color": "#555555", "accent": "#ffffff"},
    "Xiaomi":     {"emoji": "🔴", "color": "#ff6700", "accent": "#ffffff"},
    "Huawei":     {"emoji": "🌸", "color": "#cf0a2c", "accent": "#ffffff"},
    "Oppo":       {"emoji": "🟢", "color": "#1a8a1a", "accent": "#ffffff"},
    "Vivo":       {"emoji": "🔵", "color": "#415fff", "accent": "#ffffff"},
    "Realme":     {"emoji": "🟡", "color": "#ffc300", "accent": "#1a1a1a"},
    "OnePlus":    {"emoji": "🔴", "color": "#f5010c", "accent": "#ffffff"},
    "Google Pixel":{"emoji": "🔷", "color": "#4285f4", "accent": "#ffffff"},
    "Honor":      {"emoji": "🔷", "color": "#0ab3e3", "accent": "#ffffff"},
    "Infinix":    {"emoji": "🟢", "color": "#00b518", "accent": "#ffffff"},
    "Tecno":      {"emoji": "🔵", "color": "#0066cc", "accent": "#ffffff"},
    "Sony":       {"emoji": "⬛", "color": "#000000", "accent": "#ffffff"},
    "Motorola":   {"emoji": "Ⓜ️", "color": "#5c2d91", "accent": "#ffffff"},
    "Nokia":      {"emoji": "🔷", "color": "#124191", "accent": "#ffffff"},
    "LG":         {"emoji": "🔴", "color": "#a50034", "accent": "#ffffff"},
    "Asus":       {"emoji": "🔵", "color": "#00529b", "accent": "#ffffff"},
    "ZTE":        {"emoji": "🔷", "color": "#0068b7", "accent": "#ffffff"},
    "Meizu":      {"emoji": "🔵", "color": "#1e90ff", "accent": "#ffffff"},
    "Apple Vision Pro": {"emoji": "🥽", "color": "#333333", "accent": "#999999"},
    "Meta Quest":  {"emoji": "🥽", "color": "#0668E1", "accent": "#ffffff"},
}

MANUFACTURERS = {
    "Samsung":    ["Galaxy S24 Ultra", "Galaxy S24+", "Galaxy S24", "Galaxy S23 Ultra", "Galaxy S23",
                   "Galaxy S22", "Galaxy A54", "Galaxy A34", "Galaxy A14",
                   "Galaxy Tab S9", "Galaxy Tab S8", "Galaxy Tab A8",
                   "Galaxy Watch 6", "Galaxy Watch 5", "Galaxy Watch 4"],
    "Apple":      ["iPhone 15 Pro Max", "iPhone 15 Pro", "iPhone 15", "iPhone 14 Pro",
                   "iPhone 14", "iPhone 13", "iPhone 12",
                   "iPad Pro M2", "iPad Air M1", "iPad 10th",
                   "Apple Watch Series 9", "Apple Watch Ultra 2",
                   "Apple Vision Pro"],
    "Xiaomi":     ["Xiaomi 14 Pro", "Xiaomi 14", "Xiaomi 13 Pro", "Xiaomi 13",
                   "Redmi Note 13 Pro", "Redmi Note 12", "POCO X6 Pro", "POCO X5 Pro"],
    "Huawei":     ["P60 Pro", "P50 Pro", "Mate 60 Pro", "Mate 40 Pro", "Nova 10", "Nova 11"],
    "Oppo":       ["Find X7 Ultra", "Find X6 Pro", "Reno 10 Pro", "Reno 9", "A78"],
    "Vivo":       ["X100 Pro", "X90 Pro", "V29 Pro", "V27", "Y36"],
    "Realme":     ["GT 5 Pro", "GT Neo 5", "11 Pro+", "11 Pro", "C55"],
    "OnePlus":    ["12", "11", "Nord 3", "Nord CE 3", "Open"],
    "Google Pixel": ["Pixel 8 Pro", "Pixel 8", "Pixel 7a", "Pixel Fold"],
    "Honor":      ["Magic 6 Pro", "Magic 5 Pro", "X9b", "X8b"],
    "Infinix":    ["Note 30 Pro", "Note 12", "Hot 30i", "Zero 30"],
    "Tecno":      ["Phantom V Fold", "Camon 20 Pro", "Spark 20 Pro"],
    "Motorola":   ["Edge 40 Pro", "Edge 30", "Moto G84", "Moto G54"],
    "Nokia":      ["G42", "G22", "X30", "XR21"],
    "Sony":       ["Xperia 1 V", "Xperia 5 V", "Xperia 10 V"],
    "LG":         ["V60 ThinQ", "Wing", "Velvet"],
    "Asus":       ["ROG Phone 8", "Zenfone 10"],
    "ZTE":        ["Axon 40 Ultra", "Blade V50"],
    "Meizu":      ["21 Pro", "20 Pro"],
    "Wearables":  ["Apple Vision Pro", "Meta Quest 3", "Ray-Ban Meta",
                   "Xreal Air 2", "RayNeo Air 2"],
    "Qualcomm Generic": ["Snapdragon 8 Gen 3", "Snapdragon 8 Gen 2", "Snapdragon 778G"],
    "MediaTek Generic": ["Dimensity 9300", "Dimensity 9000", "Helio G99"],
}

# Sidebar navigation items
SIDEBAR_ITEMS = [
    ("🤖", "ai_tab", "AI Diagnostic"),
    ("📱", "vendor_tab", "Vendor Ops"),
    ("🏭", "brands_tab", "Brand Explorer"),
    ("⌚", "devices_tab", "Device Support"),
    ("⚡", "flash_tab", "Flash & ROM"),
    ("🧹", "format_tab", "Format & Update"),
    ("🔓", "frp_tab", "FRP & Accounts"),
    ("🔧", "repair_tab", "Repair"),
    ("💾", "recovery_tab", "Data Recovery"),
    ("🌐", "lang_tab", "Languages"),
    ("🔌", "usb_tab", "USB/ADB/FB"),
    ("🛡️", "security_tab", "Security"),
    ("💬", "chat_tab", "Live Chat"),
    ("🎬", "stream_tab", "Media Stream"),
    ("🛒", "store_tab", "E-Commerce"),
    ("⚙️", "settings_tab", "Settings"),
]


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


logger = logging.getLogger("AuraTool.UI")


# ═══════════════════════════════════════════════════════════════════════════
#  Main Application GUI
# ═══════════════════════════════════════════════════════════════════════════

class AuraToolUI:
    """Professional HD Desktop Application GUI with SVG Brand Logos & Full i18n."""

    def __init__(self, license_info: dict, driver_status: dict, factory_mgr: FactoryManager | None = None):
        self.root = tk.Tk()
        self.root.title("AuraTool-Suite — Universal Desktop Platform 2030")
        self.root.geometry("1400x950")
        self.root.minsize(1100, 750)

        # Apply dark theme
        self.root.configure(bg=Theme.BG_DARK)
        self._set_window_icon()

        self.license_info = license_info
        self.driver_status = driver_status
        self.license_mgr = LicenseManager()
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
        self.driver_mgr = DeviceDriverManager()
        self.factory_mgr = factory_mgr or FactoryManager()

        # Icon references (prevent GC)
        self._icon_refs = []
        self._brand_icon_refs = []

        self._apply_styles()
        self._build_ui()
        self._setup_logging()

    def _apply_styles(self):
        """Apply professional dark theme styling."""
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('.', background=Theme.BG_DARK, foreground=Theme.TEXT_WHITE, font=('Segoe UI', 10))
        style.configure('TFrame', background=Theme.BG_DARK)
        style.configure('TLabel', background=Theme.BG_DARK, foreground=Theme.TEXT_WHITE, font=('Segoe UI', 10))
        style.configure('TButton', background=Theme.BTN_PRIMARY, foreground=Theme.TEXT_WHITE,
                       font=('Segoe UI', 10, 'bold'), padding=(12, 6))
        style.map('TButton', background=[('active', Theme.ACCENT2)])

        style.configure('TNotebook', background=Theme.BG_DARK, borderwidth=0)
        style.configure('TNotebook.Tab', background=Theme.BG_MEDIUM, foreground=Theme.TEXT_LIGHT,
                       font=('Segoe UI', 10, 'bold'), padding=(16, 8))
        style.map('TNotebook.Tab',
                  background=[('selected', Theme.BG_LIGHT)],
                  foreground=[('selected', Theme.TEXT_WHITE)])

        style.configure('TLabelframe', background=Theme.BG_DARK, foreground=Theme.TEXT_LIGHT,
                       font=('Segoe UI', 10, 'bold'))
        style.configure('TLabelframe.Label', background=Theme.BG_DARK, foreground=Theme.TEXT_YELLOW,
                       font=('Segoe UI', 10, 'bold'))

        style.configure('TEntry', fieldbackground=Theme.BG_MEDIUM, foreground=Theme.TEXT_WHITE,
                       insertcolor=Theme.TEXT_WHITE, font=('Segoe UI', 10))
        style.configure('TCombobox', fieldbackground=Theme.BG_MEDIUM, foreground=Theme.TEXT_WHITE,
                       background=Theme.BG_LIGHT, font=('Segoe UI', 10))

        style.configure('Treeview', background=Theme.BG_MEDIUM, foreground=Theme.TEXT_WHITE,
                       fieldbackground=Theme.BG_MEDIUM, font=('Segoe UI', 9))
        style.configure('Treeview.Heading', background=Theme.BG_LIGHT, foreground=Theme.TEXT_YELLOW,
                       font=('Segoe UI', 9, 'bold'))

    def _setup_logging(self):
        handler = TextHandler(self.console)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S")
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)

    def _set_window_icon(self):
        try:
            if getattr(sys, '_MEIPASS', None):
                base = sys._MEIPASS
            else:
                base = os.path.dirname(os.path.abspath(__file__))
                base = os.path.dirname(base)

            for icon_file in ['assets/icon.ico', 'assets/icon.png']:
                icon_path = os.path.join(base, icon_file)
                if os.path.isfile(icon_path):
                    if icon_file.endswith('.ico'):
                        self.root.iconbitmap(icon_path)
                    else:
                        img = tk.PhotoImage(file=icon_path)
                        self.root.iconphoto(True, img)
                    return
        except Exception as e:
            logger.debug("Could not set window icon: %s", e)

    def _build_ui(self):
        """Build the complete UI layout with sidebar navigation."""
        # ═══════════════════════════════════════════════════════════════
        # TOP HEADER BAR
        # ═══════════════════════════════════════════════════════════════
        header = tk.Frame(self.root, bg=Theme.HEADER_BG, height=55)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # App Title + Logo
        title_frame = tk.Frame(header, bg=Theme.HEADER_BG)
        title_frame.pack(side=tk.LEFT, padx=15, pady=8)

        # App icon
        try:
            if getattr(sys, '_MEIPASS', None):
                icon_path = os.path.join(sys._MEIPASS, 'assets', 'icon.png')
            else:
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "icon.png")
            if os.path.exists(icon_path):
                app_icon = tk.PhotoImage(file=icon_path)
                app_icon = app_icon.subsample(2, 2)
                self._icon_refs.append(app_icon)
                tk.Label(title_frame, image=app_icon, bg=Theme.HEADER_BG).pack(side=tk.LEFT, padx=(0, 8))
        except Exception:
            pass

        self.title_lbl = tk.Label(title_frame,
            text=self.loc_mgr.get_string("title"),
            font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_WHITE, bg=Theme.HEADER_BG)
        self.title_lbl.pack(side=tk.LEFT)

        # License Info (Right side)
        hwid = self.license_info.get("hwid", "N/A")
        lic_status = "✅ ACTIVE" if self.license_info["is_active"] else "❌ INACTIVE"
        lic_color = Theme.TEXT_GREEN if self.license_info["is_active"] else Theme.TEXT_RED

        lic_frame = tk.Frame(header, bg=Theme.HEADER_BG)
        lic_frame.pack(side=tk.RIGHT, padx=15, pady=8)

        plat = "🐧 Linux" if platform.system() == "Linux" else "🪟 Windows"
        tk.Label(lic_frame, text=f"{plat} v2.0.0",
                font=('Segoe UI', 8), fg=Theme.TEXT_LIGHT, bg=Theme.HEADER_BG).pack(side=tk.RIGHT, padx=10)

        self.lic_lbl = tk.Label(lic_frame,
            text=f"{lic_status} | {self.license_info['tier']} ({self.license_info['days_remaining']}d) | HWID: {hwid}",
            font=('Consolas', 9), fg=lic_color, bg=Theme.HEADER_BG)
        self.lic_lbl.pack(side=tk.RIGHT)

        # ═══════════════════════════════════════════════════════════════
        # LICENSE ACTIVATION BAR
        # ═══════════════════════════════════════════════════════════════
        self.act_bar = tk.LabelFrame(self.root, text=self.loc_mgr.get_string("license_bar_lbl"),
                                     bg=Theme.BG_DARK, fg=Theme.TEXT_YELLOW,
                                     font=('Segoe UI', 9, 'bold'), bd=1, relief='groove')
        self.act_bar.pack(fill=tk.X, padx=10, pady=(5, 2))

        act_inner = tk.Frame(self.act_bar, bg=Theme.BG_DARK)
        act_inner.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(act_inner, text="🔑 Key:", font=('Segoe UI', 9),
                fg=Theme.TEXT_LIGHT, bg=Theme.BG_DARK).pack(side=tk.LEFT, padx=5)
        self.key_entry = tk.Entry(act_inner, width=36, bg=Theme.BG_MEDIUM, fg=Theme.TEXT_WHITE,
                                  insertbackground=Theme.TEXT_WHITE, font=('Consolas', 10), bd=1)
        self.key_entry.pack(side=tk.LEFT, padx=5)
        self.act_btn = tk.Button(act_inner, text=self.loc_mgr.get_string("activate_btn"),
                                bg=Theme.BTN_SUCCESS, fg=Theme.TEXT_WHITE,
                                font=('Segoe UI', 9, 'bold'), bd=0, padx=12, pady=4,
                                command=self._action_activate_key, cursor="hand2")
        self.act_btn.pack(side=tk.LEFT, padx=5)

        # ═══════════════════════════════════════════════════════════════
        # MAIN LAYOUT: SIDEBAR + CONTENT
        # ═══════════════════════════════════════════════════════════════
        main_frame = tk.Frame(self.root, bg=Theme.BG_DARK)
        main_frame.pack(expand=True, fill=tk.BOTH, padx=0, pady=0)

        # ─── SIDEBAR ────────────────────────────────────────────────────
        self.sidebar = tk.Frame(main_frame, bg=Theme.SIDEBAR_BG, width=180)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Sidebar header
        tk.Label(self.sidebar, text="🔧 Navigation", font=('Segoe UI', 10, 'bold'),
                fg=Theme.TEXT_YELLOW, bg=Theme.SIDEBAR_BG).pack(pady=(10, 5), padx=10, anchor=tk.W)

        tk.Frame(self.sidebar, bg=Theme.BORDER, height=1).pack(fill=tk.X, padx=10, pady=5)

        # Sidebar buttons
        self.sidebar_buttons = {}
        self._active_tab_idx = 0

        for idx, (icon, key, label) in enumerate(SIDEBAR_ITEMS):
            translated_label = self.loc_mgr.get_string(key)
            btn_frame = tk.Frame(self.sidebar, bg=Theme.SIDEBAR_BG, cursor="hand2")
            btn_frame.pack(fill=tk.X, padx=5, pady=1)

            icon_lbl = tk.Label(btn_frame, text=icon, font=('Segoe UI', 14),
                              fg=Theme.TEXT_WHITE, bg=Theme.SIDEBAR_BG, width=3)
            icon_lbl.pack(side=tk.LEFT, padx=(5, 2), pady=4)

            text_lbl = tk.Label(btn_frame, text=translated_label, font=('Segoe UI', 9),
                              fg=Theme.TEXT_LIGHT, bg=Theme.SIDEBAR_BG, anchor=tk.W)
            text_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5), pady=4)

            self.sidebar_buttons[key] = {"frame": btn_frame, "icon": icon_lbl, "text": text_lbl, "idx": idx}

            # Bind click events
            for widget in [btn_frame, icon_lbl, text_lbl]:
                widget.bind("<Button-1>", lambda e, i=idx: self._on_sidebar_click(i))
                widget.bind("<Enter>", lambda e, f=btn_frame: f.configure(bg=Theme.SIDEBAR_ACTIVE))
                widget.bind("<Leave>", lambda e, f=btn_frame, k=key: self._on_sidebar_leave(f, k))

        # Highlight first item
        self._highlight_sidebar(0)

        # Separator
        tk.Frame(self.sidebar, bg=Theme.BORDER, height=1).pack(fill=tk.X, padx=10, pady=5)

        # Brand logos in sidebar
        tk.Label(self.sidebar, text="📱 Brands", font=('Segoe UI', 9, 'bold'),
                fg=Theme.TEXT_YELLOW, bg=Theme.SIDEBAR_BG).pack(pady=(5, 3), padx=10, anchor=tk.W)

        brands_canvas = tk.Canvas(self.sidebar, bg=Theme.SIDEBAR_BG, highlightthickness=0, width=170)
        brands_scrollbar = tk.Scrollbar(self.sidebar, orient="vertical", command=brands_canvas.yview)
        brands_frame = tk.Frame(brands_canvas, bg=Theme.SIDEBAR_BG)

        brands_frame.bind("<Configure>", lambda e: brands_canvas.configure(scrollregion=brands_canvas.bbox("all")))
        brands_canvas.create_window((0, 0), window=brands_frame, anchor="nw")
        brands_canvas.configure(yscrollcommand=brands_scrollbar.set)

        # Add brand items to sidebar
        try:
            brand_gen = get_brand_icons() if HAS_BRAND_ICONS else None
        except Exception:
            brand_gen = None

        for brand_name, info in list(BRAND_LOGOS.items())[:12]:
            brand_frame = tk.Frame(brands_frame, bg=Theme.SIDEBAR_BG, cursor="hand2")
            brand_frame.pack(fill=tk.X, padx=5, pady=1)

            # Brand color dot
            dot = tk.Canvas(brand_frame, width=10, height=10, bg=Theme.SIDEBAR_BG, highlightthickness=0)
            dot.pack(side=tk.LEFT, padx=(8, 4), pady=3)
            dot.create_oval(1, 1, 9, 9, fill=info["color"], outline="")

            # Try to load brand icon
            if brand_gen:
                try:
                    icon_path = brand_gen.get_icon_path(brand_name, 16)
                    if icon_path and os.path.exists(icon_path):
                        pil_img = __import__("PIL.Image", fromlist=["Image"]).open(icon_path)
                        tk_img = __import__("PIL.ImageTk", fromlist=["ImageTk"]).PhotoImage(pil_img)
                        self._brand_icon_refs.append(tk_img)
                        tk.Label(brand_frame, image=tk_img, bg=Theme.SIDEBAR_BG).pack(side=tk.LEFT, padx=(0, 2), pady=2)
                except Exception:
                    pass

            tk.Label(brand_frame, text=brand_name, font=('Segoe UI', 8),
                    fg=Theme.TEXT_LIGHT, bg=Theme.SIDEBAR_BG, anchor=tk.W).pack(side=tk.LEFT, pady=3)

        brands_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 0))
        brands_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ─── CONTENT AREA ───────────────────────────────────────────────
        content_frame = tk.Frame(main_frame, bg=Theme.BG_DARK)
        content_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        # Notebook (Tabs)
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        # Tab 1: AI Diagnostic
        ai_tab = tk.Frame(self.notebook, bg=Theme.TAB_BG)
        self.notebook.add(ai_tab, text=self.loc_mgr.get_string("ai_tab"))
        self._build_ai_tab(ai_tab)

        # Tab 2: Vendor & Device Operations
        vendor_tab = tk.Frame(self.notebook, bg=Theme.TAB_BG)
        self.notebook.add(vendor_tab, text=self.loc_mgr.get_string("vendor_tab"))
        self._build_vendor_tab(vendor_tab)

        # Tab 3: Brand Explorer
        brands_tab = tk.Frame(self.notebook, bg=Theme.TAB_BG)
        self.notebook.add(brands_tab, text=self.loc_mgr.get_string("brands_tab"))
        self._build_brands_tab(brands_tab)

        # Tab 4: Device Support (All categories)
        devices_tab = tk.Frame(self.notebook, bg=Theme.TAB_BG)
        self.notebook.add(devices_tab, text=self.loc_mgr.get_string("devices_tab"))
        self._build_devices_tab(devices_tab)

        # Tab 5: Flashing & ROM Management
        flash_tab = tk.Frame(self.notebook, bg=Theme.TAB_BG)
        self.notebook.add(flash_tab, text=self.loc_mgr.get_string("flash_tab"))
        self._build_flash_tab(flash_tab)

        # Tab 6: Format & System Update
        format_tab = tk.Frame(self.notebook, bg=Theme.TAB_BG)
        self.notebook.add(format_tab, text=self.loc_mgr.get_string("format_tab"))
        self._build_format_tab(format_tab)

        # Tab 7: FRP Bypass & Account Repair
        frp_tab = tk.Frame(self.notebook, bg=Theme.TAB_BG)
        self.notebook.add(frp_tab, text=self.loc_mgr.get_string("frp_tab"))
        self._build_frp_tab(frp_tab)

        # Tab 8: Ultimate System Repair
        repair_tab = tk.Frame(self.notebook, bg=Theme.TAB_BG)
        self.notebook.add(repair_tab, text=self.loc_mgr.get_string("repair_tab"))
        self._build_repair_tab(repair_tab)

        # Tab 9: Data Recovery
        recovery_tab = tk.Frame(self.notebook, bg=Theme.TAB_BG)
        self.notebook.add(recovery_tab, text=self.loc_mgr.get_string("recovery_tab"))
        self._build_recovery_tab(recovery_tab)

        # Tab 10: Languages & Localization
        lang_tab = tk.Frame(self.notebook, bg=Theme.TAB_BG)
        self.notebook.add(lang_tab, text=self.loc_mgr.get_string("lang_tab"))
        self._build_lang_tab(lang_tab)

        # Tab 11: USB / ADB / Fastboot Manager
        usb_tab = tk.Frame(self.notebook, bg=Theme.TAB_BG)
        self.notebook.add(usb_tab, text=self.loc_mgr.get_string("usb_tab"))
        self._build_usb_tab(usb_tab)

        # Tab 12: Security & Protection
        security_tab = tk.Frame(self.notebook, bg=Theme.TAB_BG)
        self.notebook.add(security_tab, text=self.loc_mgr.get_string("security_tab"))
        self._build_security_tab(security_tab)

        # Tab 13: Live Chat
        chat_tab = tk.Frame(self.notebook, bg=Theme.TAB_BG)
        self.notebook.add(chat_tab, text=self.loc_mgr.get_string("chat_tab"))
        self._build_chat_tab(chat_tab)

        # Tab 14: Media Stream
        stream_tab = tk.Frame(self.notebook, bg=Theme.TAB_BG)
        self.notebook.add(stream_tab, text=self.loc_mgr.get_string("stream_tab"))
        self._build_stream_tab(stream_tab)

        # Tab 15: E-Commerce
        store_tab = tk.Frame(self.notebook, bg=Theme.TAB_BG)
        self.notebook.add(store_tab, text=self.loc_mgr.get_string("store_tab"))
        self._build_store_tab(store_tab)

        # Tab 16: Settings
        settings_tab = tk.Frame(self.notebook, bg=Theme.TAB_BG)
        self.notebook.add(settings_tab, text=self.loc_mgr.get_string("settings_tab"))
        self._build_settings_tab(settings_tab)

        # ─── BOTTOM CONSOLE LOG ─────────────────────────────────────────
        console_frame = tk.LabelFrame(content_frame,
            text=self.loc_mgr.get_string("console_title"),
            bg=Theme.BG_DARK, fg=Theme.TEXT_GREEN, font=('Segoe UI', 9, 'bold'), bd=1)
        console_frame.pack(fill=tk.X, padx=5, pady=(2, 5))

        self.console = scrolledtext.ScrolledText(console_frame, height=5, state='disabled',
            bg=Theme.CONSOLE_BG, fg=Theme.TEXT_GREEN, font=('Consolas', 9),
            insertbackground=Theme.TEXT_GREEN, bd=0, highlightthickness=0)
        self.console.pack(fill=tk.BOTH, padx=5, pady=5)

    # ─── Sidebar Navigation ─────────────────────────────────────────────

    def _on_sidebar_click(self, idx: int):
        """Handle sidebar button click."""
        self._highlight_sidebar(idx)
        if idx < len(self.notebook.tabs()):
            self.notebook.select(idx)

    def _on_sidebar_leave(self, frame, key):
        """Handle sidebar button leave."""
        idx = self.sidebar_buttons[key]["idx"]
        if idx != self._active_tab_idx:
            frame.configure(bg=Theme.SIDEBAR_BG)

    def _highlight_sidebar(self, idx: int):
        """Highlight the active sidebar item."""
        self._active_tab_idx = idx
        for key, info in self.sidebar_buttons.items():
            if info["idx"] == idx:
                info["frame"].configure(bg=Theme.SIDEBAR_ACTIVE)
                info["icon"].configure(fg=Theme.TEXT_YELLOW)
                info["text"].configure(fg=Theme.TEXT_WHITE, font=('Segoe UI', 9, 'bold'))
            else:
                info["frame"].configure(bg=Theme.SIDEBAR_BG)
                info["icon"].configure(fg=Theme.TEXT_WHITE)
                info["text"].configure(fg=Theme.TEXT_LIGHT, font=('Segoe UI', 9))

    # ─── Tab Builders ───────────────────────────────────────────────────

    def _build_ai_tab(self, parent):
        tk.Label(parent, text=self.loc_mgr.get_string("ai_header"),
                font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_YELLOW, bg=Theme.TAB_BG).pack(anchor=tk.W, pady=10, padx=10)

        # Brand logos strip with SVG/PNG icons
        brands_frame = tk.Frame(parent, bg=Theme.TAB_BG)
        brands_frame.pack(fill=tk.X, padx=10, pady=5)

        try:
            brand_gen = get_brand_icons() if HAS_BRAND_ICONS else None
        except Exception:
            brand_gen = None

        for brand_name, info in list(BRAND_LOGOS.items())[:14]:
            brand_def = BRAND_ICON_DEFS.get(brand_name, {}) if HAS_BRAND_ICONS else {}
            primary_color = brand_def.get("primary", info.get("color", "#333333"))

            btn_frame = tk.Frame(brands_frame, bg=primary_color, bd=0,
                                highlightbackground=primary_color, highlightthickness=1)
            btn_frame.pack(side=tk.LEFT, padx=2, pady=2)

            # Try to load generated icon
            if brand_gen:
                try:
                    icon_path = brand_gen.get_icon_path(brand_name, 24)
                    if icon_path and os.path.exists(icon_path):
                        pil_img = __import__("PIL.Image", fromlist=["Image"]).open(icon_path)
                        tk_img = __import__("PIL.ImageTk", fromlist=["ImageTk"]).PhotoImage(pil_img)
                        self._brand_icon_refs.append(tk_img)
                        icon_label = tk.Label(btn_frame, image=tk_img, bg=primary_color)
                        icon_label.pack(side=tk.LEFT, padx=(4, 2), pady=2)
                except Exception:
                    pass

            text_color = brand_def.get("text_color", info.get("accent", "#ffffff"))
            btn = tk.Button(btn_frame, text=brand_name,
                          bg=primary_color, fg=text_color,
                          font=('Segoe UI', 8, 'bold'), bd=0, padx=6, pady=3, cursor="hand2",
                          activebackground=primary_color, activeforeground=text_color)
            btn.pack(side=tk.LEFT, padx=(0, 4), pady=2)

        # AI Command area
        ai_frame = tk.Frame(parent, bg=Theme.BG_MEDIUM, bd=1, relief='groove')
        ai_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(ai_frame, text="🤖 " + self.loc_mgr.get_string("ai_command_label"),
                font=('Segoe UI', 10), fg=Theme.TEXT_LIGHT, bg=Theme.BG_MEDIUM).pack(anchor=tk.W, padx=10, pady=(10, 2))

        cmd_row = tk.Frame(ai_frame, bg=Theme.BG_MEDIUM)
        cmd_row.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.ai_cmd_entry = tk.Entry(cmd_row, width=60, bg=Theme.CONSOLE_BG, fg=Theme.TEXT_GREEN,
                                     insertbackground=Theme.TEXT_GREEN, font=('Consolas', 11), bd=1)
        self.ai_cmd_entry.pack(side=tk.LEFT, padx=(0, 8))
        self.ai_cmd_entry.insert(0, "Analyze log and bypass FRP lock")

        self.ai_btn = tk.Button(cmd_row, text=self.loc_mgr.get_string("run_ai"),
                               bg=Theme.BTN_PRIMARY, fg=Theme.TEXT_WHITE,
                               font=('Segoe UI', 10, 'bold'), bd=0, padx=16, pady=6,
                               command=self._action_run_ai, cursor="hand2")
        self.ai_btn.pack(side=tk.LEFT)

        # AI Response area
        self.ai_response = scrolledtext.ScrolledText(parent, height=12, state='disabled',
            bg=Theme.CONSOLE_BG, fg=Theme.TEXT_LIGHT, font=('Consolas', 10), bd=1)
        self.ai_response.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def _build_vendor_tab(self, parent):
        tk.Label(parent, text=self.loc_mgr.get_string("vendor_header"),
                font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_YELLOW, bg=Theme.TAB_BG).pack(anchor=tk.W, pady=10, padx=10)

        sel_frame = tk.Frame(parent, bg=Theme.BG_MEDIUM, bd=1, relief='groove')
        sel_frame.pack(fill=tk.X, padx=10, pady=5)

        row1 = tk.Frame(sel_frame, bg=Theme.BG_MEDIUM)
        row1.pack(fill=tk.X, padx=10, pady=8)

        # Brand icon next to manufacturer dropdown
        self._vendor_icon_label = tk.Label(row1, bg=Theme.BG_MEDIUM, width=3)
        self._vendor_icon_label.pack(side=tk.LEFT, padx=(0, 5))

        tk.Label(row1, text="🏭 " + self.loc_mgr.get_string("manufacturer"),
                font=('Segoe UI', 10), fg=Theme.TEXT_LIGHT, bg=Theme.BG_MEDIUM).pack(side=tk.LEFT, padx=5)
        self.vendor_cb = ttk.Combobox(row1, values=list(MANUFACTURERS.keys()), state="readonly", width=20)
        self.vendor_cb.pack(side=tk.LEFT, padx=10)
        self.vendor_cb.current(0)
        self.vendor_cb.bind("<<ComboboxSelected>>", self._on_vendor_change)

        # Brand info label
        self._brand_info_label = tk.Label(row1, text="", font=('Segoe UI', 9),
            fg=Theme.TEXT_LIGHT, bg=Theme.BG_MEDIUM)
        self._brand_info_label.pack(side=tk.LEFT, padx=10)

        row2 = tk.Frame(sel_frame, bg=Theme.BG_MEDIUM)
        row2.pack(fill=tk.X, padx=10, pady=8)
        tk.Label(row2, text="📱 " + self.loc_mgr.get_string("model"),
                font=('Segoe UI', 10), fg=Theme.TEXT_LIGHT, bg=Theme.BG_MEDIUM).pack(side=tk.LEFT, padx=5)
        self.model_cb = ttk.Combobox(row2, values=MANUFACTURERS["Samsung"], state="readonly", width=30)
        self.model_cb.pack(side=tk.LEFT, padx=10)
        self.model_cb.current(0)

        # Load initial brand icon
        self._update_vendor_brand_icon("Samsung")

        # Operations buttons
        ops_frame = tk.LabelFrame(parent, text=self.loc_mgr.get_string("operations"),
                                  bg=Theme.BG_DARK, fg=Theme.TEXT_YELLOW, font=('Segoe UI', 10, 'bold'))
        ops_frame.pack(fill=tk.X, padx=10, pady=10)

        btn_row = tk.Frame(ops_frame, bg=Theme.BG_DARK)
        btn_row.pack(fill=tk.X, padx=10, pady=10)

        buttons = [
            (self.loc_mgr.get_string("flash"), Theme.BTN_PRIMARY, self._action_flash),
            (self.loc_mgr.get_string("bypass_frp"), Theme.ACCENT2, self._action_bypass_frp),
            ("Backup EFS / NVRAM", Theme.BG_LIGHT, self._action_backup_efs),
            ("Deep Unbrick", Theme.TEXT_RED, self._action_unbrick),
        ]
        for text, color, cmd in buttons:
            tk.Button(btn_row, text=text, bg=color, fg=Theme.TEXT_WHITE,
                     font=('Segoe UI', 9, 'bold'), bd=0, padx=12, pady=6,
                     command=cmd, cursor="hand2").pack(side=tk.LEFT, padx=4)

    def _build_brands_tab(self, parent):
        """Build the Brand Explorer tab with SVG icons and brand info."""
        tk.Label(parent, text="🏭 " + self.loc_mgr.get_string("brands_tab"),
                font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_YELLOW, bg=Theme.TAB_BG).pack(anchor=tk.W, pady=10, padx=10)

        # Brand grid container
        grid_frame = tk.Frame(parent, bg=Theme.TAB_BG)
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Load brand icons
        try:
            brand_gen = get_brand_icons() if HAS_BRAND_ICONS else None
        except Exception:
            brand_gen = None

        try:
            svg_mgr = get_brand_svg_manager() if HAS_SVG else None
        except Exception:
            svg_mgr = None

        # Create brand cards in a grid layout
        cols = 4
        row_idx = 0
        col_idx = 0

        for brand_name, info in BRAND_LOGOS.items():
            # Get brand color and description
            brand_def = BRAND_ICON_DEFS.get(brand_name, {}) if HAS_BRAND_ICONS else {}
            primary_color = brand_def.get("primary", info.get("color", "#333333"))
            text_color = brand_def.get("text_color", info.get("accent", "#ffffff"))
            description = svg_mgr.get_brand_description(brand_name) if svg_mgr else ""

            # Create brand card
            card = tk.Frame(grid_frame, bg=Theme.BG_MEDIUM, bd=1, relief='groove', cursor="hand2")
            card.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky="nsew")
            grid_frame.columnconfigure(col_idx, weight=1)

            # Brand icon (larger size)
            icon_frame = tk.Frame(card, bg=primary_color, padx=8, pady=8)
            icon_frame.pack(fill=tk.X, padx=5, pady=(5, 2))

            # Try to load SVG/PNG icon
            if brand_gen:
                try:
                    icon_path = brand_gen.get_icon_path(brand_name, 48)
                    if icon_path and os.path.exists(icon_path):
                        pil_img = __import__("PIL.Image", fromlist=["Image"]).open(icon_path)
                        tk_img = __import__("PIL.ImageTk", fromlist=["ImageTk"]).PhotoImage(pil_img)
                        self._brand_icon_refs.append(tk_img)
                        tk.Label(icon_frame, image=tk_img, bg=primary_color).pack(pady=5)
                    else:
                        tk.Label(icon_frame, text=info.get("emoji", "📱"), font=('Segoe UI', 24),
                                bg=primary_color, fg=text_color).pack(pady=5)
                except Exception:
                    tk.Label(icon_frame, text=info.get("emoji", "📱"), font=('Segoe UI', 24),
                            bg=primary_color, fg=text_color).pack(pady=5)
            else:
                tk.Label(icon_frame, text=info.get("emoji", "📱"), font=('Segoe UI', 24),
                        bg=primary_color, fg=text_color).pack(pady=5)

            # Brand name
            tk.Label(card, text=brand_name, font=('Segoe UI', 11, 'bold'),
                    fg=Theme.TEXT_WHITE, bg=Theme.BG_MEDIUM).pack(pady=(8, 2))

            # Description
            tk.Label(card, text=description, font=('Segoe UI', 8),
                    fg=Theme.TEXT_LIGHT, bg=Theme.BG_MEDIUM).pack(pady=(0, 5))

            # Color swatch
            swatch_frame = tk.Frame(card, bg=Theme.BG_MEDIUM)
            swatch_frame.pack(pady=(0, 5))
            tk.Canvas(swatch_frame, width=60, height=8, bg=primary_color,
                     highlightthickness=0).pack()
            tk.Label(swatch_frame, text=primary_color, font=('Consolas', 7),
                    fg=Theme.TEXT_LIGHT, bg=Theme.BG_MEDIUM).pack()

            # SVG indicator
            if svg_mgr:
                svg_path = svg_mgr.get_svg_path(brand_name)
                if svg_path and os.path.exists(svg_path):
                    tk.Label(card, text="✅ SVG", font=('Segoe UI', 7),
                            fg=Theme.TEXT_GREEN, bg=Theme.BG_MEDIUM).pack(pady=(0, 3))

            col_idx += 1
            if col_idx >= cols:
                col_idx = 0
                row_idx += 1

        # Make all columns expand equally
        for i in range(cols):
            grid_frame.columnconfigure(i, weight=1)

    def _build_flash_tab(self, parent):
        tk.Label(parent, text=self.loc_mgr.get_string("flash_header"),
                font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_YELLOW, bg=Theme.TAB_BG).pack(anchor=tk.W, pady=10, padx=10)

        fmt_frame = tk.LabelFrame(parent, text=self.loc_mgr.get_string("supported_formats"),
                                  bg=Theme.BG_DARK, fg=Theme.TEXT_LIGHT, font=('Segoe UI', 9))
        fmt_frame.pack(fill=tk.X, padx=10, pady=5)

        formats = [
            ("📦 OTA payload.bin", "Android OTA Full Image Package"),
            ("📱 Samsung Odin (.tar/.md5)", "Samsung Firmware Archive"),
            ("🔧 MediaTek Scatter", "MTK Scatter Configuration File"),
            ("⚡ Qualcomm EDL Firehose", "Qualcomm 9008 Raw Program"),
            ("🍎 Apple IPSW", "iOS / iPadOS Firmware Package"),
            ("💾 Super.img (Dynamic)", "Android Dynamic Partition Image"),
        ]
        for icon_name, desc in formats:
            row = tk.Frame(fmt_frame, bg=Theme.BG_DARK)
            row.pack(fill=tk.X, padx=10, pady=3)
            tk.Label(row, text=icon_name, font=('Segoe UI', 9, 'bold'),
                    fg=Theme.TEXT_WHITE, bg=Theme.BG_DARK).pack(side=tk.LEFT)
            tk.Label(row, text=desc, font=('Segoe UI', 8),
                    fg=Theme.TEXT_LIGHT, bg=Theme.BG_DARK).pack(side=tk.LEFT, padx=10)

        btn_frame = tk.Frame(parent, bg=Theme.TAB_BG)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(btn_frame, text="🚀 " + self.loc_mgr.get_string("flash"),
                 bg=Theme.BTN_PRIMARY, fg=Theme.TEXT_WHITE,
                 font=('Segoe UI', 10, 'bold'), bd=0, padx=20, pady=8,
                 command=self._action_flash, cursor="hand2").pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="🧹 " + self.loc_mgr.get_string("format_device"),
                 bg=Theme.TEXT_RED, fg=Theme.TEXT_WHITE,
                 font=('Segoe UI', 10, 'bold'), bd=0, padx=20, pady=8,
                 command=self._action_format, cursor="hand2").pack(side=tk.LEFT, padx=5)

    def _build_repair_tab(self, parent):
        tk.Label(parent, text=self.loc_mgr.get_string("repair_header"),
                font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_YELLOW, bg=Theme.TAB_BG).pack(anchor=tk.W, pady=10, padx=10)

        btn_frame = tk.Frame(parent, bg=Theme.TAB_BG)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        repairs = [
            ("🔄 Repair Bootloop & Crash", Theme.BTN_PRIMARY, self._action_fix_bootloop),
            ("🛡️ Scan & Remove Viruses", Theme.ACCENT2, self._action_clean_virus),
            ("👆 Recalibrate Biometrics", Theme.BTN_SUCCESS, self._action_recalib_bio),
            ("📊 Storage Health Check", Theme.BG_LIGHT, self._action_storage_check),
        ]
        for text, color, cmd in repairs:
            tk.Button(btn_frame, text=text, bg=color, fg=Theme.TEXT_WHITE,
                     font=('Segoe UI', 10, 'bold'), bd=0, padx=16, pady=8,
                     command=cmd, cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)

    def _build_recovery_tab(self, parent):
        tk.Label(parent, text=self.loc_mgr.get_string("recovery_header"),
                font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_YELLOW, bg=Theme.TAB_BG).pack(anchor=tk.W, pady=10, padx=10)

        self.scan_btn = tk.Button(parent, text="🔍 " + self.loc_mgr.get_string("start_scan"),
                                 bg=Theme.BTN_PRIMARY, fg=Theme.TEXT_WHITE,
                                 font=('Segoe UI', 11, 'bold'), bd=0, padx=24, pady=10,
                                 command=self._action_deep_scan, cursor="hand2")
        self.scan_btn.pack(anchor=tk.W, padx=10, pady=10)

    def _build_usb_tab(self, parent):
        tk.Label(parent, text=self.loc_mgr.get_string("usb_header"),
                font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_YELLOW, bg=Theme.TAB_BG).pack(anchor=tk.W, pady=10, padx=10)

        proto_frame = tk.LabelFrame(parent, text=self.loc_mgr.get_string("protocols"),
                                    bg=Theme.BG_DARK, fg=Theme.TEXT_LIGHT, font=('Segoe UI', 9, 'bold'))
        proto_frame.pack(fill=tk.X, padx=10, pady=5)

        protocols = [
            ("ADB", "Android Debug Bridge — USB Communication"),
            ("Fastboot", "Fastboot Protocol — Bootloader Operations"),
            ("EDL 9008", "Qualcomm Emergency Download Mode"),
            ("MTK BROM", "MediaTek Boot ROM / Meta Mode"),
            ("Samsung ODIN", "Samsung Download Mode"),
            ("Apple DFU", "Apple Device Firmware Upgrade Mode"),
            ("Sideload", "Recovery Sideload Mode"),
        ]
        for proto, desc in protocols:
            row = tk.Frame(proto_frame, bg=Theme.BG_DARK)
            row.pack(fill=tk.X, padx=10, pady=3)
            tk.Label(row, text=f"✅ {proto}", font=('Segoe UI', 9, 'bold'),
                    fg=Theme.TEXT_GREEN, bg=Theme.BG_DARK, width=18, anchor='w').pack(side=tk.LEFT)
            tk.Label(row, text=desc, font=('Segoe UI', 8),
                    fg=Theme.TEXT_LIGHT, bg=Theme.BG_DARK).pack(side=tk.LEFT, padx=10)

        btn_frame = tk.Frame(parent, bg=Theme.TAB_BG)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(btn_frame, text="🔌 " + self.loc_mgr.get_string("detect_devices"),
                 bg=Theme.BTN_PRIMARY, fg=Theme.TEXT_WHITE,
                 font=('Segoe UI', 10, 'bold'), bd=0, padx=16, pady=8,
                 command=self._action_detect_devices, cursor="hand2").pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="🔧 " + self.loc_mgr.get_string("install_drivers"),
                 bg=Theme.BTN_SECONDARY, fg=Theme.TEXT_WHITE,
                 font=('Segoe UI', 10, 'bold'), bd=0, padx=16, pady=8,
                 command=self._action_install_drivers, cursor="hand2").pack(side=tk.LEFT, padx=5)

    def _build_chat_tab(self, parent):
        tk.Label(parent, text=self.loc_mgr.get_string("chat_header"),
                font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_YELLOW, bg=Theme.TAB_BG).pack(anchor=tk.W, pady=10, padx=10)

        self.chat_txt = scrolledtext.ScrolledText(parent, height=12, state="disabled",
            bg=Theme.CONSOLE_BG, fg=Theme.TEXT_LIGHT, font=('Consolas', 10), bd=1)
        self.chat_txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        input_f = tk.Frame(parent, bg=Theme.TAB_BG)
        input_f.pack(fill=tk.X, padx=10, pady=5)
        self.chat_entry = tk.Entry(input_f, width=60, bg=Theme.BG_MEDIUM, fg=Theme.TEXT_WHITE,
                                  insertbackground=Theme.TEXT_WHITE, font=('Segoe UI', 10), bd=1)
        self.chat_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(input_f, text="📤 Send", bg=Theme.BTN_PRIMARY, fg=Theme.TEXT_WHITE,
                 font=('Segoe UI', 9, 'bold'), bd=0, padx=12,
                 command=self._action_send_chat, cursor="hand2").pack(side=tk.LEFT, padx=5)

    def _build_stream_tab(self, parent):
        tk.Label(parent, text=self.loc_mgr.get_string("stream_header"),
                font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_YELLOW, bg=Theme.TAB_BG).pack(anchor=tk.W, pady=10, padx=10)

        for vid in self.media_stream.list_streams():
            row = tk.Frame(parent, bg=Theme.BG_MEDIUM, bd=1, relief='groove')
            row.pack(fill=tk.X, padx=10, pady=3)
            tk.Label(row, text=f"🎬 [{vid['category']}] {vid['title']} ({vid['duration']})",
                    font=('Segoe UI', 9), fg=Theme.TEXT_LIGHT, bg=Theme.BG_MEDIUM).pack(side=tk.LEFT, padx=10, pady=5)
            tk.Button(row, text="▶ Play", bg=Theme.BTN_PRIMARY, fg=Theme.TEXT_WHITE,
                     font=('Segoe UI', 8, 'bold'), bd=0, padx=10,
                     command=lambda v=vid['id']: self._action_play_stream(v), cursor="hand2").pack(side=tk.RIGHT, padx=10)

    def _build_store_tab(self, parent):
        tk.Label(parent, text=self.loc_mgr.get_string("store_header"),
                font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_YELLOW, bg=Theme.TAB_BG).pack(anchor=tk.W, pady=10, padx=10)

        cols = ("ID", "Name", "Category", "Price", "Stock")
        self.store_tree = ttk.Treeview(parent, columns=cols, show="headings", height=8)
        for c in cols:
            self.store_tree.heading(c, text=c)
            self.store_tree.column(c, width=120 if c != "Name" else 260)
        self.store_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        for item in self.ecommerce_mgr.get_catalogue():
            self.store_tree.insert("", tk.END, values=(
                item["id"], item["name"], item["category"],
                f"${item['price']:.2f}", item["stock"]))

        tk.Button(parent, text="🛒 " + self.loc_mgr.get_string("checkout"),
                 bg=Theme.BTN_SUCCESS, fg=Theme.TEXT_WHITE,
                 font=('Segoe UI', 10, 'bold'), bd=0, padx=20, pady=8,
                 command=self._action_checkout, cursor="hand2").pack(anchor=tk.W, padx=10, pady=10)

    def _build_devices_tab(self, parent):
        """Build Device Support tab showing all supported device categories."""
        tk.Label(parent, text="⌚ " + self.loc_mgr.get_string("devices_tab"),
                font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_YELLOW, bg=Theme.TAB_BG).pack(anchor=tk.W, pady=10, padx=10)

        # Device categories overview
        cats_frame = tk.Frame(parent, bg=Theme.TAB_BG)
        cats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        categories = [
            ("📱", "Smartphones", "Android & iOS phones from all manufacturers", Theme.BTN_PRIMARY),
            ("📋", "Tablets", "Android tablets & iPad devices", Theme.ACCENT2),
            ("🍎", "iPads", "Apple iPad (all models 2010–2024)", Theme.BG_LIGHT),
            ("⌚", "Smartwatches", "WearOS, watchOS, proprietary smartwatches", Theme.BTN_SUCCESS),
            ("🥽", "Smart Glasses", "Meta, Apple Vision Pro, XREAL, RayNeo", Theme.TEXT_RED),
            ("🕶️", "AR/VR Headsets", "Meta Quest, PSVR2, HTC Vive, Pico", "#6a1b9a"),
        ]

        for icon, name, desc, color in categories:
            card = tk.Frame(cats_frame, bg=Theme.BG_MEDIUM, bd=1, relief='groove')
            card.pack(fill=tk.X, padx=5, pady=3)
            icon_lbl = tk.Label(card, text=icon, font=('Segoe UI', 20), bg=color, fg=Theme.TEXT_WHITE, padx=10, pady=5)
            icon_lbl.pack(side=tk.LEFT, padx=(5, 10))
            info_frame = tk.Frame(card, bg=Theme.BG_MEDIUM)
            info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=5)
            tk.Label(info_frame, text=name, font=('Segoe UI', 11, 'bold'), fg=Theme.TEXT_WHITE, bg=Theme.BG_MEDIUM).pack(anchor=tk.W)
            tk.Label(info_frame, text=desc, font=('Segoe UI', 9), fg=Theme.TEXT_LIGHT, bg=Theme.BG_MEDIUM).pack(anchor=tk.W)

        # Year range info
        tk.Label(parent, text="📅 Supported Years: 2002 – 2030 | 🔧 Chipsets: Qualcomm, MediaTek, Exynos, Kirin, Apple Silicon, Unisoc",
                font=('Segoe UI', 9), fg=Theme.TEXT_LIGHT, bg=Theme.TAB_BG).pack(anchor=tk.W, padx=10, pady=5)

    def _build_format_tab(self, parent):
        """Build Format & System Update tab."""
        tk.Label(parent, text="🧹 Format & System Update",
                font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_YELLOW, bg=Theme.TAB_BG).pack(anchor=tk.W, pady=10, padx=10)

        # Format options
        fmt_frame = tk.LabelFrame(parent, text="Format Operations",
                                  bg=Theme.BG_DARK, fg=Theme.TEXT_LIGHT, font=('Segoe UI', 9, 'bold'))
        fmt_frame.pack(fill=tk.X, padx=10, pady=5)

        fmt_buttons = [
            ("🧹 Full Factory Reset", "Complete device wipe including all data", Theme.TEXT_RED, self._action_format),
            ("📂 Format Data Only", "Wipe user data while keeping system", Theme.BTN_PRIMARY, self._action_format),
            ("🗑️ Wipe Cache Partition", "Clear cache without affecting data", Theme.ACCENT2, self._action_wipe_cache),
            ("🔄 System Update", "Install available system updates", Theme.BTN_SUCCESS, self._action_system_update),
            ("💾 EFS/NVRAM Backup", "Backup radio calibration before format", Theme.BG_LIGHT, self._action_backup_efs),
            ("↩️ EFS/NVRAM Restore", "Restore radio calibration after format", "#00838f", self._action_restore_efs),
        ]
        for text, desc, color, cmd in fmt_buttons:
            row = tk.Frame(fmt_frame, bg=Theme.BG_DARK)
            row.pack(fill=tk.X, padx=10, pady=2)
            tk.Button(row, text=text, bg=color, fg=Theme.TEXT_WHITE,
                     font=('Segoe UI', 9, 'bold'), bd=0, padx=10, pady=4,
                     command=cmd, cursor="hand2").pack(side=tk.LEFT, padx=2)
            tk.Label(row, text=desc, font=('Segoe UI', 8), fg=Theme.TEXT_LIGHT, bg=Theme.BG_DARK).pack(side=tk.LEFT, padx=5)

    def _build_frp_tab(self, parent):
        """Build FRP Bypass & Account Repair tab."""
        tk.Label(parent, text="🔓 FRP Bypass & Account Repair",
                font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_YELLOW, bg=Theme.TAB_BG).pack(anchor=tk.W, pady=10, padx=10)

        # Brand selection
        sel_frame = tk.Frame(parent, bg=Theme.BG_MEDIUM, bd=1, relief='groove')
        sel_frame.pack(fill=tk.X, padx=10, pady=5)

        row1 = tk.Frame(sel_frame, bg=Theme.BG_MEDIUM)
        row1.pack(fill=tk.X, padx=10, pady=8)

        tk.Label(row1, text="🏭 Brand:", font=('Segoe UI', 10), fg=Theme.TEXT_LIGHT, bg=Theme.BG_MEDIUM).pack(side=tk.LEFT, padx=5)
        self.frp_brand_cb = ttk.Combobox(row1, values=["Samsung", "Google Pixel", "Xiaomi", "Huawei", "OPPO", "Realme", "Vivo", "OnePlus", "Motorola", "Nokia", "Sony", "Apple"], state="readonly", width=20)
        self.frp_brand_cb.pack(side=tk.LEFT, padx=10)
        self.frp_brand_cb.current(0)

        tk.Label(row1, text="🔒 Lock Type:", font=('Segoe UI', 10), fg=Theme.TEXT_LIGHT, bg=Theme.BG_MEDIUM).pack(side=tk.LEFT, padx=5)
        self.frp_lock_cb = ttk.Combobox(row1, values=["FRP (Google)", "Samsung Account", "Xiaomi Mi Account", "Huawei ID", "OPPO Account", "Vivo Account", "Pattern/PIN/Password", "Screen Lock", "Email Account"], state="readonly", width=22)
        self.frp_lock_cb.pack(side=tk.LEFT, padx=10)
        self.frp_lock_cb.current(0)

        # FRP operations
        ops_frame = tk.Frame(parent, bg=Theme.TAB_BG)
        ops_frame.pack(fill=tk.X, padx=10, pady=10)

        frp_buttons = [
            ("🔓 Bypass FRP Lock", "Remove Google/manufacturer FRP protection", Theme.BTN_PRIMARY, self._action_bypass_frp),
            ("📧 Bypass Email Account", "Clear email account sync after format", Theme.ACCENT2, self._action_bypass_email),
            ("🔑 Remove Screen Lock", "Remove Pattern/PIN/Password lock", Theme.BTN_SUCCESS, self._action_remove_screen_lock),
            ("📊 Account Diagnostics", "Check account and security status", Theme.BG_LIGHT, self._action_account_diagnostics),
            ("🔧 Restore EFS/NVRAM", "Restore radio calibration partitions", "#00838f", self._action_restore_efs),
            ("📡 Network Repair", "Repair network calibration", "#e65100", self._action_network_repair),
        ]
        for text, desc, color, cmd in frp_buttons:
            row = tk.Frame(ops_frame, bg=Theme.TAB_BG)
            row.pack(fill=tk.X, padx=5, pady=2)
            tk.Button(row, text=text, bg=color, fg=Theme.TEXT_WHITE,
                     font=('Segoe UI', 9, 'bold'), bd=0, padx=10, pady=4,
                     command=cmd, cursor="hand2").pack(side=tk.LEFT, padx=2)
            tk.Label(row, text=desc, font=('Segoe UI', 8), fg=Theme.TEXT_LIGHT, bg=Theme.TAB_BG).pack(side=tk.LEFT, padx=5)

        # Info
        info_frame = tk.Frame(parent, bg=Theme.BG_MEDIUM, bd=1, relief='groove')
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(info_frame, text="ℹ️ Supported: Google FRP, Samsung Knox, Xiaomi Mi Cloud, Huawei ID, OPPO/Vivo accounts, Apple Activation Lock (guidance only), Pattern/PIN/Password removal",
                font=('Segoe UI', 9), fg=Theme.TEXT_LIGHT, bg=Theme.BG_MEDIUM, wraplength=900).pack(padx=10, pady=5)

    def _build_lang_tab(self, parent):
        """Build Languages & Localization tab."""
        tk.Label(parent, text="🌐 Languages & Localization",
                font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_YELLOW, bg=Theme.TAB_BG).pack(anchor=tk.W, pady=10, padx=10)

        # Language selection
        lang_frame = tk.LabelFrame(parent, text="Select Interface Language",
                                   bg=Theme.BG_DARK, fg=Theme.TEXT_LIGHT, font=('Segoe UI', 9, 'bold'))
        lang_frame.pack(fill=tk.X, padx=10, pady=5)

        self.lang_cb2 = ttk.Combobox(lang_frame,
            values=list(LocalizationManager.SUPPORTED_LANGUAGES.values()), state="readonly", width=35)
        self.lang_cb2.pack(side=tk.LEFT, padx=10, pady=8)
        self.lang_cb2.current(0)

        tk.Button(lang_frame, text="Apply Language",
                 bg=Theme.BTN_PRIMARY, fg=Theme.TEXT_WHITE,
                 font=('Segoe UI', 9, 'bold'), bd=0, padx=12,
                 command=self._action_change_lang, cursor="hand2").pack(side=tk.LEFT, padx=5)

        # RTL support info
        rtl_frame = tk.LabelFrame(parent, text="RTL (Right-to-Left) Support",
                                  bg=Theme.BG_DARK, fg=Theme.TEXT_LIGHT, font=('Segoe UI', 9, 'bold'))
        rtl_frame.pack(fill=tk.X, padx=10, pady=5)

        rtl_langs = "Arabic (العربية), Persian (فارسی), Urdu (اردو), Hebrew (עברית) — Full RTL layout with Arabic character reshaping"
        tk.Label(rtl_frame, text=rtl_langs, font=('Segoe UI', 9), fg=Theme.TEXT_GREEN, bg=Theme.BG_DARK, wraplength=900).pack(padx=10, pady=5)

        # Language coverage
        tk.Label(parent, text=f"📋 {len(LocalizationManager.SUPPORTED_LANGUAGES)} languages supported with full UI translations and log messages",
                font=('Segoe UI', 9), fg=Theme.TEXT_LIGHT, bg=Theme.TAB_BG).pack(anchor=tk.W, padx=10, pady=5)

    def _build_security_tab(self, parent):
        """Build Security & Protection tab."""
        tk.Label(parent, text="🛡️ Security & Anti-Reverse Engineering",
                font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_YELLOW, bg=Theme.TAB_BG).pack(anchor=tk.W, pady=10, padx=10)

        # Protection status
        sec_mgr = SecurityManager()
        protection = sec_mgr.get_protection_status()

        status_frame = tk.LabelFrame(parent, text="Protection Status",
                                     bg=Theme.BG_DARK, fg=Theme.TEXT_LIGHT, font=('Segoe UI', 9, 'bold'))
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        items = [
            ("🛡️ Anti-Reverse Engineering", "ACTIVE" if protection["protection_active"] else "INACTIVE", Theme.TEXT_GREEN if protection["protection_active"] else Theme.TEXT_RED),
            ("🔍 Debugger Detection", "CLEAN" if not protection["debugger_detected"] else "DETECTED", Theme.TEXT_GREEN if not protection["debugger_detected"] else Theme.TEXT_RED),
            ("💻 VM Detection", "CLEAN" if not protection["vm_detected"] else "VM DETECTED", Theme.TEXT_GREEN if not protection["vm_detected"] else Theme.TEXT_YELLOW),
            ("🔐 Code Integrity", "VERIFIED" if protection["code_integrity"] else "FAILED", Theme.TEXT_GREEN if protection["code_integrity"] else Theme.TEXT_RED),
            ("🔒 License Protection", "AES + HMAC Encrypted", Theme.TEXT_GREEN),
            ("🗝️ Key Obfuscation", "XOR Stream Cipher Active", Theme.TEXT_GREEN),
        ]
        for label, value, color in items:
            row = tk.Frame(status_frame, bg=Theme.BG_DARK)
            row.pack(fill=tk.X, padx=10, pady=2)
            tk.Label(row, text=label, font=('Segoe UI', 9, 'bold'), fg=Theme.TEXT_WHITE, bg=Theme.BG_DARK, width=28, anchor='w').pack(side=tk.LEFT)
            tk.Label(row, text=value, font=('Consolas', 9), fg=color, bg=Theme.BG_DARK).pack(side=tk.LEFT, padx=5)

        # Security features
        feat_frame = tk.LabelFrame(parent, text="Security Features",
                                   bg=Theme.BG_DARK, fg=Theme.TEXT_LIGHT, font=('Segoe UI', 9, 'bold'))
        feat_frame.pack(fill=tk.X, padx=10, pady=10)

        features = [
            "✅ HWID-bound license encryption",
            "✅ System clock tamper detection",
            "✅ Encrypted license file (AES + HMAC)",
            "✅ Anti-debugger protection",
            "✅ Virtual machine detection",
            "✅ Code integrity verification",
            "✅ Secure data wipe (3-pass overwrite)",
            "✅ Storage health guardian (UFS/eMMC)",
            "✅ Auto-shutdown on license expiry",
        ]
        for feat in features:
            tk.Label(feat_frame, text=feat, font=('Segoe UI', 9), fg=Theme.TEXT_GREEN, bg=Theme.BG_DARK).pack(anchor=tk.W, padx=10, pady=1)

    def _build_settings_tab(self, parent):
        tk.Label(parent, text=self.loc_mgr.get_string("settings_header"),
                font=('Segoe UI', 13, 'bold'), fg=Theme.TEXT_YELLOW, bg=Theme.TAB_BG).pack(anchor=tk.W, pady=10, padx=10)

        lang_frame = tk.LabelFrame(parent, text=self.loc_mgr.get_string("language_label"),
                                   bg=Theme.BG_DARK, fg=Theme.TEXT_LIGHT, font=('Segoe UI', 9, 'bold'))
        lang_frame.pack(fill=tk.X, padx=10, pady=5)

        self.lang_cb = ttk.Combobox(lang_frame,
            values=list(LocalizationManager.SUPPORTED_LANGUAGES.values()), state="readonly", width=30)
        self.lang_cb.pack(side=tk.LEFT, padx=10, pady=8)
        self.lang_cb.current(0)

        tk.Button(lang_frame, text=self.loc_mgr.get_string("apply_lang"),
                 bg=Theme.BTN_PRIMARY, fg=Theme.TEXT_WHITE,
                 font=('Segoe UI', 9, 'bold'), bd=0, padx=12,
                 command=self._action_change_lang, cursor="hand2").pack(side=tk.LEFT, padx=5)

        driver_frame = tk.LabelFrame(parent, text=self.loc_mgr.get_string("driver_mgmt"),
                                     bg=Theme.BG_DARK, fg=Theme.TEXT_LIGHT, font=('Segoe UI', 9, 'bold'))
        driver_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(driver_frame, text="🔌 " + self.loc_mgr.get_string("install_drivers"),
                 bg=Theme.BTN_SECONDARY, fg=Theme.TEXT_WHITE,
                 font=('Segoe UI', 9, 'bold'), bd=0, padx=12,
                 command=self._action_install_drivers, cursor="hand2").pack(anchor=tk.W, padx=10, pady=8)

        # Version info
        tk.Label(parent, text="AuraTool-Suite v3.0.0 | Universal Desktop Platform 2030",
                font=('Segoe UI', 9), fg=Theme.TEXT_LIGHT, bg=Theme.TAB_BG).pack(anchor=tk.W, padx=10, pady=10)
        tk.Label(parent, text="© 2024-2030 AuraTool-Suite. All rights reserved.",
                font=('Segoe UI', 8), fg=Theme.TEXT_LIGHT, bg=Theme.TAB_BG).pack(anchor=tk.W, padx=10)

    # ─── Actions ────────────────────────────────────────────────────────

    def _on_vendor_change(self, event=None):
        vendor = self.vendor_cb.get()
        if vendor in MANUFACTURERS:
            self.model_cb['values'] = MANUFACTURERS[vendor]
            self.model_cb.current(0)
            self._update_vendor_brand_icon(vendor)

    def _update_vendor_brand_icon(self, brand_name: str):
        """Update the brand icon displayed next to the manufacturer dropdown."""
        try:
            brand_gen = get_brand_icons() if HAS_BRAND_ICONS else None
            if brand_gen:
                icon_path = brand_gen.get_icon_path(brand_name, 40)
                if icon_path and os.path.exists(icon_path):
                    pil_img = __import__("PIL.Image", fromlist=["Image"]).open(icon_path)
                    tk_img = __import__("PIL.ImageTk", fromlist=["ImageTk"]).PhotoImage(pil_img)
                    self._brand_icon_refs.append(tk_img)
                    self._vendor_icon_label.config(image=tk_img, text="")

            brand_def = BRAND_ICON_DEFS.get(brand_name, {}) if HAS_BRAND_ICONS else {}
            abbr = brand_def.get("abbr", brand_name[:3])
            style = brand_def.get("style", "standard")
            primary = brand_def.get("primary", BRAND_LOGOS.get(brand_name, {}).get("color", "#333"))

            # Check SVG availability
            svg_status = ""
            if HAS_SVG:
                try:
                    svg_mgr = get_brand_svg_manager()
                    svg_path = svg_mgr.get_svg_path(brand_name)
                    if svg_path and os.path.exists(svg_path):
                        svg_status = " | ✅ SVG"
                except Exception:
                    pass

            self._brand_info_label.config(text=f"[{abbr}] • {style}{svg_status}")
        except Exception as e:
            logging.debug(f"Could not update brand icon: {e}")

    def _action_activate_key(self):
        key = self.key_entry.get().strip()
        if not key:
            messagebox.showwarning("Activation", "Please enter a license key.")
            return
        if self.license_mgr.activate_key(key):
            new_status = self.license_mgr.check_license_status()
            self.license_info = new_status
            lic_txt = f"✅ ACTIVE | {new_status['tier']} ({new_status['days_remaining']}d) | HWID: {new_status['hwid']}"
            self.lic_lbl.config(text=lic_txt, fg=Theme.TEXT_GREEN)
            messagebox.showinfo("Success", f"License activated!\nTier: {new_status['tier']}\nValid: {new_status['days_remaining']} days.")
        else:
            messagebox.showerror("Failed", "Invalid key or HWID mismatch.")

    def _action_run_ai(self):
        cmd = self.ai_cmd_entry.get().strip()
        if not cmd:
            return
        res = self.ai_assistant.process_voice_or_text_command(cmd)
        self.ai_response.configure(state='normal')
        self.ai_response.insert(tk.END, f"[AI] {res['message']}\n")
        self.ai_response.configure(state='disabled')
        logging.info(f"Aura-AI: {res['message']}")

    def _action_flash(self):
        m = self.model_cb.get()
        logging.info(self.loc_mgr.get_arabic_log("FLASHING_START"))
        self.flashing_engine.flash_firmware(m, f"/firmware/{m}.bin")

    def _action_format(self):
        m = self.model_cb.get()
        if messagebox.askyesno("Confirm", f"Format device {m}? All data will be erased!"):
            self.flashing_engine.perform_full_format(m)
            logging.info("Device formatted successfully.")

    def _action_bypass_frp(self):
        m = self.model_cb.get()
        v = self.vendor_cb.get()
        res = self.account_repair.remove_frp_and_cloud_locks(m, brand=v)
        logging.info(self.loc_mgr.get_arabic_log("FRP_SUCCESS"))

    def _action_backup_efs(self):
        m = self.model_cb.get()
        self.account_repair.backup_efs_nvram(m, f"/backups/{m}/efs")

    def _action_unbrick(self):
        m = self.model_cb.get()
        v = self.vendor_cb.get()
        res = self.flashing_engine.unbrick_device(m, brand=v)
        logging.info(f"Unbrick completed for {m}: {res['status']}")

    def _action_fix_bootloop(self):
        m = self.model_cb.get()
        self.ultimate_repair.repair_major_system_issues(m)

    def _action_clean_virus(self):
        m = self.model_cb.get()
        self.ultimate_repair.scan_and_remove_viruses(m)
        logging.info(self.loc_mgr.get_arabic_log("VIRUS_REMOVED"))

    def _action_recalib_bio(self):
        m = self.model_cb.get()
        self.biometrics_fix.recalibrate_sensors(m)

    def _action_storage_check(self):
        m = self.model_cb.get()
        res = self.flashing_engine.scan_storage_health(m)
        messagebox.showinfo("Storage Health", f"Health: {res['storage_health']}\nRead: {res['read_speed_mbps']} MB/s\nWrite: {res['write_speed_mbps']} MB/s")

    def _action_deep_scan(self):
        m = self.model_cb.get()
        logging.info(self.loc_mgr.get_arabic_log("RECOVERY_START"))
        res = self.data_recovery.perform_deep_scan(m)
        messagebox.showinfo("Scan Complete", f"Photos: {res['photos_found']}\nSMS: {res['sms_messages_found']}\nContacts: {res['contacts_found']}")

    def _action_detect_devices(self):
        devs = self.driver_mgr.get_connected_adb_devices()
        fb = self.driver_mgr.get_fastboot_devices()
        logging.info(f"ADB devices: {len(devs)} | Fastboot: {len(fb)}")
        messagebox.showinfo("Devices", f"ADB: {len(devs)}\nFastboot: {len(fb)}")

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
        logging.info(f"Stream: {res['stream_url']}")

    def _action_checkout(self):
        sel = self.store_tree.selection()
        if sel:
            item_id = self.store_tree.item(sel[0])["values"][0]
            self.ecommerce_mgr.add_to_cart(item_id)
            order = self.ecommerce_mgr.checkout()
            messagebox.showinfo("Order", f"Order ID: {order['order_id']}\nTotal: ${order['total_amount']:.2f}")

    def _action_install_drivers(self):
        res = self.driver_mgr.check_all_drivers()
        logging.info(f"Drivers verified: {len(res)} stacks ready.")

    def _action_wipe_cache(self):
        m = self.model_cb.get()
        logging.info("Wiping cache partition...")
        self.flashing_engine.adb("shell", "rm", "-rf", "/cache/*")
        messagebox.showinfo("Done", "Cache partition wiped successfully.")

    def _action_system_update(self):
        m = self.model_cb.get()
        logging.info(f"Checking system updates for {m}...")
        res = self.smart_dev_mgr.scan_firmware_updates(m)
        messagebox.showinfo("Update Check", f"Current: {res['current_version']}\nLatest: {res['latest_version']}\nUpdate Available: {res['update_available']}")

    def _action_restore_efs(self):
        m = self.model_cb.get()
        logging.info(f"Restoring EFS/NVRAM for {m}...")
        self.account_repair.restore_efs_nvram(m, f"/backups/{m}/efs")
        messagebox.showinfo("Done", "EFS/NVRAM restored successfully.")

    def _action_bypass_email(self):
        m = self.model_cb.get()
        v = self.frp_brand_cb.get() if hasattr(self, 'frp_brand_cb') else self.vendor_cb.get()
        res = self.account_repair.bypass_email_account(m, brand=v)
        logging.info(f"Email account bypass completed for {m}")
        messagebox.showinfo("Email Bypass", f"Status: {res['status']}\n{res['message']}")

    def _action_remove_screen_lock(self):
        m = self.model_cb.get()
        lock_type = self.frp_lock_cb.get() if hasattr(self, 'frp_lock_cb') else "PATTERN"
        res = self.account_repair.remove_screen_lock(m, lock_type=lock_type.split("(")[0].strip())
        logging.info(f"Screen lock removed for {m}")
        messagebox.showinfo("Screen Lock", f"Status: {res['status']}\n{res['message']}")

    def _action_account_diagnostics(self):
        m = self.model_cb.get()
        res = self.account_repair.run_account_diagnostics(m)
        logging.info(f"Account diagnostics for {m}: FRP={res.get('frp_status', 'N/A')}")
        messagebox.showinfo("Account Diagnostics",
            f"Brand: {res.get('brand', 'Unknown')}\n"
            f"Model: {res.get('model', 'Unknown')}\n"
            f"FRP Status: {res.get('frp_status', 'N/A')}\n"
            f"Bootloader: {res.get('bootloader_status', 'N/A')}\n"
            f"Integrity: {res.get('integrity_check', 'N/A')}")

    def _action_network_repair(self):
        m = self.model_cb.get()
        v = self.frp_brand_cb.get() if hasattr(self, 'frp_brand_cb') else self.vendor_cb.get()
        res = self.account_repair.repair_network_calibration(m, brand=v)
        logging.info(f"Network repair for {m}: {res['status']}")
        messagebox.showinfo("Network Repair", f"Baseband: {res['baseband_status']}\nIMEI: {'Valid' if res['imei_valid'] else 'Invalid'}")

    def _action_change_lang(self):
        selected = self.lang_cb.get()
        for code, name in LocalizationManager.SUPPORTED_LANGUAGES.items():
            if name == selected:
                self.loc_mgr.set_language(code)
                self._apply_rtl_support()

                self.title_lbl.config(text=self.loc_mgr.get_string("title"))
                self.act_bar.config(text=self.loc_mgr.get_string("license_bar_lbl"))
                self.act_btn.config(text=self.loc_mgr.get_string("activate_btn"))
                self.ai_btn.config(text=self.loc_mgr.get_string("run_ai"))
                self.scan_btn.config(text="🔍 " + self.loc_mgr.get_string("start_scan"))

                # Update sidebar labels
                for key, info in self.sidebar_buttons.items():
                    translated = self.loc_mgr.get_string(key)
                    info["text"].config(text=translated)

                # Update tab labels
                tab_keys = [item[1] for item in SIDEBAR_ITEMS]
                for idx, key in enumerate(tab_keys):
                    if idx < len(self.notebook.tabs()):
                        self.notebook.tab(idx, text=self.loc_mgr.get_string(key))

                logging.info(f"Language changed to {selected} (RTL: {self.loc_mgr.is_rtl()}).")
                break

    def _apply_rtl_support(self):
        """Apply RTL/LTR layout adjustments based on current language."""
        is_rtl = self.loc_mgr.is_rtl()
        anchor = "e" if is_rtl else "w"
        self.title_lbl.config(anchor=anchor)
        self.act_bar.config(anchor=anchor)
        logging.info(f"RTL support applied: direction={'RTL' if is_rtl else 'LTR'}")

    def run(self):
        self.root.mainloop()
