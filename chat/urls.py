"""
URL configuration for the chat app.
This file defines the routing within the main chat application.
It maps URLs (like /chat/ or /api/chat/) to the functions (views) in views.py that handle them.
"""

from django.urls import path
from . import views

urlpatterns = [
    # The home page where users upload their PDFs.
    # When a user visits the root of this app (""), the upload_view function handles it.
    path("", views.upload_view, name="upload_page"),
    
    # The actual chat interface page.
    path("chat/", views.chat_view, name="chat_page"),
    
    # URL to reset the current session (deletes the vector db and uploaded files).
    path("reset/", views.reset_view, name="reset_page"),
    
    # The API endpoint that the frontend JavaScript calls to ask a question.
    # It receives the question in JSON format and returns the LLM's answer.
    path("api/chat/", views.chat_api, name="chat_api"),
]
