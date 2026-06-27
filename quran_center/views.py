from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
from collections import OrderedDict
from urllib.parse import quote, unquote

from .models import (
    Student, Attendance, AttendanceChangeLog, StageProfile, Teacher,
    TeacherAttendance, STAGE_CHOICES, PERIOD_STATUS_CHOICES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_user_stage(user):
    """Return the stage code this user manages, or None for the manager.

    The manager (is_superuser=True) sees all 5 stages. A stage account has
    a StageProfile whose managed_stage restricts their access.
    """
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return None
    profile = getattr(user, 'stage_profile', None)
    return profile.managed_stage if profile else None


def get_arabic_weekday_name(target_date):
    names = {
        0: 'الاثنين', 1: 'الثلاثاء', 2: 'الأربعاء',
        3: 'الخميس', 4: 'الجمعة', 5: 'السبت', 6: 'الأحد',
    }
    return names.get(target_date.weekday(), 'الأحد')


def notify_parents_of_negative_attendance(attendance_ids):
    """TODO: Integration point for parent notifications.

    This function would notify parents of students who have negative
    attendance (غائب, متأخر, مستأذن, غياب بعذر) on a finalized day.

    In the original project, this was handled by a WhatsApp bot
    (whatsapp_bot/ folder, deleted in Step 1) and an SMS API. This stub
    marks where a freestanding notification service would eventually plug
    back in — NOT by resurrecting the deleted bot code wholesale, but as a
    clean integration point that could call any notification backend (SMS,
    push, email, etc.).
    """
    pass


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class TeacherLoginView(LoginView):
    """Login view with remember-me cookie support for Arabic usernames."""
    template_name = 'login.html'

    def get_initial(self):
        initial = super().get_initial()
        remembered_username = self.request.COOKIES.get('remembered_username')
        if remembered_username:
            try:
                remembered_username = unquote(remembered_username)
            except Exception:
                remembered_username = ''
        if remembered_username:
            initial['username'] = remembered_username
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        remembered_username = self.request.COOKIES.get('remembered_username', '')
        if remembered_username:
            try:
                remembered_username = unquote(remembered_username)
            except Exception:
                remembered_username = ''
        context['remembered_username'] = remembered_username
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        remember_me = self.request.POST.get('remember_me') == 'on'
        username = form.cleaned_data.get('username', '')
        if remember_me:
            safe_username = quote(username, safe='')
            response.set_cookie(
                'remembered_username', safe_username,
                max_age=60 * 60 * 24 * 30, httponly=False, samesite='Lax',
            )
        else:
            response.delete_cookie('remembered_username')
        return response


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------

def welcome_view(request):
    # Registration Google Form link — passed as context so it's defined in
    # one place. Update this constant when a new camp iteration's form is
    # ready. See welcome.html template for usage.
    registration_url = 'https://forms.gle/FQUnKzF9UemCo4mB6'
    return render(request, 'welcome.html', {
        'registration_url': registration_url,
    })


def parent_inquiry(request):
    """Password-free phone lookup for parents.

    SECURITY: national_id must NEVER appear in the rendered HTML, any JSON
    response, or any URL on this page. We use the Attendance row's own auto
    `id` and the forloop counter for any frontend references instead.
    """
    error_message = None
    if request.method == 'POST':
        parent_phone = request.POST.get('parent_phone', '').strip()
        if not parent_phone:
            error_message = "يرجى إدخال رقم الجوال"
        else:
            students = Student.objects.filter(parent_phone=parent_phone).order_by('full_name')
            results = []

            for student in students:
                attendances = Attendance.objects.filter(student=student)

                # Counts across ALL 4 period columns and all dates.
                # We deliberately do NOT count or display حاضر.
                absent_count = 0
                late_count = 0
                excused_count = 0       # مستأذن (displayed as منصرف)
                absent_excused_count = 0  # غياب بعذر

                # Timeline of every non-حاضر period entry.
                timeline = []
                for att in attendances:
                    for period_num, field in enumerate(
                        ['period_1', 'period_2', 'period_3', 'period_4'], start=1
                    ):
                        val = getattr(att, field)
                        if val == 'غائب':
                            absent_count += 1
                        elif val == 'متأخر':
                            late_count += 1
                        elif val == 'مستأذن':
                            excused_count += 1
                        elif val == 'غياب بعذر':
                            absent_excused_count += 1

                        if val != 'حاضر':
                            timeline.append({
                                # Using att.id (NOT national_id) for any
                                # frontend reference — see security note above.
                                'attendance_id': att.id,
                                'date': att.date,
                                'period': period_num,
                                'status': val,
                            })

                timeline.sort(key=lambda x: x['date'], reverse=True)

                results.append({
                    # NOTE: national_id is intentionally omitted here.
                    'full_name': student.full_name,
                    'stage': student.stage,
                    'absent_count': absent_count,
                    'late_count': late_count,
                    'excused_count': excused_count,
                    'absent_excused_count': absent_excused_count,
                    'timeline': timeline,
                })

            return render(request, 'parent_inquiry_results.html', {
                'students': results,
                'parent_phone': parent_phone,
            })

    return render(request, 'parent_inquiry.html', {'error_message': error_message})


# ---------------------------------------------------------------------------
# Attendance page (core deliverable — Step 4)
# ---------------------------------------------------------------------------

@login_required
def attendance_page(request):
    """Single page serving both manager and stage accounts.

    Manager: sees all 5 stages via a tabbed layout (all tables pre-rendered
    in the DOM, only one visible at a time).
    Stage account: sees only their stage's table (no tabs).
    """
    selected_date_str = request.GET.get('date') or str(timezone.now().date())
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except ValueError:
        selected_date = timezone.now().date()

    is_manager = request.user.is_superuser
    user_stage = get_user_stage(request.user)

    if is_manager:
        stages = STAGE_CHOICES
    elif user_stage:
        stages = [(user_stage, user_stage)]
    else:
        stages = []

    stages_data = []
    for stage_code, stage_name in stages:
        students = Student.objects.filter(
            stage=stage_code
        ).select_related('teacher').order_by('teacher__name', 'full_name')

        attendance_records = Attendance.objects.filter(
            student__stage=stage_code, date=selected_date
        )
        attendance_map = {att.student_id: att for att in attendance_records}

        # Group by teacher (generic — works with any number of teachers).
        groups = OrderedDict()
        for student in students:
            teacher_key = student.teacher_id
            if teacher_key not in groups:
                teacher_name = student.teacher.name if student.teacher else "غير محدد"
                groups[teacher_key] = {'teacher_name': teacher_name, 'students': []}

            att = attendance_map.get(student.national_id)
            groups[teacher_key]['students'].append({
                'student': student,
                'attendance_id': att.id if att else None,
                'is_finalized': att.is_finalized if att else False,
                'period_1': att.period_1 if att else 'حاضر',
                'period_2': att.period_2 if att else 'حاضر',
                'period_3': att.period_3 if att else 'حاضر',
                'period_4': att.period_4 if att else 'حاضر',
            })

        stages_data.append({
            'stage_code': stage_code,
            'stage_name': stage_name,
            'groups': list(groups.values()),
        })

    context = {
        'stages_data': stages_data,
        'selected_date': selected_date,
        'today': timezone.now().date(),
        'is_manager': is_manager,
        'user_stage': user_stage,
        'weekday_name': get_arabic_weekday_name(selected_date),
    }
    return render(request, 'attendance.html', context)


@login_required
def save_period(request):
    """AJAX endpoint: save a single period's status for one student/date."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST only'})

    # national_id is used here on this authenticated staff endpoint; it is
    # never exposed to the parent portal (see parent_inquiry security note).
    student_national_id = request.POST.get('student_id')
    date_str = request.POST.get('date')
    period_num = request.POST.get('period')
    status = request.POST.get('status')

    try:
        att_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'invalid date'})

    if period_num not in ('1', '2', '3', '4'):
        return JsonResponse({'ok': False, 'error': 'invalid period'})

    valid_statuses = [c[0] for c in PERIOD_STATUS_CHOICES]
    if status not in valid_statuses:
        return JsonResponse({'ok': False, 'error': 'invalid status'})

    student = get_object_or_404(Student, national_id=student_national_id)

    # Permission: stage account can only edit their own stage's students.
    user_stage = get_user_stage(request.user)
    if user_stage and student.stage != user_stage:
        return JsonResponse({'ok': False, 'error': 'permission denied'})

    att, created = Attendance.objects.get_or_create(
        student=student, date=att_date,
    )

    # Finalized rows are locked for stage accounts; manager can override.
    if att.is_finalized and not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'finalized'})

    setattr(att, f'period_{period_num}', status)
    att._changed_by = request.user  # for the audit trail in save()
    att.save()

    return JsonResponse({
        'ok': True,
        'attendance_id': att.id,
        'is_finalized': att.is_finalized,
    })


@login_required
def finalize_attendance(request):
    """AJAX endpoint: mark the day's attendance as finalized (locked).

    Stage accounts finalize their own stage; the manager finalizes whichever
    stage tab is currently active (sent via the `stage` POST parameter).
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST only'})

    date_str = request.POST.get('date')
    stage_code = request.POST.get('stage')

    try:
        att_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'invalid date'})

    if request.user.is_superuser:
        target_stage = stage_code
    else:
        user_stage = get_user_stage(request.user)
        target_stage = user_stage

    if not target_stage:
        return JsonResponse({'ok': False, 'error': 'no stage specified'})

    students = Student.objects.filter(stage=target_stage)
    attendance_ids = []
    for student in students:
        att, created = Attendance.objects.get_or_create(
            student=student, date=att_date,
        )
        if not att.is_finalized:
            att.is_finalized = True
            att._changed_by = request.user
            att.save()
        attendance_ids.append(att.id)

    # Fire the notification stub — see TODO in the function definition.
    # This is where the WhatsApp/SMS notification service would plug in.
    notify_parents_of_negative_attendance(attendance_ids)

    return JsonResponse({
        'ok': True,
        'finalized_count': len(attendance_ids),
        'stage': target_stage,
    })


