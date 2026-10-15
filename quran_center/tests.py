from io import BytesIO

from django.contrib.auth.models import User
from django.test import TestCase
from openpyxl import load_workbook

from .models import Role, Student, UserRole


class StudentDataExportTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username='manager', password='password')
        manager_role = Role.objects.create(code='manager', name='المدير')
        UserRole.objects.create(user=self.manager, role=manager_role)
        self.teacher = User.objects.create_user(
            username='teacher', password='password', first_name='معلم', last_name='مسؤول'
        )
        Student.objects.create(
            full_name='طالب تجريبي',
            student_phone='0501234567',
            parent_phone='0557654321',
            identity_number='1234567890',
            grade='1_pri',
            last_tested_part='1',
            previous_center='مركز سابق',
            neighborhood='حي النور',
            teacher=self.teacher,
            status='منتظم',
        )

    def test_manager_can_download_all_requested_student_fields(self):
        self.client.force_login(self.manager)

        response = self.client.get('/admin-dashboard/export-students/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertIn('attachment; filename="student_data.xlsx"', response['Content-Disposition'])
        worksheet = load_workbook(BytesIO(response.content), data_only=False).active
        self.assertEqual(
            [cell.value for cell in worksheet[1]],
            [
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
            ],
        )
        self.assertEqual(
            [cell.value for cell in worksheet[2]],
            [
                'طالب تجريبي',
                '0501234567',
                '0557654321',
                '1234567890',
                'أول ابتدائي',
                'جزء 1',
                'مركز سابق',
                'حي النور',
                'معلم مسؤول',
                'منتظم',
                'مبكرة',
            ],
        )
        self.assertTrue(worksheet.sheet_view.rightToLeft)

    def test_non_admin_cannot_download_student_data(self):
        teacher = User.objects.get(username='teacher')
        self.client.force_login(teacher)

        response = self.client.get('/admin-dashboard/export-students/')

        self.assertEqual(response.status_code, 302)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get('/admin-dashboard/export-students/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])
