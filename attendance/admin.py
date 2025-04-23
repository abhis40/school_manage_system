from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Class, Student

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_admin', 'is_teacher')
    list_filter = ('is_admin', 'is_teacher')
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('is_admin', 'is_teacher')}),
    )

class ClassAdmin(admin.ModelAdmin):
    list_display = ('get_class_name', 'get_teachers', 'created_at')
    list_filter = ('class_level', 'section', 'stream', 'teachers')
    search_fields = ('class_level', 'section', 'stream', 'teachers__username')
    filter_horizontal = ('teachers',)
    
    class Media:
        js = ('admin/js/class_admin.js',)

    def get_class_name(self, obj):
        return str(obj)
    get_class_name.short_description = 'Class'
    
    def get_teachers(self, obj):
        return ", ".join([teacher.username for teacher in obj.teachers.all()])
    get_teachers.short_description = 'Teachers'

class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'roll_number', 'class_name', 'gender', 'parent_mobile')
    list_filter = ('class_name', 'gender', 'admission_date')
    search_fields = ('name', 'roll_number', 'aadhar_number', 'father_name', 'mother_name', 'parent_mobile')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'roll_number', 'class_name', 'date_of_birth', 'gender')
        }),
        ('Identity Information', {
            'fields': ('aadhar_number',)
        }),
        ('Contact Information', {
            'fields': ('address',)
        }),
        ('Parent/Guardian Information', {
            'fields': ('father_name', 'mother_name', 'parent_mobile', 'alternate_mobile', 'parent_email')
        }),
    )
    
    ordering = ['class_name', 'roll_number']

admin.site.register(User, CustomUserAdmin)
admin.site.register(Class, ClassAdmin)
admin.site.register(Student, StudentAdmin)
