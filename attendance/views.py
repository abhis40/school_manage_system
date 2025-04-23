from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from .models import User, Class, Student, Attendance, Test, TestResult, Question, TestAttempt, QuestionAttempt
from .forms import UserLoginForm, ClassForm, StudentForm, TestForm, TestResultForm, QuestionFormSet, StudentLoginForm, TestAttemptForm, QuestionForm
from django.utils import timezone
from django.db.models import Count, Q
from collections import defaultdict
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
from reportlab.pdfgen import canvas
from django.forms import formset_factory
from django.core.serializers.json import DjangoJSONEncoder
import json

def is_admin(user):
    return user.is_admin or user.is_superuser

def is_teacher(user):
    return user.is_teacher

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_admin:
            return redirect('admin:index')  # Redirect to Django admin interface
        elif request.user.is_teacher:
            return redirect('teacher_dashboard')
        else:
            messages.error(request, 'You do not have permission to access this system.')
            return redirect('logout')
    
    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # Set is_admin flag for superusers if not already set
            if user.is_superuser and not user.is_admin:
                user.is_admin = True
                user.save()
            
            login(request, user)
            if user.is_superuser or user.is_admin:
                return redirect('admin:index')  # Redirect to Django admin interface
            elif user.is_teacher:
                return redirect('teacher_dashboard')
            else:
                messages.error(request, 'You do not have permission to access this system.')
                return redirect('logout')
    else:
        form = UserLoginForm()
    
    return render(request, 'attendance/login.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    classes = Class.objects.all()
    teachers = User.objects.filter(is_teacher=True)
    students = Student.objects.all()
    context = {
        'classes': classes,
        'teachers': teachers,
        'students': students,
    }
    return render(request, 'attendance/admin_dashboard.html', context)

@login_required
@user_passes_test(is_teacher)
def teacher_dashboard(request):
    # Get teacher's classes
    classes = Class.objects.filter(teachers=request.user)
    
    # Calculate total students across all classes
    total_students = sum(class_obj.students.count() for class_obj in classes)
    
    # Get recent tests
    recent_tests = Test.objects.filter(created_by=request.user).order_by('-date')[:5]
    
    # Get test attempts for each test
    test_attempts = {}
    for test in recent_tests:
        attempts = TestAttempt.objects.filter(test=test, is_completed=True).select_related('student')
        test_attempts[test.id] = {
            'total_students': test.class_name.students.count(),
            'attempted_students': attempts.count(),
            'attempts': attempts
        }
    
    # Get current year for footer
    current_year = timezone.now().year
    
    return render(request, 'attendance/teacher_dashboard.html', {
        'classes': classes,
        'recent_tests': recent_tests,
        'test_attempts': test_attempts,
        'current_year': current_year,
        'total_students': total_students
    })

@login_required
@user_passes_test(is_admin)
def add_class(request):
    if request.method == 'POST':
        form = ClassForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Class added successfully')
            return redirect('admin_dashboard')
    else:
        form = ClassForm()
    return render(request, 'attendance/add_class.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def add_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student added successfully')
            return redirect('admin_dashboard')
    else:
        form = StudentForm()
    return render(request, 'attendance/add_student.html', {'form': form})

@login_required
@user_passes_test(is_teacher)
def take_attendance(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id, teachers=request.user)
    students = Student.objects.filter(class_name=class_obj).order_by('roll_number')
    today = timezone.now().date()
    
    # Initialize attendance_status dictionary
    attendance_status = {}
    
    # Get existing attendance for today
    for student in students:
        attendance = Attendance.objects.filter(
            student=student,
            date=today
        ).first()
        attendance_status[student.id] = attendance.status if attendance else False
    
    if request.method == 'POST':
        date = request.POST.get('date', today)
        for student in students:
            status = request.POST.get(f'student_{student.id}') == 'present'
            
            # Check if attendance record already exists
            attendance, created = Attendance.objects.get_or_create(
                student=student,
                date=date,
                defaults={
                    'status': status,
                    'marked_by': request.user
                }
            )
            
            # If record exists, update it
            if not created:
                attendance.status = status
                attendance.marked_by = request.user
                attendance.save()
        
        messages.success(request, 'Attendance marked successfully')
        return redirect('teacher_dashboard')
    
    return render(request, 'attendance/take_attendance.html', {
        'class_obj': class_obj,
        'class_name': str(class_obj),
        'students': students,
        'today_date': today,
        'attendance_status': attendance_status
    })

@login_required
@user_passes_test(is_teacher)
def attendance_history(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id, teachers=request.user)
    students = Student.objects.filter(class_name=class_obj).order_by('roll_number')
    
    # Get all attendance records for this class
    attendance_records = Attendance.objects.filter(student__class_name=class_obj).order_by('-date')
    
    # Group attendance by date
    attendance_history = {}
    total_percentage = 0
    total_days = 0
    
    for record in attendance_records:
        date_str = record.date.strftime('%Y-%m-%d')
        if date_str not in attendance_history:
            attendance_history[date_str] = {
                'date': record.date.strftime('%Y-%m-%d'),
                'display_date': record.date.strftime('%b %d, %Y'),
                'records': [],
                'present_count': 0,
                'total_count': 0,
                'percentage': 0
            }
        
        attendance_history[date_str]['records'].append({
            'student': str(record.student),
            'status': record.status,
            'marked_by': str(record.marked_by)
        })
        
        if record.status:
            attendance_history[date_str]['present_count'] += 1
        attendance_history[date_str]['total_count'] += 1
    
    # Calculate attendance percentage for each date and total average
    for date_str, data in attendance_history.items():
        if data['total_count'] > 0:
            data['percentage'] = round((data['present_count'] / data['total_count']) * 100, 1)
            total_percentage += data['percentage']
            total_days += 1
    
    # Calculate average attendance
    average_attendance = round(total_percentage / total_days, 1) if total_days > 0 else 0
    
    # Serialize attendance history to JSON
    attendance_history_json = json.dumps(attendance_history, cls=DjangoJSONEncoder)
    
    context = {
        'class_name': str(class_obj),
        'class_id': class_id,
        'attendance_history': attendance_history,
        'attendance_history_json': attendance_history_json,
        'students': students,
        'average_attendance': average_attendance
    }
    
    return render(request, 'attendance/attendance_history.html', context)

@login_required
@user_passes_test(is_teacher)
def download_attendance_pdf(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id, teachers=request.user)
    students = Student.objects.filter(class_name=class_obj).order_by('roll_number')
    
    # Get date range from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Get all attendance records for this class
    attendance_records = Attendance.objects.filter(student__class_name=class_obj)
    
    # Apply date filtering if provided
    if start_date:
        attendance_records = attendance_records.filter(date__gte=start_date)
    if end_date:
        attendance_records = attendance_records.filter(date__lte=end_date)
    
    attendance_records = attendance_records.order_by('-date')
    
    # Group attendance by date
    attendance_by_date = {}
    for record in attendance_records:
        date_str = record.date.strftime('%Y-%m-%d')
        if date_str not in attendance_by_date:
            attendance_by_date[date_str] = {
                'date': record.date,
                'display_date': record.date.strftime('%b %d, %Y'),
                'records': {},
                'present_count': 0,
                'total_count': 0,
                'percentage': 0
            }
        
        attendance_by_date[date_str]['records'][record.student.id] = {
            'student': record.student,
            'status': record.status
        }
        
        if record.status:
            attendance_by_date[date_str]['present_count'] += 1
        attendance_by_date[date_str]['total_count'] += 1
    
    # Calculate attendance percentage for each date
    for date_str, data in attendance_by_date.items():
        if data['total_count'] > 0:
            data['percentage'] = (data['present_count'] / data['total_count']) * 100
    
    # Create the PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="attendance_report_{class_obj}.pdf"'
    
    # Create the PDF object
    p = canvas.Canvas(response)
    
    # Add title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 800, f"Attendance Report - {class_obj}")
    
    # Add date range if provided
    p.setFont("Helvetica", 12)
    if start_date and end_date:
        p.drawString(50, 770, f"Date Range: {start_date} to {end_date}")
    elif start_date:
        p.drawString(50, 770, f"From: {start_date}")
    elif end_date:
        p.drawString(50, 770, f"Until: {end_date}")
    
    # Add current date
    p.drawString(50, 750, f"Generated on: {timezone.now().strftime('%b %d, %Y')}")
    
    # Add table headers
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, 720, "Date")
    p.drawString(200, 720, "Present")
    p.drawString(300, 720, "Absent")
    p.drawString(400, 720, "Percentage")
    
    # Add table data
    y = 700
    p.setFont("Helvetica", 10)
    for date_str, data in attendance_by_date.items():
        if y < 50:  # Start a new page if we're running out of space
            p.showPage()
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, 800, f"Attendance Report - {class_obj} (continued)")
            p.setFont("Helvetica", 10)
            y = 750
        
        p.drawString(50, y, data['display_date'])
        p.drawString(200, y, str(data['present_count']))
        p.drawString(300, y, str(data['total_count'] - data['present_count']))
        p.drawString(400, y, f"{data['percentage']:.1f}%")
        y -= 20
    
    # Add student details section
    p.showPage()
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 800, f"Student Details - {class_obj}")
    
    # Add table headers
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, 770, "Roll No.")
    p.drawString(150, 770, "Name")
    p.drawString(300, 770, "Gender")
    p.drawString(400, 770, "Parent Contact")
    
    # Add student data
    y = 750
    p.setFont("Helvetica", 10)
    for student in students:
        if y < 50:  # Start a new page if we're running out of space
            p.showPage()
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, 800, f"Student Details - {class_obj} (continued)")
            p.setFont("Helvetica", 10)
            y = 750
        
        p.drawString(50, y, student.roll_number)
        p.drawString(150, y, student.name)
        p.drawString(300, y, student.get_gender_display())
        p.drawString(400, y, student.parent_mobile or "N/A")
        y -= 20
    
    # Save the PDF
    p.showPage()
    p.save()
    
    return response

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')

