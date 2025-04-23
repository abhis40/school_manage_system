from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from .models import Class, Student, Test, TestResult, Question
from django.forms import BaseModelFormSet

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))

class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['class_level', 'section', 'stream', 'teachers']

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'roll_number', 'class_name']

class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = ['title', 'subject', 'total_marks', 'time_limit', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'total_marks': forms.NumberInput(attrs={'min': '1', 'step': '1', 'class': 'form-control'}),
            'time_limit': forms.NumberInput(attrs={'min': '1', 'step': '1', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(TestForm, self).__init__(*args, **kwargs)
        
        # Add class selection field
        if user and user.is_teacher:
            # Get all classes for the teacher
            teacher_classes = Class.objects.filter(teachers=user)
            
            # Create choices with a General option
            choices = [('general', 'General (All Classes)')]
            choices.extend([(str(c.id), str(c)) for c in teacher_classes])
            
            self.fields['classes'] = forms.ChoiceField(
                choices=choices,
                widget=forms.Select(attrs={'class': 'form-control'}),
                required=True,
                label='Select Class'
            )
            
            # Add Bootstrap classes to all fields
            for field_name, field in self.fields.items():
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'

    def clean_total_marks(self):
        total_marks = self.cleaned_data.get('total_marks')
        if total_marks is not None and total_marks < 1:
            raise forms.ValidationError('Total marks must be at least 1')
        return total_marks

class TestResultForm(forms.ModelForm):
    class Meta:
        model = TestResult
        fields = ['marks_obtained']
        widgets = {
            'marks_obtained': forms.NumberInput(attrs={'min': '0', 'step': '0.5'}),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text', 'option1', 'option2', 'option3', 'option4', 'correct_option', 'marks']
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'option1': forms.TextInput(attrs={'class': 'form-control'}),
            'option2': forms.TextInput(attrs={'class': 'form-control'}),
            'option3': forms.TextInput(attrs={'class': 'form-control'}),
            'option4': forms.TextInput(attrs={'class': 'form-control'}),
            'correct_option': forms.Select(attrs={'class': 'form-control'}),
            'marks': forms.NumberInput(attrs={'min': '1', 'step': '1', 'class': 'form-control'}),
        }

class BaseQuestionFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = Question.objects.none()

QuestionFormSet = forms.modelformset_factory(
    Question,
    form=QuestionForm,
    formset=BaseQuestionFormSet,
    extra=1,
    can_delete=True,
    validate_min=1,
    exclude=['test']
)

class StudentLoginForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your name'
        })
    )
    parent_mobile = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter parent mobile number'
        })
    )

    def clean_parent_mobile(self):
        parent_mobile = self.cleaned_data['parent_mobile']
        # Remove any non-digit characters
        parent_mobile = ''.join(filter(str.isdigit, parent_mobile))
        if len(parent_mobile) < 10:
            raise forms.ValidationError('Please enter a valid mobile number')
        return parent_mobile

class TestAttemptForm(forms.Form):
    def __init__(self, *args, **kwargs):
        questions = kwargs.pop('questions', [])
        super(TestAttemptForm, self).__init__(*args, **kwargs)
        
        for question in questions:
            self.fields[f'question_{question.id}'] = forms.ChoiceField(
                choices=[
                    (1, question.option1),
                    (2, question.option2),
                    (3, question.option3),
                    (4, question.option4)
                ],
                widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
                label=question.question_text,
                required=True
            ) 