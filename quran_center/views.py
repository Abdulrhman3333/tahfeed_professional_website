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

# دالة مساعدة للتحقق من صلاحية مشرف المرحلة
def is_stage_supervisor(user):
    """تحقق إذا كان المستخدم مشرف مرحلة"""
    return hasattr(user, 'stage_supervisor') or user.is_superuser or user_has_role(user, 'supervisor')


def user_has_role(user, role_code):
    """تحقق من العضوية"""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return UserRole.objects.filter(user=user, role__code=role_code).exists()


def can_access_preparer_attendance(user):
    """السماح للمحضّر بالدخول لصفحات متابعة/تحضير الحضور العامة."""
    return user_has_role(user, 'preparer')


ARABIC_WEEKDAY_NAMES = {
    # Python's date.weekday() starts from Monday=0 to Sunday=6.
    0: 'الاثنين',
    1: 'الثلاثاء',
    2: 'الأربعاء',
    3: 'الخميس',
    4: 'الجمعة',
    5: 'السبت',
    6: 'الأحد',
}


def get_arabic_weekday_name(target_date):
    return ARABIC_WEEKDAY_NAMES.get(target_date.weekday(), 'الأحد')


def normalize_saudi_phone(phone):
    phone = phone or ''
    digits = ''.join([ch for ch in phone if ch.isdigit()])
    if digits.startswith('966'):
        return digits
    if digits.startswith('0'):
        return '966' + digits[1:]
    if digits.startswith('5'):
        return '966' + digits
    return digits


def normalize_excel_value(value):
    if value is None:
        return ''
    return str(value).strip()


def normalize_arabic_text(value):
    text = normalize_excel_value(value)
    replacements = {
        'أ': 'ا',
        'إ': 'ا',
        'آ': 'ا',
        'ى': 'ي',
        'ة': 'ه',
    }
    for old_char, new_char in replacements.items():
        text = text.replace(old_char, new_char)
    return ' '.join(text.split()).lower()


def map_grade_from_excel(raw_grade):
    text_value = normalize_excel_value(raw_grade)
    if not text_value:
        return ''

    # Accept internal code directly (e.g. 3_pri).
    valid_codes = {choice[0] for choice in Student.GRADE_CHOICES}
    if text_value in valid_codes:
        return text_value

    normalized_text = normalize_arabic_text(text_value)

    # Values that mean "not selected yet" are accepted as empty grade.
    empty_markers = {
        normalize_arabic_text('لم يتم التحديد بعد'),
        normalize_arabic_text('غير محدد'),
        normalize_arabic_text('غير محدده'),
        normalize_arabic_text('لا يوجد'),
    }
    if normalized_text in empty_markers:
        return ''

    # Accept official labels and common writing variants.
    label_map = {
        normalize_arabic_text('أول ابتدائي'): '1_pri',
        normalize_arabic_text('اول ابتدائي'): '1_pri',
        normalize_arabic_text('اولى ابتدائي'): '1_pri',
        normalize_arabic_text('اولي ابتدائي'): '1_pri',
        normalize_arabic_text('ثاني ابتدائي'): '2_pri',
        normalize_arabic_text('ثانيه ابتدائي'): '2_pri',
        normalize_arabic_text('ثالث ابتدائي'): '3_pri',
        normalize_arabic_text('ثالثه ابتدائي'): '3_pri',
        normalize_arabic_text('رابع ابتدائي'): '4_pri',
        normalize_arabic_text('رابعه ابتدائي'): '4_pri',
        normalize_arabic_text('خامس ابتدائي'): '5_pri',
        normalize_arabic_text('خامسه ابتدائي'): '5_pri',
        normalize_arabic_text('سادس ابتدائي'): '6_pri',
        normalize_arabic_text('سادسه ابتدائي'): '6_pri',
        normalize_arabic_text('أول متوسط'): '1_med',
        normalize_arabic_text('اول متوسط'): '1_med',
        normalize_arabic_text('اولى متوسط'): '1_med',
        normalize_arabic_text('اولي متوسط'): '1_med',
        normalize_arabic_text('ثاني متوسط'): '2_med',
        normalize_arabic_text('ثالث متوسط'): '3_med',
        normalize_arabic_text('أول ثانوي'): '1_sec',
        normalize_arabic_text('اول ثانوي'): '1_sec',
        normalize_arabic_text('ثاني ثانوي'): '2_sec',
        normalize_arabic_text('ثالث ثانوي'): '3_sec',
        normalize_arabic_text('جامعي'): 'uni',
    }

    return label_map.get(normalized_text, '')