@login_required
def create_test(request):
    if not request.user.is_teacher:
        return redirect('login')
    
    if request.method == 'POST':
        test_form = TestForm(request.POST, user=request.user)
        question_formset = QuestionFormSet(request.POST, prefix='questions')
        
        if test_form.is_valid() and question_formset.is_valid():
            # Get selected class option
            class_choice = test_form.cleaned_data.get('classes')
            
            # Get all teacher's classes if General is selected, otherwise get the specific class
            if class_choice == 'general':
                selected_classes = Class.objects.filter(teachers=request.user)
            else:
                try:
                    selected_class = Class.objects.get(id=int(class_choice), teachers=request.user)
                    selected_classes = [selected_class]
                except (Class.DoesNotExist, ValueError):
                    messages.error(request, 'Invalid class selection.')
                    return redirect('create_test')
            
            # Create test for each selected class
            for class_obj in selected_classes:
                test = test_form.save(commit=False)
                test.created_by = request.user
                test.class_name = class_obj
                test.save()
                
                # Create questions
                for form in question_formset:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        question = form.save(commit=False)
                        question.test = test
                        question.save()
                
                # Debug print to verify test creation
                print(f"Created test '{test.title}' for class '{class_obj}'")
            
            messages.success(request, 'Test created successfully!')
            return redirect('teacher_dashboard')
        else:
            # Print form errors for debugging
            print("Test Form Errors:", test_form.errors)
            print("Question Formset Errors:", question_formset.errors)
            messages.error(request, 'Please correct the errors below.')
    else:
        test_form = TestForm(user=request.user)
        question_formset = QuestionFormSet(prefix='questions')
    
    return render(request, 'attendance/create_test.html', {
        'test_form': test_form,
        'question_formset': question_formset,
    })

