from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

# العضويات الافتراضية
ROLE_CHOICES = [
    ('preparer', 'المُحضّر'),
    ('examiner', 'المُختبر'),
    ('finance', 'المالي'),
    ('supervisor', 'المشرف'),
    ('manager', 'المدير'),
]

LAST_TESTED_PART_CHOICES = [
    ('0', 'لم يتم الاختبار'),
    ('1', 'جزء 1'),
    ('2', 'جزء 2'),
    ('3', 'جزء 3'),
    ('5', 'جزء 5'),
    ('8', 'جزء 8'),
    ('10', 'جزء 10'),
    ('13', 'جزء 13'),
    ('15', 'جزء 15'),
    ('20', 'جزء 20'),
    ('25', 'جزء 25'),
    ('30', 'جزء 30 (القرآن كاملاً)'),
]


class Role(models.Model):
    """عضوية المستخدم"""
    code = models.CharField(max_length=30, unique=True, choices=ROLE_CHOICES, verbose_name="الكود")
    name = models.CharField(max_length=30, verbose_name="الاسم")

    class Meta:
        verbose_name = "عضوية"
        verbose_name_plural = "العضويات"

    def __str__(self):
        return self.name


class UserRole(models.Model):
    """ربط المستخدم بالعضويات (متعددة)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="المستخدم")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name="العضوية")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "عضوية مستخدم"
        verbose_name_plural = "عضويات المستخدمين"
        unique_together = ('user', 'role')

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"

# تعريف قاعدة: يجب أن يكون الرقم 10 خانات
id_validator = RegexValidator(regex=r'^\d{10}$', message="رقم الهوية غير صحيح")

# نموذج مشرف المرحلة
class StageSupervisor(models.Model):
    """مشرف المرحلة - لديه صلاحيات أكبر من المعلم"""
    STAGE_CHOICES = [
        ('مبكرة', 'مبكرة'),
        ('عليا', 'عليا'),
        ('متوسط', 'متوسط'),
        ('ثانوي', 'ثانوي'),
        ('جامعي', 'جامعي'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="المستخدم", related_name='stage_supervisor')
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, verbose_name="المرحلة المسؤول عنها", blank=True, null=True)
    can_approve_students = models.BooleanField(default=True, verbose_name="يمكنه قبول الطلاب")
    can_assign_teachers = models.BooleanField(default=True, verbose_name="يمكنه تعيين المعلمين")
    
    class Meta:
        verbose_name = "مشرف مرحلة"
        verbose_name_plural = "مشرفو المراحل"
    
    def __str__(self):
        return f"مشرف {self.stage}: {self.user.username}"

class Student(models.Model):
    # خيارات الصف الدراسي
    GRADE_CHOICES = [
        ('1_pri', 'أول ابتدائي'), ('2_pri', 'ثاني ابتدائي'), ('3_pri', 'ثالث ابتدائي'),
        ('4_pri', 'رابع ابتدائي'), ('5_pri', 'خامس ابتدائي'), ('6_pri', 'سادس ابتدائي'),
        ('1_med', 'أول متوسط'), ('2_med', 'ثاني متوسط'), ('3_med', 'ثالث متوسط'),
        ('1_sec', 'أول ثانوي'), ('2_sec', 'ثاني ثانوي'), ('3_sec', 'ثالث ثانوي'),
        ('uni', 'جامعي'),
    ]

    STATUS_CHOICES = [('منتظر', 'منتظر'), ('منتظم', 'منتظم')]

    # البيانات المطلوبة
    full_name = models.CharField(max_length=200, verbose_name="الاسم الثلاثي", blank=True, default="")
    student_unique_id = models.PositiveIntegerField(unique=True, blank=True, null=True, editable=False, verbose_name="المعرف الفريد")
    student_phone = models.CharField(max_length=15, blank=True, null=True, verbose_name="جوال الطالب")
    parent_phone = models.CharField(max_length=15, verbose_name="جوال ولي الأمر", blank=True, default="")
    identity_number = models.CharField(max_length=100, verbose_name="رقم الهوية", blank=True, null=True)
    jamiaa_id = models.CharField(max_length=100, verbose_name="رقم الجمعية", blank=True, null=True)
    parent_identity = models.CharField(max_length=50, verbose_name="رقم هوية ولي الأمر", blank=True, null=True)
    grade = models.CharField(max_length=20, choices=GRADE_CHOICES, verbose_name="الصف الدراسي", blank=True, default="")
    birth_date = models.CharField(max_length=50, verbose_name="تاريخ الميلاد", blank=True, null=True)
    last_tested_part = models.CharField(
        max_length=50,
        choices=LAST_TESTED_PART_CHOICES,
        default='0',
        verbose_name="آخر جزء تم اختباره"
    )
    previous_center = models.CharField(max_length=100, blank=True, null=True, verbose_name="التحفيظ السابق")
    neighborhood = models.CharField(max_length=100, verbose_name="الحي", blank=True, null=True)
    
    # حقول تلقائية
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="المعلم المسؤول")
    status = models.CharField(max_length=20, default='منتظر', choices=STATUS_CHOICES)
    educational_stage = models.CharField(max_length=50, blank=True)
    absence_reset_at = models.DateField(blank=True, null=True, verbose_name="تاريخ تصفير الغياب المؤقت")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.student_unique_id:
            max_id = Student.objects.aggregate(max_id=models.Max('student_unique_id'))['max_id'] or 0
            self.student_unique_id = max_id + 1

        # أتمتة المرحلة الدراسية بناءً على الصف
        primary_early = ['1_pri', '2_pri', '3_pri']
        primary_late = ['4_pri', '5_pri', '6_pri']
        intermediate = ['1_med', '2_med', '3_med']
        secondary = ['1_sec', '2_sec', '3_sec']

        if self.grade in primary_early:
            self.educational_stage = "مبكرة"
        elif self.grade in primary_late:
            self.educational_stage = "عليا"
        elif self.grade in intermediate:
            self.educational_stage = "متوسط"
        elif self.grade in secondary:
            self.educational_stage = "ثانوي"
        else:
            self.educational_stage = "جامعي"
            
        super(Student, self).save(*args, **kwargs)

    def __str__(self):
        return self.full_name


# نموذج التقويم الدراسي
class AcademicCalendar(models.Model):
    """التقويم الدراسي - 19 أسبوع من 18 يناير إلى 4 يوليو"""
    week_number = models.IntegerField(unique=True, verbose_name="رقم الأسبوع")
    start_date = models.DateField(verbose_name="تاريخ بداية الأسبوع")
    end_date = models.DateField(verbose_name="تاريخ نهاية الأسبوع")
    
    class Meta:
        verbose_name = "أسبوع دراسي"
        verbose_name_plural = "التقويم الدراسي"
        ordering = ['week_number']
    
    def __str__(self):
        return f"الأسبوع {self.week_number} ({self.start_date} - {self.end_date})"
    
    @classmethod
    def get_week_from_date(cls, target_date):
        """الحصول على رقم الأسبوع من التاريخ"""
        week = cls.objects.filter(
            start_date__lte=target_date,
            end_date__gte=target_date
        ).first()
        return week.week_number if week else 1


class Attendance(models.Model):
    WEEKDAY_CHOICES = [
        ('الأحد', 'الأحد'),
        ('الاثنين', 'الاثنين'),
        ('الثلاثاء', 'الثلاثاء'),
        ('الأربعاء', 'الأربعاء'),
        ('الخميس', 'الخميس'),
    ]
    
    STATUS_CHOICES = [
        ('حاضر', 'حاضر'),
        ('غائب', 'غائب'),
        ('غياب بعذر', 'غياب بعذر'),
        ('مستأذن', 'منصرف'),
        ('متأخر', 'متأخر'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="الطالب")
    date = models.DateField(verbose_name="التاريخ")
    weekday = models.CharField(max_length=10, choices=WEEKDAY_CHOICES, verbose_name="اليوم")
    week_number = models.IntegerField(verbose_name="رقم الأسبوع")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='حاضر', verbose_name="الحالة")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'date')
        verbose_name = "حضور"
        verbose_name_plural = "سجلات الحضور"
        ordering = ['-date']

    def __str__(self):
        return f"{self.student.full_name} - {self.weekday} الأسبوع {self.week_number} - {self.status}"


class TeacherAttendance(models.Model):
    WEEKDAY_CHOICES = [
        ('الأحد', 'الأحد'),
        ('الاثنين', 'الاثنين'),
        ('الثلاثاء', 'الثلاثاء'),
        ('الأربعاء', 'الأربعاء'),
        ('الخميس', 'الخميس'),
    ]

    STATUS_CHOICES = [
        ('حاضر', 'حاضر'),
        ('غائب', 'غائب'),
        ('غياب بعذر', 'غياب بعذر'),
        ('مستأذن', 'منصرف'),
        ('متأخر', 'متأخر'),
    ]

    teacher = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="المعلم")
    date = models.DateField(verbose_name="التاريخ")
    weekday = models.CharField(max_length=10, choices=WEEKDAY_CHOICES, verbose_name="اليوم")
    week_number = models.IntegerField(verbose_name="رقم الأسبوع")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='حاضر', verbose_name="الحالة")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('teacher', 'date')
        verbose_name = "حضور معلم"
        verbose_name_plural = "سجلات حضور المعلمين"
        ordering = ['-date']

    def __str__(self):
        return f"{self.teacher.username} - {self.weekday} الأسبوع {self.week_number} - {self.status}"


# نموذج ترشيح الاختبار
class ExamNomination(models.Model):
    """ترشيح الطالب للاختبار الداخلي"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="الطالب")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="المعلم المرشح")
    last_tested_part = models.CharField(
        max_length=50,
        choices=LAST_TESTED_PART_CHOICES,
        verbose_name="آخر جزء تم اختباره"
    )
    teacher_grade = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="درجة المعلم", null=True, blank=True)
    internal_grade = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="درجة الاختبار الداخلي", null=True, blank=True)
    association_grade = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="درجة اختبار الجمعية", null=True, blank=True)
    nomination_date = models.DateField(auto_now_add=True, verbose_name="تاريخ الترشيح")
    internal_passed = models.BooleanField(default=False, verbose_name="اجتاز الداخلي")
    association_tested = models.BooleanField(default=False, verbose_name="تم اختبار الجمعية")
    
    class Meta:
        verbose_name = "ترشيح اختبار"
        verbose_name_plural = "ترشيحات الاختبارات"
        ordering = ['-nomination_date']
    
    def __str__(self):
        return f"{self.student.full_name} - جزء {self.last_tested_part}"
    
    def get_next_part(self):
        """الحصول على الجزء التالي للاختبار"""
        part_sequence = ['0', '1', '2', '3', '5', '8', '10', '13', '15', '20', '25', '30']
        try:
            current_index = part_sequence.index(self.last_tested_part)
            if current_index < len(part_sequence) - 1:
                return part_sequence[current_index + 1]
            return '30'  # القرآن كاملاً
        except ValueError:
            return '1'