def parse_excel_birth_date(value):
    if value in (None, ''):
        return ''

    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, (int, float)):
        try:
            base_date = datetime(1899, 12, 30)
            parsed = base_date + timedelta(days=float(value))
            return parsed.strftime('%Y-%m-%d')
        except Exception:
            return str(value)

    text = str(value).strip()
    digit_map = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
    text = text.translate(digit_map)
    return text


def read_excel_sheet_as_dicts(uploaded_file):
    workbook = load_workbook(uploaded_file, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []

    headers = [normalize_excel_value(item) for item in rows[0]]
    data_rows = []

    for row_idx, row_values in enumerate(rows[1:], start=2):
        row_data = {}
        for col_idx, header in enumerate(headers):
            if not header:
                continue
            row_data[header] = row_values[col_idx] if col_idx < len(row_values) else None
        data_rows.append({'excel_row': row_idx, 'data': row_data})

    return data_rows


def sheet_to_dict_rows(sheet):
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []

    headers = [normalize_excel_value(item) for item in rows[0]]
    result = []

    for row_values in rows[1:]:
        row_data = {}
        for col_idx, header in enumerate(headers):
            if not header:
                continue
            row_data[header] = row_values[col_idx] if col_idx < len(row_values) else None
        result.append(row_data)

    return result


def parse_memorization_bundle_from_workbook(workbook):
    metadata_sheet = workbook['metadata'] if 'metadata' in workbook.sheetnames else None
    if metadata_sheet is None and 'meta' in workbook.sheetnames:
        metadata_sheet = workbook['meta']

    if metadata_sheet is not None:
        metadata_rows = sheet_to_dict_rows(metadata_sheet)
        metadata_map = {
            normalize_excel_value(row.get('key')): row.get('value')
            for row in metadata_rows
            if normalize_excel_value(row.get('key'))
        }

        template_map = {}
        for key, value in metadata_map.items():
            match = re.match(r'^template\.(\d+)\.(value|dataKey|title|description|sheet)$', key)
            if not match:
                continue
            idx = int(match.group(1))
            field = match.group(2)
            if idx not in template_map:
                template_map[idx] = {}
            template_map[idx][field] = normalize_excel_value(value)

        template_defs = []
        memorization_data = {}

        for idx in sorted(template_map.keys()):
            item = template_map[idx]
            value = normalize_excel_value(item.get('value'))
            data_key = normalize_excel_value(item.get('dataKey'))
            title = normalize_excel_value(item.get('title'))
            description = normalize_excel_value(item.get('description'))
            sheet_name = normalize_excel_value(item.get('sheet'))

            if not value or not data_key or not title or not sheet_name:
                continue
            if sheet_name not in workbook.sheetnames:
                continue

            data_rows = sheet_to_dict_rows(workbook[sheet_name])
            entries = [
                normalize_excel_value(row.get('entryText') or row.get('entry') or row.get('value'))
                for row in data_rows
            ]
            entries = [entry for entry in entries if entry]
            if not entries:
                continue

            memorization_data[data_key] = {
                'data': entries,
                'index': {},
            }
            template_defs.append({
                'value': value,
                'dataKey': data_key,
                'title': title,
                'description': description,
            })

        if template_defs and memorization_data:
            return {
                'template_definitions': template_defs,
                'memorization_data': memorization_data,
            }

    # Legacy format fallback: templates + entries + indexes sheets.
    if 'entries' not in workbook.sheetnames:
        raise ValueError('الملف لا يحتوي على ورقة metadata أو entries بالصيغة المعتمدة.')

    template_rows = sheet_to_dict_rows(workbook['templates']) if 'templates' in workbook.sheetnames else []
    data_rows = sheet_to_dict_rows(workbook['entries'])
    index_rows = sheet_to_dict_rows(workbook['indexes']) if 'indexes' in workbook.sheetnames else []

    memorization_data = {}
    for row in data_rows:
        data_key = normalize_excel_value(row.get('dataKey'))
        entry_text = normalize_excel_value(row.get('entryText'))
        entry_index_raw = row.get('entryIndex')
        if not data_key or not entry_text:
            continue

        try:
            entry_index = int(entry_index_raw)
        except (TypeError, ValueError):
            continue

        if data_key not in memorization_data:
            memorization_data[data_key] = {'data': [], 'index': {}}

        data_list = memorization_data[data_key]['data']
        while len(data_list) <= entry_index:
            data_list.append('')
        data_list[entry_index] = entry_text

    for payload in memorization_data.values():
        payload['data'] = [entry for entry in payload['data'] if entry]

    for row in index_rows:
        data_key = normalize_excel_value(row.get('dataKey'))
        index_key = normalize_excel_value(row.get('indexKey'))
        if not data_key or not index_key or data_key not in memorization_data:
            continue

        try:
            index_value = int(row.get('indexValue'))
        except (TypeError, ValueError):
            continue

        if 0 <= index_value < len(memorization_data[data_key]['data']):
            memorization_data[data_key]['index'][index_key] = index_value

    template_defs = []
    if template_rows:
        for row in template_rows:
            value = normalize_excel_value(row.get('value'))
            data_key = normalize_excel_value(row.get('dataKey'))
            title = normalize_excel_value(row.get('title'))
            description = normalize_excel_value(row.get('description'))
            if not value or not data_key or not title or data_key not in memorization_data:
                continue
            template_defs.append({
                'value': value,
                'dataKey': data_key,
                'title': title,
                'description': description,
            })

    if not template_defs:
        for idx, data_key in enumerate(memorization_data.keys(), start=1):
            template_defs.append({
                'value': f'custom_{idx}',
                'dataKey': data_key,
                'title': f'خطة {data_key}',
                'description': 'خطة مستوردة',
            })

    if not memorization_data:
        raise ValueError('لا توجد بيانات حفظ صالحة داخل الملف المرفوع.')

    return {
        'template_definitions': template_defs,
        'memorization_data': memorization_data,
    }


def merge_sibling_rows(rows):
    """Group attendance rows by parent phone so siblings get one combined message.

    Within a group: first names are joined with ' و', total_days are summed,
    and teacher info is taken from the first sibling. Rows without a parent
    phone are passed through individually so they still appear in the failure
    list of send_batch_messages.
    """
    grouped = {}
    no_phone_rows = []
    order = []

    for row in rows:
        phone = (row.get('phone_number') or '').strip()
        if not phone:
            no_phone_rows.append(row)
            continue
        if phone not in grouped:
            grouped[phone] = []
            order.append(phone)
        grouped[phone].append(row)

    merged = []
    for phone in order:
        siblings = grouped[phone]
        if len(siblings) == 1:
            merged.append(siblings[0])
            continue

        first_names = [s.get('first_name') or '' for s in siblings if s.get('first_name')]
        full_names = [s.get('full_name') or '' for s in siblings if s.get('full_name')]

        combined = dict(siblings[0])
        if first_names:
            combined['first_name'] = ' و'.join(first_names)
        if full_names:
            combined['full_name'] = ' و'.join(full_names)
        combined['total_days'] = sum(int(s.get('total_days') or 0) for s in siblings)
        merged.append(combined)

    merged.extend(no_phone_rows)
    return merged


def build_status_export_rows(target_date, status_code):
    attendances = Attendance.objects.filter(date=target_date, status=status_code).select_related('student')
    rows = []

    for attendance in attendances:
        student = attendance.student
        teacher = student.teacher
        full_name = student.full_name or ''
        first_name = full_name.split()[0] if full_name.split() else ''
        total_days = Attendance.objects.filter(student=student, status=status_code).count()
        teacher_name = ''
        teacher_phone = ''

        if teacher:
            teacher_name = teacher.get_full_name() or teacher.username or ''
            profile = getattr(teacher, 'teacher_profile', None)
            teacher_phone = normalize_saudi_phone(getattr(profile, 'phone', '')) if profile else ''

        rows.append({
            'phone_number': normalize_saudi_phone(student.parent_phone),
            'first_name': first_name,
            'full_name': full_name,
            'teacher_name': teacher_name,
            'teacher_phone': teacher_phone,
            'total_days': total_days,
            'today_date': target_date,
            'today_day_name': get_arabic_weekday_name(target_date),
        })

    return rows


def export_status_rows_to_excel(rows, status_label, target_date):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = status_label
    worksheet.sheet_view.rightToLeft = True

    headers = ['رقم الجوال', 'الاسم الأول', 'الاسم الكامل', f'إجمالي أيام {status_label}', 'تاريخ اليوم', 'اسم اليوم']
    worksheet.append(headers)

    for row in rows:
        worksheet.append([
            row['phone_number'],
            row['first_name'],
            row['full_name'],
            row['total_days'],
            row['today_date'].strftime('%Y-%m-%d'),
            row['today_day_name'],
        ])

    filename = f'preparer_contacts_{status_label}_{target_date.strftime("%Y-%m-%d")}.xlsx'
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    workbook.save(response)
    return response


def render_message_template(template_text, row_data):
    """Simple token renderer for templates like: Hello {{{first_name}}}."""
    if not template_text:
        return ''

    placeholders = {
        'first_name': row_data.get('first_name', ''),
        'full_name': row_data.get('full_name', ''),
        'phone_number': row_data.get('phone_number', ''),
        'teacher_name': row_data.get('teacher_name', ''),
        'teacher_phone': row_data.get('teacher_phone', ''),
        'total_days': row_data.get('total_days', ''),
        'part_number': row_data.get('part_number', ''),
        'today_date': row_data.get('today_date', ''),
        'today_day_name': row_data.get('today_day_name', ''),
        # Arabic aliases for template variables.
        'الاسم_الأول': row_data.get('first_name', ''),
        'الاسم_الكامل': row_data.get('full_name', ''),
        'رقم_الجوال': row_data.get('phone_number', ''),
        'اسم_المعلم': row_data.get('teacher_name', ''),
        'جوال_المعلم': row_data.get('teacher_phone', ''),
        'رقم_جوال_المعلم': row_data.get('teacher_phone', ''),
        'المجموع': row_data.get('total_days', ''),
        'رقم_الجزء': row_data.get('part_number', ''),
        'التاريخ': row_data.get('today_date', ''),
        'اليوم': row_data.get('today_day_name', ''),
    }

    rendered = template_text
    for key, value in placeholders.items():
        rendered = rendered.replace(f'{{{{{{{key}}}}}}}', str(value or ''))
    return rendered.strip()


def send_sms_via_api(phone_number, message_text):
    """Send one SMS using a configurable JSON API endpoint."""
    api_url = getattr(settings, 'SMS_API_URL', '').strip()
    api_key = getattr(settings, 'SMS_API_KEY', '').strip()

    if not api_url:
        return False, 'SMS API URL is not configured.'
    if not api_key:
        return False, 'SMS API key is not configured.'

    phone_field = getattr(settings, 'SMS_PHONE_FIELD', 'to')
    message_field = getattr(settings, 'SMS_MESSAGE_FIELD', 'message')
    sender_field = getattr(settings, 'SMS_SENDER_FIELD', 'sender')
    sender_id = getattr(settings, 'SMS_SENDER_ID', '').strip()

    phone_is_array = bool(getattr(settings, 'SMS_PHONE_IS_ARRAY', False))

    payload = {
        phone_field: [phone_number] if phone_is_array else phone_number,
        message_field: message_text,
    }

    if sender_id:
        payload[sender_field] = sender_id
    elif sender_field == 'src':
        return False, 'SMS_SENDER_ID is not configured (required field: src).'

    auth_header = getattr(settings, 'SMS_AUTH_HEADER', 'Authorization')
    auth_scheme = getattr(settings, 'SMS_AUTH_SCHEME', 'Bearer').strip()
    auth_value = f'{auth_scheme} {api_key}' if auth_scheme else api_key

    body = json.dumps(payload).encode('utf-8')
    req = urlrequest.Request(
        api_url,
        data=body,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            auth_header: auth_value,
        },
        method='POST',
    )

    try:
        timeout = int(getattr(settings, 'SMS_API_TIMEOUT', 15))
        with urlrequest.urlopen(req, timeout=timeout) as response:
            status_code = getattr(response, 'status', 200)
            return 200 <= status_code < 300, f'HTTP {status_code}'
    except HTTPError as exc:
        return False, f'HTTP {exc.code}'
    except URLError as exc:
        return False, f'URL error: {exc.reason}'
    except Exception as exc:
        return False, str(exc)