@login_required
@user_passes_test(is_teacher)
def test_results(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    
    # Get the selected class from the URL parameter
    class_id = request.GET.get('class_id')
    if class_id:
        try:
            selected_class = Class.objects.get(id=class_id, teachers=request.user)
            # Update the test's class for this view
            test.class_name = selected_class
        except Class.DoesNotExist:
            messages.error(request, 'Invalid class selected')
            return redirect('test_results', test_id=test_id)
    
    # Get all classes for the teacher
    classes = Class.objects.filter(teachers=request.user)
    
    # Get all students in the test's class
    students = Student.objects.filter(class_name=test.class_name).order_by('roll_number')
    
    # Get all completed test attempts
    attempts = TestAttempt.objects.filter(
        test=test,
        is_completed=True
    ).select_related('student').order_by('student__roll_number')
    
    # Create a dictionary of attempts keyed by student ID
    attempts_dict = {attempt.student.id: attempt for attempt in attempts}
    
    # Calculate percentage for any attempts that don't have it
    for attempt in attempts:
        if attempt.percentage is None and test.total_marks > 0:
            attempt.percentage = round((float(attempt.score) / test.total_marks) * 100, 2)
            attempt.save()
    
    # Calculate statistics for current class
    total_students = students.count()
    attempted_students = attempts.count()
    average_score = 0
    highest_score = 0
    lowest_score = test.total_marks
    
    if attempts:
        total_score = sum(attempt.score for attempt in attempts)
        average_score = round(total_score / len(attempts), 2)
        highest_score = max(attempt.score for attempt in attempts)
        lowest_score = min(attempt.score for attempt in attempts)
    
    # Calculate statistics for all classes
    class_stats = {}
    for class_obj in classes:
        class_students = Student.objects.filter(class_name=class_obj).count()
        class_attempts = TestAttempt.objects.filter(
            test=test,
            student__class_name=class_obj,
            is_completed=True
        )
        class_attempted = class_attempts.count()
        
        class_average = 0
        class_highest = 0
        if class_attempts:
            total_score = sum(attempt.score for attempt in class_attempts)
            class_average = round(total_score / class_attempted, 2)
            class_highest = max(attempt.score for attempt in class_attempts)
        
        class_stats[class_obj.id] = {
            'name': f"{class_obj.get_class_level_display()} {class_obj.get_section_display()}",
            'total_students': class_students,
            'attempted': class_attempted,
            'average_score': class_average,
            'highest_score': class_highest
        }
    
    return render(request, 'attendance/test_results.html', {
        'test': test,
        'students': students,
        'attempts': attempts_dict,
        'total_students': total_students,
        'attempted_students': attempted_students,
        'average_score': average_score,
        'highest_score': highest_score,
        'lowest_score': lowest_score,
        'classes': classes,
        'selected_class_id': test.class_name.id,
        'class_stats': class_stats
    })

def student_login(request):
    if request.method == 'POST':
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name'].strip()  # Remove any whitespace
            parent_mobile = form.cleaned_data['parent_mobile']
            
            print(f"Attempting login with name: {name}, mobile: {parent_mobile}")  # Debug print
            
            try:
                # Case-insensitive name search
                students = Student.objects.filter(name__iexact=name)
                print(f"Found {students.count()} students with name: {name}")  # Debug print
                
                if not students.exists():
                    messages.error(request, 'No student found with that name')
                    return render(request, 'attendance/student_login.html', {'form': form})
                
                # Check for exact mobile match
                student = students.get(parent_mobile=parent_mobile)
                print(f"Found matching student: {student}")  # Debug print
                
                request.session['student_id'] = student.id
                request.session['student_name'] = student.name
                messages.success(request, f'Welcome back, {student.name}!')
                return redirect('student_dashboard')
            except Student.DoesNotExist:
                print("No matching student found")  # Debug print
                messages.error(request, 'Invalid parent mobile number')
            except Exception as e:
                print(f"Error during login: {str(e)}")  # Debug print
                messages.error(request, 'An error occurred. Please try again.')
        else:
            print(f"Form errors: {form.errors}")  # Debug print
            messages.error(request, 'Please enter valid credentials')
    else:
        form = StudentLoginForm()
    
    return render(request, 'attendance/student_login.html', {'form': form})

def student_dashboard(request):
    if 'student_id' not in request.session:
        messages.error(request, 'Please login first')
        return redirect('student_login')
    
    try:
        student = get_object_or_404(Student, id=request.session['student_id'])
        
        # Get available tests (tests that haven't been attempted)
        available_tests = Test.objects.filter(
            Q(class_name=student.class_name) |  # Tests for student's class
            Q(class_name__class_level='General', class_name__section='All Classes'),  # Tests for all classes
            date__gte=timezone.now().date()  # Only upcoming tests
        ).exclude(
            attempts__student=student  # Exclude tests already attempted
        ).order_by('date')
        
        # Debug print for available tests
        print(f"Available tests query: {available_tests.query}")
        print(f"Found {available_tests.count()} available tests for student {student.name}")
        
        # Get previous test attempts
        previous_attempts = TestAttempt.objects.filter(
            student=student,
            is_completed=True
        ).select_related('test').order_by('-start_time')
        
        # Calculate percentage for each attempt
        for attempt in previous_attempts:
            if attempt.test.total_marks > 0:
                attempt.percentage = round((attempt.score / attempt.test.total_marks) * 100, 2)
            else:
                attempt.percentage = 0
        
        # Calculate attendance statistics
        total_attendance = Attendance.objects.filter(student=student).count()
        present_attendance = Attendance.objects.filter(student=student, status=True).count()
        attendance_percentage = round((present_attendance / total_attendance * 100), 2) if total_attendance > 0 else 0
        
        # Calculate performance statistics
        total_tests = previous_attempts.count()
        total_marks_obtained = sum(attempt.score for attempt in previous_attempts)
        total_possible_marks = sum(attempt.test.total_marks for attempt in previous_attempts)
        overall_performance = round((total_marks_obtained / total_possible_marks * 100), 2) if total_possible_marks > 0 else 0
        
        # Get subject-wise performance
        subject_performance = {}
        for attempt in previous_attempts:
            subject = attempt.test.get_subject_display()
            if subject not in subject_performance:
                subject_performance[subject] = {
                    'total_marks': 0,
                    'obtained_marks': 0,
                    'tests_count': 0
                }
            subject_performance[subject]['total_marks'] += attempt.test.total_marks
            subject_performance[subject]['obtained_marks'] += attempt.score
            subject_performance[subject]['tests_count'] += 1
        
        # Calculate percentage for each subject
        for subject in subject_performance:
            total = subject_performance[subject]['total_marks']
            obtained = subject_performance[subject]['obtained_marks']
            subject_performance[subject]['percentage'] = round((obtained / total * 100), 2) if total > 0 else 0
        
        return render(request, 'attendance/student_dashboard.html', {
            'student': student,
            'available_tests': available_tests,
            'previous_attempts': previous_attempts,
            'attendance_percentage': attendance_percentage,
            'overall_performance': overall_performance,
            'subject_performance': subject_performance,
            'total_tests': total_tests,
            'total_marks_obtained': total_marks_obtained,
            'total_possible_marks': total_possible_marks
        })
    except Exception as e:
        print(f"Error in student dashboard: {str(e)}")
        messages.error(request, 'An error occurred while loading the dashboard.')
        return redirect('student_login')

def attempt_test(request, test_id):
    if 'student_id' not in request.session:
        return redirect('student_login')
    
    student = get_object_or_404(Student, id=request.session['student_id'])
    test = get_object_or_404(Test, id=test_id)
    
    # Check if student has already attempted the test
    if TestAttempt.objects.filter(student=student, test=test).exists():
        messages.error(request, 'You have already attempted this test')
        return redirect('student_dashboard')
    
    # Check if test is for student's class or if student is in any of the teacher's classes
    if test.class_name != student.class_name and not Class.objects.filter(teachers=test.created_by, students=student).exists():
        messages.error(request, 'This test is not for your class')
        return redirect('student_dashboard')
    
    # Get all questions for the test
    questions = Question.objects.filter(test=test)
    
    if request.method == 'POST':
        # Create test attempt
        test_attempt = TestAttempt.objects.create(
            test=test,
            student=student,
            is_completed=True,
            end_time=timezone.now()
        )
        
        # Check if student exited fullscreen
        fullscreen_exit = request.POST.get('fullscreen_exit') == 'true'
        
        # Calculate score (0 if fullscreen was exited)
        total_score = 0
        if not fullscreen_exit:
            for question in questions:
                selected_option = request.POST.get(f'question_{question.id}')
                if selected_option:
                    selected_option = int(selected_option)
                    is_correct = selected_option == question.correct_option
                    marks_obtained = question.marks if is_correct else 0
                    total_score += marks_obtained
                
                # Create question attempt
                QuestionAttempt.objects.create(
                    test_attempt=test_attempt,
                    question=question,
                    selected_option=selected_option,
                    is_correct=is_correct,
                    marks_obtained=marks_obtained
                )
        
        # Update test attempt with score and percentage
        test_attempt.score = total_score
        if test.total_marks > 0:
            test_attempt.percentage = round((float(total_score) / test.total_marks) * 100, 2)
        test_attempt.save()
        
        if fullscreen_exit:
            messages.warning(request, 'Test submitted with 0 marks due to fullscreen exit or tab switch.')
        else:
            messages.success(request, 'Test submitted successfully!')
        return redirect('student_dashboard')
    
    return render(request, 'attendance/attempt_test.html', {
        'test': test,
        'questions': questions
    })

def student_logout(request):
    if 'student_id' in request.session:
        del request.session['student_id']
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')

@login_required
@user_passes_test(is_teacher)
def delete_test(request, test_id):
    try:
        # Get the test and verify ownership
        test = get_object_or_404(Test, id=test_id)
        if test.created_by != request.user:
            messages.error(request, 'You do not have permission to delete this test.')
            return redirect('teacher_dashboard')
        
        if request.method == 'POST':
            print(f"Deleting test: {test.title} (ID: {test.id})")  # Debug print
            
            # Delete related test attempts and results first
            TestAttempt.objects.filter(test=test).delete()
            TestResult.objects.filter(test=test).delete()
            
            # Delete the test itself
            test.delete()
            
            messages.success(request, f'Test "{test.title}" has been deleted successfully.')
        else:
            messages.error(request, 'Invalid request method.')
            
    except Exception as e:
        print(f"Error deleting test: {str(e)}")  # Debug print
        messages.error(request, f'Error deleting test: {str(e)}')
    
    return redirect('teacher_dashboard')
