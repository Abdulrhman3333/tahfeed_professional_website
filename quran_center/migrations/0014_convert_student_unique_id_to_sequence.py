from django.db import migrations, models


def assign_sequence_ids(apps, schema_editor):
    Student = apps.get_model('quran_center', 'Student')

    for index, student in enumerate(Student.objects.order_by('id'), start=1):
        student.student_sequence_id = index
        student.save(update_fields=['student_sequence_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('quran_center', '0013_student_unique_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='student_sequence_id',
            field=models.PositiveIntegerField(blank=True, editable=False, null=True, unique=True, verbose_name='المعرف الفريد'),
        ),
        migrations.RunPython(assign_sequence_ids, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='student',
            name='student_unique_id',
        ),
        migrations.RenameField(
            model_name='student',
            old_name='student_sequence_id',
            new_name='student_unique_id',
        ),
    ]
