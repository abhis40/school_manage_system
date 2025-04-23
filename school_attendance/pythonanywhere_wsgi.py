import os
import sys

# Add your project directory to the sys.path
path = '/home/<your-pythonanywhere-username>/school_manage_system'
if path not in sys.path:
    sys.path.append(path)

# Set environment variables
os.environ['DJANGO_SETTINGS_MODULE'] = 'school_attendance.production_settings'
os.environ['PYTHONPATH'] = path

# Import your Django project
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
