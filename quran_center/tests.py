from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date
from quran_center.models import Student, Attendance, StageProfile, Teacher


class PublicPageTest(TestCase):
    def test_welcome_page(self):
        response = self.client.get(reverse('welcome'))
        self.assertEqual(response.status_code, 200)

    def test_welcome_page_content(self):
        """Verify all واعد ٤ promotional content is present."""
        response = self.client.get(reverse('welcome'))
        content = response.content.decode('utf-8')

        # All 9 activities
        for activity in ['ربوع بلادي', 'لقاءات مهارية', 'أنشطة رياضية',
                         'هدايا مميزة', 'تحديات ممتعة', 'مسابقات ثقافية',
                         'مفاجآت متنوعة', 'أنشطة اجتماعية', 'دورات تدريبية']:
            self.assertIn(activity, content, f'Missing activity: {activity}')

        # All 4 features
        for feature in ['كادر تربوي', 'متابعة مستمرة', 'بيئة آمنة', 'برامج ملهمة']:
            self.assertIn(feature, content, f'Missing feature: {feature}')

        # Key dates (Hijri) — dates are split across value and sub elements
        for d in ['10/1', '15/1', '27/1', '23/2']:
            self.assertIn(d, content, f'Missing date: {d}')
        self.assertIn('1448', content)

        # Fees
        self.assertIn('500', content)
        self.assertIn('550', content)
        self.assertIn('600', content)
        self.assertIn('الرسوم لا تشمل', content)

        # Notice
        self.assertIn('التسجيل لا يُعد مؤكدًا', content)

        # Google Form link (appears twice: hero + final CTA)
        self.assertIn('forms.gle/FQUnKzF9UemCo4mB6', content)
        self.assertEqual(content.count('forms.gle/FQUnKzF9UemCo4mB6'), 2)
        self.assertIn('target="_blank"', content)
        self.assertIn('noopener', content)

        # Staff links still present
        self.assertIn('تسجيل الدخول', content)
        self.assertIn('الاستعلام عن حالة الأبناء', content)

        # Logo reference
        self.assertIn('waed4_logo.jpeg', content)

        # No attendance data leakage
        self.assertNotIn('national_id', content)

    def test_parent_inquiry_page(self):
        response = self.client.get(reverse('parent_inquiry'))
        self.assertEqual(response.status_code, 200)

    def test_login_page(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)


class AttendancePageAccessTest(TestCase):
    def test_redirects_when_not_logged_in(self):
        response = self.client.get(reverse('attendance_page'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])


