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
            'parent_identity', 'grade', 'birth_date', 'last_tested_part', 
            'previous_center', 'neighborhood'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'student_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'identity_number': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_identity': forms.TextInput(attrs={'class': 'form-control'}),
            'grade': forms.Select(attrs={'class': 'form-select'}),
            'birth_date': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: 15/04/2012'}),
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
