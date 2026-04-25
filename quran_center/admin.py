from django.contrib import admin
from .models import Student, Attendance, StageSupervisor, AcademicCalendar, ExamNomination, Role, UserRole, TeacherPlanPreference, MemorizationTemplateBundle

@admin.register(StageSupervisor)
class StageSupervisorAdmin(admin.ModelAdmin):
    list_display = ('user', 'stage', 'can_approve_students', 'can_assign_teachers')
    list_filter = ('stage', 'can_approve_students', 'can_assign_teachers')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

@admin.register(AcademicCalendar)
class AcademicCalendarAdmin(admin.ModelAdmin):
    list_display = ('week_number', 'start_date', 'end_date')
    ordering = ['week_number']

@admin.register(ExamNomination)
class ExamNominationAdmin(admin.ModelAdmin):
    list_display = ('student', 'teacher', 'last_tested_part', 'teacher_grade', 'internal_grade', 'association_grade', 'internal_passed', 'association_tested', 'nomination_date')
    list_filter = ('internal_passed', 'association_tested', 'nomination_date', 'teacher')
    search_fields = ('student__full_name',)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('user__username',)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    # الأعمدة التي تظهر في الجدول للمدير
    list_display = ('full_name', 'student_unique_id', 'grade', 'educational_stage', 'status', 'teacher')
    
    # فلاتر جانبية للبحث السريع
    list_filter = ('status', 'educational_stage', 'teacher', 'grade')
    
    # إمكانية البحث بالاسم أو الهوية
    search_fields = ('full_name', 'identity_number', 'student_unique_id__exact')
    
    # إمكانية تعديل الحالة أو المعلم مباشرة من الجدول
    list_editable = ('status', 'teacher')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'weekday', 'week_number', 'date', 'status')
    list_filter = ('date', 'status', 'weekday', 'week_number')
    search_fields = ('student__full_name',)
    date_hierarchy = 'date'


@admin.register(TeacherPlanPreference)
class TeacherPlanPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'mem_plan', 'big_review_pages', 'updated_at')
    search_fields = ('user__username',)


@admin.register(MemorizationTemplateBundle)
class MemorizationTemplateBundleAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_filename', 'is_active', 'uploaded_by', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'source_filename', 'uploaded_by__username')

