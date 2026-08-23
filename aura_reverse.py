import os
import sys
import zipfile

class AuraReverseEngine:
    def __init__(self, target_path):
        self.target_path = target_path

    def analyze_apk(self):
        """فحص وتحليل حزم أندرويد APK كجزء من أدوات الهندسة العكسية"""
        if not os.path.exists(self.target_path):
            print(f"[-] الخطأ: الملف غير موجود -> {self.target_path}")
            return

        print(f"[*] جاري بدء الهندسة العكسية والتحليل للملف: {self.target_path}")
       
        # ملفات الـ APK هي في الأصل ملفات مضغوطة بصيغة ZIP
        if zipfile.is_zipfile(self.target_path):
            print("[+] الملف سليم وهو عبارة عن حزمة صالحة للتحليل.")
            with zipfile.ZipFile(self.target_path, 'r') as apk:
                files = apk.namelist()
                print(f"[+] إجمالي الملفات الداخلية المكتشفة: {len(files)}")
               
                # البحث عن الملفات الحساسة أو الرئيسية
                if "AndroidManifest.xml" in files:
                    print("[✓] تم العثور على ملف التكوين الأساسي: AndroidManifest.xml")
                if "classes.dex" in files:
                    print("[✓] تم العثور على ملف الشيفرة البرمجية: classes.dex")
        else:
            print("[-] تحذير: الملف ليس حزمة APK صالحة أو أنه مشفر/تالف.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("الاستخدام: python3 aura_reverse.py <مسار_ملف_APK>")
    else:
        engine = AuraReverseEngine(sys.argv[1])
        engine.analyze_apk()
