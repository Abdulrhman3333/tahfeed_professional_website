"""
Seed demo data for the Attendance Platform.

Generates:
  - 1 manager account (superuser)
  - 5 stage accounts (each with a StageProfile)
  - ~20 students per stage with fake national IDs, Arabic names, Saudi phones
  - 3 days of historical Attendance rows with a mix of statuses

WARNING: This command deletes ALL existing Student, Attendance,
AttendanceChangeLog, StageProfile, and non-admin User data before
re-seeding. Do NOT run it against a production database. It is safe to
run multiple times (it is destructive-idempotent: it wipes and recreates).
"""

import random
import sys
import codecs

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from datetime import date, timedelta

from quran_center.models import (
    Student, Attendance, AttendanceChangeLog, StageProfile, Teacher,
    TeacherAttendance, STAGE_CHOICES, PERIOD_STATUS_CHOICES,
)

# Fix Windows console encoding for Arabic text output
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# --- Name pools for realistic Arabic demo data ---

MALE_FIRST = [
    'أحمد', 'محمد', 'عبدالله', 'عبدالرحمن', 'خالد', 'سعد', 'فهد',
    'ناصر', 'يوسف', 'إبراهيم', 'عمر', 'علي', 'حسن', 'سلمان',
    'طارق', 'ماجد', 'وليد', 'راشد', 'بدر', 'سامي', 'عبدالعزيز',
    'زياد', 'هاني', 'فارس', 'مشعل',
]

FEMALE_FIRST = [
    'فاطمة', 'عائشة', 'مريم', 'سارة', 'نورة', 'هند', 'لطيفة',
    'عبير', 'شهد', 'رنا', 'الجوهرة', 'أسماء', 'زينب', 'صفية',
    'ريم', 'ديمة', 'جنى', 'حور', 'روان', 'إيمان', 'ريماس',
]

FATHER_NAMES = [
    'محمد', 'عبدالله', 'علي', 'حسن', 'إبراهيم', 'خالد', 'سعد',
    'ناصر', 'عبدالرحمن', 'سلمان', 'أحمد', 'فهد', 'يوسف', 'بدر',
    'ماجد', 'عبدالعزيز', 'راشد', 'سعيد', 'وليد', 'طالع',
]

FAMILY_NAMES = [
    'العتيبي', 'القحطاني', 'الحربي', 'الشمري', 'الدوسري',
    'الغامدي', 'الزهراني', 'المالكي', 'السبيعي', 'البقمي',
    'الرشيدي', 'العنزي', 'المطيري', 'الحازمي', 'السلمي',
    'الجهني', 'الشهري', 'البلوي', 'المعمري', 'الخالدي',
]

# Stage account usernames (English for login reliability)
STAGE_ACCOUNTS = [
    ('stage_mubkira', 'مبكرة', 'أ. فاطمة الزهراني'),
    ('stage_aaliya', 'عليا', 'أ. عائشة العتيبي'),
    ('stage_mutawasit', 'متوسط', 'أ. أحمد القحطاني'),
    ('stage_thaanawi', 'ثانوي', 'أ. محمد الشمري'),
    ('stage_jaami3i', 'جامعي', 'أ. خالد الحربي'),
]

# Teacher names per stage (3-6 real teachers per stage)
TEACHER_NAMES = {
    'مبكرة': ['أ. فاطمة الزهراني', 'أ. نورة العتيبي', 'أ. سارة القحطاني', 'أ. هند الشمري'],
    'عليا': ['أ. عائشة العتيبي', 'أ. عبير الحربي', 'أ. رنا الدوسري', 'أ. شهد الغامدي', 'أ. مريم الزهراني'],
    'متوسط': ['أ. أحمد القحطاني', 'أ. خالد العتيبي', 'أ. سعد الحربي', 'أ. فهد الشمري'],
    'ثانوي': ['أ. محمد الشمري', 'أ. عبدالله العتيبي', 'أ. يوسف القحطاني', 'أ. عمر الحربي', 'أ. علي الدوسري', 'أ. حسن الغامدي'],
    'جامعي': ['أ. خالد الحربي', 'أ. ناصر العتيبي', 'أ. طارق القحطاني'],
}

MANAGER_USERNAME = 'manager'
DEFAULT_PASSWORD = 'demo12345'
STUDENTS_PER_STAGE = 20


def generate_national_id(used):
    """Generate a unique 10-digit national ID string."""
    while True:
        nid = ''.join(random.choices('0123456789', k=10))
        if nid not in used:
            used.add(nid)
            return nid


def generate_phone():
    """Generate a Saudi-format mobile number: 05XXXXXXXX."""
    return '05' + ''.join(random.choices('0123456789', k=8))


def generate_full_name():
    first = random.choice(MALE_FIRST + FEMALE_FIRST)
    father = random.choice(FATHER_NAMES)
    family = random.choice(FAMILY_NAMES)
    return f'{first} {father} {family}'


