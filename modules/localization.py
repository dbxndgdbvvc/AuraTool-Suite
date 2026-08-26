"""
AuraTool-Suite — Global Multi-Language System (i18n) & Arabic Shaping
======================================================================
Comprehensive internationalization supporting LTR and RTL languages,
with built-in character reshaping and bidirectional rendering support.
"""

import logging

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_ARABIC_RESHAPER = True
except ImportError:
    HAS_ARABIC_RESHAPER = False


class LocalizationManager:
    """Handles global translations, RTL/LTR layout, and Arabic character shaping."""

    SUPPORTED_LANGUAGES = {
        "en": "English",
        "ar": "العربية (Arabic)",
        "es": "Español (Spanish)",
        "fr": "Français (French)",
        "de": "Deutsch (German)",
        "ru": "Русский (Russian)",
        "zh": "中文 (Chinese)",
        "ja": "日本語 (Japanese)",
        "tr": "Türkçe (Turkish)",
        "hi": "हिन्दी (Hindi)",
        "pt": "Português (Portuguese)",
        "ko": "한국어 (Korean)",
        "id": "Bahasa Indonesia (Indonesian)",
        "fa": "فارسی (Persian)",
        "ur": "اردو (Urdu)",
        "th": "ไทย (Thai)",
    }

    RTL_LANGUAGES = ["ar", "fa", "ur"]

    LOG_MESSAGES = {
        "en": {
            "FLASHING_START": "Firmware flashing started",
            "FRP_SUCCESS": "FRP bypass completed successfully",
            "VIRUS_REMOVED": "Virus scan and removal complete",
            "RECOVERY_START": "Deep data recovery scan started",
        },
        "ar": {
            "FLASHING_START": "تم بدء تفليش البرنامج الثابت",
            "FRP_SUCCESS": "تم تجاوز FRP بنجاح",
            "VIRUS_REMOVED": "اكتمل فحص الفيروسات وإزالته",
            "RECOVERY_START": "تم بدء فحص استعادة البيانات العميق",
        },
        "es": {
            "FLASHING_START": "Inicio del flasheo de firmware",
            "FRP_SUCCESS": "Bypass FRP completado exitosamente",
            "VIRUS_REMOVED": "Escaneo y eliminación de virus completados",
            "RECOVERY_START": "Inicio del escaneo profundo de recuperación",
        },
        "pt": {
            "FLASHING_START": "Flashagem de firmware iniciada",
            "FRP_SUCCESS": "Bypass FRP concluído com sucesso",
            "VIRUS_REMOVED": "Verificação e remoção de vírus concluídas",
            "RECOVERY_START": "Varredura profunda de recuperação de dados iniciada",
        },
        "ko": {
            "FLASHING_START": "펌웨어 플래싱 시작됨",
            "FRP_SUCCESS": "FRP 우회 성공적으로 완료됨",
            "VIRUS_REMOVED": "바이러스 검사 및 제거 완료",
            "RECOVERY_START": "심층 데이터 복구 스캔 시작됨",
        },
        "id": {
            "FLASHING_START": "Flashing firmware dimulai",
            "FRP_SUCCESS": "Bypass FRP berhasil diselesaikan",
            "VIRUS_REMOVED": "Pemindaian dan penghapusan virus selesai",
            "RECOVERY_START": "Pemindaian pemulihan data mendalam dimulai",
        },
        "fa": {
            "FLASHING_START": "شروع فلش کردن فریمور",
            "FRP_SUCCESS": "دور زدن FRP با موفقیت انجام شد",
            "VIRUS_REMOVED": "اسکن و حذف ویروس کامل شد",
            "RECOVERY_START": "اسکن بازیابی عمیق داده آغاز شد",
        },
        "ur": {
            "FLASHING_START": "فیرم ویئر فلیشنگ شروع ہوئی",
            "FRP_SUCCESS": "FRP بائی پاس کامیابی سے مکمل ہوا",
            "VIRUS_REMOVED": "وائرس اسکین اور حذف مکمل",
            "RECOVERY_START": "گہری ڈیٹا ریکوری اسکین شروع ہوئی",
        },
        "th": {
            "FLASHING_START": "เริ่มการแฟลชเฟิร์มแวร์",
            "FRP_SUCCESS": "การข้าม FRP เสร็จสมบูรณ์",
            "VIRUS_REMOVED": "การสแกนและลบไวรัสเสร็จสมบูรณ์",
            "RECOVERY_START": "เริ่มการสแกนกู้คืนข้อมูลเชิงลึก",
        },
    }

    TRANSLATIONS = {
        "en": {
            "title": "AuraTool-Suite — Universal Desktop Platform 2030",
            "license_lbl": "License Status:",
            "ai_tab": "Aura-AI Diagnostic",
            "vendor_tab": "Vendor Operations",
            "repair_tab": "Ultimate Repair",
            "recovery_tab": "Data Recovery",
            "chat_tab": "Live Chat Rooms",
            "stream_tab": "Media Stream Network",
            "store_tab": "E-Commerce Store",
            "settings_tab": "Settings & Language",
            "run_ai": "Run AI Command",
            "flash": "Flash Firmware Image",
            "bypass_frp": "Bypass FRP & Cloud Lock",
            "start_scan": "Start Deep Scan",
            "checkout": "Complete Checkout",
            "activate_btn": "Activate Key",
            "license_bar_lbl": "License Activation & HWID Binding",
        },
        "ar": {
            "title": "AuraTool-Suite — المنصة الشاملة لإدارة وصيانة الأجهزة 2030",
            "license_lbl": "حالة الترخيص:",
            "ai_tab": "المساعد الذكي Aura-AI",
            "vendor_tab": "عمليات الشركات",
            "repair_tab": "الإصلاح الشامل",
            "recovery_tab": "استعادة البيانات",
            "chat_tab": "غرف الدردشة المباشرة",
            "stream_tab": "شبكة بث الوسائط",
            "store_tab": "متجر قطع الغيار والتراخيص",
            "settings_tab": "الإعدادات واللغة",
            "run_ai": "تشغيل الأمر الذكي",
            "flash": "بدء تفليش النظام",
            "bypass_frp": "تجاوز حماية FRP وقفل الحساب",
            "start_scan": "بدء الفحص العميق",
            "checkout": "إتمام الشراء",
            "activate_btn": "تفعيل المفتاح",
            "license_bar_lbl": "تفعيل الترخيص وربط معرف العتاد (HWID)",
        },
        "es": {
            "title": "AuraTool-Suite — Marco Avanzado de Mantenimiento",
            "license_lbl": "Estado de Licencia:",
            "ai_tab": "Diagnóstico Aura-AI",
            "vendor_tab": "Operaciones de Fabricante",
            "repair_tab": "Reparación Definitiva",
            "recovery_tab": "Recuperación de Datos",
            "chat_tab": "Salas de Chat",
            "stream_tab": "Red de Transmisión",
            "store_tab": "Tienda Electrónica",
            "settings_tab": "Configuración e Idioma",
            "run_ai": "Ejecutar Comando AI",
            "flash": "Iniciar Flasheo",
            "bypass_frp": "Bypass FRP y Bloqueo de Nube",
            "start_scan": "Iniciar Escaneo Profundo",
            "checkout": "Finalizar Compra",
            "activate_btn": "Activar Clave",
            "license_bar_lbl": "Activación de Licencia y Enlace HWID",
        },
        "pt": {
            "title": "AuraTool-Suite — Plataforma Universal de Desktop 2030",
            "license_lbl": "Status da Licença:",
            "ai_tab": "Diagnóstico Aura-AI",
            "vendor_tab": "Operações do Fabricante",
            "repair_tab": "Reparação Definitiva",
            "recovery_tab": "Recuperação de Dados",
            "chat_tab": "Salas de Chat ao Vivo",
            "stream_tab": "Rede de Transmissão de Mídia",
            "store_tab": "Loja de E-Commerce",
            "settings_tab": "Configurações e Idioma",
            "run_ai": "Executar Comando AI",
            "flash": "Iniciar Flash de Firmware",
            "bypass_frp": "Bypass FRP e Bloqueio na Nuvem",
            "start_scan": "Iniciar Verificação Profunda",
            "checkout": "Finalizar Compra",
            "activate_btn": "Ativar Chave",
            "license_bar_lbl": "Ativação de Licença e Vinculação HWID",
        },
        "ko": {
            "title": "AuraTool-Suite — 범용 데스크톱 플랫폼 2030",
            "license_lbl": "라이선스 상태:",
            "ai_tab": "Aura-AI 진단",
            "vendor_tab": "벤더 운영",
            "repair_tab": "최종 수리",
            "recovery_tab": "데이터 복구",
            "chat_tab": "실시간 채팅방",
            "stream_tab": "미디어 스트림 네트워크",
            "store_tab": "이커머스 스토어",
            "settings_tab": "설정 및 언어",
            "run_ai": "AI 명령 실행",
            "flash": "펌웨어 이미지 플래싱",
            "bypass_frp": "FRP 및 클라우드 잠금 우회",
            "start_scan": "심층 스캔 시작",
            "checkout": "결제 완료",
            "activate_btn": "키 활성화",
            "license_bar_lbl": "라이선스 활성화 및 HWID 바인딩",
        },
        "id": {
            "title": "AuraTool-Suite — Platform Desktop Universal 2030",
            "license_lbl": "Status Lisensi:",
            "ai_tab": "Diagnostik Aura-AI",
            "vendor_tab": "Operasi Vendor",
            "repair_tab": "Perbaikan Utama",
            "recovery_tab": "Pemulihan Data",
            "chat_tab": "Ruangan Chat Langsung",
            "stream_tab": "Jaringan Streaming Media",
            "store_tab": "Toko E-Commerce",
            "settings_tab": "Pengaturan & Bahasa",
            "run_ai": "Jalankan Perintah AI",
            "flash": "Flash Gambar Firmware",
            "bypass_frp": "Bypass FRP & Kunci Cloud",
            "start_scan": "Mulai Pindai Mendalam",
            "checkout": "Selesaikan Pembayaran",
            "activate_btn": "Aktifkan Kunci",
            "license_bar_lbl": "Aktivasi Lisensi & Pengikatan HWID",
        },
        "fa": {
            "title": "AuraTool-Suite — پلتفرم دسکتاپ جهانی 2030",
            "license_lbl": "وضعیت مجوز:",
            "ai_tab": "تشخیص Aura-AI",
            "vendor_tab": "عملیات فروشنده",
            "repair_tab": "تعمیر نهایی",
            "recovery_tab": "بازیابی داده",
            "chat_tab": "اتاق‌های چت زنده",
            "stream_tab": "شبکه پخش رسانه",
            "store_tab": "فروشگاه آنلاین",
            "settings_tab": "تنظیمات و زبان",
            "run_ai": "اجرای دستور AI",
            "flash": "فلش تصویر فریمور",
            "bypass_frp": "دور زدن FRP و قفل ابری",
            "start_scan": "شروع اسکن عمیق",
            "checkout": "تکمیل خرید",
            "activate_btn": "فعال‌سازی کلید",
            "license_bar_lbl": "فعال‌سازی مجوز و اتصال HWID",
        },
        "ur": {
            "title": "AuraTool-Suite — یونیورسل ڈیسکٹاپ پلیٹ فارم 2030",
            "license_lbl": "لائسنس کی حالت:",
            "ai_tab": "Aura-AI تشخیص",
            "vendor_tab": "وینڈر آپریشنز",
            "repair_tab": "آخری مرمت",
            "recovery_tab": "ڈیٹا ریکوری",
            "chat_tab": "لائیو چیٹ رومز",
            "stream_tab": "میڈیا سٹریم نیٹ ورک",
            "store_tab": "ای کامرس اسٹور",
            "settings_tab": "ترتیبات اور زبان",
            "run_ai": "AI کمانڈ چلائیں",
            "flash": "فیرم ویئر امیج فلیش",
            "bypass_frp": "FRP اور کلاؤڈ لاک بائی پاس",
            "start_scan": "گہری اسکین شروع کریں",
            "checkout": "چیک آؤٹ مکمل کریں",
            "activate_btn": "کلید فعال کریں",
            "license_bar_lbl": "لائسنس فعال سازی اور HWID بائنڈنگ",
        },
        "th": {
            "title": "AuraTool-Suite — แพลตฟอร์มเดสก์ท็อปสากล 2030",
            "license_lbl": "สถานะใบอนุญาต:",
            "ai_tab": "การวินิจฉัย Aura-AI",
            "vendor_tab": "การดำเนินงานของผู้ผลิต",
            "repair_tab": "การซ่อมแซมขั้นสุดท้าย",
            "recovery_tab": "การกู้คืนข้อมูล",
            "chat_tab": "ห้องแชทสด",
            "stream_tab": "เครือข่ายสตรีมมิ่งสื่อ",
            "store_tab": "ร้านค้าอีคอมเมิร์ซ",
            "settings_tab": "การตั้งค่าและภาษา",
            "run_ai": "เรียกใช้คำสั่ง AI",
            "flash": "แฟลชรูปภาพเฟิร์มแวร์",
            "bypass_frp": "ข้าม FRP และล็อกคลาวด์",
            "start_scan": "เริ่มการสแกนเชิงลึก",
            "checkout": "ชำระเงินให้เสร็จสิ้น",
            "activate_btn": "เปิดใช้งานคีย์",
            "license_bar_lbl": "การเปิดใช้งานใบอนุญาตและการเชื่อมโยง HWID",
        },
    }

    def __init__(self, default_lang: str = "en"):
        self.logger = logging.getLogger("AuraTool.Localization")
        self.current_lang = default_lang if default_lang in self.SUPPORTED_LANGUAGES else "en"

    def set_language(self, lang_code: str) -> bool:
        if lang_code in self.SUPPORTED_LANGUAGES:
            self.current_lang = lang_code
            self.logger.info(f"Language set to: {self.SUPPORTED_LANGUAGES[lang_code]}")
            return True
        return False

    def is_rtl(self) -> bool:
        return self.current_lang in self.RTL_LANGUAGES

    def reshape_arabic_text(self, text: str) -> str:
        """Reshapes and applies bidirectional rendering to Arabic text for proper desktop GUI rendering."""
        if not text or self.current_lang not in ("ar", "fa", "ur"):
            return text

        if HAS_ARABIC_RESHAPER:
            try:
                reshaped = arabic_reshaper.reshape(text)
                return get_display(reshaped)
            except Exception as e:
                self.logger.warning(f"Arabic/Persian/Urdu text reshaping failed: {e}")

        return text

    def get_string(self, key: str) -> str:
        lang_dict = self.TRANSLATIONS.get(self.current_lang, self.TRANSLATIONS["en"])
        raw_str = lang_dict.get(key, self.TRANSLATIONS["en"].get(key, key))
        return self.reshape_arabic_text(raw_str)

    def apply_locale_to_device(self, device_id: str, lang_code: str, enable_rtl: bool = False) -> bool:
        """Apply a locale setting to a connected device.

        Simulates pushing a language configuration to the device via ADB/fastboot.
        """
        if lang_code not in self.SUPPORTED_LANGUAGES:
            self.logger.warning(f"Unsupported language code: {lang_code}")
            return False

        self.logger.info(
            f"Applying locale '{self.SUPPORTED_LANGUAGES[lang_code]}' ({lang_code}) "
            f"to device [{device_id}]" + (" with RTL" if enable_rtl else "")
        )
        # In production this would run: adb shell setprop persist.sys.locale {lang_code}
        return True

    def configure_csc(self, device_id: str, csc_code: str) -> bool:
        """Configure the CSC (Country Specific Code) for regional features.

        CSC controls carrier branding, regional apps, and feature availability.
        Common codes: XSG (UAE), KSA (Saudi Arabia), TUR (Turkey), etc.
        """
        if not csc_code or len(csc_code) < 3:
            self.logger.warning(f"Invalid CSC code: {csc_code}")
            return False

        self.logger.info(f"Configuring CSC '{csc_code}' on device [{device_id}]")
        # In production this would modify the CSC partition / NV data
        return True

    def unhide_system_languages(self, device_id: str) -> bool:
        """Unhide system languages that are restricted by carrier or OEM.

        Some carriers hide languages from the settings UI. This unlocks them.
        """
        self.logger.info(f"Unhiding system languages on device [{device_id}]")
        # In production this would modify the carrier config overlay
        return True

    def get_arabic_log(self, key: str) -> str:
        """Return a localized log message for the given key."""
        lang_dict = self.LOG_MESSAGES.get(self.current_lang, self.LOG_MESSAGES.get("en", {}))
        raw_msg = lang_dict.get(key, key)
        return self.reshape_arabic_text(raw_msg)
