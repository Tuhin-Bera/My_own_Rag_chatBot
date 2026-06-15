"""
URL configuration for rag_chatbot project.
This is the master routing file for the entire Django project.
It decides which app's urls.py should handle a given web request.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # The built-in Django admin interface for managing users and database tables.
    path("admin/", admin.site.urls),
    
    # Any URL starting with "auth/" (e.g. /auth/login/) is handed off to the chat app's auth_urls.py
    path("auth/", include("chat.auth_urls")),
    
    # Any other URL is handed off to the chat app's main urls.py
    path("", include("chat.urls")),
]

# When running in development mode (DEBUG=True), this tells Django to serve 
# uploaded media files (like PDFs) from the MEDIA_ROOT directory directly.
# In production, a web server like Nginx or WhiteNoise handles this instead.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
