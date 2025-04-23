import os
import sys

# Add your project directory to the sys.path
path = '/home/<your-pythonanywhere-username>/school_manage_system'
if path not in sys.path:
    sys.path.append(path)

# Set environment variables
os.environ['DJANGO_SETTINGS_MODULE'] = 'school_attendance.production_settings'
os.environ['PYTHONPATH'] = path

# Production environment variables
os.environ['DJANGO_SECRET_KEY'] = '5h%uxgn6&+f+3mbs9_k6&jysg$^n16s9@op=%dk6@n81_$^d-%'
os.environ['DB_NAME'] = '<your-pythonanywhere-username>$school_db'
os.environ['DB_USER'] = '<your-pythonanywhere-username>'
os.environ['DB_PASSWORD'] = '<your-mysql-password>'
os.environ['DB_HOST'] = '<your-pythonanywhere-username>.mysql.pythonanywhere-services.com'

# Import your Django project
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
