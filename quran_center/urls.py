from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.welcome_view, name='welcome'),
    path('parent-inquiry/', views.parent_inquiry, name='parent_inquiry'),
    path('attendance/', views.attendance_page, name='attendance_page'),
    path('attendance/save-period/', views.save_period, name='save_period'),
    path('attendance/finalize/', views.finalize_attendance, name='finalize_attendance'),
    path('add-student/', views.add_student, name='add_student'),
    path('teachers-api/', views.teachers_api, name='teachers_api'),
    path('admin-statistics/', views.admin_statistics, name='admin_statistics'),
<<<<<<< HEAD
    path('admin-dashboard/export-students/', views.export_student_data, name='export_student_data'),
=======
    path('add-teacher/', views.add_teacher, name='add_teacher'),
    path('teacher-attendance/', views.teacher_attendance_page, name='teacher_attendance_page'),
    path('teacher-attendance/save-period/', views.save_teacher_period, name='save_teacher_period'),
    path('teacher-attendance/finalize/', views.finalize_teacher_attendance, name='finalize_teacher_attendance'),
    path('student-status/', views.student_status_page, name='student_status_page'),
    path('teacher-status/', views.teacher_status_page, name='teacher_status_page'),
>>>>>>> f212ca62147e61e58b9c37514b9328ce33da2624
    path('login/', views.TeacherLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='welcome'), name='logout'),
]
