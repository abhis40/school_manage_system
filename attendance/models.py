from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# Create your models here.

class User(AbstractUser):
    is_teacher = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username

class Class(models.Model):
    CLASS_LEVEL_CHOICES = [
        ('NURSERY', 'Nursery'),
        ('LKG', 'LKG'),
        ('UKG', 'UKG'),
        ('1', 'Class 1'),
        ('2', 'Class 2'),
        ('3', 'Class 3'),
        ('4', 'Class 4'),
        ('5', 'Class 5'),
        ('6', 'Class 6'),
        ('7', 'Class 7'),
        ('8', 'Class 8'),
        ('9', 'Class 9'),
        ('10', 'Class 10'),
        ('11', 'Class 11'),
        ('12', 'Class 12'),
    ]

    SECTION_CHOICES = [
        ('A', 'Section A'),
        ('B', 'Section B'),
        ('C', 'Section C'),
        ('D', 'Section D'),
        ('E', 'Section E'),
    ]

    STREAM_CHOICES = [
        ('ARTS', 'Arts'),
        ('COMMERCE', 'Commerce'),
        ('MEDICAL', 'Medical'),
        ('NON_MEDICAL', 'Non-Medical'),
    ]

    class_level = models.CharField(max_length=20, choices=CLASS_LEVEL_CHOICES, default='1')
    section = models.CharField(max_length=1, choices=SECTION_CHOICES, default='A')
    stream = models.CharField(max_length=20, choices=STREAM_CHOICES, null=True, blank=True)
    teachers = models.ManyToManyField(User, related_name='classes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        if self.class_level in ['11', '12']:
            return f"{self.get_class_level_display()} {self.get_section_display()} - {self.get_stream_display()}"
        return f"{self.get_class_level_display()} {self.get_section_display()}"

class Student(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    # Basic Student Information
    name = models.CharField(max_length=100)
    roll_number = models.CharField(max_length=20)
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='students')
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='M')
    aadhar_number = models.CharField(max_length=12, unique=True, help_text="12-digit Aadhar number", null=True, blank=True)
    
    # Contact Information
    address = models.TextField(null=True, blank=True)
    
    # Parent/Guardian Information
    father_name = models.CharField(max_length=100, null=True, blank=True)
    mother_name = models.CharField(max_length=100, null=True, blank=True)
    parent_mobile = models.CharField(max_length=15, help_text="Primary contact number", null=True, blank=True)
    alternate_mobile = models.CharField(max_length=15, blank=True, null=True, help_text="Alternative contact number")
    parent_email = models.EmailField(blank=True, null=True)
    
    # Additional Information
    admission_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['class_name', 'roll_number']
        unique_together = ['class_name', 'roll_number']
    
    def __str__(self):
        return f"{self.name} ({self.roll_number})"

class Test(models.Model):
    SUBJECT_CHOICES = [
        ('math', 'Mathematics'),
        ('science', 'Science'),
        ('english', 'English'),
        ('hindi', 'Hindi'),
        ('social', 'Social Studies'),
        ('computer', 'Computer Science'),
    ]

    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES)
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='tests')
    total_marks = models.IntegerField()
    time_limit = models.IntegerField(help_text="Time limit in minutes", default=60)
    date = models.DateField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.class_name}"

class Question(models.Model):
    test = models.ForeignKey('Test', on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    option1 = models.CharField(max_length=200)
    option2 = models.CharField(max_length=200)
    option3 = models.CharField(max_length=200)
    option4 = models.CharField(max_length=200)
    correct_option = models.IntegerField(choices=[(1, 'Option 1'), (2, 'Option 2'), (3, 'Option 3'), (4, 'Option 4')])
    marks = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Question for {self.test.title}"

class QuestionAttempt(models.Model):
    test_attempt = models.ForeignKey('TestAttempt', on_delete=models.CASCADE, related_name='question_attempts')
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    selected_option = models.IntegerField(choices=[(1, 'Option 1'), (2, 'Option 2'), (3, 'Option 3'), (4, 'Option 4')], null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    marks_obtained = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('test_attempt', 'question')

    def __str__(self):
        return f"{self.test_attempt.student.name} - {self.question.test.title}"

class TestAttempt(models.Model):
    test = models.ForeignKey('Test', on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='test_attempts')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    score = models.IntegerField(null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    time_taken = models.IntegerField(help_text="Time taken in minutes", null=True, blank=True)

    class Meta:
        unique_together = ('test', 'student')

    def __str__(self):
        return f"{self.student.name} - {self.test.title} ({self.score}/{self.test.total_marks})"

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    status = models.BooleanField(default=False)  # True for present, False for absent
    created_at = models.DateTimeField(auto_now_add=True)
    marked_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['student', 'date']
    
    def __str__(self):
        return f"{self.student.name} - {self.date}"

class TestResult(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    marks_obtained = models.IntegerField()
    time_taken = models.IntegerField(help_text="Time taken in minutes", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('test', 'student')

    def __str__(self):
        return f"{self.student.name} - {self.test.title}"