# ---------------------------------------------------------------------------
# Add student page
# ---------------------------------------------------------------------------

@login_required
def add_student(request):
    """Add a new student.

    Manager: can choose any stage and any teacher within that stage.
    Stage account: stage is fixed to their managed_stage, teacher dropdown
    shows only teachers in their stage.
    """
    is_manager = request.user.is_superuser
    user_stage = get_user_stage(request.user)

    if request.method == 'POST':
        national_id = request.POST.get('national_id', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        student_phone = request.POST.get('student_phone', '').strip()
        parent_phone = request.POST.get('parent_phone', '').strip()

        if is_manager:
            stage = request.POST.get('stage', '').strip()
        else:
            stage = user_stage or ''
        teacher_id = request.POST.get('teacher', '').strip()

        # --- Validation ---
        errors = []
        if not national_id:
            errors.append('رقم الهوية مطلوب')
        elif not national_id.isdigit() or len(national_id) != 10:
            errors.append('رقم الهوية يجب أن يكون 10 أرقام')
        elif Student.objects.filter(national_id=national_id).exists():
            errors.append('رقم الهوية موجود مسبقاً')

        if not full_name:
            errors.append('الاسم مطلوب')

        if stage not in [c[0] for c in STAGE_CHOICES]:
            errors.append('المرحلة غير صحيحة')

        teacher = None
        if teacher_id:
            try:
                teacher = Teacher.objects.get(id=teacher_id)
                if teacher.stage != stage:
                    errors.append('المعلم لا ينتمي لهذه المرحلة')
            except Teacher.DoesNotExist:
                errors.append('المعلم غير صحيح')

        if errors:
            teachers_in_stage = Teacher.objects.filter(stage=stage) if stage else Teacher.objects.none()
            return render(request, 'add_student.html', {
                'is_manager': is_manager,
                'user_stage': user_stage,
                'stage_choices': STAGE_CHOICES,
                'teachers_in_stage': teachers_in_stage,
                'errors': errors,
                'form_data': {
                    'national_id': national_id,
                    'full_name': full_name,
                    'stage': stage,
                    'teacher': teacher_id,
                    'student_phone': student_phone,
                    'parent_phone': parent_phone,
                },
            })

        Student.objects.create(
            national_id=national_id,
            full_name=full_name,
            stage=stage,
            teacher=teacher,
            student_phone=student_phone,
            parent_phone=parent_phone,
        )

        teachers_in_stage = Teacher.objects.filter(stage=stage)
        return render(request, 'add_student.html', {
            'is_manager': is_manager,
            'user_stage': user_stage,
            'stage_choices': STAGE_CHOICES,
            'teachers_in_stage': teachers_in_stage,
            'success': True,
            'success_name': full_name,
        })

    # GET: pre-populate teachers for the right stage
    if is_manager:
        initial_stage = request.GET.get('stage', '')
        teachers_in_stage = Teacher.objects.filter(stage=initial_stage) if initial_stage else Teacher.objects.none()
    else:
        initial_stage = user_stage or ''
        teachers_in_stage = Teacher.objects.filter(stage=user_stage) if user_stage else Teacher.objects.none()

    return render(request, 'add_student.html', {
        'is_manager': is_manager,
        'user_stage': user_stage,
        'stage_choices': STAGE_CHOICES,
        'teachers_in_stage': teachers_in_stage,
        'initial_stage': initial_stage,
    })


# ---------------------------------------------------------------------------
# Admin pages: statistics + add teacher (manager only)
# ---------------------------------------------------------------------------

@login_required
def teachers_api(request):
    """Return teachers for a given stage as JSON (used by add_student JS)."""
    stage = request.GET.get('stage', '').strip()
    if stage not in [c[0] for c in STAGE_CHOICES]:
        return JsonResponse({'teachers': []})
    teachers = Teacher.objects.filter(stage=stage).order_by('name')
    return JsonResponse({
        'teachers': [{'id': t.id, 'name': t.name} for t in teachers],
    })


@login_required
def admin_statistics(request):
    """Manager-only page showing per-stage attendance statistics.

    For each stage shows: total students, students absent today (period_1 =
    غائب), students not yet recorded, and whether attendance is finalized.
    Also shows a per-teacher breakdown within each stage.
    """
    if not request.user.is_superuser:
        return redirect('attendance_page')

    today = timezone.now().date()

    stage_stats = []
    for stage_code, stage_name in STAGE_CHOICES:
        students = Student.objects.filter(stage=stage_code)
        total = students.count()

        today_attendance = Attendance.objects.filter(
            student__stage=stage_code, date=today,
        )
        attendance_map = {att.student_id: att for att in today_attendance}

        recorded_count = today_attendance.count()
        absent_count = today_attendance.filter(period_1='غائب').count()
        present_count = today_attendance.filter(period_1='حاضر').count()
        not_recorded_count = total - recorded_count

        is_finalized = today_attendance.exists() and not today_attendance.filter(is_finalized=False).exists()

        # Per-teacher breakdown
        teacher_breakdown = []
        for teacher in Teacher.objects.filter(stage=stage_code).order_by('name'):
            t_students = students.filter(teacher=teacher)
            t_total = t_students.count()
            t_absent = sum(
                1 for s in t_students
                if attendance_map.get(s.national_id) and attendance_map[s.national_id].period_1 == 'غائب'
            )
            t_recorded = sum(
                1 for s in t_students
                if s.national_id in attendance_map
            )
            teacher_breakdown.append({
                'teacher': teacher,
                'total': t_total,
                'absent': t_absent,
                'recorded': t_recorded,
            })

        # Students with no teacher assigned
        unassigned = students.filter(teacher__isnull=True).count()

        stage_stats.append({
            'stage_code': stage_code,
            'stage_name': stage_name,
            'total': total,
            'recorded': recorded_count,
            'absent': absent_count,
            'present': present_count,
            'not_recorded': not_recorded_count,
            'is_finalized': is_finalized,
            'teacher_breakdown': teacher_breakdown,
            'unassigned': unassigned,
        })

    return render(request, 'admin_statistics.html', {
        'stage_stats': stage_stats,
        'today': today,
        'weekday_name': get_arabic_weekday_name(today),
    })


@login_required
def add_teacher(request):
    """Manager-only page to add a new teacher and assign them to a stage."""
    if not request.user.is_superuser:
        return redirect('attendance_page')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        stage = request.POST.get('stage', '').strip()
        phone = request.POST.get('phone', '').strip()

        errors = []
        if not name:
            errors.append('اسم المعلم مطلوب')
        if stage not in [c[0] for c in STAGE_CHOICES]:
            errors.append('المرحلة غير صحيحة')

        if errors:
            return render(request, 'add_teacher.html', {
                'stage_choices': STAGE_CHOICES,
                'errors': errors,
                'form_data': {'name': name, 'stage': stage, 'phone': phone},
            })

        Teacher.objects.create(name=name, stage=stage, phone=phone)

        teachers = Teacher.objects.all().order_by('stage', 'name')
        return render(request, 'add_teacher.html', {
            'stage_choices': STAGE_CHOICES,
            'teachers': teachers,
            'success': True,
            'success_name': name,
        })

    teachers = Teacher.objects.all().order_by('stage', 'name')
    return render(request, 'add_teacher.html', {
        'stage_choices': STAGE_CHOICES,
        'teachers': teachers,
    })


# ---------------------------------------------------------------------------
# Teacher attendance (mirrors student attendance structure)
# ---------------------------------------------------------------------------

@login_required
def teacher_attendance_page(request):
    """Take attendance for teachers (4 periods per day).

    Manager: sees all 5 stages via tabs.
    Stage account: sees only their stage's teachers.
    """
    selected_date_str = request.GET.get('date') or str(timezone.now().date())
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except ValueError:
        selected_date = timezone.now().date()

    is_manager = request.user.is_superuser
    user_stage = get_user_stage(request.user)

    if is_manager:
        stages = STAGE_CHOICES
    elif user_stage:
        stages = [(user_stage, user_stage)]
    else:
        stages = []

    stages_data = []
    for stage_code, stage_name in stages:
        teachers = Teacher.objects.filter(stage=stage_code).order_by('name')
        attendance_records = TeacherAttendance.objects.filter(
            teacher__stage=stage_code, date=selected_date
        )
        attendance_map = {att.teacher_id: att for att in attendance_records}

        teacher_rows = []
        for teacher in teachers:
            att = attendance_map.get(teacher.id)
            teacher_rows.append({
                'teacher': teacher,
                'attendance_id': att.id if att else None,
                'is_finalized': att.is_finalized if att else False,
                'period_1': att.period_1 if att else 'حاضر',
                'period_2': att.period_2 if att else 'حاضر',
                'period_3': att.period_3 if att else 'حاضر',
                'period_4': att.period_4 if att else 'حاضر',
            })

        stages_data.append({
            'stage_code': stage_code,
            'stage_name': stage_name,
            'teachers': teacher_rows,
        })

    context = {
        'stages_data': stages_data,
        'selected_date': selected_date,
        'today': timezone.now().date(),
        'is_manager': is_manager,
        'user_stage': user_stage,
        'weekday_name': get_arabic_weekday_name(selected_date),
    }
    return render(request, 'teacher_attendance.html', context)


@login_required
def save_teacher_period(request):
    """AJAX endpoint: save a single period's status for one teacher/date."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST only'})

    teacher_id = request.POST.get('teacher_id')
    date_str = request.POST.get('date')
    period_num = request.POST.get('period')
    status = request.POST.get('status')

    try:
        att_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'invalid date'})

    if period_num not in ('1', '2', '3', '4'):
        return JsonResponse({'ok': False, 'error': 'invalid period'})

    valid_statuses = [c[0] for c in PERIOD_STATUS_CHOICES]
    if status not in valid_statuses:
        return JsonResponse({'ok': False, 'error': 'invalid status'})

    teacher = get_object_or_404(Teacher, id=teacher_id)

    # Permission: stage account can only edit their own stage's teachers.
    user_stage = get_user_stage(request.user)
    if user_stage and teacher.stage != user_stage:
        return JsonResponse({'ok': False, 'error': 'permission denied'})

    att, created = TeacherAttendance.objects.get_or_create(
        teacher=teacher, date=att_date,
    )

    if att.is_finalized and not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'finalized'})

    setattr(att, f'period_{period_num}', status)
    att.save()

    return JsonResponse({
        'ok': True,
        'attendance_id': att.id,
        'is_finalized': att.is_finalized,
    })


@login_required
def finalize_teacher_attendance(request):
    """AJAX endpoint: finalize teacher attendance for a stage/date."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST only'})

    date_str = request.POST.get('date')
    stage_code = request.POST.get('stage')

    try:
        att_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'invalid date'})

    if request.user.is_superuser:
        target_stage = stage_code
    else:
        user_stage = get_user_stage(request.user)
        target_stage = user_stage

    if not target_stage:
        return JsonResponse({'ok': False, 'error': 'no stage specified'})

    teachers = Teacher.objects.filter(stage=target_stage)
    count = 0
    for teacher in teachers:
        att, created = TeacherAttendance.objects.get_or_create(
            teacher=teacher, date=att_date,
        )
        if not att.is_finalized:
            att.is_finalized = True
            att.save()
            count += 1

    return JsonResponse({
        'ok': True,
        'finalized_count': count,
        'stage': target_stage,
    })