def send_batch_messages(rows, template_text):
    """Send templated messages to each row phone and return a summary."""
    success_count = 0
    failed_count = 0
    failures = []

    for row in rows:
        phone_number = row.get('phone_number')
        if not phone_number:
            failed_count += 1
            failures.append('رقم هاتف فارغ')
            continue

        message_text = render_message_template(template_text, row)
        if not message_text:
            failed_count += 1
            failures.append(f'{phone_number}: الرسالة فارغة')
            continue

        ok, info = send_sms_via_api(phone_number, message_text)
        if ok:
            success_count += 1
        else:
            failed_count += 1
            failures.append(f'{phone_number}: {info}')

    return {
        'success_count': success_count,
        'failed_count': failed_count,
        'failures': failures[:5],
    }


def send_whatsapp_batch(messages):
    """Send a list of {phone, text, label} via the local whatsapp-web.js bot.

    Returns a summary dict similar to send_batch_messages.
    """
    bot_url = (getattr(settings, 'WHATSAPP_BOT_URL', '') or '').strip()
    if not bot_url:
        return {
            'success_count': 0,
            'failed_count': len(messages),
            'failures': ['WHATSAPP_BOT_URL is not configured.'],
        }

    bot_token = getattr(settings, 'WHATSAPP_BOT_TOKEN', '') or ''
    timeout = getattr(settings, 'WHATSAPP_BOT_TIMEOUT', 600)
    min_delay_ms = getattr(settings, 'WHATSAPP_MIN_DELAY_MS', 4000)
    max_delay_ms = getattr(settings, 'WHATSAPP_MAX_DELAY_MS', 12000)

    payload = {
        'messages': messages,
        'min_delay_ms': min_delay_ms,
        'max_delay_ms': max_delay_ms,
    }
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    endpoint = bot_url.rstrip('/') + '/send'

    req = urlrequest.Request(
        endpoint,
        data=body,
        headers={
            'Content-Type': 'application/json; charset=utf-8',
            'X-Bot-Token': bot_token,
        },
        method='POST',
    )

    try:
        with urlrequest.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode('utf-8') or '{}'
            data = json.loads(raw)
    except HTTPError as e:
        return {
            'success_count': 0,
            'failed_count': len(messages),
            'failures': [f'WhatsApp bot HTTP {e.code}: {e.reason}'],
        }
    except (URLError, TimeoutError) as e:
        return {
            'success_count': 0,
            'failed_count': len(messages),
            'failures': [f'WhatsApp bot unreachable: {e}'],
        }
    except json.JSONDecodeError:
        return {
            'success_count': 0,
            'failed_count': len(messages),
            'failures': ['WhatsApp bot returned invalid JSON.'],
        }

    results = data.get('results', []) if isinstance(data, dict) else []
    success_count = sum(1 for r in results if r.get('ok'))
    failed_count = sum(1 for r in results if not r.get('ok'))
    failures = []
    for r in results:
        if r.get('ok'):
            continue
        label = r.get('label') or r.get('phone') or '?'
        failures.append(f"{label}: {r.get('error') or 'unknown'}")
        if len(failures) >= 10:
            break

    return {
        'success_count': success_count,
        'failed_count': failed_count,
        'failures': failures,
    }


