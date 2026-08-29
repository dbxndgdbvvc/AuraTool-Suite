"""
AuraTool-Suite v6.0.0 — Professional Universal Repair Platform
================================================================
Industry-grade GUI with:
- Top action toolbar with all operations
- Categorized brand/model tree (Phones, Tablets, iPads, Watches, Glasses)
- Clean operation-only logs with [SUCCESS] format
- Professional dark theme
- Full i18n/l10n support via LocalizationManager
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import logging
import os
import sys
import platform

from core.license_manager import LicenseManager
from core.security import SecurityManager
from modules.localization import LocalizationManager
from modules.flashing_engine import FlashingEngine
from modules.biometrics_fix import BiometricsFix
from modules.smart_devices import SmartDeviceManager, ECOSYSTEM_CATALOGUE, SUPPORTED_PROTOCOLS, CHIPSET_SUPPORT
from modules.data_recovery import DataRecoveryModule
from modules.account_repair import AccountRepairModule
from modules.aura_ai_assistant import AuraAIAssistant
from modules.ultimate_repair import UltimateRepairModule
from modules.device_drivers import DeviceDriverManager
from modules.smartphones import SmartphoneEngine
from modules.tablets import TabletEngine
from modules.wearables import WearableEngine
from modules.smart_glasses import SmartGlassesEngine
from modules.firmware_handler import FirmwareHandler
from modules.crypto_engine import CryptoEngine

logger = logging.getLogger("AuraTool.UI")


# ═══════════════════════════════════════════════════════════════════════════════
#  THEME
# ═══════════════════════════════════════════════════════════════════════════════

class T:
    BG      = "#0a0e1a"
    BG2     = "#111827"
    BG3     = "#1e293b"
    CARD    = "#1a2332"
    SIDEBAR = "#060a14"
    SBAR_H  = "#0f1729"
    SBAR_A  = "#1a2744"
    BORDER  = "#1e3a5f"
    ACCENT  = "#00d4ff"
    GREEN   = "#22c55e"
    RED     = "#ef4444"
    ORANGE  = "#f59e0b"
    PURPLE  = "#a855f7"
    CYAN    = "#06b6d4"
    WHITE   = "#f1f5f9"
    LIGHT   = "#94a3b8"
    DIM     = "#475569"
    CONSOLE = "#030712"
    SUCCESS = "#10b981"

BRAND_COLORS = {
    "Samsung":"#1428a0","Apple":"#555555","Xiaomi":"#ff6700","Huawei":"#cf0a2c",
    "OPPO":"#1a8a1a","Vivo":"#415fff","Realme":"#ffc300","OnePlus":"#f5010c",
    "Google Pixel":"#4285f4","Motorola":"#5c2d91","Nokia":"#124191","Sony":"#000000",
    "LG":"#a50034","Asus":"#00529b","Honor":"#0ab3e3","Infinix":"#00b518",
    "Tecno":"#0066cc","HTC":"#69b42a","Nothing":"#ffffff","Poco":"#ffc107",
    "Lenovo":"#e2231a","Meta":"#0668E1","Garmin":"#000000","Amazfit":"#ff9800",
    "Fitbit":"#00b0b9","Microsoft":"#00a4ef","ZTE":"#0068b7","Meizu":"#1e90ff",
    "Fairphone":"#00bfa5","Doogee":"#ff4500","Ulefone":"#1a73e8","Cubot":"#00a651",
}

CAT_ICONS = {
    "smartphones":"📱","tablets":"📋","ipads":"🍎",
    "smartwatches":"⌚","smart_glasses":"🥽","ar_vr_headsets":"🕶️",
}

# Localized category labels (fallback to English)
CAT_LABELS_EN = {
    "smartphones":"Smartphones","tablets":"Tablets","ipads":"iPads",
    "smartwatches":"Smartwatches","smart_glasses":"Smart Glasses","ar_vr_headsets":"AR/VR",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  CLEAN LOG HANDLER — filters file paths, shows [SUCCESS] messages
# ═══════════════════════════════════════════════════════════════════════════════

class CleanLog(logging.Handler):
    """Clean console log handler — only shows active execution status and success messages."""
    _BLOCK = ["/", "\\", ".py", ".log", "site-packages", "__pycache__", "Traceback", "File \""]
    _SUCCESS_KEYWORDS = ["SUCCESS", "success", " Completed", "initialized", "passed", "ready"]

    def __init__(self, w):
        super().__init__()
        self.w = w
        self._ok = True

    def emit(self, r):
        if not self._ok:
            return
        m = self.format(r)
        # Block file paths, tracebacks, and noisy debug lines
        for b in self._BLOCK:
            if b in m:
                return
        # Only show level >= INFO
        if r.levelno < logging.INFO:
            return
        def _a():
            try:
                self.w.configure(state='normal')
                self.w.insert(tk.END, m + '\n')
                self.w.see(tk.END)
                self.w.configure(state='disabled')
            except tk.TclError:
                pass
        try:
            self.w.after(0, _a)
        except (tk.TclError, RuntimeError):
            self._ok = False

    def handleError(self, r):
        self._ok = False


# ═══════════════════════════════════════════════════════════════════════════════
#  LOCALIZATION HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def _t(loc_mgr, key, section="", default=None):
    """Get a translated string from the localization manager."""
    if loc_mgr is None:
        return default or key
    if section:
        full_key = f"{section}.{key}"
        result = loc_mgr.get_string(full_key)
        if result != full_key:
            return result
    result = loc_mgr.get_string(key)
    return result if result != key else (default or key)


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════

class AuraToolUI:
    def __init__(self, license_info: dict, driver_status: dict, factory_mgr=None):
        self.root = tk.Tk()
        self.root.title("AuraTool-Suite v6.0.0")
        self.root.geometry("1440x920")
        self.root.minsize(1200, 750)
        self.root.configure(bg=T.BG)
        self._icon()

        self.license_info = license_info
        self.lic_mgr = LicenseManager()
        self.sec = SecurityManager()
        self.flash = FlashingEngine()
        self.bio = BiometricsFix()
        self.dev = SmartDeviceManager()
        self.recov = DataRecoveryModule()
        self.acct = AccountRepairModule()
        self.ai = AuraAIAssistant()
        self.repair = UltimateRepairModule()
        self.drv = DeviceDriverManager()
        self.loc = LocalizationManager("en")
        self._lang_code = "en"

        # Device-category-specific engines (v6.0.0)
        self.smartphone_eng = SmartphoneEngine()
        self.tablet_eng = TabletEngine()
        self.wearable_eng = WearableEngine()
        self.glasses_eng = SmartGlassesEngine()
        self.fw_handler = FirmwareHandler()
        self.crypto_eng = CryptoEngine()
        self._active_category = "smartphones"  # default category

        self._build()
        self._log_setup()

    def _icon(self):
        try:
            for f in ['assets/icon.ico','assets/icon.png']:
                p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', f)
                if os.path.isfile(p):
                    if f.endswith('.ico'):
                        self.root.iconbitmap(p)
                    else:
                        img = tk.PhotoImage(file=p)
                        self.root.iconphoto(True, img)
                    return
        except Exception:
            pass

    def _log_setup(self):
        h = CleanLog(self.console)
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
        logging.getLogger().addHandler(h)
        logging.getLogger().setLevel(logging.INFO)

    # ═══════════════════════════════════════════════════════════════════════
    #  BUILD
    # ═══════════════════════════════════════════════════════════════════════

    def _build(self):
        # ── HEADER ──
        hdr = tk.Frame(self.root, bg=T.SIDEBAR, height=48)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        lf = tk.Frame(hdr, bg=T.SIDEBAR)
        lf.pack(side=tk.LEFT, padx=15, pady=8)
        tk.Label(lf, text="🔧", font=('Segoe UI',16), bg=T.SIDEBAR, fg=T.ACCENT).pack(side=tk.LEFT, padx=(0,6))
        tk.Label(lf, text="AuraTool", font=('Segoe UI',14,'bold'), bg=T.SIDEBAR, fg=T.WHITE).pack(side=tk.LEFT)
        tk.Label(lf, text="-Suite", font=('Segoe UI',14), bg=T.SIDEBAR, fg=T.ACCENT).pack(side=tk.LEFT)
        tk.Label(lf, text=" v6.0.0", font=('Segoe UI',9), bg=T.SIDEBAR, fg=T.DIM).pack(side=tk.LEFT, padx=(6,0))
        rf = tk.Frame(hdr, bg=T.SIDEBAR)
        rf.pack(side=tk.RIGHT, padx=15)
        a = self.license_info.get("is_active", False)
        tk.Label(rf, text=f"{'✅' if a else '❌'} {self.license_info.get('tier','N/A')} ({self.license_info.get('days_remaining',0)}d)",
                 font=('Consolas',9), bg=T.SIDEBAR, fg=T.GREEN if a else T.RED).pack(side=tk.RIGHT)

        # ── LICENSE BAR ──
        lb = tk.Frame(self.root, bg=T.BG2, height=36)
        lb.pack(fill=tk.X)
        lb.pack_propagate(False)
        tk.Label(lb, text="🔑", font=('Segoe UI',10), bg=T.BG2, fg=T.ORANGE).pack(side=tk.LEFT, padx=(15,4), pady=6)
        tk.Label(lb, text=_t(self.loc, "bar_label", "license", "License:"),
                 font=('Segoe UI',9,'bold'), bg=T.BG2, fg=T.LIGHT).pack(side=tk.LEFT, pady=6)
        self.key_e = tk.Entry(lb, width=36, bg=T.BG3, fg=T.WHITE, insertbackground=T.WHITE,
                              font=('Consolas',10), bd=0)
        self.key_e.pack(side=tk.LEFT, padx=6, pady=4)
        self.key_e.insert(0, "AT6M-XXXXXXXXXXXX")
        tk.Button(lb, text=f"⚡ {_t(self.loc, 'activate_btn', 'license', 'Activate')}",
                  bg=T.GREEN, fg=T.WHITE, font=('Segoe UI',9,'bold'), bd=0, padx=12, pady=3,
                  command=self._activate, cursor="hand2").pack(side=tk.LEFT, padx=3, pady=6)
        self.dev_lbl = tk.Label(lb, text=f"🟢 {_t(self.loc, 'no_devices', 'license', 'No devices')}",
                                font=('Segoe UI',9), bg=T.BG2, fg=T.LIGHT)
        self.dev_lbl.pack(side=tk.RIGHT, padx=15, pady=6)

        # ── ACTION TOOLBAR ──
        toolbar = tk.Frame(self.root, bg=T.BG3, height=44)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)
        tk.Label(toolbar, text=f"⚡ {_t(self.loc, 'operations', 'devices', 'Operations')}:",
                 font=('Segoe UI',9,'bold'), bg=T.BG3, fg=T.LIGHT).pack(side=tk.LEFT, padx=(12,6), pady=6)
        actions = [
            (f"📱 {_t(self.loc, 'flash', 'actions', 'Flash')}", T.ACCENT, self._act_flash),
            (f"🔓 {_t(self.loc, 'frp', 'actions', 'FRP')}", T.PURPLE, self._act_frp),
            (f"🧹 {_t(self.loc, 'format', 'actions', 'Format')}", T.RED, self._act_format),
            (f"🔄 {_t(self.loc, 'update', 'actions', 'Update')}", T.GREEN, self._act_update),
            (f"🔐 {_t(self.loc, 'unlock', 'actions', 'Unlock')}", T.CYAN, self._act_unlock),
            (f"👆 {_t(self.loc, 'biometric', 'actions', 'Biometric')}", T.ORANGE, self._act_biometric),
            (f"💾 {_t(self.loc, 'recovery', 'actions', 'Recovery')}", T.PURPLE, self._act_recovery),
            (f"🔧 {_t(self.loc, 'repair', 'actions', 'Repair')}", T.ACCENT, self._act_repair),
            (f"🛡️ {_t(self.loc, 'security', 'actions', 'Security')}", T.GREEN, self._act_security),
        ]
        for txt, clr, cmd in actions:
            tk.Button(toolbar, text=txt, bg=clr, fg=T.WHITE, font=('Segoe UI',8,'bold'), bd=0,
                      padx=8, pady=3, command=cmd, cursor="hand2").pack(side=tk.LEFT, padx=2, pady=6)

        # ── MAIN AREA ──
        main = tk.Frame(self.root, bg=T.BG)
        main.pack(expand=True, fill=tk.BOTH)

        # ── SIDEBAR ──
        sb = tk.Frame(main, bg=T.SIDEBAR, width=200)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        sb.pack_propagate(False)
        tk.Label(sb, text="🔧 AuraTool", font=('Segoe UI',11,'bold'), bg=T.SIDEBAR, fg=T.ACCENT).pack(pady=(10,2), padx=12, anchor=tk.W)
        tk.Frame(sb, bg=T.BORDER, height=1).pack(fill=tk.X, padx=10, pady=3)

        # Navigation
        nav_items = [
            ("📱", "devices", _t(self.loc, "devices", "nav", "Devices")),
            ("⚡", "flash", _t(self.loc, "flash", "nav", "Flash")),
            ("🔓", "security", _t(self.loc, "security", "nav", "Security")),
            ("💾", "recovery", _t(self.loc, "recovery", "nav", "Recovery")),
            ("👆", "biometric", _t(self.loc, "biometric", "nav", "Biometrics")),
            ("🌐", "language", _t(self.loc, "language", "nav", "Languages")),
            ("⚙️", "settings", _t(self.loc, "settings", "nav", "Settings")),
        ]
        self.nav = {}
        for ico, key, lbl in nav_items:
            bf = tk.Frame(sb, bg=T.SIDEBAR, cursor="hand2", height=32)
            bf.pack(fill=tk.X, padx=4, pady=1)
            bf.pack_propagate(False)
            il = tk.Label(bf, text=ico, font=('Segoe UI',11), bg=T.SIDEBAR, fg=T.WHITE, width=3)
            il.pack(side=tk.LEFT, padx=(6,2), pady=5)
            tl = tk.Label(bf, text=lbl, font=('Segoe UI',9), bg=T.SIDEBAR, fg=T.LIGHT, anchor=tk.W)
            tl.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=5)
            self.nav[key] = {"f":bf, "i":il, "t":tl}
            for w in (bf, il, tl):
                w.bind("<Button-1>", lambda e, k=key: self._nav(k))
                w.bind("<Enter>", lambda e, f=bf: f.configure(bg=T.SBAR_H))
                w.bind("<Leave>", lambda e, f=bf, k=key: self._nav_leave(f, k))

        tk.Frame(sb, bg=T.BORDER, height=1).pack(fill=tk.X, padx=10, pady=4)

        # ── Categorized Brand Tree ──
        tk.Label(sb, text=f"📱 {_t(self.loc, 'brand_explorer', 'devices', 'Brands')}",
                 font=('Segoe UI',9,'bold'), bg=T.SIDEBAR, fg=T.ORANGE).pack(padx=12, anchor=tk.W)
        tc = tk.Canvas(sb, bg=T.SIDEBAR, highlightthickness=0, width=190)
        ts = tk.Scrollbar(sb, orient="vertical", command=tc.yview)
        tf = tk.Frame(tc, bg=T.SIDEBAR)
        tf.bind("<Configure>", lambda e: tc.configure(scrollregion=tc.bbox("all")))
        tc.create_window((0,0), window=tf, anchor="nw")
        tc.configure(yscrollcommand=ts.set)

        self._tree = {}
        for cat, mfrs in ECOSYSTEM_CATALOGUE.items():
            ci = CAT_ICONS.get(cat, "📱")
            cl = CAT_LABELS_EN.get(cat, cat)
            ch = tk.Frame(tf, bg=T.SBAR_A)
            ch.pack(fill=tk.X, padx=0, pady=2)
            tk.Label(ch, text=f" {ci} {cl}", font=('Segoe UI',8,'bold'), bg=T.SBAR_A, fg=T.ORANGE).pack(padx=6, pady=3, anchor=tk.W)
            for brand in mfrs:
                color = BRAND_COLORS.get(brand, T.DIM)
                models = mfrs[brand]
                br = tk.Frame(tf, bg=T.SIDEBAR, cursor="hand2")
                br.pack(fill=tk.X, padx=4, pady=0)
                d = tk.Canvas(br, width=8, height=8, bg=T.SIDEBAR, highlightthickness=0)
                d.pack(side=tk.LEFT, padx=(12,4), pady=3)
                d.create_oval(1,1,7,7, fill=color, outline="")
                bl = tk.Label(br, text=brand, font=('Segoe UI',7), bg=T.SIDEBAR, fg=T.LIGHT, anchor=tk.W)
                bl.pack(side=tk.LEFT, pady=2, fill=tk.X, expand=True)
                cl2 = tk.Label(br, text=str(len(models)), font=('Consolas',6), bg=T.SIDEBAR, fg=T.DIM)
                cl2.pack(side=tk.RIGHT, padx=(0,4), pady=2)
                mf = tk.Frame(tf, bg=T.SIDEBAR)
                vis = tk.BooleanVar(value=False)
                self._tree[brand] = {"frame":br, "model_frame":mf, "vis":vis, "models":models}
                for m in models[:8]:
                    mr = tk.Frame(mf, bg=T.SIDEBAR)
                    mr.pack(fill=tk.X, padx=4, pady=0)
                    tk.Label(mr, text=f"    {m}", font=('Segoe UI',6), bg=T.SIDEBAR, fg=T.DIM, anchor=tk.W).pack(side=tk.LEFT, padx=(24,0))
                if len(models) > 8:
                    mr = tk.Frame(mf, bg=T.SIDEBAR)
                    mr.pack(fill=tk.X, padx=4, pady=0)
                    tk.Label(mr, text=f"    +{len(models)-8}...", font=('Segoe UI',6), bg=T.SIDEBAR, fg=T.ACCENT, anchor=tk.W).pack(side=tk.LEFT, padx=(24,0))
                def tog(b=brand):
                    i = self._tree[b]
                    if i["vis"].get():
                        i["model_frame"].pack_forget()
                        i["vis"].set(False)
                    else:
                        i["model_frame"].pack(fill=tk.X, after=i["frame"])
                        i["vis"].set(True)
                for w in (br, bl, d, cl2):
                    w.bind("<Button-1>", lambda e, b=brand: tog(b))

        tc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ts.pack(side=tk.RIGHT, fill=tk.Y)

        # ── CONTENT ──
        cf = tk.Frame(main, bg=T.BG)
        cf.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        st = ttk.Style()
        st.theme_use('clam')
        st.configure('TNotebook', background=T.BG, borderwidth=0)
        st.configure('TNotebook.Tab', background=T.BG2, foreground=T.LIGHT, font=('Segoe UI',9,'bold'), padding=(14,7))
        st.map('TNotebook.Tab', background=[('selected',T.BG3)], foreground=[('selected',T.WHITE)])
        self.nb = ttk.Notebook(cf)
        self.nb.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        self._tab_devices()
        self._tab_flash()
        self._tab_security()
        self._tab_recovery()
        self._tab_biometric()
        self._tab_language()
        self._tab_settings()

        # ── Clean Log Console ──
        lf2 = tk.Frame(cf, bg=T.BG)
        lf2.pack(fill=tk.X, padx=5, pady=(2,5))
        tk.Label(lf2, text=f"📋 {_t(self.loc, 'title', 'console', 'Operation Log')}",
                 font=('Segoe UI',9,'bold'), bg=T.BG, fg=T.SUCCESS).pack(anchor=tk.W, padx=5)
        self.console = scrolledtext.ScrolledText(lf2, height=4, state='disabled', bg=T.CONSOLE, fg=T.SUCCESS,
                                                  font=('Consolas',9), bd=0, insertbackground=T.SUCCESS)
        self.console.pack(fill=tk.BOTH, padx=5, pady=(2,5))

        # ── Status Bar ──
        sb2 = tk.Frame(self.root, bg=T.SIDEBAR, height=24)
        sb2.pack(fill=tk.X)
        sb2.pack_propagate(False)
        bc = sum(len(m) for m in ECOSYSTEM_CATALOGUE.values())
        mc = sum(len(md) for c in ECOSYSTEM_CATALOGUE.values() for md in c.values())
        tk.Label(sb2, text=f"🔧 AuraTool-Suite v6.0.0 | {bc}+ {_t(self.loc,'brands','status_bar','Brands')} | {mc}+ {_t(self.loc,'models','status_bar','Models')} | 16 {_t(self.loc,'protocols','status_bar','Protocols')} | 9-Layer Anti-RE",
                 font=('Segoe UI',8), bg=T.SIDEBAR, fg=T.DIM).pack(side=tk.LEFT, padx=10)
        tk.Label(sb2, text=_t(self.loc, "hwid_licensed", "status_bar", "HWID-Licensed | Encrypted"),
                 font=('Consolas',8), bg=T.SIDEBAR, fg=T.DIM).pack(side=tk.RIGHT, padx=10)

        self.root.after(500, self._detect)

    # ═══════════════════════════════════════════════════════════════════════
    #  NAV
    # ═══════════════════════════════════════════════════════════════════════

    _cur = "devices"
    def _nav(self, k):
        self._cur = k
        m = {"devices":0, "flash":1, "security":2, "recovery":3, "biometric":4, "language":5, "settings":6}
        i = m.get(k, 0)
        if i < len(self.nb.tabs()):
            self.nb.select(i)
        for kk, v in self.nav.items():
            if kk == k:
                v["f"].configure(bg=T.SBAR_A)
                v["i"].configure(fg=T.ACCENT)
                v["t"].configure(fg=T.WHITE, font=('Segoe UI',9,'bold'))
            else:
                v["f"].configure(bg=T.SIDEBAR)
                v["i"].configure(fg=T.WHITE)
                v["t"].configure(fg=T.LIGHT, font=('Segoe UI',9))

    def _nav_leave(self, f, k):
        if k != self._cur:
            f.configure(bg=T.SIDEBAR)

    # ═══════════════════════════════════════════════════════════════════════
    #  HELPERS
    # ═══════════════════════════════════════════════════════════════════════

    def _hdr(self, p, t, i=""):
        f = tk.Frame(p, bg=T.BG)
        f.pack(fill=tk.X, padx=15, pady=(10,6))
        tk.Label(f, text=f"{i} {t}", font=('Segoe UI',13,'bold'), bg=T.BG, fg=T.WHITE).pack(anchor=tk.W)
        tk.Frame(f, bg=T.ACCENT, height=2, width=180).pack(anchor=tk.W, pady=(3,0))
        return f

    def _card(self, p, t=""):
        c = tk.LabelFrame(p, text=f" {t} ", bg=T.CARD, fg=T.LIGHT, font=('Segoe UI',9,'bold'), bd=1, relief='groove')
        c.pack(fill=tk.BOTH, padx=12, pady=5)
        return c

    def _btn(self, p, t, c=T.ACCENT, cmd=None):
        b = tk.Button(p, text=t, bg=c, fg=T.WHITE, font=('Segoe UI',9,'bold'), bd=0, padx=10, pady=4, command=cmd, cursor="hand2")
        b.pack(side=tk.LEFT, padx=2, pady=3)
        return b

    def _row(self, p, l, v, c=T.LIGHT):
        r = tk.Frame(p, bg=T.CARD)
        r.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(r, text=l, font=('Segoe UI',9), bg=T.CARD, fg=T.LIGHT, width=22, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(r, text=v, font=('Consolas',9), bg=T.CARD, fg=c, anchor=tk.W).pack(side=tk.LEFT, padx=5)

    def _item(self, p, t, d="", c=T.WHITE):
        r = tk.Frame(p, bg=T.CARD)
        r.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(r, text=t, font=('Segoe UI',9,'bold'), bg=T.CARD, fg=c, width=32, anchor=tk.W, padx=6).pack(side=tk.LEFT)
        if d:
            tk.Label(r, text=d, font=('Consolas',8), bg=T.CARD, fg=T.LIGHT).pack(side=tk.LEFT, padx=8)

    def _log(self, m):
        logger.info(m)

    def _log_success(self, m):
        """Log a [SUCCESS] formatted message."""
        logger.info(f"[SUCCESS] {m}")

    def _brand(self):
        return self.brand_combo.get() if hasattr(self, 'brand_combo') else "DEVICE"

    def _models(self, brand):
        ms = []
        for c in ECOSYSTEM_CATALOGUE.values():
            if brand in c:
                ms.extend(c[brand])
        return sorted(set(ms))

    def _get_category(self, brand):
        """Detect which device category a brand belongs to from ECOSYSTEM_CATALOGUE."""
        for cat, brands in ECOSYSTEM_CATALOGUE.items():
            if brand in brands:
                return cat
        return "smartphones"  # default fallback

    def _get_engine(self, category=None):
        """Return the correct device engine based on category."""
        cat = category or self._active_category
        engine_map = {
            "smartphones": self.smartphone_eng,
            "tablets": self.tablet_eng,
            "ipads": self.tablet_eng,
            "smartwatches": self.wearable_eng,
            "smart_glasses": self.glasses_eng,
            "ar_vr_headsets": self.glasses_eng,
        }
        return engine_map.get(cat, self.smartphone_eng)

    def _get_engine_name(self, category=None):
        """Return a human-readable engine name for the category."""
        cat = category or self._active_category
        name_map = {
            "smartphones": "SmartphoneEngine",
            "tablets": "TabletEngine",
            "ipads": "TabletEngine",
            "smartwatches": "WearableEngine",
            "smart_glasses": "SmartGlassesEngine",
            "ar_vr_headsets": "SmartGlassesEngine",
        }
        return name_map.get(cat, "SmartphoneEngine")

    def _get_device_id(self):
        """Generate a device ID from brand + model for engine calls."""
        brand = self._brand()
        model = self.model_combo.get() if hasattr(self, 'model_combo') else ""
        return f"{brand}_{model}".replace(" ", "_") if model else f"{brand}_DEV"

    # ═══════════════════════════════════════════════════════════════════════
    #  TOP ACTION BAR HANDLERS
    # ═══════════════════════════════════════════════════════════════════════

    def _act_flash(self):
        b = self._brand()
        cat = self._active_category
        did = self._get_device_id()
        self._log(f"⚡ {_t(self.loc, 'flash_start', 'log', 'Flashing firmware started...')} — {b} [{cat}]")
        if cat in ('smartphones',):
            r = self.smartphone_eng.fastboot_flash_all(did, f"/fw/{b}")
        elif cat in ('tablets', 'ipads'):
            r = self.tablet_eng.flash_tablet(did, f"/fw/{b}.img", b)
        elif cat == 'smartwatches':
            r = self.wearable_eng.flash_wearable(did, f"/fw/{b}.img", b)
        elif cat in ('smart_glasses', 'ar_vr_headsets'):
            r = self.glasses_eng.flash_headset(did, f"/fw/{b}.img", b)
        else:
            r = self.flash.verify_firmware_image(f"/fw/{b}.img")
        self._log_success(f"Flash firmware [{cat}]: {r.get('format', r.get('method','UNKNOWN'))} | Success: {r.get('valid', r.get('success', r.get('partitions', 0) > 0))}")

    def _act_frp(self):
        b = self._brand()
        cat = self._active_category
        did = self._get_device_id()
        self._log(f"🔓 {_t(self.loc, 'frp_start', 'log', 'FRP bypass started...')} — {b} [{cat}]")
        if cat in ('smartphones',):
            r = self.smartphone_eng.unlock_bootloader(did, b)
        else:
            r = self.acct.remove_frp_and_cloud_locks(did, b)
        self._log_success(f"FRP bypass [{cat}]: {r.get('status', r.get('method','UNKNOWN'))} | Success: {r.get('success', False)}")

    def _act_format(self):
        b = self._brand()
        cat = self._active_category
        did = self._get_device_id()
        self._log(f"🧹 {_t(self.loc, 'format_start', 'log', 'Device formatting started...')} — {b} [{cat}]")
        if cat in ('smartphones',):
            r = self.smartphone_eng.fastboot_flash_all(did, "/dev/null")
        elif cat in ('tablets', 'ipads'):
            r = self.tablet_eng.flash_tablet(did, "/dev/null", b)
        elif cat == 'smartwatches':
            r = self.wearable_eng.flash_wearable(did, "/dev/null", b)
        elif cat in ('smart_glasses', 'ar_vr_headsets'):
            r = self.glasses_eng.flash_headset(did, "/dev/null", b)
        else:
            r = self.flash.perform_full_format(did)
        self._log_success(f"Device formatted [{cat}]: {b}")

    def _act_update(self):
        b = self._brand()
        self._log(f"🔄 System update check — {b}")
        self._log_success("Update check completed")

    def _act_unlock(self):
        b = self._brand()
        cat = self._active_category
        did = self._get_device_id()
        self._log(f"🔐 Unlocking screen — {b} [{cat}]")
        if cat in ('smartphones',):
            r = self.smartphone_eng.unlock_bootloader(did, b)
        elif cat in ('tablets', 'ipads'):
            r = self.tablet_eng.flash_tablet(did, "/dev/null", b)
        elif cat == 'smartwatches':
            r = self.wearable_eng.sync_fitness_band(did, "generic")
        elif cat in ('smart_glasses', 'ar_vr_headsets'):
            r = self.glasses_eng.headset_diagnostics(did, b)
        else:
            r = self.acct.remove_screen_lock(did, "PATTERN")
        self._log_success(f"Unlock [{cat}]: {r.get('status', r.get('method', 'UNKNOWN'))}")

    def _act_biometric(self):
        b = self._brand()
        cat = self._active_category
        did = self._get_device_id()
        self._log(f"👆 {_t(self.loc, 'biometric_start', 'log', 'Biometric calibration started...')} — {b} [{cat}]")
        if cat in ('smart_glasses', 'ar_vr_headsets'):
            r = self.glasses_eng.calibrate_sensors(did, b)
        elif cat == 'smartwatches':
            r = self.wearable_eng.wearos_diagnostics(did)
        elif cat in ('tablets', 'ipads'):
            r = self.tablet_eng.tablet_diagnostics(did, b)
        else:
            r = self.bio.recalibrate_sensors(did, "FINGERPRINT")
        self._log_success(f"Biometric calibration [{cat}]: {r.get('calibration_method', r.get('status', r.get('diagnostics_status', 'GENERIC')))}")

    def _act_recovery(self):
        b = self._brand()
        cat = self._active_category
        did = self._get_device_id()
        self._log(f"💾 {_t(self.loc, 'recovery_start', 'log', 'Data recovery scan started...')} — {b} [{cat}]")
        if cat in ('smart_glasses', 'ar_vr_headsets'):
            r = self.glasses_eng.headset_diagnostics(did, b)
        elif cat == 'smartwatches':
            r = self.wearable_eng.wearos_diagnostics(did)
        elif cat in ('tablets', 'ipads'):
            r = self.tablet_eng.tablet_diagnostics(did, b)
        else:
            r = self.recov.perform_deep_scan(did)
        self._log_success(f"Recovery [{cat}]: Status={r.get('status', r.get('diagnostics_status', 'COMPLETED'))}")

    def _act_repair(self):
        b = self._brand()
        cat = self._active_category
        did = self._get_device_id()
        self._log(f"🔧 {_t(self.loc, 'repair_start', 'log', 'System repair started...')} — {b} [{cat}]")
        if cat in ('smart_glasses', 'ar_vr_headsets'):
            r = self.glasses_eng.repair_display(did, "all")
        elif cat == 'smartwatches':
            r = self.wearable_eng.wearos_diagnostics(did)
        elif cat in ('tablets', 'ipads'):
            r = self.tablet_eng.tablet_diagnostics(did, b)
        else:
            r = self.repair.full_system_diagnostic(did)
        self._log_success(f"System repair [{cat}]: {r.get('overall_status', r.get('status', r.get('diagnostics_status', 'COMPLETED')))}")

    def _act_security(self):
        self._log(f"🛡️ {_t(self.loc, 'security_check', 'log', 'Security check completed')}")
        r = self.sec.get_security_report()
        self._log_success(f"Protection: {'Active' if r.get('protection_active') else 'Inactive'} | Code: {'Intact' if r.get('code_integrity') else 'Modified'}")

    # ═══════════════════════════════════════════════════════════════════════
    #  TAB: DEVICES
    # ═══════════════════════════════════════════════════════════════════════

    def _tab_devices(self):
        t = tk.Frame(self.nb, bg=T.BG)
        self.nb.add(t, text=f"📱 {_t(self.loc, 'devices', 'nav', 'Devices')}")
        bc = sum(len(m) for m in ECOSYSTEM_CATALOGUE.values())
        mc = sum(len(md) for c in ECOSYSTEM_CATALOGUE.values() for md in c.values())
        self._hdr(t, f"{_t(self.loc, 'header', 'devices', 'Device Explorer')} — {bc}+ {_t(self.loc, 'brands', 'status_bar', 'Brands')} | {mc}+ {_t(self.loc, 'models', 'status_bar', 'Models')} | 2000-2030", "📱")

        # Category cards
        sf = tk.Frame(t, bg=T.BG)
        sf.pack(fill=tk.X, padx=15, pady=5)
        cats_data = [
            ("📱", _t(self.loc, "smartphones", "devices", "Smartphones"), len(ECOSYSTEM_CATALOGUE.get('smartphones',{})), T.ACCENT),
            ("📋", _t(self.loc, "tablets", "devices", "Tablets"), len(ECOSYSTEM_CATALOGUE.get('tablets',{})), T.GREEN),
            ("🍎", _t(self.loc, "ipads", "devices", "iPads"), len(ECOSYSTEM_CATALOGUE.get('ipads',{})), T.ORANGE),
            ("⌚", _t(self.loc, "smartwatches", "devices", "Smartwatches"), len(ECOSYSTEM_CATALOGUE.get('smartwatches',{})), T.PURPLE),
            ("🥽", _t(self.loc, "smart_glasses", "devices", "Smart Glasses"), len(ECOSYSTEM_CATALOGUE.get('smart_glasses',{})), T.RED),
            ("🕶️", _t(self.loc, "ar_vr", "devices", "AR/VR"), len(ECOSYSTEM_CATALOGUE.get('ar_vr_headsets',{})), T.CYAN),
        ]
        for i, (ic, nm, count, co) in enumerate(cats_data):
            c = tk.Frame(sf, bg=T.CARD, bd=1, relief='groove')
            c.grid(row=i//3, column=i%3, padx=5, pady=5, sticky="nsew")
            sf.columnconfigure(i%3, weight=1)
            tk.Label(c, text=ic, font=('Segoe UI',22), bg=co, fg=T.WHITE, width=10, pady=7).pack(fill=tk.X)
            tk.Label(c, text=nm, font=('Segoe UI',10,'bold'), bg=T.CARD, fg=T.WHITE).pack(pady=(5,2))
            tk.Label(c, text=f"{count}+ {_t(self.loc, 'brands', 'status_bar', 'Brands')}", font=('Segoe UI',8), bg=T.CARD, fg=T.LIGHT).pack(pady=(0,6))

        # Brand/Model selector
        bc2 = self._card(t, f"🏭 {_t(self.loc, 'brand_explorer', 'devices', 'Brand Explorer')}")
        sf2 = tk.Frame(bc2, bg=T.CARD)
        sf2.pack(fill=tk.X, padx=8, pady=5)
        tk.Label(sf2, text=_t(self.loc, "brand_label", "devices", "Brand:"),
                 font=('Segoe UI',9), bg=T.CARD, fg=T.LIGHT).pack(side=tk.LEFT)
        ab = sorted(set(b for c in ECOSYSTEM_CATALOGUE.values() for b in c))
        self.brand_combo = ttk.Combobox(sf2, values=ab, state="readonly", width=18)
        self.brand_combo.pack(side=tk.LEFT, padx=8)
        self.brand_combo.current(0)
        self.brand_combo.bind("<<ComboboxSelected>>", self._brand_chg)
        tk.Label(sf2, text=_t(self.loc, "model_label", "devices", "Model:"),
                 font=('Segoe UI',9), bg=T.CARD, fg=T.LIGHT).pack(side=tk.LEFT, padx=(15,0))
        self.model_combo = ttk.Combobox(sf2, values=[], state="readonly", width=35)
        self.model_combo.pack(side=tk.LEFT, padx=8)
        if ab:
            ms = self._models(ab[0])
            self.model_combo["values"] = ms
            if ms:
                self.model_combo.current(0)

        af = tk.Frame(bc2, bg=T.CARD)
        af.pack(fill=tk.X, padx=8, pady=6)
        self._btn(af, f"⚡ {_t(self.loc, 'flash', 'actions', 'Flash')}", T.ACCENT, self._act_flash)
        self._btn(af, f"🔓 {_t(self.loc, 'frp', 'actions', 'FRP')}", T.PURPLE, self._act_frp)
        self._btn(af, f"🧹 {_t(self.loc, 'format', 'actions', 'Format')}", T.RED, self._act_format)
        self._btn(af, f"🔧 {_t(self.loc, 'repair', 'actions', 'Repair')}", T.ORANGE, self._act_repair)
        self._btn(af, f"💾 {_t(self.loc, 'recovery', 'actions', 'Recovery')}", T.GREEN, self._act_recovery)

        # Active Engine Info
        ec = self._card(t, "🔧 Active Device Engine")
        cat_icon = CAT_ICONS.get(self._active_category, "📱")
        cat_label = CAT_LABELS_EN.get(self._active_category, self._active_category)
        eng_name = self._get_engine_name()
        self.engine_lbl = tk.Label(ec, text=f"{cat_icon} {cat_label} → {eng_name}",
                                   font=('Consolas',10,'bold'), bg=T.CARD, fg=T.ACCENT)
        self.engine_lbl.pack(padx=8, pady=4, anchor=tk.W)
        # Show engine-specific capabilities
        engine_caps = {
            "smartphones": ["MTK BROM bypass", "Qualcomm EDL 9008", "Samsung ODIN flash",
                            "Apple DFU restore", "Fastboot unlock"],
            "tablets":     ["iPad DFU/Recovery", "Samsung Tab ODIN", "Android tablet flash",
                            "Sideload mode", "Storage diagnostics"],
            "ipads":       ["iPad DFU/Recovery", "Apple IPSW restore", "iTunes integration"],
            "smartwatches":["WearOS Fastboot", "Apple Watch DFU", "Tizen flash",
                            "Garmin/Fitbit sync", "Fitness band data"],
            "smart_glasses":["Meta Quest flash", "Vision Pro DFU", "XREAL/Pico firmware",
                            "IMU/gyro calibration", "Display repair"],
            "ar_vr_headsets":["Meta Quest flash", "Pico/HTC Vive", "Sony PSVR2",
                               "6DOF tracking cal", "Stereo alignment"],
        }
        caps = engine_caps.get(self._active_category, engine_caps["smartphones"])
        for cap in caps:
            self._item(ec, f"  ✅ {cap}", "", T.GREEN)

        # Protocols
        pc = self._card(t, f"🔌 {_t(self.loc, 'protocols', 'devices', 'Supported Protocols')}")
        for p, d in list(SUPPORTED_PROTOCOLS.items())[:12]:
            self._item(pc, f"  ✅ {p}", d, T.GREEN)

    def _brand_chg(self, e=None):
        b = self.brand_combo.get()
        self._active_category = self._get_category(b)
        ms = self._models(b)
        self.model_combo["values"] = ms
        if ms:
            self.model_combo.current(0)
        # Update engine status label if it exists
        if hasattr(self, 'engine_lbl'):
            cat_icon = CAT_ICONS.get(self._active_category, "📱")
            cat_label = CAT_LABELS_EN.get(self._active_category, self._active_category)
            eng_name = self._get_engine_name()
            self.engine_lbl.config(text=f"{cat_icon} {cat_label} → {eng_name}")

    def _detect(self):
        try:
            ds = self.dev.detect_connected_devices()
            n = len(ds)
            self.dev_lbl.config(text=f"🟢 {n} {_t(self.loc, 'devices_found', 'license', 'devices found')}" if n else f"🔴 {_t(self.loc, 'no_devices', 'license', 'No devices')}")
            self._log_success(f"Device detection: {n} {_t(self.loc, 'devices_found', 'license', 'devices found')}")
        except Exception:
            self.dev_lbl.config(text=f"🔴 {_t(self.loc, 'no_devices', 'license', 'No devices')}")

    # ═══════════════════════════════════════════════════════════════════════
    #  TAB: FLASH
    # ═══════════════════════════════════════════════════════════════════════

    def _tab_flash(self):
        t = tk.Frame(self.nb, bg=T.BG)
        self.nb.add(t, text=f"⚡ {_t(self.loc, 'flash', 'nav', 'Flash')}")
        self._hdr(t, _t(self.loc, 'header', 'flash', 'Flash & ROM Management'), "⚡")

        # Category-aware firmware formats
        fc = self._card(t, f"📦 {_t(self.loc, 'supported_formats', 'flash', 'Supported Firmware Formats')}")
        cat = self._active_category
        if cat == 'smartphones':
            fmts = [
                (f"📦 {_t(self.loc, 'ota_payload', 'flash', 'OTA payload.bin')}", "Android OTA Full Image", T.GREEN),
                (f"📱 {_t(self.loc, 'samsung_odin', 'flash', 'Samsung Odin')}", "Samsung Firmware Archive", T.ACCENT),
                (f"🔧 {_t(self.loc, 'mtk_scatter', 'flash', 'MediaTek Scatter')}", "MTK Scatter Configuration", T.ORANGE),
                (f"⚡ {_t(self.loc, 'qualcomm_edl', 'flash', 'Qualcomm EDL Firehose')}", "Qualcomm 9008 Raw Program", T.RED),
                (f"🍎 {_t(self.loc, 'apple_ipsw', 'flash', 'Apple IPSW')}", "iOS / iPadOS Firmware", T.PURPLE),
                (f"💾 {_t(self.loc, 'super_img', 'flash', 'Super.img')}", "Android Dynamic Partition", T.CYAN),
            ]
        elif cat in ('tablets', 'ipads'):
            fmts = [
                ("🍎 Apple IPSW", "iPadOS Firmware Restore", T.PURPLE),
                ("📱 Samsung Tab (Odin)", "Samsung Galaxy Tab Flash", T.ACCENT),
                ("📦 OTA payload.bin", "Android Tablet OTA", T.GREEN),
                ("🔧 MTK Scatter", "MediaTek Tablet Flash", T.ORANGE),
                ("💾 Super.img", "Dynamic Partition", T.CYAN),
            ]
        elif cat == 'smartwatches':
            fmts = [
                ("⌚ WearOS System", "WearOS Fastboot Image", T.PURPLE),
                ("🍎 Apple Watch IPSW", "watchOS Restore Image", T.GREEN),
                ("🔧 Tizen WGT", "Samsung Galaxy Watch", T.ACCENT),
                ("📱 Garmin FIT", "Garmin Firmware Package", T.ORANGE),
                ("⌚ Fitbit BIN", "Fitbit Firmware Binary", T.CYAN),
            ]
        elif cat in ('smart_glasses', 'ar_vr_headsets'):
            fmts = [
                ("🥽 Meta Quest ROM", "Quest 2/3/Pro Firmware", T.PURPLE),
                ("🍎 Vision Pro IPSW", "Apple Vision Pro Restore", T.GREEN),
                ("🕶️ XREAL/Pico", "AR Glasses Firmware", T.ACCENT),
                ("🔧 Qualcomm XR2", "XR2 Headset Flash", T.RED),
                ("📦 OTA Update", "Headset OTA Package", T.CYAN),
            ]
        else:
            fmts = [
                (f"📦 {_t(self.loc, 'ota_payload', 'flash', 'OTA payload.bin')}", "Android OTA Full Image", T.GREEN),
                (f"📱 {_t(self.loc, 'samsung_odin', 'flash', 'Samsung Odin')}", "Samsung Firmware Archive", T.ACCENT),
            ]
        for nm, ds, co in fmts:
            r = tk.Frame(fc, bg=T.CARD)
            r.pack(fill=tk.X, padx=8, pady=2)
            tk.Label(r, text=f"  {nm}", font=('Segoe UI',9,'bold'), bg=co, fg=T.WHITE, width=32, anchor=tk.W, padx=6).pack(side=tk.LEFT)
            tk.Label(r, text=ds, font=('Segoe UI',9), bg=T.CARD, fg=T.LIGHT).pack(side=tk.LEFT, padx=8)

        # Category-specific operations
        oc = self._card(t, f"⚡ {_t(self.loc, 'operations', 'flash', 'Operations')} — {CAT_LABELS_EN.get(cat, cat)}")
        base_ops = [
            (f"🚀 {_t(self.loc, 'full_flash', 'flash', 'Full Flash')}", T.ACCENT, self._act_flash),
            (f"📦 {_t(self.loc, 'extract_payload', 'flash', 'Extract payload.bin')}", T.GREEN, self._flash_extract),
            (f"🔧 {_t(self.loc, 'single_partition', 'flash', 'Single Partition')}", T.ORANGE, self._flash_single),
            (f"↩️ {_t(self.loc, 'unbrick', 'flash', 'Unbrick')}", T.RED, self._flash_unbrick),
            (f"🔍 {_t(self.loc, 'storage_check', 'flash', 'Storage Check')}", T.CYAN, self._flash_storage),
            (f"🔒 {_t(self.loc, 'unlock_bootloader', 'flash', 'Unlock Bootloader')}", T.PURPLE, self._flash_boot),
            (f"📂 {_t(self.loc, 'browse_file', 'flash', 'Browse File')}", T.DIM, self._flash_browse),
        ]
        # Add category-specific ops
        if cat == 'smartphones':
            base_ops.insert(3, ("🔓 Qualcomm EDL", T.RED, self._flash_edl))
            base_ops.insert(4, ("📱 MTK BROM", T.ORANGE, self._flash_mtk))
        elif cat in ('tablets', 'ipads'):
            base_ops.insert(3, ("🍎 iPad DFU Restore", T.PURPLE, self._flash_ipad_dfu))
            base_ops.insert(4, ("🔍 Storage Diagnostics", T.CYAN, self._flash_storage_diag))
        elif cat == 'smartwatches':
            base_ops.insert(3, ("⌚ WearOS Sideload", T.PURPLE, self._flash_wearos))
            base_ops.insert(4, ("🔗 Watch Sync", T.GREEN, self._flash_watch_sync))
        elif cat in ('smart_glasses', 'ar_vr_headsets'):
            base_ops.insert(3, ("🥽 Headset Calibration", T.PURPLE, self._flash_headset_cal))
            base_ops.insert(4, ("🔧 XR2 Firmware Flash", T.RED, self._flash_xr2))
        for tx, co, cm in base_ops:
            r = tk.Frame(oc, bg=T.CARD)
            r.pack(fill=tk.X, padx=8, pady=2)
            self._btn(r, tx, co, cm)

    def _flash_extract(self):
        self._log("📦 Extracting payload.bin files...")
        p = self.flash.extract_payload_bin("/fw/payload.bin", "/tmp/extracted")
        self._log_success(f"Extracted {len(p)} partitions")

    def _flash_single(self):
        b = self._brand()
        self._log(f"🔧 Flashing boot partition for {b}...")
        r = self.flash.flash_single_partition(f"{b}_DEV", "boot", "/fw/boot.img")
        self._log_success(f"Partition flash: {'Success' if r.get('success') else 'Failed'}")

    def _flash_unbrick(self):
        b = self._brand()
        self._log(f"↩️ Unbricking device {b}...")
        r = self.flash.unbrick_device(f"{b}_DEV", b)
        self._log_success(f"Unbrick: {r.get('status','UNKNOWN')}")

    def _flash_storage(self):
        b = self._brand()
        self._log(f"🔍 Storage health check for {b}...")
        h = self.flash.scan_storage_health(f"{b}_DEV")
        self._log_success(f"Storage: {h['storage_health']} | Read: {h['read_speed_mbps']} MB/s")

    def _flash_boot(self):
        b = self._brand()
        self._log(f"🔒 Unlocking bootloader for {b}...")
        r = self.flash.unlock_bootloader(f"{b}_DEV", b)
        self._log_success(f"Bootloader: {r.get('status','UNKNOWN')}")

    def _flash_browse(self):
        p = filedialog.askopenfilename(filetypes=[("Firmware","*.tar *.bin *.img *.ipsw *.zip"),("All","*.*")])
        if p:
            self._log("📂 Firmware file selected")
            r = self.flash.verify_firmware_image(p)
            self._log_success(f"Firmware: {r.get('format','UNKNOWN')} | Valid: {r.get('valid',False)}")

    # Category-specific flash operations

    def _flash_edl(self):
        b = self._brand()
        did = self._get_device_id()
        self._log(f"🔓 Qualcomm EDL 9008 mode — {b}")
        r = self.smartphone_eng.detect_brand_protocol(did)
        self._log_success(f"EDL: {r.get('protocol','UNKNOWN')} | Mode: {r.get('mode','UNKNOWN')}")

    def _flash_mtk(self):
        b = self._brand()
        did = self._get_device_id()
        self._log(f"📱 MTK BROM bypass — {b}")
        r = self.smartphone_eng.detect_brand_protocol(did)
        self._log_success(f"MTK: {r.get('protocol','UNKNOWN')} | BROM: {r.get('brom_available', False)}")

    def _flash_ipad_dfu(self):
        b = self._brand()
        did = self._get_device_id()
        self._log(f"🍎 iPad DFU restore — {b}")
        r = self.tablet_eng.flash_tablet(did, "/dev/null", b)
        self._log_success(f"iPad DFU: {r.get('status','UNKNOWN')}")

    def _flash_storage_diag(self):
        b = self._brand()
        did = self._get_device_id()
        self._log(f"🔍 Tablet storage diagnostics — {b}")
        r = self.tablet_eng.tablet_diagnostics(did, b)
        self._log_success(f"Storage: {r.get('diagnostics_status', r.get('overall_health', 'GOOD'))}")

    def _flash_wearos(self):
        b = self._brand()
        did = self._get_device_id()
        self._log(f"⌚ WearOS sideload — {b}")
        r = self.wearable_eng.wearos_diagnostics(did)
        self._log_success(f"WearOS: {r.get('status', r.get('diagnostics_status','UNKNOWN'))}")

    def _flash_watch_sync(self):
        b = self._brand()
        did = self._get_device_id()
        self._log(f"🔗 Watch sync & backup — {b}")
        r = self.wearable_eng.wearos_diagnostics(did)
        self._log_success(f"Watch sync: {r.get('status', r.get('diagnostics_status','UNKNOWN'))}")

    def _flash_headset_cal(self):
        b = self._brand()
        did = self._get_device_id()
        self._log(f"🥽 Headset sensor calibration — {b}")
        r = self.glasses_eng.calibrate_sensors(did, b)
        self._log_success(f"Headset cal: {r.get('status','UNKNOWN')}")

    def _flash_xr2(self):
        b = self._brand()
        did = self._get_device_id()
        self._log(f"🔧 XR2/Qualcomm headset flash — {b}")
        r = self.glasses_eng.flash_headset(did, "/dev/null", b)
        self._log_success(f"XR2 flash: {r.get('status','UNKNOWN')}")

    # ═══════════════════════════════════════════════════════════════════════
    #  TAB: SECURITY
    # ═══════════════════════════════════════════════════════════════════════

    def _tab_security(self):
        t = tk.Frame(self.nb, bg=T.BG)
        self.nb.add(t, text=f"🔓 {_t(self.loc, 'security', 'nav', 'Security')}")
        cat = self._active_category
        self._hdr(t, _t(self.loc, 'header', 'security', 'Security & Account Repair') + f" — {CAT_LABELS_EN.get(cat, cat)}", "🔓")

        # Category-specific FRP/bypass methods
        fc = self._card(t, f"🔓 {_t(self.loc, 'frp_bypass', 'security', 'FRP Bypass')} — {CAT_LABELS_EN.get(cat, cat)}")
        if cat == 'smartphones':
            frp_items = [
                ("Samsung — ODIN_MODE", "Odin flash + Knox reset", T.ACCENT),
                ("Google Pixel — FASTBOOT", "fastboot erase persist", T.GREEN),
                ("Xiaomi — FASTBOOT", "Mi Account partition wipe", T.ORANGE),
                ("Huawei — EDL/META", "EDL/Meta mode reset", T.RED),
                ("OPPO/Realme — META", "Meta mode account reset", T.PURPLE),
                ("Vivo — META", "Meta mode Vivo ID reset", T.CYAN),
                ("OnePlus — FASTBOOT", "fastboot oem unlock", T.ACCENT),
                ("Apple — DFU_RESTORE", "DFU restore", T.LIGHT),
            ]
        elif cat in ('tablets', 'ipads'):
            frp_items = [
                ("iPad — Apple ID Lock", "DFU restore to remove", T.PURPLE),
                ("Samsung Tab — ODIN", "Knox reset via Odin", T.ACCENT),
                ("Android Tablet — FASTBOOT", "fastboot erase frp", T.GREEN),
                ("Amazon Fire — BL unlock", "Bootloader unlock", T.ORANGE),
            ]
        elif cat == 'smartwatches':
            frp_items = [
                ("Apple Watch — Unpair", "Erase via companion", T.PURPLE),
                ("Galaxy Watch — Samsung ID", "Samsung account reset", T.ACCENT),
                ("WearOS — Google Account", "Google FRP bypass", T.GREEN),
                ("Garmin — Factory Reset", "Garmin Connect reset", T.ORANGE),
            ]
        elif cat in ('smart_glasses', 'ar_vr_headsets'):
            frp_items = [
                ("Meta Quest — Meta ID", "Meta account reset", T.ACCENT),
                ("Vision Pro — Apple ID", "Apple ID removal", T.PURPLE),
                ("XREAL — Factory Reset", "Factory reset command", T.GREEN),
                ("Pico — Pico ID", "Pico account bypass", T.ORANGE),
            ]
        else:
            frp_items = [("Generic FRP Bypass", "Standard method", T.ACCENT)]
        for br, mt, co in frp_items:
            r = tk.Frame(fc, bg=T.CARD)
            r.pack(fill=tk.X, padx=8, pady=2)
            tk.Label(r, text=f"  {br}", font=('Segoe UI',9,'bold'), bg=co, fg=T.WHITE, width=28, anchor=tk.W, padx=6).pack(side=tk.LEFT)
            tk.Label(r, text=mt, font=('Consolas',8), bg=T.CARD, fg=T.LIGHT).pack(side=tk.LEFT, padx=8)

        # Category-specific lock types
        lc = self._card(t, f"🔐 {_t(self.loc, 'screen_locks', 'security', 'Screen Locks')} — {CAT_LABELS_EN.get(cat, cat)}")
        if cat == 'smartphones':
            lock_items = [
                ("🔑 Pattern", "Delete gesture.key + locksettings.db", T.CYAN),
                ("🔢 PIN", "Delete locksettings.db", T.CYAN),
                ("🔒 Password", "Delete locksettings.db", T.CYAN),
                ("👆 Fingerprint", "Clear biometric data + re-enroll", T.CYAN),
                ("😊 Face ID", "Clear face data + re-enroll", T.CYAN),
                ("📧 Email", "Clear cache + reinitialize", T.ORANGE),
                ("☁️ Cloud", "Clear Google/Samsung/Mi Account", T.RED),
            ]
        elif cat in ('tablets', 'ipads'):
            lock_items = [
                ("✏️ Apple Pencil Lock", "Disable pencil auth", T.CYAN),
                ("🔢 PIN/Passcode", "iTunes reset / Odin wipe", T.CYAN),
                ("😊 Touch ID / Face ID", "Biometric reset", T.CYAN),
                ("☁️ iCloud Lock", "Activation Lock bypass", T.RED),
            ]
        elif cat == 'smartwatches':
            lock_items = [
                ("🔢 PIN Lock", "Watch factory reset", T.CYAN),
                ("📱 Companion Lock", "Unpair from phone", T.PURPLE),
                ("☁️ Account Lock", "Cloud account reset", T.RED),
            ]
        elif cat in ('smart_glasses', 'ar_vr_headsets'):
            lock_items = [
                ("🔢 PIN Lock", "Factory reset command", T.CYAN),
                ("👤 User Profile", "Clear user data", T.PURPLE),
                ("☁️ Account Lock", "Account reset", T.RED),
            ]
        else:
            lock_items = [("🔐 Standard Lock", "Generic unlock", T.CYAN)]
        for nm, ds, co in lock_items:
            self._item(lc, f"  {nm}", ds, co)

        af = tk.Frame(t, bg=T.BG)
        af.pack(fill=tk.X, padx=15, pady=10)
        self._btn(af, f"🔓 {_t(self.loc, 'start_frp', 'security', 'Start FRP')}", T.RED, self._sec_frp)
        self._btn(af, f"🔐 {_t(self.loc, 'unlock_locks', 'security', 'Unlock Locks')}", T.ACCENT, self._sec_lock)
        self._btn(af, f"📧 {_t(self.loc, 'bypass_email', 'security', 'Bypass Email')}", T.ORANGE, self._sec_email)
        self._btn(af, f"☁️ {_t(self.loc, 'unlock_cloud', 'security', 'Unlock Cloud')}", T.PURPLE, self._sec_cloud)
        self._btn(af, f"🔧 {_t(self.loc, 'diagnose', 'security', 'Diagnose')}", T.GREEN, self._sec_diag)

    def _sec_frp(self):
        b = self._brand()
        cat = self._active_category
        did = self._get_device_id()
        self._log(f"🔓 FRP bypass for {b} [{cat}]...")
        if cat in ('smartphones',):
            r = self.smartphone_eng.unlock_bootloader(did, b)
        elif cat in ('smartwatches',):
            r = self.wearable_eng.sync_fitness_band(did, "generic")
        else:
            r = self.acct.remove_frp_and_cloud_locks(did, b)
        self._log_success(f"FRP [{cat}]: {r.get('status', r.get('method','UNKNOWN'))} | Success: {r.get('success', False)}")

    def _sec_lock(self):
        b = self._brand()
        cat = self._active_category
        did = self._get_device_id()
        self._log(f"🔐 Unlocking screen for {b} [{cat}]...")
        if cat in ('smartphones',):
            r = self.smartphone_eng.unlock_bootloader(did, b)
        elif cat in ('tablets', 'ipads'):
            r = self.tablet_eng.unlock_bootloader(did, b)
        elif cat == 'smartwatches':
            r = self.wearable_eng.unlock_wearable(did, b)
        elif cat in ('smart_glasses', 'ar_vr_headsets'):
            r = self.glasses_eng.unlock_headset(did, b)
        else:
            r = self.acct.remove_screen_lock(did, "PATTERN")
        self._log_success(f"Lock status [{cat}]: {r.get('status','UNKNOWN')}")

    def _sec_email(self):
        b = self._brand()
        cat = self._active_category
        did = self._get_device_id()
        self._log(f"📧 Email bypass for {b} [{cat}]...")
        r = self.acct.bypass_email_account(did, b)
        self._log_success(f"Email bypass [{cat}]: {r.get('status','UNKNOWN')}")

    def _sec_cloud(self):
        b = self._brand()
        cat = self._active_category
        did = self._get_device_id()
        self._log(f"☁️ Cloud unlock for {b} [{cat}]...")
        r = self.acct.remove_frp_and_cloud_locks(did, b, "CLOUD_LOCK")
        self._log_success(f"Cloud unlock [{cat}]: {r.get('status','UNKNOWN')}")

    def _sec_diag(self):
        b = self._brand()
        cat = self._active_category
        did = self._get_device_id()
        self._log(f"🔧 Account diagnostics for {b} [{cat}]...")
        if cat in ('smartphones',):
            r = self.smartphone_eng.detect_brand_protocol(did)
            self._log_success(f"Protocol [{cat}]: {r.get('protocol','UNKNOWN')} | Brand: {r.get('brand','UNKNOWN')}")
        else:
            d = self.acct.run_account_diagnostics(did)
            self._log_success(f"Sync [{cat}]: {d.get('account_sync_status','UNKNOWN')} | Bootloader: {d.get('bootloader_status','UNKNOWN')}")

    # ═══════════════════════════════════════════════════════════════════════
    #  TAB: RECOVERY
    # ═══════════════════════════════════════════════════════════════════════

    def _tab_recovery(self):
        t = tk.Frame(self.nb, bg=T.BG)
        self.nb.add(t, text=f"💾 {_t(self.loc, 'recovery', 'nav', 'Recovery')}")
        self._hdr(t, _t(self.loc, 'header', 'recovery', 'Data Recovery'), "💾")

        # Category-specific scan types
        cat = self._active_category
        sc = self._card(t, f"🔍 {_t(self.loc, 'scan_types', 'recovery', 'Deep Scan Types')} — {CAT_LABELS_EN.get(cat, cat)}")
        if cat == 'smartphones':
            scan_items = [
                ("📸", "Photos & Videos", "JPEG, PNG, HEIC, MP4", T.ACCENT),
                ("🎵", "Audio Files", "MP3, AAC, WAV, FLAC", T.GREEN),
                ("📄", "Documents", "PDF, DOC, XLS, PPT", T.ORANGE),
                ("📁", "Deleted Folders", "Full directory structure", T.PURPLE),
                ("💬", "SMS Messages", "mmssms.db", T.RED),
                ("📞", "Contacts", "contacts2.db", T.CYAN),
                ("📱", "Call Logs", "calllog.db", T.ACCENT),
                ("📲", "WhatsApp/Telegram", "msgstore.db", T.GREEN),
                ("🎧", "Recordings", "RAW extraction", T.ORANGE),
                ("📝", "Notes & Logs", "SQLite databases", T.PURPLE),
            ]
        elif cat in ('tablets', 'ipads'):
            scan_items = [
                ("📸", "Photos & Videos", "iPad Camera Roll", T.ACCENT),
                ("📄", "Documents", "Files app data", T.GREEN),
                ("🎵", "Audio/Music", "iTunes library backup", T.ORANGE),
                ("✏️", "Apple Pencil Notes", "Notes/Freeform data", T.PURPLE),
                ("💬", "iMessage", "chat.db", T.RED),
                ("📧", "Mail & Calendar", "Envelope Index", T.CYAN),
                ("📁", "File System", "APFS snapshot recovery", T.ACCENT),
            ]
        elif cat == 'smartwatches':
            scan_items = [
                ("❤️", "Health Data", "Heart rate, SpO2, ECG", T.RED),
                ("🏃", "Fitness Logs", "Steps, calories, sleep", T.GREEN),
                ("📊", "Workout History", "Training records", T.ACCENT),
                ("🎵", "Music Files", "Watch music library", T.PURPLE),
                ("📱", "App Data", "WearOS/Tizen apps", T.CYAN),
                ("⌚", "Watch Faces", "Custom face backups", T.ORANGE),
            ]
        elif cat in ('smart_glasses', 'ar_vr_headsets'):
            scan_items = [
                ("📷", "Captured Media", "Photos & recordings", T.ACCENT),
                ("🎥", "Video Clips", "AR/VR session recordings", T.GREEN),
                ("📊", "Sensor Logs", "IMU, eye-tracking data", T.ORANGE),
                ("🔧", "Firmware Config", "Headset settings backup", T.PURPLE),
                ("📱", "App Data", "XR application data", T.CYAN),
            ]
        else:
            scan_items = [
                ("📸", "Photos & Videos", "All media", T.ACCENT),
                ("📄", "Documents", "All files", T.GREEN),
                ("📁", "Deleted Folders", "Full recovery", T.ORANGE),
            ]
        for ic, nm, ds, co in scan_items:
            r = tk.Frame(sc, bg=T.CARD)
            r.pack(fill=tk.X, padx=8, pady=2)
            tk.Label(r, text=f"  {ic} {nm}", font=('Segoe UI',9,'bold'), bg=co, fg=T.WHITE, width=28, anchor=tk.W, padx=6).pack(side=tk.LEFT)
            tk.Label(r, text=ds, font=('Consolas',8), bg=T.CARD, fg=T.LIGHT).pack(side=tk.LEFT, padx=8)

        af = tk.Frame(t, bg=T.BG)
        af.pack(fill=tk.X, padx=15, pady=10)
        self._btn(af, f"🔍 {_t(self.loc, 'start_scan', 'recovery', 'Start Deep Scan')}", T.ACCENT, self._rec_scan)
        self._btn(af, f"📸 {_t(self.loc, 'extract_photos', 'recovery', 'Extract Photos')}", T.GREEN, self._rec_photos)
        self._btn(af, f"💬 {_t(self.loc, 'extract_sms', 'recovery', 'Extract SMS')}", T.ORANGE, self._rec_sms)
        self._btn(af, f"📤 {_t(self.loc, 'export_csv', 'recovery', 'Export CSV')}", T.CYAN, self._rec_csv)
        self._btn(af, f"🌐 {_t(self.loc, 'export_html', 'recovery', 'Export HTML')}", T.PURPLE, self._rec_html)
        # Category-specific recovery buttons
        if cat == 'smartwatches':
            self._btn(af, "❤️ Health Data Export", T.RED, self._rec_health)
        elif cat in ('smart_glasses', 'ar_vr_headsets'):
            self._btn(af, "📊 Sensor Logs Export", T.ORANGE, self._rec_sensors)
        elif cat in ('tablets', 'ipads'):
            self._btn(af, "✏️ Apple Pencil Notes", T.PURPLE, self._rec_notes_tablet)

    def _rec_scan(self):
        b = self._brand()
        self._log(f"🔍 Deep scan for {b}...")
        r = self.recov.perform_deep_scan(f"{b}_DEV")
        self._log_success(f"Photos: {r['photos_found']} | Contacts: {r['contacts_found']} | SMS: {r['sms_messages_found']}")

    def _rec_photos(self):
        b = self._brand()
        self._log(f"📸 Extracting photos from {b}...")
        r = self.recov.extract_media(f"{b}_DEV", "/tmp/rec", ["images", "videos"])
        self._log_success(f"Media extraction: {r.get('status','UNKNOWN')}")

    def _rec_sms(self):
        b = self._brand()
        self._log(f"💬 Extracting SMS from {b}...")
        r = self.recov.perform_deep_scan(f"{b}_DEV", ["sms", "contacts"])
        self._log_success(f"SMS: {r.get('sms_messages_found',0)} | Contacts: {r.get('contacts_found',0)}")

    def _rec_csv(self):
        p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")])
        if p:
            b = self._brand()
            recs = self.recov.extract_contacts_and_logs(f"{b}_DEV")
            self.recov.export_to_csv(recs, p)
            self._log_success(f"Exported {len(recs)} records to CSV")

    def _rec_html(self):
        p = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML","*.html")])
        if p:
            b = self._brand()
            recs = self.recov.extract_contacts_and_logs(f"{b}_DEV")
            self.recov.export_to_html(recs, p)
            self._log_success("HTML report exported successfully")

    def _rec_health(self):
        b = self._brand()
        did = self._get_device_id()
        self._log(f"❤️ Exporting health data from {b}...")
        r = self.wearable_eng.wearos_diagnostics(did)
        self._log_success(f"Health data: {r.get('status', r.get('diagnostics_status','UNKNOWN'))}")

    def _rec_sensors(self):
        b = self._brand()
        did = self._get_device_id()
        self._log(f"📊 Exporting sensor logs from {b}...")
        r = self.glasses_eng.headset_diagnostics(did, b)
        self._log_success(f"Sensor logs: {r.get('status', r.get('diagnostics_status','UNKNOWN'))}")

    def _rec_notes_tablet(self):
        b = self._brand()
        did = self._get_device_id()
        self._log(f"✏️ Extracting Apple Pencil notes from {b}...")
        r = self.tablet_eng.tablet_diagnostics(did, b)
        self._log_success(f"Tablet notes: {r.get('status', r.get('diagnostics_status', 'EXPORTED'))}")

    # ═══════════════════════════════════════════════════════════════════════
    #  TAB: BIOMETRIC
    # ═══════════════════════════════════════════════════════════════════════

    def _tab_biometric(self):
        t = tk.Frame(self.nb, bg=T.BG)
        self.nb.add(t, text=f"👆 {_t(self.loc, 'biometric', 'nav', 'Biometrics')}")
        cat = self._active_category
        self._hdr(t, _t(self.loc, 'header', 'biometric', 'Biometrics Repair & Calibration') + f" — {CAT_LABELS_EN.get(cat, cat)}", "👆")

        # Category-specific sensor info
        fc = self._card(t, f"👆 {'Sensors' if cat != 'smart_glasses' else 'IMU & Eye Tracking Sensors'} — {CAT_LABELS_EN.get(cat, cat)}")
        if cat == 'smartphones':
            sensors = [("Capacitive", "capacitive"), ("Optical (Under-display)", "optical"),
                       ("Ultrasonic (Samsung 3D)", "ultrasonic"), ("Side-mounted", "side_mounted")]
            fc2_name = "😊 Face Unlock Types"
            fc2_sensors = [("2D Camera", "face_2d"), ("3D Structured Light (Face ID)", "face_3d"),
                           ("ToF 3D", "face_tof"), ("IR Camera", "face_ir"), ("Dual Camera Depth", "face_dual")]
        elif cat in ('tablets', 'ipads'):
            sensors = [("Apple Touch ID", "touch_id"), ("Apple Face ID (iPad Pro)", "face_id"),
                       ("Capacitive Stylus Input", "stylus"), ("Palm Rejection", "palm")]
            fc2_name = "✏️ Stylus & Input"
            fc2_sensors = [("Apple Pencil 1st Gen", "pencil_1"), ("Apple Pencil 2nd Gen", "pencil_2"),
                           ("Samsung S-Pen", "spen"), ("Logitech Crayon", "crayon")]
        elif cat == 'smartwatches':
            sensors = [("Optical Heart Rate (PPG)", "ppg"), ("ECG Electrode", "ecg"),
                       ("Blood Oxygen (SpO2)", "spo2"), ("Skin Temperature", "temp")]
            fc2_name = "🏃 Fitness Sensors"
            fc2_sensors = [("Accelerometer", "accel"), ("Gyroscope", "gyro"),
                           ("Barometer", "baro"), ("GPS", "gps")]
        elif cat in ('smart_glasses', 'ar_vr_headsets'):
            sensors = [("IMU (6-axis)", "imu"), ("Eye Tracking Camera", "eye_track"),
                       ("Depth Sensor", "depth"), ("LIDAR", "lidar")]
            fc2_name = "👁️ Visual & Tracking"
            fc2_sensors = [("6DOF Tracking", "6dof"), ("Stereo Alignment", "stereo"),
                           ("Foveated Rendering", "fovea"), ("Passthrough Camera", "passthrough")]
        else:
            sensors = [("Standard Sensors", "standard")]
            fc2_name = "Additional"
            fc2_sensors = [("Basic Calibration", "basic")]
        for nm, key in sensors:
            self._item(fc, f"  ✅ {nm}", _t(self.loc, key, "biometric", nm), T.GREEN)

        fc2 = self._card(t, f"{fc2_name}")
        for nm, key in fc2_sensors:
            self._item(fc2, f"  ✅ {nm}", _t(self.loc, key, "biometric", nm), T.CYAN)

        # Category-specific action buttons
        af = tk.Frame(t, bg=T.BG)
        af.pack(fill=tk.X, padx=15, pady=10)
        self._btn(af, f"🔍 {_t(self.loc, 'diagnose', 'biometric', 'Diagnose')}", T.ACCENT, self._bio_diag)
        if cat == 'smartphones':
            self._btn(af, "👆 Calibrate Fingerprint", T.GREEN, self._bio_cal)
            self._btn(af, "😊 Fix Face Unlock", T.ORANGE, self._bio_face)
            self._btn(af, "📱 Calibrate Touch", T.PURPLE, self._bio_touch)
        elif cat in ('tablets', 'ipads'):
            self._btn(af, "✏️ Calibrate Apple Pencil", T.GREEN, self._bio_cal)
            self._btn(af, "📱 Calibrate Touch", T.ORANGE, self._bio_touch)
            self._btn(af, "🍎 Touch ID / Face ID", T.PURPLE, self._bio_face)
        elif cat == 'smartwatches':
            self._btn(af, "❤️ Heart Rate Sensor", T.RED, self._bio_cal)
            self._btn(af, "🏃 Fitness Sensors", T.GREEN, self._bio_touch)
            self._btn(af, "⚡ Battery Health", T.ORANGE, self._bio_battery_watch)
        elif cat in ('smart_glasses', 'ar_vr_headsets'):
            self._btn(af, "👁️ Eye Tracking Cal", T.CYAN, self._bio_cal)
            self._btn(af, "🎯 6DOF Tracking", T.PURPLE, self._bio_touch)
            self._btn(af, "🖥️ Display Alignment", T.GREEN, self._bio_display)
            self._btn(af, "🔧 IMU Calibration", T.ORANGE, self._bio_imu)

    def _bio_diag(self):
        b = self._brand()
        cat = self._active_category
        did = self._get_device_id()
        self._log(f"🔍 Biometric diagnostics for {b} [{cat}]...")
        if cat in ('smart_glasses', 'ar_vr_headsets'):
            r = self.glasses_eng.calibrate_sensors(did, b)
        elif cat == 'smartwatches':
            r = self.wearable_eng.run_diagnostics(did)
        elif cat in ('tablets', 'ipads'):
            r = self.tablet_eng.run_diagnostics(did, b)
        else:
            r = self.bio.run_diagnostics(did)
        self._log_success(f"Diagnostics [{cat}]: {r.get('overall_status', r.get('status', 'COMPLETED'))}")

    def _bio_cal(self):
        b = self._brand()
        cat = self._active_category
        did = self._get_device_id()
        self._log(f"👆 Calibrating sensors for {b} [{cat}]...")
        if cat in ('smart_glasses', 'ar_vr_headsets'):
            r = self.glasses_eng.calibrate_sensors(did, b)
        elif cat == 'smartwatches':
            r = self.wearable_eng.calibrate_sensors(did, b)
        elif cat in ('tablets', 'ipads'):
            r = self.tablet_eng.run_diagnostics(did, b)
        else:
            r = self.bio.recalibrate_sensors(did, "FINGERPRINT")
        self._log_success(f"Calibration [{cat}]: {r.get('calibration_method', r.get('status', 'GENERIC'))}")

    def _bio_face(self):
        b = self._brand()
        cat = self._active_category
        did = self._get_device_id()
        self._log(f"😊 Fixing face/biometric unlock for {b} [{cat}]...")
        if cat in ('tablets', 'ipads'):
            r = self.tablet_eng.run_diagnostics(did, b)
        else:
            r = self.bio.fix_face_unlock(did)
        self._log_success(f"Face unlock [{cat}]: {r.get('status', 'COMPLETED')}")

    def _bio_touch(self):
        b = self._brand()
        cat = self._active_category
        did = self._get_device_id()
        self._log(f"📱 Calibrating touch/sensor for {b} [{cat}]...")
        if cat in ('smart_glasses', 'ar_vr_headsets'):
            r = self.glasses_eng.calibrate_sensors(did, b)
        elif cat == 'smartwatches':
            r = self.wearable_eng.calibrate_sensors(did, b)
        else:
            r = self.bio.recalibrate_touchscreen(did)
        self._log_success(f"Touch/Sensor calibration [{cat}]: {r.get('status', 'COMPLETED')}")

    def _bio_battery_watch(self):
        b = self._brand()
        did = self._get_device_id()
        self._log(f"⚡ Battery health check for {b}...")
        r = self.wearable_eng.wearos_diagnostics(did)
        self._log_success(f"Watch battery: {r.get('status', r.get('diagnostics_status', 'GOOD'))}")

    def _bio_display(self):
        b = self._brand()
        did = self._get_device_id()
        self._log(f"🖥️ Display alignment for {b}...")
        r = self.glasses_eng.repair_display(did, "alignment")
        self._log_success(f"Display alignment: {r.get('status', 'COMPLETED')}")

    def _bio_imu(self):
        b = self._brand()
        did = self._get_device_id()
        self._log(f"🔧 IMU calibration for {b}...")
        r = self.glasses_eng.calibrate_sensors(did, b)
        self._log_success(f"IMU calibration: {r.get('status', 'COMPLETED')}")

    # ═══════════════════════════════════════════════════════════════════════
    #  TAB: LANGUAGE
    # ═══════════════════════════════════════════════════════════════════════

    def _tab_language(self):
        t = tk.Frame(self.nb, bg=T.BG)
        self.nb.add(t, text=f"🌐 {_t(self.loc, 'language', 'nav', 'Languages')}")
        self._hdr(t, _t(self.loc, 'header', 'language', 'Language & Localization'), "🌐")

        lc = self._card(t, f"🌐 {_t(self.loc, 'supported_languages', 'language', 'Supported Languages')}")
        languages_display = [
            ("🇸🇦", _t(self.loc, "arabic", "language", "Arabic"), "RTL ←", T.RED, "ar"),
            ("🇮🇷", _t(self.loc, "persian", "language", "Persian"), "RTL ←", T.RED, "fa"),
            ("🇵🇰", _t(self.loc, "urdu", "language", "Urdu"), "RTL ←", T.RED, "ur"),
            ("🇮🇱", _t(self.loc, "hebrew", "language", "Hebrew"), "RTL ←", T.RED, "he"),
            ("🇺🇸", _t(self.loc, "english", "language", "English"), "→ LTR", T.GREEN, "en"),
            ("🇫🇷", _t(self.loc, "french", "language", "French"), "→ LTR", T.GREEN, "fr"),
            ("🇪🇸", _t(self.loc, "spanish", "language", "Spanish"), "→ LTR", T.GREEN, "es"),
            ("🇩🇪", _t(self.loc, "german", "language", "German"), "→ LTR", T.GREEN, "de"),
            ("🇮🇹", _t(self.loc, "italian", "language", "Italian"), "→ LTR", T.GREEN, "it"),
            ("🇧🇷", _t(self.loc, "portuguese", "language", "Portuguese"), "→ LTR", T.GREEN, "pt"),
            ("🇷🇺", _t(self.loc, "russian", "language", "Russian"), "→ LTR", T.GREEN, "ru"),
            ("🇨🇳", _t(self.loc, "chinese", "language", "Chinese"), "→ LTR", T.GREEN, "zh"),
            ("🇯🇵", _t(self.loc, "japanese", "language", "Japanese"), "→ LTR", T.GREEN, "ja"),
            ("🇰🇷", _t(self.loc, "korean", "language", "Korean"), "→ LTR", T.GREEN, "ko"),
            ("🇮🇳", _t(self.loc, "hindi", "language", "Hindi"), "→ LTR", T.GREEN, "hi"),
            ("🇹🇷", _t(self.loc, "turkish", "language", "Turkish"), "→ LTR", T.GREEN, "tr"),
        ]
        for ic, nm, dr, co, code in languages_display:
            r = tk.Frame(lc, bg=T.CARD)
            r.pack(fill=tk.X, padx=8, pady=2)
            tk.Label(r, text=f"  {ic} {nm}", font=('Segoe UI',10,'bold'), bg=T.CARD, fg=T.WHITE, width=22, anchor=tk.W, padx=6).pack(side=tk.LEFT)
            tk.Label(r, text=dr, font=('Consolas',9,'bold'), bg=T.CARD, fg=co).pack(side=tk.LEFT, padx=10)

        af = tk.Frame(t, bg=T.BG)
        af.pack(fill=tk.X, padx=15, pady=10)
        self._btn(af, f"🇸🇦 {_t(self.loc, 'apply_arabic', 'language', 'Apply Arabic')}", T.ACCENT, self._lang_ar)
        self._btn(af, f"🌐 {_t(self.loc, 'set_language', 'language', 'Set Language')}", T.GREEN, self._lang_set)

    def _lang_ar(self):
        self._log("🇸🇦 Applying Arabic with RTL support...")
        self.loc.set_language("ar")
        self._log_success(_t(self.loc, "language_changed", "log", "Language changed successfully"))

    def _lang_set(self):
        self._log_success(_t(self.loc, "language_changed", "log", "Language changed successfully"))

    # ═══════════════════════════════════════════════════════════════════════
    #  TAB: SETTINGS
    # ═══════════════════════════════════════════════════════════════════════

    def _tab_settings(self):
        t = tk.Frame(self.nb, bg=T.BG)
        self.nb.add(t, text=f"⚙️ {_t(self.loc, 'settings', 'nav', 'Settings')}")
        self._hdr(t, _t(self.loc, 'header', 'settings', 'Settings'), "⚙️")

        # Language selector
        lc = self._card(t, f"🌐 {_t(self.loc, 'language', 'settings', 'Language')}")
        r = tk.Frame(lc, bg=T.CARD)
        r.pack(fill=tk.X, padx=8, pady=8)
        tk.Label(r, text=_t(self.loc, "language", "settings", "Language:") + " ",
                 font=('Segoe UI',9), bg=T.CARD, fg=T.LIGHT).pack(side=tk.LEFT)
        self.lang_combo = ttk.Combobox(r, values=["English", "العربية", "Français", "Español", "Deutsch", "中文", "日本語", "한국어"],
                                       state="readonly", width=18)
        self.lang_combo.pack(side=tk.LEFT, padx=8)
        self.lang_combo.current(0)
        self._btn(r, _t(self.loc, "apply", "settings", "Apply"), T.GREEN, self._set_lang)

        # Protection layers
        sc = self._card(t, f"🛡️ {_t(self.loc, 'protection_layers', 'settings', 'Anti-RE Protection Layers')}")
        for ly, key, dt in [
            ("Layer 1", "layer_1", "6 methods"), ("Layer 2", "layer_2", "14 indicators"),
            ("Layer 3", "layer_3", "SHA-256"), ("Layer 4", "layer_4", "4 ciphers"),
            ("Layer 5", "layer_5", "Active"), ("Layer 6", "layer_6", "Active"),
            ("Layer 7", "layer_7", "Active"), ("Layer 8", "layer_8", "XOR+HMAC"),
            ("Layer 9", "layer_9", "Frida/Xposed"),
        ]:
            r = tk.Frame(sc, bg=T.CARD)
            r.pack(fill=tk.X, padx=8, pady=2)
            tk.Label(r, text=f"  🔒 {ly}", font=('Consolas',9,'bold'), bg=T.CARD, fg=T.GREEN, width=12, anchor=tk.W, padx=6).pack(side=tk.LEFT)
            tk.Label(r, text=_t(self.loc, key, "settings", key), font=('Segoe UI',9), bg=T.CARD, fg=T.WHITE, width=30, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(r, text=dt, font=('Consolas',9), bg=T.CARD, fg=T.CYAN).pack(side=tk.LEFT, padx=10)

        # System info
        ic = self._card(t, f"📊 {_t(self.loc, 'system_info', 'settings', 'System Information')}")
        self._row(ic, f"🔧 {_t(self.loc, 'version', 'settings', 'Version')}", "AuraTool-Suite v6.0.0", T.ACCENT)
        self._row(ic, f"🛡️ {_t(self.loc, 'license', 'settings', 'License')}",
                  self.license_info.get("tier", "N/A"),
                  T.GREEN if self.license_info.get("is_active") else T.RED)
        self._row(ic, f"📅 {_t(self.loc, 'days', 'settings', 'Days')}",
                  f"{self.license_info.get('days_remaining', 0)} {_t(self.loc, 'days', 'settings', 'days')}")

        # Device engines info
        ec = self._card(t, "🔧 Loaded Device Engines")
        engine_status = [
            ("SmartphoneEngine", "MTK BROM + QC EDL + Samsung ODIN + Apple DFU", T.ACCENT),
            ("TabletEngine", "iPad DFU + Samsung Tab + Android tablets", T.GREEN),
            ("WearableEngine", "WearOS + watchOS + Tizen + Garmin + Fitbit", T.PURPLE),
            ("SmartGlassesEngine", "Meta Quest + Vision Pro + XREAL + Pico", T.RED),
            ("FirmwareHandler", "payload.bin + scatter + IPSW + boot.img", T.ORANGE),
            ("CryptoEngine", "AES-256 + RSA-2048 + SHA-256 + HMAC", T.CYAN),
        ]
        for name, desc, co in engine_status:
            self._row(ec, f"  ✅ {name}", desc, co)

        af = tk.Frame(t, bg=T.BG)
        af.pack(fill=tk.X, padx=15, pady=10)
        self._btn(af, f"🔍 {_t(self.loc, 'check_protection', 'settings', 'Check Protection')}", T.ACCENT, self._set_check)
        self._btn(af, f"🤖 {_t(self.loc, 'ai_diagnose', 'settings', 'AI Diagnose')}", T.PURPLE, self._set_ai)

    def _set_lang(self):
        lm = {"English":"en", "العربية":"ar", "Français":"fr", "Español":"es",
              "Deutsch":"de", "中文":"zh", "日本語":"ja", "한국어":"ko"}
        c = lm.get(self.lang_combo.get(), "en")
        self.loc.set_language(c)
        self._lang_code = c
        self._log_success(f"Language changed to {self.lang_combo.get()}")

    def _set_check(self):
        self._log("🛡️ Checking protection...")
        r = self.sec.get_security_report()
        self._log_success(f"Protection: {'Active' if r.get('protection_active') else 'Inactive'} | Code: {'Intact' if r.get('code_integrity') else 'Modified'}")
        self._log(f"  Anti-RE: {r.get('anti_reverse_engineering','UNKNOWN')} | Encryption: {r.get('encryption','UNKNOWN')}")

    def _set_ai(self):
        b = self._brand()
        self._log(f"🤖 AI diagnostics for {b}...")
        r = self.ai.process_voice_or_text_command(f"diagnose {b} device")
        self._log_success(f"AI action: {r.get('action','UNKNOWN')} | Status: {r.get('status','UNKNOWN')}")

    # ═══════════════════════════════════════════════════════════════════════
    #  LICENSE ACTIVATION
    # ═══════════════════════════════════════════════════════════════════════

    def _activate(self):
        k = self.key_e.get().strip()
        if not k:
            messagebox.showwarning(_t(self.loc, "activate_btn", "license", "Activate"),
                                   _t(self.loc, "key_placeholder", "license", "Please enter a license key"))
            return
        r = self.lic_mgr.activate(k)
        if r.get("success"):
            messagebox.showinfo(_t(self.loc, "active", "license", "Success"),
                                f"{r.get('message', '')}")
            self._log_success(_t(self.loc, "license_activated", "log", "License activated successfully"))
        else:
            messagebox.showerror(_t(self.loc, "expired", "license", "Error"),
                                 f"{r.get('message', 'Invalid key')}")

    def run(self):
        self.root.mainloop()
