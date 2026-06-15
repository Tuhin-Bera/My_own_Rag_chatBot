"""
Authentication views — Login, Signup, Logout.
These views handle user registration and session creation so each user has their own environment.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages


def login_view(request):
    """
    Handle user login.
    This view authenticates a user with their username and password.
    If successful, it creates a session for the user so they stay logged in.
    """
    # If the user is already logged in, we don't need them to log in again.
    # Redirect them directly to the main upload page.
    if request.user.is_authenticated:
        return redirect("upload_page")

    # If the request method is POST, it means the user submitted the login form.
    if request.method == "POST":
        # Extract the username and password from the form data (POST body)
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # Basic validation: ensure both fields are provided
        if not username or not password:
            messages.error(request, "Please fill in all fields.")
            return render(request, "chat/login.html")

        # The 'authenticate' function checks the database to see if the username
        # and password match an existing user record.
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # If a user is found, 'login' attaches the user to the current session.
            login(request, user)
            
            # Often, if a user tries to access a protected page, they are redirected
            # to the login page with a 'next' URL parameter. After logging in,
            # we send them back to that original page. If 'next' is missing,
            # we default to the 'upload_page'.
            next_url = request.GET.get("next", "upload_page")
            return redirect(next_url)
        else:
            # If authenticate() returns None, the credentials were wrong.
            messages.error(request, "Invalid username or password.")

    # If the request is GET (or if login failed), render the login HTML page.
    return render(request, "chat/login.html")


def signup_view(request):
    """
    Handle user registration.
    This view takes user details, validates them, and creates a new User in the database.
    """
    # If already logged in, redirect them away from the signup page.
    if request.user.is_authenticated:
        return redirect("upload_page")

    # When the user submits the registration form...
    if request.method == "POST":
        # Retrieve all fields submitted via the signup form.
        full_name = request.POST.get("full_name", "").strip()
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")

        # Validation phase: accumulate errors in a list.
        errors = []
        if not all([full_name, username, email, password, password2]):
            errors.append("All fields are required.")
        if password != password2:
            errors.append("Passwords do not match.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
            
        # Check if the chosen username or email already exists in the database.
        if User.objects.filter(username=username).exists():
            errors.append("Username is already taken.")
        if User.objects.filter(email=email).exists():
            errors.append("An account with this email already exists.")

        # If we found any errors during validation, show them to the user.
        if errors:
            for err in errors:
                # 'messages.error' allows us to pass temporary flash messages to the template.
                messages.error(request, err)
            # Re-render the form, keeping the data they already typed in (except passwords).
            return render(request, "chat/signup.html", {
                "form_data": {
                    "full_name": full_name,
                    "username": username,
                    "email": email,
                }
            })

        # If validation passes, we can create the user.
        # Split the full name into a first name and a last name.
        first_name = full_name.split()[0] if full_name else ""
        last_name = " ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else ""

        # create_user automatically hashes the password for security before saving it.
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        
        # Log the newly registered user in automatically.
        login(request, user)
        messages.success(request, f"Welcome, {first_name}! Your account has been created.")
        
        # Redirect them to the main application page.
        return redirect("upload_page")

    # For a GET request, just display the empty signup form.
    return render(request, "chat/signup.html")


def logout_view(request):
    """
    Log the user out.
    This destroys the user's session cookie and logs them out of the system.
    """
    logout(request)
    # Redirect back to the login screen after logging out.
    return redirect("login")