# ---------------------------------------------------------------------------
# Status pages (summary with drill-down)
# ---------------------------------------------------------------------------

@login_required
def student_status_page(request):
    """Summary of student attendance status for a given date.

    Shows counts per status (present, absent, late, etc.) with drill-down
    to see which students and which periods.
    """
    selected_date_str = request.GET.get('date') or str(timezone.now().date())
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except ValueError:
        selected_date = timezone.now().date()

    is_manager = request.user.is_superuser
    user_stage = get_user_stage(request.user)

    if is_manager:
        stage_filter = request.GET.get('stage', '')
        students = Student.objects.all()
        if stage_filter:
            students = students.filter(stage=stage_filter)
    elif user_stage:
        students = Student.objects.filter(stage=user_stage)
        stage_filter = user_stage
    else:
        students = Student.objects.none()
        stage_filter = ''

    attendance_records = Attendance.objects.filter(
        student__in=students, date=selected_date
    ).select_related('student')

    # Build status summary: for each status, collect (student_name, periods)
    status_details = {}
    for status_code, status_label in PERIOD_STATUS_CHOICES:
        status_details[status_code] = {
            'label': status_label,
            'entries': [],
        }

    for att in attendance_records:
        for period_num, field_name in enumerate(
            ['period_1', 'period_2', 'period_3', 'period_4'], start=1
        ):
            val = getattr(att, field_name)
            if val in status_details:
                status_details[val]['entries'].append({
                    'student_name': att.student.full_name,
                    'student_stage': att.student.stage,
                    'teacher_name': att.student.teacher.name if att.student.teacher else 'غير محدد',
                    'period': period_num,
                })

    # Sort entries by student name within each status
    for status_code in status_details:
        status_details[status_code]['entries'].sort(key=lambda x: x['student_name'])

    context = {
        'status_details': status_details,
        'selected_date': selected_date,
        'today': timezone.now().date(),
        'is_manager': is_manager,
        'user_stage': user_stage,
        'stage_choices': STAGE_CHOICES,
        'stage_filter': stage_filter,
        'weekday_name': get_arabic_weekday_name(selected_date),
        'total_students': students.count(),
        'recorded_count': attendance_records.values('student').distinct().count(),
    }
    return render(request, 'student_status.html', context)