class Command(BaseCommand):
    help = (
        'Seed demo data: 1 manager + 5 stage accounts + ~20 students per '
        'stage + 3 days of historical attendance. DESTRUCTIVE: wipes '
        'existing data first. Do NOT run twice on a database you care about.'
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            'WARNING: This will DELETE all existing users, students, and attendance. '
            'Proceeding...'
        ))

        # --- Clean slate ---
        AttendanceChangeLog.objects.all().delete()
        Attendance.objects.all().delete()
        Student.objects.all().delete()
        Teacher.objects.all().delete()
        StageProfile.objects.all().delete()
        # Delete non-admin users (keep the Django default admin if present)
        User.objects.filter(is_superuser=False).delete()
        # Also delete any existing superusers to avoid duplicate manager
        User.objects.filter(is_superuser=True).delete()

        # --- Create manager account ---
        manager = User.objects.create_superuser(
            username=MANAGER_USERNAME,
            password=DEFAULT_PASSWORD,
            first_name='المدير',
            last_name='العام',
        )
        self.stdout.write(self.style.SUCCESS(
            f'  Manager:  username={MANAGER_USERNAME}  password={DEFAULT_PASSWORD}'
        ))

        # --- Create 5 stage accounts ---
        stage_users = {}
        for username, stage_code, display_name_parts in STAGE_ACCOUNTS:
            parts = display_name_parts.split(' ', 1)
            user = User.objects.create_user(
                username=username,
                password=DEFAULT_PASSWORD,
                first_name=parts[0] if len(parts) > 0 else '',
                last_name=parts[1] if len(parts) > 1 else '',
            )
            StageProfile.objects.create(user=user, managed_stage=stage_code)
            stage_users[stage_code] = user
            self.stdout.write(self.style.SUCCESS(
                f'  Stage:    username={username}  password={DEFAULT_PASSWORD}  '
                f'stage={stage_code}'
            ))

        # --- Create teachers per stage (3-6 per stage) ---
        stage_teachers = {}
        total_teachers = 0
        for _, stage_code, _ in STAGE_ACCOUNTS:
            stage_teachers[stage_code] = []
            for tname in TEACHER_NAMES.get(stage_code, []):
                t = Teacher.objects.create(
                    name=tname,
                    stage=stage_code,
                    phone=generate_phone(),
                )
                stage_teachers[stage_code].append(t)
                total_teachers += 1

        self.stdout.write(self.style.SUCCESS(
            f'  Created {total_teachers} teachers across 5 stages.'
        ))

        # --- Create students (assigned to random teachers in their stage) ---
        used_ids = set()
        total_students = 0
        for _, stage_code, _ in STAGE_ACCOUNTS:
            teachers = stage_teachers[stage_code]
            for _ in range(STUDENTS_PER_STAGE):
                teacher = random.choice(teachers) if teachers else None
                Student.objects.create(
                    national_id=generate_national_id(used_ids),
                    full_name=generate_full_name(),
                    stage=stage_code,
                    teacher=teacher,
                    student_phone=generate_phone(),
                    parent_phone=generate_phone(),
                )
                total_students += 1

        self.stdout.write(self.style.SUCCESS(
            f'  Created {total_students} students across 5 stages.'
        ))

        # --- Seed 3 days of historical attendance ---
        today = date.today()
        statuses = [c[0] for c in PERIOD_STATUS_CHOICES]
        # Weight: mostly حاضر, some غائب, fewer others
        weighted = ['حاضر'] * 70 + ['غائب'] * 12 + ['متأخر'] * 6 + ['مستأذن'] * 6 + ['غياب بعذر'] * 6

        all_students = list(Student.objects.all())
        for day_offset in range(3):
            att_date = today - timedelta(days=day_offset)
            for student in all_students:
                att = Attendance.objects.create(
                    student=student,
                    date=att_date,
                    period_1=random.choice(weighted),
                    period_2=random.choice(weighted),
                    period_3=random.choice(weighted),
                    period_4=random.choice(weighted),
                )
                # Finalize the oldest day to demonstrate locked rows
                if day_offset == 2:
                    att.is_finalized = True
                    att.save()

        self.stdout.write(self.style.SUCCESS(
            f'  Created 3 days of historical attendance '
            f'({total_students * 3} records).'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'  Oldest day is finalized to demonstrate locked rows.'
        ))

        self.stdout.write(self.style.SUCCESS('\nSeed complete.'))
        self.stdout.write(self.style.WARNING(
            f'\nLogin credentials (all use password "{DEFAULT_PASSWORD}"):\n'
            f'  Manager:     {MANAGER_USERNAME}\n'
            + '\n'.join(f'  Stage {s[1]:>8}: {s[0]}' for s in STAGE_ACCOUNTS)
        ))
