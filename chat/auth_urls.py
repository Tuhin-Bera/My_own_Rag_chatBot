"""
Authentication URL configuration.
This file defines the routing specifically for user authentication.
It maps URLs (like /login/ or /signup/) to the functions (views) in auth_views.py.
"""

from django.urls import path
from . import auth_views

urlpatterns = [
    # Route for the login page
    path("login/", auth_views.login_view, name="login"),
    
    # Route for the signup/registration page
    path("signup/", auth_views.signup_view, name="signup"),
    
    # Route to log the user out and redirect them
    path("logout/", auth_views.logout_view, name="logout"),
]
