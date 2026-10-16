from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quran_center', '0023_sync_teacherprofile_class_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='smstemplatesetting',
            name='section',
            field=models.CharField(
                choices=[
                    ('absent', 'غياب'),
                    ('absent_excused', 'غياب بعذر'),
                    ('late', 'تأخر'),
                    ('excused', 'انصراف'),
                    ('association_exam', 'اختبار الجمعية'),
                    ('association_exam_teacher', 'اختبار الجمعية - المعلمين'),
                ],
                max_length=30,
                verbose_name='القسم',
            ),
        ),
    ]
