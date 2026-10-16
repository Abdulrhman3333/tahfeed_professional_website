from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quran_center', '0016_alter_student_birth_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attendance',
            name='status',
            field=models.CharField(
                choices=[
                    ('حاضر', 'حاضر'),
                    ('غائب', 'غائب'),
                    ('غياب بعذر', 'غياب بعذر'),
                    ('مستأذن', 'مستأذن'),
                    ('متأخر', 'متأخر'),
                ],
                default='حاضر',
                max_length=10,
                verbose_name='الحالة',
            ),
        ),
        migrations.AlterField(
            model_name='teacherattendance',
            name='status',
            field=models.CharField(
                choices=[
                    ('حاضر', 'حاضر'),
                    ('غائب', 'غائب'),
                    ('غياب بعذر', 'غياب بعذر'),
                    ('مستأذن', 'مستأذن'),
                    ('متأخر', 'متأخر'),
                ],
                default='حاضر',
                max_length=10,
                verbose_name='الحالة',
            ),
        ),
    ]
