#la_pontificia_horarios/wsgi.py
"""
WSGI config for la_pontificia_horarios project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'la_pontificia_horarios.settings')

application = get_wsgi_application()
