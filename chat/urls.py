"""
URL configuration for the chat app.
"""

from django.urls import path
from . import views

urlpatterns = [
    path("", views.upload_view, name="upload_page"),
    path("chat/", views.chat_view, name="chat_page"),
    path("reset/", views.reset_view, name="reset_page"),
    path("api/chat/", views.chat_api, name="chat_api"),
]