@login_required
def pending_students(request):
    """صفحة الطلاب المنتظرين - للمشرفين فقط"""
    # التحقق من الصلاحيات
    if not is_stage_supervisor(request.user):
        return redirect('home')

    # جلب الطلاب حسب مرحلة المشرف
    if request.user.is_superuser:
        # المدير يرى جميع الطلاب
        students = Student.objects.filter(status='منتظر').order_by('full_name')
    elif hasattr(request.user, 'stage_supervisor'):
        # مشرف المرحلة يرى فقط طلاب مرحلته
        supervisor = request.user.stage_supervisor
        students = Student.objects.filter(status='منتظر', educational_stage=supervisor.stage).order_by('full_name')
    elif user_has_role(request.user, 'supervisor'):
        # المشرف العام يرى جميع الطلاب
        students = Student.objects.filter(status='منتظر').order_by('full_name')
    else:
        students = Student.objects.none()

    # جلب جميع المعلمين لقائمة التعيين (المعلمين الحاليين + الموظفين)
    teachers = User.objects.filter(
        Q(student__isnull=False) | Q(is_staff=True)
    ).distinct().order_by('username')

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
=======
def preparer_take_students_attendance(request):
    """تحضير طلاب أي معلم - للمحضّر فقط"""
    if not can_access_preparer_attendance(request.user):
        return redirect('home')

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

    default_templates = {
        'absent': 'ولي الأمر المكرم، نفيدكم بغياب الابن {{{الاسم_الأول}}} اليوم {{{اليوم}}} {{{التاريخ}}}. مجموع أيام غيابه حتى الآن: ({{{المجموع}}}) أيام. للاستفسار: المعلم {{{اسم_المعلم}}} - {{{جوال_المعلم}}}.\nإدارة جامع الحمودي',
        'absent_excused': 'ولي الأمر المكرم، نفيدكم بغياب الابن {{{الاسم_الأول}}} بعذر اليوم {{{اليوم}}} {{{التاريخ}}}. مجموع مرات الغياب بعذر حتى الآن: ({{{المجموع}}}) يوم. للاستفسار: المعلم {{{اسم_المعلم}}} - {{{جوال_المعلم}}}.\nإدارة جامع الحمودي',
        'late': 'ولي الأمر المكرم، نحيطكم علماً بتأخر الابن {{{الاسم_الأول}}} عن حلقة اليوم {{{اليوم}}} {{{التاريخ}}}. مجموع مرات التأخير: ({{{المجموع}}}). للاستفسار: المعلم {{{اسم_المعلم}}} - {{{جوال_المعلم}}}.\nإدارة جامع الحمودي',
        'excused': 'ولي الأمر المكرم، نود إحاطتكم بانصراف الابن {{{الاسم_الأول}}} وخروجه قبل نهاية وقت الحلقة اليوم {{{اليوم}}}. مجموع مرات الانصراف: ({{{المجموع}}}). للاستفسار: المعلم {{{اسم_المعلم}}} - {{{جوال_المعلم}}}.\nإدارة جامع الحمودي',
    }

    saved_templates = {
        row.section: row.template_text
        for row in SmsTemplateSetting.objects.filter(user=request.user)
    }

    current_templates = {
        'absent': saved_templates.get('absent', default_templates['absent']),
        'absent_excused': saved_templates.get('absent_excused', default_templates['absent_excused']),
        'late': saved_templates.get('late', default_templates['late']),
        'excused': saved_templates.get('excused', default_templates['excused']),
    }

    posted_templates = {
        'absent': request.POST.get('absent_sms_template'),
        'absent_excused': request.POST.get('absent_excused_sms_template'),
        'late': request.POST.get('late_sms_template'),
        'excused': request.POST.get('excused_sms_template'),
    }
    for key, value in posted_templates.items():
        if value is not None:
            current_templates[key] = value

    template_save_feedback = None
    if request.method == 'POST':
        reset_student_id = request.POST.get('reset_student_id')
        if reset_student_id:
            student = get_object_or_404(Student, id=reset_student_id)
            student.absence_reset_at = timezone.now().date()
            student.save()
            return redirect(f"{reverse('preparer_absent_contacts')}?date={target_date}")

        if request.POST.get('save_templates') == '1':
            template_field_map = {
                'absent': 'absent_sms_template',
                'absent_excused': 'absent_excused_sms_template',
                'late': 'late_sms_template',
                'excused': 'excused_sms_template',
            }
            saved_count = 0
            for section, field_name in template_field_map.items():
                if field_name not in request.POST:
                    continue
                template_text = (request.POST.get(field_name) or '').strip()
                if not template_text:
                    template_text = default_templates[section]

                SmsTemplateSetting.objects.update_or_create(
                    user=request.user,
                    section=section,
                    defaults={'template_text': template_text},
                )
                current_templates[section] = template_text
                saved_count += 1

            template_save_feedback = f'تم حفظ القالب بنجاح ({saved_count}).'

    def collect_parent_phones_by_status(status_code):
        status_attendance = Attendance.objects.filter(date=target_date, status=status_code).select_related('student')
        phones = []
        for attendance in status_attendance:
            formatted = normalize_saudi_phone(attendance.student.parent_phone)
            if formatted:
                phones.append(formatted)

        unique_phones = sorted(set(phones))
        return {
            'phones': unique_phones,
            'phones_text': "\n".join(unique_phones),
            'phones_count': len(unique_phones),
        }

    absent_contacts = collect_parent_phones_by_status('غائب')
    absent_excused_contacts = collect_parent_phones_by_status('غياب بعذر')
    late_contacts = collect_parent_phones_by_status('متأخر')
    excused_contacts = collect_parent_phones_by_status('مستأذن')

    status_rows = {
        'absent': build_status_export_rows(target_date, 'غائب'),
        'absent_excused': build_status_export_rows(target_date, 'غياب بعذر'),
        'late': build_status_export_rows(target_date, 'متأخر'),
        'excused': build_status_export_rows(target_date, 'مستأذن'),
    }

    sms_feedback = None
    if request.method == 'POST':
        sms_action = request.POST.get('sms_action')
        if sms_action in status_rows and request.POST.get('save_templates') != '1':
            merged_rows = merge_sibling_rows(status_rows[sms_action])
            batch_result = send_batch_messages(merged_rows, current_templates[sms_action])
            sms_feedback = {
                'section': sms_action,
                'success_count': batch_result['success_count'],
                'failed_count': batch_result['failed_count'],
                'failures': batch_result['failures'],
            }

    if download_type in {'absent', 'absent_excused', 'late', 'excused'}:
        status_map = {
            'absent': ('غائب', 'غياب'),
            'absent_excused': ('غياب بعذر', 'غياب_بعذر'),
            'late': ('متأخر', 'تأخر'),
            'excused': ('مستأذن', 'انصراف'),
        }
        status_code, status_label = status_map[download_type]
        rows = build_status_export_rows(target_date, status_code)
        return export_status_rows_to_excel(rows, status_label, target_date)

    at_risk = []
    students = Student.objects.filter(status='منتظم').order_by('full_name')
    for student in students:
        total_absences = Attendance.objects.filter(
            student=student,
            status='غائب'
        ).count()

        if student.absence_reset_at:
            temp_count = Attendance.objects.filter(
                student=student,
                status='غائب',
                created_at__date__gt=student.absence_reset_at
            ).count()
        else:
            temp_count = Attendance.objects.filter(
                student=student,
                status='غائب'
            ).count()
        if temp_count >= 5:
            parent_phone = normalize_saudi_phone(student.parent_phone)
            if parent_phone.startswith('966'):
                parent_phone = '0' + parent_phone[3:]
            at_risk.append({
                'student': student,
                'temp_count': temp_count,
                'total_absences': total_absences,
                'parent_phone': parent_phone,
            })

    context = {
        'target_date': target_date,
        'absent_phones_text': absent_contacts['phones_text'],
        'absent_phones_count': absent_contacts['phones_count'],
        'absent_excused_phones_text': absent_excused_contacts['phones_text'],
        'absent_excused_phones_count': absent_excused_contacts['phones_count'],
        'late_phones_text': late_contacts['phones_text'],
        'late_phones_count': late_contacts['phones_count'],
        'excused_phones_text': excused_contacts['phones_text'],
        'excused_phones_count': excused_contacts['phones_count'],
        'absent_sms_template': current_templates['absent'],
        'absent_excused_sms_template': current_templates['absent_excused'],
        'late_sms_template': current_templates['late'],
        'excused_sms_template': current_templates['excused'],
        'sms_feedback': sms_feedback,
        'template_save_feedback': template_save_feedback,
        'at_risk': at_risk,
    }
    return render(request, 'preparer_absent_contacts.html', context)

