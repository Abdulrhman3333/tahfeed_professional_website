from django.contrib import admin
from .models import Student, Attendance, AttendanceChangeLog, StageProfile, Teacher


@admin.register(StageProfile)
class StageProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'managed_stage')
    list_filter = ('managed_stage',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('name', 'stage', 'phone')
    list_filter = ('stage',)
    search_fields = ('name', 'phone')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'national_id', 'stage', 'teacher')
    list_filter = ('stage', 'teacher')
    search_fields = ('full_name', 'national_id')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'period_1', 'period_2', 'period_3', 'period_4', 'is_finalized')
    list_filter = ('date', 'is_finalized', 'student__stage')
    search_fields = ('student__full_name',)
    date_hierarchy = 'date'


@admin.register(AttendanceChangeLog)
class AttendanceChangeLogAdmin(admin.ModelAdmin):
    list_display = ('attendance', 'period_number', 'old_value', 'new_value', 'changed_by', 'changed_at')
    list_filter = ('period_number', 'changed_at')
    search_fields = ('attendance__student__full_name',)
    date_hierarchy = 'changed_at'