@login_required
def teacher_status_page(request):
    """Summary of teacher attendance status for a given date.

    Shows counts per status (present, absent, late, etc.) with drill-down
    to see which teachers and which periods.
    """
    selected_date_str = request.GET.get('date') or str(timezone.now().date())
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except ValueError:
        selected_date = timezone.now().date()

    is_manager = request.user.is_superuser
    user_stage = get_user_stage(request.user)

    if is_manager:
        stage_filter = request.GET.get('stage', '')
        teachers = Teacher.objects.all()
        if stage_filter:
            teachers = teachers.filter(stage=stage_filter)
    elif user_stage:
        teachers = Teacher.objects.filter(stage=user_stage)
        stage_filter = user_stage
    else:
        teachers = Teacher.objects.none()
        stage_filter = ''

    attendance_records = TeacherAttendance.objects.filter(
        teacher__in=teachers, date=selected_date
    ).select_related('teacher')

    # Build status summary
    status_details = {}
    for status_code, status_label in PERIOD_STATUS_CHOICES:
        status_details[status_code] = {
            'label': status_label,
            'entries': [],
        }

    for att in attendance_records:
        for period_num, field_name in enumerate(
            ['period_1', 'period_2', 'period_3', 'period_4'], start=1
        ):
            val = getattr(att, field_name)
            if val in status_details:
                status_details[val]['entries'].append({
                    'teacher_name': att.teacher.name,
                    'teacher_stage': att.teacher.stage,
                    'period': period_num,
                })

    for status_code in status_details:
        status_details[status_code]['entries'].sort(key=lambda x: x['teacher_name'])

    context = {
        'status_details': status_details,
        'selected_date': selected_date,
        'today': timezone.now().date(),
        'is_manager': is_manager,
        'user_stage': user_stage,
        'stage_choices': STAGE_CHOICES,
        'stage_filter': stage_filter,
        'weekday_name': get_arabic_weekday_name(selected_date),
        'total_teachers': teachers.count(),
        'recorded_count': attendance_records.values('teacher').distinct().count(),
    }
    return render(request, 'teacher_status.html', context)