class AttendanceFlowTest(TestCase):
    """End-to-end test: stage account edits a period, finalizes, manager overrides."""

    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_superuser(
            username='manager', password='demo12345',
        )
        cls.stage_user = User.objects.create_user(
            username='stage_mubkira', password='demo12345',
        )
        StageProfile.objects.create(user=cls.stage_user, managed_stage='مبكرة')
        cls.teacher = Teacher.objects.create(name='أ. اختبار', stage='مبكرة')
        cls.student = Student.objects.create(
            national_id='1234567890',
            full_name='طالب تجريبي',
            stage='مبكرة',
            teacher=cls.teacher,
            parent_phone='0500000000',
        )

    def test_stage_account_can_save_period(self):
        self.client.login(username='stage_mubkira', password='demo12345')
        today = date.today().isoformat()
        response = self.client.post(reverse('save_period'), {
            'student_id': '1234567890',
            'date': today,
            'period': '1',
            'status': 'غائب',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        att = Attendance.objects.get(student=self.student, date=today)
        self.assertEqual(att.period_1, 'غائب')

    def test_stage_account_cannot_edit_other_stage(self):
        other_user = User.objects.create_user(username='stage_thaanawi', password='demo12345')
        StageProfile.objects.create(user=other_user, managed_stage='ثانوي')
        self.client.login(username='stage_thaanawi', password='demo12345')
        today = date.today().isoformat()
        response = self.client.post(reverse('save_period'), {
            'student_id': '1234567890',
            'date': today,
            'period': '1',
            'status': 'غائب',
        })
        data = response.json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'permission denied')

    def test_finalized_locks_stage_account_but_not_manager(self):
        today = date.today().isoformat()

        self.client.login(username='stage_mubkira', password='demo12345')
        response = self.client.post(reverse('finalize_attendance'), {
            'date': today,
            'stage': 'مبكرة',
        })
        self.assertEqual(response.json()['ok'], True)
        att = Attendance.objects.get(student=self.student, date=today)
        self.assertTrue(att.is_finalized)

        response = self.client.post(reverse('save_period'), {
            'student_id': '1234567890',
            'date': today,
            'period': '1',
            'status': 'متأخر',
        })
        self.assertEqual(response.json()['error'], 'finalized')

        self.client.login(username='manager', password='demo12345')
        response = self.client.post(reverse('save_period'), {
            'student_id': '1234567890',
            'date': today,
            'period': '1',
            'status': 'متأخر',
        })
        self.assertTrue(response.json()['ok'])
        att.refresh_from_db()
        self.assertEqual(att.period_1, 'متأخر')

    def test_change_log_created_on_period_change(self):
        self.client.login(username='stage_mubkira', password='demo12345')
        today = date.today().isoformat()

        self.client.post(reverse('save_period'), {
            'student_id': '1234567890', 'date': today,
            'period': '2', 'status': 'غائب',
        })
        att = Attendance.objects.get(student=self.student, date=today)
        self.assertEqual(att.change_logs.count(), 1)
        log = att.change_logs.first()
        self.assertEqual(log.old_value, 'حاضر')
        self.assertEqual(log.new_value, 'غائب')
        self.assertEqual(log.period_number, 2)

        self.client.post(reverse('save_period'), {
            'student_id': '1234567890', 'date': today,
            'period': '2', 'status': 'متأخر',
        })
        att.refresh_from_db()
        self.assertEqual(att.change_logs.count(), 2)
        latest_log = att.change_logs.first()
        self.assertEqual(latest_log.old_value, 'غائب')
        self.assertEqual(latest_log.new_value, 'متأخر')

    def test_national_id_not_in_parent_portal(self):
        Student.objects.create(
            national_id='9999999999',
            full_name='طالب اختبار',
            stage='مبكرة',
            teacher=self.teacher,
            parent_phone='0555555555',
        )
        response = self.client.post(reverse('parent_inquiry'), {
            'parent_phone': '0555555555',
        })
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertNotIn('9999999999', content)
        self.assertNotIn('1234567890', content)
        self.assertNotIn('national_id', content)

    def test_manager_sees_all_stages(self):
        self.client.login(username='manager', password='demo12345')
        response = self.client.get(reverse('attendance_page'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        for stage_code in ['مبكرة', 'عليا', 'متوسط', 'ثانوي', 'جامعي']:
            self.assertIn(stage_code, content)

    def test_stage_account_sees_only_their_stage(self):
        self.client.login(username='stage_mubkira', password='demo12345')
        response = self.client.get(reverse('attendance_page'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('مبكرة', content)
        self.assertNotIn('ثانوي', content)

    def test_attendance_page_groups_by_teacher_name(self):
        self.client.login(username='stage_mubkira', password='demo12345')
        response = self.client.get(reverse('attendance_page'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('أ. اختبار', content)


class AddStudentTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_superuser(
            username='manager', password='demo12345',
        )
        cls.stage_user = User.objects.create_user(
            username='stage_mubkira', password='demo12345',
        )
        StageProfile.objects.create(user=cls.stage_user, managed_stage='مبكرة')
        cls.teacher1 = Teacher.objects.create(name='أ. أحمد', stage='مبكرة')
        cls.teacher2 = Teacher.objects.create(name='أ. فاطمة', stage='مبكرة')

    def test_manager_sees_stage_and_teacher_selectors(self):
        self.client.login(username='manager', password='demo12345')
        response = self.client.get(reverse('add_student'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('name="stage"', content)
        self.assertIn('name="teacher"', content)

    def test_manager_can_add_student_with_teacher(self):
        self.client.login(username='manager', password='demo12345')
        response = self.client.post(reverse('add_student'), {
            'national_id': '1112223334',
            'full_name': 'Test Student',
            'stage': 'مبكرة',
            'teacher': str(self.teacher1.id),
            'student_phone': '0501234567',
            'parent_phone': '0509876543',
        })
        self.assertEqual(response.status_code, 200)
        s = Student.objects.filter(national_id='1112223334')
        self.assertTrue(s.exists())
        self.assertEqual(s.first().stage, 'مبكرة')
        self.assertEqual(s.first().teacher, self.teacher1)

    def test_stage_account_sees_teachers_in_their_stage(self):
        self.client.login(username='stage_mubkira', password='demo12345')
        response = self.client.get(reverse('add_student'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('type="hidden" name="stage"', content)
        self.assertIn('أ. أحمد', content)
        self.assertIn('أ. فاطمة', content)

    def test_stage_account_adds_to_their_own_stage(self):
        self.client.login(username='stage_mubkira', password='demo12345')
        response = self.client.post(reverse('add_student'), {
            'national_id': '5556667778',
            'full_name': 'Stage Test',
            'teacher': str(self.teacher2.id),
            'student_phone': '0511112222',
            'parent_phone': '0533334444',
        })
        self.assertEqual(response.status_code, 200)
        s = Student.objects.filter(national_id='5556667778')
        self.assertTrue(s.exists())
        self.assertEqual(s.first().stage, 'مبكرة')
        self.assertEqual(s.first().teacher, self.teacher2)

    def test_duplicate_national_id_rejected(self):
        Student.objects.create(
            national_id='1234500000', full_name='Existing',
            stage='مبكرة', teacher=self.teacher1,
        )
        self.client.login(username='manager', password='demo12345')
        response = self.client.post(reverse('add_student'), {
            'national_id': '1234500000',
            'full_name': 'Duplicate',
            'stage': 'مبكرة',
        })
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('موجود مسبقاً', content)

    def test_short_name_filter(self):
        from quran_center.templatetags.role_tags import short_name
        self.assertEqual(short_name('أحمد عبدالله العتيبي'), 'أحمد ع. العتيبي')
        self.assertEqual(short_name('محمد علي'), 'محمد علي')
        self.assertEqual(short_name('فاطمة'), 'فاطمة')
        self.assertEqual(short_name(''), '')


class AdminPagesTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_superuser(
            username='manager', password='demo12345',
        )
        cls.stage_user = User.objects.create_user(
            username='stage_mubkira', password='demo12345',
        )
        StageProfile.objects.create(user=cls.stage_user, managed_stage='مبكرة')
        cls.teacher = Teacher.objects.create(name='أ. اختبار', stage='مبكرة')
        Student.objects.create(
            national_id='1111111111', full_name='طالب 1',
            stage='مبكرة', teacher=cls.teacher,
        )
        Student.objects.create(
            national_id='2222222222', full_name='طالب 2',
            stage='مبكرة', teacher=cls.teacher,
        )

    def test_statistics_page_manager_only(self):
        # Stage account redirected
        self.client.login(username='stage_mubkira', password='demo12345')
        response = self.client.get(reverse('admin_statistics'))
        self.assertEqual(response.status_code, 302)

        # Manager sees it
        self.client.login(username='manager', password='demo12345')
        response = self.client.get(reverse('admin_statistics'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('مبكرة', content)
        self.assertIn('إجمالي الطلاب', content)

    def test_statistics_shows_student_count(self):
        self.client.login(username='manager', password='demo12345')
        response = self.client.get(reverse('admin_statistics'))
        content = response.content.decode('utf-8')
        # 2 students in مبكرة
        self.assertIn('2', content)

    def test_add_teacher_manager_only(self):
        self.client.login(username='stage_mubkira', password='demo12345')
        response = self.client.get(reverse('add_teacher'))
        self.assertEqual(response.status_code, 302)

        self.client.login(username='manager', password='demo12345')
        response = self.client.get(reverse('add_teacher'))
        self.assertEqual(response.status_code, 200)

    def test_manager_can_add_teacher(self):
        self.client.login(username='manager', password='demo12345')
        response = self.client.post(reverse('add_teacher'), {
            'name': 'أ. معلم جديد',
            'stage': 'ثانوي',
            'phone': '0555555555',
        })
        self.assertEqual(response.status_code, 200)
        t = Teacher.objects.filter(name='أ. معلم جديد', stage='ثانوي')
        self.assertTrue(t.exists())

    def test_teachers_api_returns_json(self):
        self.client.login(username='manager', password='demo12345')
        response = self.client.get(reverse('teachers_api'), {'stage': 'مبكرة'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('teachers', data)
        names = [t['name'] for t in data['teachers']]
        self.assertIn('أ. اختبار', names)