# 1. للمدير فقط: لا يدخل إلا من لديه صلاحيات Superuser
def is_admin(user):
    return user.is_superuser or user_has_role(user, 'manager')

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    # كود لوحة التحكم الشاملة
    return render(request, 'admin_view.html')


@login_required
@user_passes_test(is_admin)
def export_student_data(request):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'بيانات الطلاب'
    worksheet.sheet_view.rightToLeft = True

    headers = [
        'اسم الطالب',
        'جوال الطالب',
        'جوال ولي الأمر',
        'رقم الهوية الوطنية',
        'الصف الدراسي',
        'آخر جزء تم اختباره',
        'التحفيظ السابق',
        'الحي',
        'المعلم المسؤول',
        'الحالة',
        'المرحلة التعليمية',
    ]
    students = Student.objects.select_related('teacher').order_by('full_name', 'id')
    rows = [headers]
    for student in students:
        teacher_name = ''
        if student.teacher:
            teacher_name = student.teacher.get_full_name() or student.teacher.username
        rows.append([
            student.full_name,
            student.student_phone,
            student.parent_phone,
            student.identity_number,
            student.get_grade_display(),
            student.get_last_tested_part_display(),
            student.previous_center,
            student.neighborhood,
            teacher_name,
            student.get_status_display(),
            student.educational_stage,
        ])

    for row_number, row in enumerate(rows, start=1):
        for column_number, value in enumerate(row, start=1):
            cell = worksheet.cell(row=row_number, column=column_number)
            cell.value = '' if value is None else str(value)
            cell.data_type = 's'

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="student_data.xlsx"'
    workbook.save(response)
    return response

