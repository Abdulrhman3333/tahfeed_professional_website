# Generated migration file
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('quran_center', '0002_stagesupervisor'),
    ]

    operations = [
        migrations.AddField(
            model_name='stagesupervisor',
            name='stage',
            field=models.CharField(blank=True, choices=[('مبكرة', 'مبكرة'), ('عليا', 'عليا'), ('متوسط', 'متوسط'), ('ثانوي', 'ثانوي'), ('جامعي', 'جامعي')], max_length=20, null=True, verbose_name='المرحلة المسؤول عنها'),
        ),
        migrations.CreateModel(
            name='AcademicCalendar',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('week_number', models.IntegerField(unique=True, verbose_name='رقم الأسبوع')),
                ('start_date', models.DateField(verbose_name='تاريخ بداية الأسبوع')),
                ('end_date', models.DateField(verbose_name='تاريخ نهاية الأسبوع')),
            ],
            options={
                'verbose_name': 'أسبوع دراسي',
                'verbose_name_plural': 'التقويم الدراسي',
                'ordering': ['week_number'],
            },
        ),
        migrations.AlterField(
            model_name='attendance',
            name='date',
            field=models.DateField(verbose_name='التاريخ'),
        ),
        migrations.AddField(
            model_name='attendance',
            name='weekday',
            field=models.CharField(choices=[('الأحد', 'الأحد'), ('الاثنين', 'الاثنين'), ('الثلاثاء', 'الثلاثاء'), ('الأربعاء', 'الأربعاء'), ('الخميس', 'الخميس')], default='الأحد', max_length=10, verbose_name='اليوم'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='attendance',
            name='week_number',
            field=models.IntegerField(default=1, verbose_name='رقم الأسبوع'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='attendance',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name='attendance',
            name='status',
            field=models.CharField(choices=[('حاضر', 'حاضر'), ('غائب', 'غائب'), ('مستأذن', 'مستأذن'), ('متأخر', 'متأخر')], default='حاضر', max_length=10, verbose_name='الحالة'),
        ),
        migrations.AlterField(
            model_name='student',
            name='grade',
            field=models.CharField(choices=[('1_pri', 'أول ابتدائي'), ('2_pri', 'ثاني ابتدائي'), ('3_pri', 'ثالث ابتدائي'), ('4_pri', 'رابع ابتدائي'), ('5_pri', 'خامس ابتدائي'), ('6_pri', 'سادس ابتدائي'), ('1_med', 'أول متوسط'), ('2_med', 'ثاني متوسط'), ('3_med', 'ثالث متوسط'), ('1_sec', 'أول ثانوي'), ('2_sec', 'ثاني ثانوي'), ('3_sec', 'ثالث ثانوي'), ('uni', 'جامعي')], max_length=20, verbose_name='الصف الدراسي'),
        ),
    ]
