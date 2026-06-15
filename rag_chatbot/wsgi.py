"""
WSGI config for rag_chatbot project.

WSGI (Web Server Gateway Interface) is the standard interface between Python 
web applications and web servers (like Gunicorn, Apache, or Nginx).
This file exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
from django.core.wsgi import get_wsgi_application

# Tell the server which settings file to use for this Django application.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rag_chatbot.settings")

# Get the WSGI application object that the server will use to communicate with Django.
application = get_wsgi_application()
