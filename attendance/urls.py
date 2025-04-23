from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('teacher-dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('take-attendance/<int:class_id>/', views.take_attendance, name='take_attendance'),
    path('attendance-history/<int:class_id>/', views.attendance_history, name='attendance_history'),
    path('download-attendance/<int:class_id>/', views.download_attendance_pdf, name='download_attendance_pdf'),
    path('create-test/', views.create_test, name='create_test'),
    path('test-results/<int:test_id>/', views.test_results, name='test_results'),
    path('student-login/', views.student_login, name='student_login'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('attempt-test/<int:test_id>/', views.attempt_test, name='attempt_test'),
    path('student-logout/', views.student_logout, name='student_logout'),
    path('test/<int:test_id>/delete/', views.delete_test, name='delete_test'),
] 