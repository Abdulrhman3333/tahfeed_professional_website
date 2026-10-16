# Generated migration for ExamNomination model
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('quran_center', '0003_auto_updates'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExamNomination',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_tested_part', models.CharField(max_length=50, verbose_name='آخر جزء تم اختباره')),
                ('expected_grade', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='الدرجة المتوقعة')),
                ('achieved_grade', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='الدرجة المحصلة')),
                ('nomination_date', models.DateField(auto_now_add=True, verbose_name='تاريخ الترشيح')),
                ('is_tested', models.BooleanField(default=False, verbose_name='تم الاختبار')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='quran_center.student', verbose_name='الطالب')),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='المعلم المرشح')),
            ],
            options={
                'verbose_name': 'ترشيح اختبار',
                'verbose_name_plural': 'ترشيحات الاختبارات',
                'ordering': ['-nomination_date'],
            },
        ),
    ]
