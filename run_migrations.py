"""
Script to migrate database and setup calendar
"""
import subprocess
import sys

# Fix Windows console encoding for Arabic text
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def run_command(command, description):
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr and "warning" not in result.stderr.lower():
        print("STDERR:", result.stderr)
    return result.returncode

# Navigate to project directory
import os
os.chdir(r'C:\Users\Microsoft\Desktop\local_progs\tahfeed_professional_website_2\myproject')

# Run migrations
print("\nبدء عملية الترحيل...")
exit_code = run_command("python manage.py migrate", "تطبيق الترحيلات")

if exit_code == 0:
    print("\n✓ تم تطبيق الترحيلات بنجاح!")
    
    # Run setup calendar
    print("\nإعداد التقويم الدراسي...")
    exit_code = run_command("python setup_calendar.py", "إنشاء التقويم")
    
    if exit_code == 0:
        print("\n✓ تم إعداد التقويم بنجاح!")
    else:
        print("\n✗ حدث خطأ في إعداد التقويم")
else:
    print("\n✗ حدث خطأ في تطبيق الترحيلات")

print("\n" + "="*60)
print("يمكنك الآن تشغيل: python manage.py runserver")
print("="*60)
