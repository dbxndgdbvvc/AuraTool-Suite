import sys
import re
import hashlib

def advanced_analyze(file_path):
    print(f"[*] جاري بدء الهندسة العكسية والتحليل المتقدم للملف: {file_path}")
    try:
        with open(file_path, "rb") as f:
            data = f.read()
           
        # حساب البصمة التشفيرية للملف
        sha256 = hashlib.sha256(data).hexdigest()
        print(f"[+] SHA256 Hash: {sha256}")
       
        # تحويل المحتوى إلى نص واستخراج الروابط والأنماط
        text_content = data.decode(errors='ignore')
        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text_content)
        unique_urls = list(set(urls))
       
        print(f"[+] إجمالي الروابط والمصادر المكتشفة: {len(unique_urls)}")
        for url in unique_urls[:15]:  # عرض أول 15 رابطاً مهماً
            print(f"    -> {url}")
           
    except Exception as e:
        print(f"[-] حدث خطأ أثناء التحليل: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        advanced_analyze(sys.argv[1])
    else:
        print("الاستخدام: python3 aura_advanced_re.py <مسار_الملف>")