@login_required
@user_passes_test(is_admin)
def admin_statistics(request):
    """صفحة الإحصائيات الشاملة للمدير"""
    from django.db.models import Count, Q

    # الحصول على جميع المراحل الموجودة
    STAGES = [
        ('مبكرة', 'مبكرة'),
        ('عليا', 'عليا'),
        ('متوسط', 'متوسط'),
        ('ثانوي', 'ثانوي'),
        ('جامعي', 'جامعي'),
    ]

    # إحصائيات عامة
    total_students = Student.objects.filter(status='منتظم').count()
    total_tested = ExamNomination.objects.filter(internal_passed=True).count()

    # إجمالي الغياب اليومي
    today = timezone.now().date()
    total_absent_today = Attendance.objects.filter(date=today, status='غائب').count()
    total_teacher_absent_today = TeacherAttendance.objects.filter(date=today, status='غائب').count()

    # إحصائيات حسب المرحلة
    stage_stats = []
    for stage_code, stage_name in STAGES:
        stage_students = Student.objects.filter(status='منتظم', educational_stage=stage_code)
        stage_tested = ExamNomination.objects.filter(
            student__educational_stage=stage_code,
            internal_passed=True
        ).count()

        # الغياب اليومي في هذه المرحلة
        stage_absent_today = Attendance.objects.filter(
            student__educational_stage=stage_code,
            date=today,
            status='غائب'
        ).count()

        if stage_students.count() > 0:
            stage_stats.append({
                'stage': stage_name,
                'total_students': stage_students.count(),
                'tested': stage_tested,
                'absent_today': stage_absent_today,
            })

    # إحصائيات حسب المعلم
    teachers = User.objects.filter(
        student__status='منتظم'
    ).distinct().order_by('username')

    teacher_stats = []
    for teacher in teachers:
        teacher_students = Student.objects.filter(teacher=teacher, status='منتظم')
        teacher_tested = ExamNomination.objects.filter(
            teacher=teacher,
            internal_passed=True
        ).count()

        # الغياب اليومي عند هذا المعلم
        teacher_absent_today = Attendance.objects.filter(
            student__teacher=teacher,
            date=today,
            status='غائب'
        ).count()

        # غياب المعلم نفسه اليوم
        teacher_self_absent_today = TeacherAttendance.objects.filter(
            teacher=teacher,
            date=today,
            status='غائب'
        ).count()

        # إحصائيات المعلم حسب المرحلة
        teacher_stage_stats = []
        for stage_code, stage_name in STAGES:
            stage_students = teacher_students.filter(educational_stage=stage_code)
            if stage_students.count() > 0:
                stage_tested = ExamNomination.objects.filter(
                    teacher=teacher,
                    student__educational_stage=stage_code,
                    internal_passed=True
                ).count()

                stage_absent = Attendance.objects.filter(
                    student__teacher=teacher,
                    student__educational_stage=stage_code,
                    date=today,
                    status='غائب'
                ).count()

                teacher_stage_stats.append({
                    'stage': stage_name,
                    'total_students': stage_students.count(),
                    'tested': stage_tested,
                    'absent_today': stage_absent,
                })

        teacher_stats.append({
            'teacher': teacher.username,
            'total_students': teacher_students.count(),
            'tested': teacher_tested,
            'absent_today': teacher_absent_today,
            'teacher_self_absent_today': teacher_self_absent_today,
            'stage_stats': teacher_stage_stats,
        })

    context = {
        'total_students': total_students,
        'total_tested': total_tested,
        'total_absent_today': total_absent_today,
        'total_teacher_absent_today': total_teacher_absent_today,
        'today': today,
        'stage_stats': stage_stats,
        'teacher_stats': teacher_stats,
    }

    return render(request, 'admin_statistics.html', context)

# 2. للمعلمين: أي مستخدم مسجل دخول (معلم أو مدير)
@login_required
def attendance_view(request):
    # كود التحضير
    return render(request, 'attendance.html')
