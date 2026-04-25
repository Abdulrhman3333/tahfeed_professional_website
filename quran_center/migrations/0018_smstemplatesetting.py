from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('quran_center', '0017_add_absence_with_excuse_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='SmsTemplateSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('section', models.CharField(choices=[('absent', 'غياب'), ('absent_excused', 'غياب بعذر'), ('late', 'تأخر'), ('excused', 'انصراف')], max_length=20, verbose_name='القسم')),
                ('template_text', models.TextField(verbose_name='نص القالب')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sms_template_settings', to='auth.user', verbose_name='المستخدم')),
            ],
            options={
                'verbose_name': 'قالب رسالة SMS',
                'verbose_name_plural': 'قوالب رسائل SMS',
                'unique_together': {('user', 'section')},
            },
        ),
    ]
