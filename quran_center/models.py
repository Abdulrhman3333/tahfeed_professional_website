from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator


# Reused from the original project — 10-digit national ID validation.
id_validator = RegexValidator(regex=r'^\d{10}$', message="رقم الهوية غير صحيح")

# The 5 stages, reusing the exact Arabic labels from the original
# StageSupervisor.STAGE_CHOICES / Student.educational_stage logic.
STAGE_CHOICES = [
    ('مبكرة', 'مبكرة'),
    ('عليا', 'عليا'),
    ('متوسط', 'متوسط'),
    ('ثانوي', 'ثانوي'),
    ('جامعي', 'جامعي'),
]

# Same 5 status choices from the original Attendance model.
# IMPORTANT quirk preserved: stored value 'مستأذن' is displayed as 'منصرف'.
# The tuple format is (stored_value, display_label).
PERIOD_STATUS_CHOICES = [
    ('حاضر', 'حاضر'),
    ('غائب', 'غائب'),
    ('غياب بعذر', 'غياب بعذر'),
    ('مستأذن', 'منصرف'),
    ('متأخر', 'متأخر'),
]


class StageProfile(models.Model):
    """Links a non-manager User account to the single stage they manage.

    Design decision (Step 3): the manager account is simply a superuser
    (is_superuser=True) and does NOT have a StageProfile — they can view/edit
    all 5 stages. Each of the 5 stage accounts has exactly one StageProfile
    whose managed_stage restricts them to students/attendance in that stage
    only. We use Django's is_superuser flag for the manager rather than a
    custom is_manager boolean because it is the Django convention for
    "can do everything," it automatically grants admin access, and with only
    6 total accounts a full Role/UserRole system (removed in Step 1) is
    overkill.
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='stage_profile',
        verbose_name="المستخدم",
    )
    managed_stage = models.CharField(
        max_length=20, choices=STAGE_CHOICES, verbose_name="المرحلة المسؤول عنها",
    )

    class Meta:
        verbose_name = "ملف مرحلة"
        verbose_name_plural = "ملفات المراحل"

    def __str__(self):
        return f"{self.user.username} — {self.managed_stage}"


class Teacher(models.Model):
    """A real-world teacher in a stage (not a login account).

    Each stage has 3-6 teachers. Students are assigned to a specific teacher
    within their stage. The login stage accounts (StageProfile) take
    attendance for ALL students in their stage regardless of which teacher
    the student belongs to — the teacher field here is the "teacher of
    record" for grouping/display purposes on the attendance grid.
    """
    name = models.CharField(max_length=200, verbose_name="اسم المعلم")
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, verbose_name="المرحلة")
    phone = models.CharField(max_length=15, blank=True, default="", verbose_name="رقم الجوال")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "معلم"
        verbose_name_plural = "المعلمون"
        ordering = ['stage', 'name']

    def __str__(self):
        return f"{self.name} ({self.stage})"


class Student(models.Model):
    national_id = models.CharField(
        max_length=10, primary_key=True, validators=[id_validator],
        verbose_name="رقم الهوية",
    )
    full_name = models.CharField(max_length=200, verbose_name="الاسم الثلاثي")
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, verbose_name="المرحلة")

    # Teacher of record — a real-world teacher in the stage, used for
    # grouping on the attendance grid. This is NOT the login account;
    # the login stage account (StageProfile) takes attendance for all
    # students in the stage regardless of their teacher.
    teacher = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="المعلم المسؤول",
    )
    student_phone = models.CharField(
        max_length=15, blank=True, default="", verbose_name="جوال الطالب",
    )
    parent_phone = models.CharField(
        max_length=15, blank=True, default="", verbose_name="جوال ولي الأمر",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "طالب"
        verbose_name_plural = "الطلاب"
        ordering = ['full_name']

    def __str__(self):
        return self.full_name


class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="الطالب")
    date = models.DateField(verbose_name="التاريخ")

    # 4 period columns instead of a single status field. Each uses the same
    # 5 status choices (with the مستأذن→منصرف display quirk preserved).
    period_1 = models.CharField(
        max_length=10, choices=PERIOD_STATUS_CHOICES, default='حاضر',
        verbose_name="الفترة 1",
    )
    period_2 = models.CharField(
        max_length=10, choices=PERIOD_STATUS_CHOICES, default='حاضر',
        verbose_name="الفترة 2",
    )
    period_3 = models.CharField(
        max_length=10, choices=PERIOD_STATUS_CHOICES, default='حاضر',
        verbose_name="الفترة 3",
    )
    period_4 = models.CharField(
        max_length=10, choices=PERIOD_STATUS_CHOICES, default='حاضر',
        verbose_name="الفترة 4",
    )

    is_finalized = models.BooleanField(default=False, verbose_name="إنهاء التحضير")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'date')
        verbose_name = "حضور"
        verbose_name_plural = "سجلات الحضور"
        ordering = ['-date']

    def __str__(self):
        return f"{self.student.full_name} — {self.date}"

    def save(self, *args, **kwargs):
        # Audit trail: compare against the DB's current values before saving.
        # For new records (no pk) there is nothing to compare — just save.
        #
        # The calling view sets `self._changed_by = request.user` before
        # calling save() so the log knows who made the change. If the
        # attribute is absent (e.g. creates via admin or shell), changed_by
        # will be None, which is acceptable.
        if self.pk:
            try:
                old = Attendance.objects.get(pk=self.pk)
                changed_by = getattr(self, '_changed_by', None)
                for period_num, field_name in enumerate(
                    ['period_1', 'period_2', 'period_3', 'period_4'], start=1
                ):
                    old_val = getattr(old, field_name)
                    new_val = getattr(self, field_name)
                    if old_val != new_val:
                        AttendanceChangeLog.objects.create(
                            attendance=self,
                            period_number=period_num,
                            old_value=old_val,
                            new_value=new_val,
                            changed_by=changed_by,
                        )
            except Attendance.DoesNotExist:
                pass
        super().save(*args, **kwargs)


class AttendanceChangeLog(models.Model):
    """Lightweight audit trail — one row per period value change."""
    attendance = models.ForeignKey(
        Attendance, on_delete=models.CASCADE, related_name='change_logs',
        verbose_name="سجل الحضور",
    )
    period_number = models.IntegerField(verbose_name="رقم الفترة")
    old_value = models.CharField(max_length=10, verbose_name="القيمة القديمة")
    new_value = models.CharField(max_length=10, verbose_name="القيمة الجديدة")
    changed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="تم التعديل بواسطة",
    )
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التعديل")

    class Meta:
        verbose_name = "سجل تعديل"
        verbose_name_plural = "سجلات التعديلات"
        ordering = ['-changed_at']

    def __str__(self):
        return (
            f"{self.attendance.student.full_name} — الفترة {self.period_number}: "
            f"{self.old_value} → {self.new_value}"
        )


class TeacherAttendance(models.Model):
    """Attendance tracking for teachers (4 periods per day, same as students)."""
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, verbose_name="المعلم")
    date = models.DateField(verbose_name="التاريخ")

    period_1 = models.CharField(
        max_length=10, choices=PERIOD_STATUS_CHOICES, default='حاضر',
        verbose_name="الفترة 1",
    )
    period_2 = models.CharField(
        max_length=10, choices=PERIOD_STATUS_CHOICES, default='حاضر',
        verbose_name="الفترة 2",
    )
    period_3 = models.CharField(
        max_length=10, choices=PERIOD_STATUS_CHOICES, default='حاضر',
        verbose_name="الفترة 3",
    )
    period_4 = models.CharField(
        max_length=10, choices=PERIOD_STATUS_CHOICES, default='حاضر',
        verbose_name="الفترة 4",
    )

    is_finalized = models.BooleanField(default=False, verbose_name="إنهاء التحضير")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('teacher', 'date')
        verbose_name = "حضور معلم"
        verbose_name_plural = "سجلات حضور المعلمين"
        ordering = ['-date']

    def __str__(self):
        return f"{self.teacher.name} — {self.date}"
