from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_roles_and_parts(apps, schema_editor):
    Role = apps.get_model('quran_center', 'Role')
    Student = apps.get_model('quran_center', 'Student')
    ExamNomination = apps.get_model('quran_center', 'ExamNomination')

    role_choices = [
        ('preparer', 'المُحضّر'),
        ('examiner', 'المُختبر'),
        ('finance', 'المالي'),
        ('supervisor', 'المشرف'),
        ('manager', 'المدير'),
    ]

    for code, name in role_choices:
        Role.objects.get_or_create(code=code, defaults={'name': name})

    allowed_parts = {'0', '1', '2', '3', '5', '8', '10', '13', '15', '20', '25', '30'}

    for student in Student.objects.all():
        current = (student.last_tested_part or '').strip()
        if current == 'لم يتم الاختبار من قبل':
            student.last_tested_part = '0'
        elif current not in allowed_parts:
            student.last_tested_part = '0'
        student.save(update_fields=['last_tested_part'])

    for nomination in ExamNomination.objects.all():
        current = (nomination.last_tested_part or '').strip()
        if current == 'لم يتم الاختبار من قبل':
            nomination.last_tested_part = '0'
        elif current not in allowed_parts:
            nomination.last_tested_part = '0'
        nomination.save(update_fields=['last_tested_part'])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('quran_center', '0004_examnomination'),
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(choices=[('preparer', 'المُحضّر'), ('examiner', 'المُختبر'), ('finance', 'المالي'), ('supervisor', 'المشرف'), ('manager', 'المدير')], max_length=30, unique=True, verbose_name='الكود')),
                ('name', models.CharField(max_length=30, verbose_name='الاسم')),
            ],
            options={
                'verbose_name': 'عضوية',
                'verbose_name_plural': 'العضويات',
            },
        ),
        migrations.CreateModel(
            name='UserRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='quran_center.role', verbose_name='العضوية')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='المستخدم')),
            ],
            options={
                'verbose_name': 'عضوية مستخدم',
                'verbose_name_plural': 'عضويات المستخدمين',
                'unique_together': {('user', 'role')},
            },
        ),
        migrations.AddField(
            model_name='student',
            name='absence_reset_at',
            field=models.DateField(blank=True, null=True, verbose_name='تاريخ تصفير الغياب المؤقت'),
        ),
        migrations.AlterField(
            model_name='student',
            name='last_tested_part',
            field=models.CharField(choices=[('0', 'لم يتم الاختبار'), ('1', 'جزء 1'), ('2', 'جزء 2'), ('3', 'جزء 3'), ('5', 'جزء 5'), ('8', 'جزء 8'), ('10', 'جزء 10'), ('13', 'جزء 13'), ('15', 'جزء 15'), ('20', 'جزء 20'), ('25', 'جزء 25'), ('30', 'جزء 30 (القرآن كاملاً)')], default='0', max_length=50, verbose_name='آخر جزء تم اختباره'),
        ),
        migrations.AlterField(
            model_name='examnomination',
            name='last_tested_part',
            field=models.CharField(choices=[('0', 'لم يتم الاختبار'), ('1', 'جزء 1'), ('2', 'جزء 2'), ('3', 'جزء 3'), ('5', 'جزء 5'), ('8', 'جزء 8'), ('10', 'جزء 10'), ('13', 'جزء 13'), ('15', 'جزء 15'), ('20', 'جزء 20'), ('25', 'جزء 25'), ('30', 'جزء 30 (القرآن كاملاً)')], max_length=50, verbose_name='آخر جزء تم اختباره'),
        ),
        migrations.RenameField(
            model_name='examnomination',
            old_name='expected_grade',
            new_name='teacher_grade',
        ),
        migrations.RenameField(
            model_name='examnomination',
            old_name='achieved_grade',
            new_name='internal_grade',
        ),
        migrations.AddField(
            model_name='examnomination',
            name='association_grade',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='درجة اختبار الجمعية'),
        ),
        migrations.AddField(
            model_name='examnomination',
            name='internal_passed',
            field=models.BooleanField(default=False, verbose_name='اجتاز الداخلي'),
        ),
        migrations.AddField(
            model_name='examnomination',
            name='association_tested',
            field=models.BooleanField(default=False, verbose_name='تم اختبار الجمعية'),
        ),
        migrations.RemoveField(
            model_name='examnomination',
            name='is_tested',
        ),
        migrations.RunPython(seed_roles_and_parts),
    ]
