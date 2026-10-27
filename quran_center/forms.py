from django import forms
from .models import Student, LAST_TESTED_PART_CHOICES

class StudentRegistrationForm(forms.ModelForm):
    # تعريف خيارات آخر جزء تم اختباره
    last_tested_part = forms.ChoiceField(
        choices=LAST_TESTED_PART_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='آخر جزء تم اختباره'
    )
    
    class Meta:
        model = Student
        # نختار الحقول التي يدخلها الطالب فقط (الحالة والمرحلة تُحسب تلقائياً)
        fields = [
            'full_name', 'student_phone', 'parent_phone', 'identity_number',
            'grade', 'last_tested_part', 'previous_center', 'neighborhood'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'student_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'identity_number': forms.TextInput(attrs={'class': 'form-control'}),
            'grade': forms.Select(attrs={'class': 'form-select'}),
            'previous_center': forms.TextInput(attrs={'class': 'form-control'}),
            'neighborhood': forms.TextInput(attrs={'class': 'form-control'}),
        }


class StudentBulkUploadForm(forms.Form):
    excel_file = forms.FileField(
        label='ملف Excel',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx'})
    )

    def clean_excel_file(self):
        excel_file = self.cleaned_data['excel_file']
        filename = excel_file.name.lower()

        if not filename.endswith('.xlsx'):
            raise forms.ValidationError('يرجى رفع ملف Excel بصيغة .xlsx')

        return excel_file


class MemorizationTemplateUploadForm(forms.Form):
    excel_file = forms.FileField(
        label='ملف قوالب الحفظ (Excel)',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx'})
    )

    def clean_excel_file(self):
        excel_file = self.cleaned_data['excel_file']
        filename = (excel_file.name or '').lower()
        if not filename.endswith('.xlsx'):
            raise forms.ValidationError('يرجى رفع ملف Excel بصيغة .xlsx فقط.')
        return excel_file


class AttendanceReportDateRangeForm(forms.Form):
    start_date = forms.DateField(
        label='من تاريخ',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d'],
    )
    end_date = forms.DateField(
        label='إلى تاريخ',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d'],
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError('يجب أن يكون تاريخ البداية قبل تاريخ النهاية أو مساويًا له.')
        return cleaned_data
