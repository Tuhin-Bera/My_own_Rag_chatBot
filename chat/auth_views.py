"""
Authentication views — Login, Signup, Logout.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages


def login_view(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect("upload_page")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if not username or not password:
            messages.error(request, "Please fill in all fields.")
            return render(request, "chat/login.html")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Redirect to 'next' param or default
            next_url = request.GET.get("next", "upload_page")
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "chat/login.html")


def signup_view(request):
    """Handle user registration."""
    if request.user.is_authenticated:
        return redirect("upload_page")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")

        # Validation
        errors = []
        if not all([full_name, username, email, password, password2]):
            errors.append("All fields are required.")
        if password != password2:
            errors.append("Passwords do not match.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if User.objects.filter(username=username).exists():
            errors.append("Username is already taken.")
        if User.objects.filter(email=email).exists():
            errors.append("An account with this email already exists.")

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, "chat/signup.html", {
                "form_data": {
                    "full_name": full_name,
                    "username": username,
                    "email": email,
                }
            })

        # Create user
        first_name = full_name.split()[0] if full_name else ""
        last_name = " ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else ""

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        login(request, user)
        messages.success(request, f"Welcome, {first_name}! Your account has been created.")
        return redirect("upload_page")

    return render(request, "chat/signup.html")


def logout_view(request):
    """Log the user out."""
    logout(request)
    return redirect("login")