class TeacherProfile(models.Model):
    """ملف تعريفي للمعلم يحتوي على معلومات إضافية"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="المستخدم", related_name='teacher_profile')
    phone = models.CharField(max_length=15, verbose_name="رقم الجوال", blank=True, null=True)
    
    class Meta:
        verbose_name = "ملف المعلم"
        verbose_name_plural = "ملفات المعلمين"
    
    def __str__(self):
        return f"ملف {self.user.username}"


class TeacherPlanPreference(models.Model):
    """Teacher default preferences used when generating a student plan."""
    MEM_PLAN_CHOICES = [
        ('none', 'مراجعة فقط'),
        ('2', 'صفحتان'),
        ('1', 'صفحة'),
        ('0.5', 'نصف صفحة'),
        ('0.25', 'ربع صفحة'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='plan_preference', verbose_name="المعلم")
    mem_plan = models.CharField(max_length=10, choices=MEM_PLAN_CHOICES, default='1', verbose_name="نوع الحفظ الافتراضي")
    big_review_pages = models.PositiveIntegerField(default=5, verbose_name="عدد صفحات المراجعة الكبرى")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تفضيل خطة المعلم"
        verbose_name_plural = "تفضيلات خطط المعلمين"

    def __str__(self):
        return f"تفضيلات {self.user.username}"


class SmsTemplateSetting(models.Model):
    """Per-user SMS templates used by preparer absent contacts page."""
    SECTION_CHOICES = [
        ('absent', 'غياب'),
        ('absent_excused', 'غياب بعذر'),
        ('late', 'تأخر'),
        ('excused', 'انصراف'),
        ('association_exam', 'اختبار الجمعية'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sms_template_settings', verbose_name="المستخدم")
    section = models.CharField(max_length=20, choices=SECTION_CHOICES, verbose_name="القسم")
    template_text = models.TextField(verbose_name="نص القالب")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")

    class Meta:
        verbose_name = "قالب رسالة SMS"
        verbose_name_plural = "قوالب رسائل SMS"
        unique_together = ('user', 'section')

    def __str__(self):
        return f"{self.user.username} - {self.get_section_display()}"


class MemorizationTemplateBundle(models.Model):
    """Stores uploaded memorization templates so all teachers use one active bundle."""
    name = models.CharField(max_length=120, default='قوالب حفظ مخصصة', verbose_name="اسم الحزمة")
    source_filename = models.CharField(max_length=255, blank=True, default='', verbose_name="اسم الملف المرفوع")
    template_definitions = models.JSONField(default=list, verbose_name="تعريفات القوالب")
    memorization_data = models.JSONField(default=dict, verbose_name="بيانات الحفظ")
    is_active = models.BooleanField(default=True, verbose_name="الحزمة النشطة")
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_memorization_bundles',
        verbose_name="تم الرفع بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الرفع")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")

    class Meta:
        verbose_name = "حزمة قوالب الحفظ"
        verbose_name_plural = "حزم قوالب الحفظ"
        ordering = ['-created_at']

    def __str__(self):
        state = 'نشطة' if self.is_active else 'غير نشطة'
        return f"{self.name} ({state})"
