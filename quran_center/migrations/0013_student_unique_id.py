from django.db import migrations, models
import uuid


def assign_unique_ids(apps, schema_editor):
    Student = apps.get_model('quran_center', 'Student')

    for student in Student.objects.filter(student_unique_id__isnull=True):
        while True:
            candidate = f"STD-{uuid.uuid4().hex[:12].upper()}"
            if not Student.objects.filter(student_unique_id=candidate).exists():
                student.student_unique_id = candidate
                student.save(update_fields=['student_unique_id'])
                break


class Migration(migrations.Migration):

    dependencies = [
        ('quran_center', '0012_teacherprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='student_unique_id',
            field=models.CharField(blank=True, editable=False, max_length=24, null=True, unique=True, verbose_name='المعرف الفريد'),
        ),
        migrations.RunPython(assign_unique_ids, migrations.RunPython.noop),
    ]
